#!/usr/bin/env python3
"""
Add NDVI Vegetation Health Trend to Coastal ANP Files
=====================================================

Computes the linear trend in annual mean NDVI from 2000 to 2023 for
each coastal ANP using MODIS MOD13A2 (16-day NDVI composite, 1km).

A negative trend indicates vegetation decline / ecosystem degradation.

Data source:
- MODIS/061/MOD13A2 (Terra NDVI 16-day, 1km resolution)

Output dataset_type: ndvi_trend

Usage:
    python3 add_ndvi_trend.py              # Process all coastal ANPs
    python3 add_ndvi_trend.py --test       # Test with first 3 coastal ANPs
    python3 add_ndvi_trend.py --no-db      # JSON-only mode (no database)
    python3 add_ndvi_trend.py "sian_ka_an" # Process single ANP
"""

import ee
import json
import os
import sys
import time
from datetime import datetime

# Use shared auth helper
try:
    from gee_auth import init_ee
except ImportError:
    def init_ee():
        ee.Initialize(project='gen-lang-client-0866285082')

# Database support
try:
    from db.db_utils import upsert_dataset, export_anp_to_json
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False

DATA_DIR = 'anp_data'
COASTAL_ANPS_FILE = 'coastal_anps_subset.json'

# GEE Dataset
MODIS_NDVI = 'MODIS/061/MOD13A2'
NDVI_BAND = 'NDVI'
NDVI_SCALE = 0.0001  # MODIS NDVI scale factor

# Analysis parameters
START_YEAR = 2000
END_YEAR = 2023
EARLY_START = 2000
EARLY_END = 2005
LATE_START = 2018
LATE_END = 2023


def load_coastal_anps():
    """Load list of coastal ANP IDs from the subset file."""
    with open(COASTAL_ANPS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('anp_ids_with_data', data.get('anp_ids', []))


def load_anp_data(anp_id):
    """Load an ANP's data JSON file."""
    data_file = os.path.join(DATA_DIR, f'{anp_id}_data.json')
    if not os.path.exists(data_file):
        return None
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_anp_boundary(anp_id):
    """Load an ANP's boundary GeoJSON file."""
    boundary_file = os.path.join(DATA_DIR, f'{anp_id}_boundary.geojson')
    if not os.path.exists(boundary_file):
        return None
    with open(boundary_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_geometry(anp_data, boundary_geojson):
    """Get ee.Geometry from boundary or bounds."""
    # Prefer boundary GeoJSON (more precise)
    if boundary_geojson:
        try:
            if boundary_geojson['type'] == 'FeatureCollection':
                features = boundary_geojson.get('features', [])
                if features:
                    geom = features[0]['geometry']
                else:
                    geom = None
            elif boundary_geojson['type'] == 'Feature':
                geom = boundary_geojson['geometry']
            else:
                geom = boundary_geojson

            if geom:
                if geom['type'] == 'Polygon':
                    return ee.Geometry.Polygon(geom['coordinates'])
                elif geom['type'] == 'MultiPolygon':
                    return ee.Geometry.MultiPolygon(geom['coordinates'])
                else:
                    return ee.Geometry(geom)
        except Exception:
            pass

    # Fallback to bounds
    bounds = anp_data.get('geometry', {}).get('bounds')
    if bounds:
        return ee.Geometry.Polygon(bounds)

    return None


def compute_annual_ndvi(geometry, year):
    """Compute mean NDVI for a single year over the geometry."""
    start = f'{year}-01-01'
    end = f'{year}-12-31'

    col = (ee.ImageCollection(MODIS_NDVI)
           .filterDate(start, end)
           .select(NDVI_BAND))

    mean_img = col.mean().multiply(NDVI_SCALE)

    stats = mean_img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=1000,  # MODIS native resolution
        maxPixels=1e9,
        bestEffort=True
    )

    return stats.get(NDVI_BAND)


def extract_ndvi_trend(anp_id, geometry):
    """Extract NDVI trend for a single ANP.

    Uses GEE's linearFit reducer for the trend computation,
    and also computes early/late period means.

    Args:
        anp_id: ANP identifier
        geometry: ee.Geometry for the ANP

    Returns:
        dict with NDVI trend data
    """
    result = {
        'data_available': False,
        'extracted_at': datetime.now().isoformat(),
        'source': 'MODIS MOD13A2 v061',
        'resolution_m': 1000,
    }

    try:
        # Build a collection of annual mean NDVI images with a 'year' band
        # for linear regression
        years = list(range(START_YEAR, END_YEAR + 1))
        annual_images = []

        for year in years:
            start = f'{year}-01-01'
            end = f'{year}-12-31'

            annual_mean = (ee.ImageCollection(MODIS_NDVI)
                           .filterDate(start, end)
                           .select(NDVI_BAND)
                           .mean()
                           .multiply(NDVI_SCALE)
                           .rename('ndvi'))

            # Add a 'year' band for linear regression (centered)
            year_img = ee.Image.constant(year - START_YEAR).rename('year').float()
            combined = year_img.addBands(annual_mean)
            annual_images.append(combined)

        annual_col = ee.ImageCollection(annual_images)

        # Compute linear trend using linearFit
        # linearFit expects bands: [independent, dependent]
        trend = annual_col.select(['year', 'ndvi']).reduce(ee.Reducer.linearFit())

        # Get trend stats
        trend_stats = trend.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=1000,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()

        slope = trend_stats.get('scale')  # slope per year
        offset = trend_stats.get('offset')  # intercept

        if slope is None:
            result['error'] = 'No NDVI data available for this area'
            return result

        # Compute early and late period means
        early_years = list(range(EARLY_START, EARLY_END + 1))
        late_years = list(range(LATE_START, LATE_END + 1))

        early_images = []
        for year in early_years:
            img = (ee.ImageCollection(MODIS_NDVI)
                   .filterDate(f'{year}-01-01', f'{year}-12-31')
                   .select(NDVI_BAND)
                   .mean()
                   .multiply(NDVI_SCALE))
            early_images.append(img)

        late_images = []
        for year in late_years:
            img = (ee.ImageCollection(MODIS_NDVI)
                   .filterDate(f'{year}-01-01', f'{year}-12-31')
                   .select(NDVI_BAND)
                   .mean()
                   .multiply(NDVI_SCALE))
            late_images.append(img)

        early_mean = ee.ImageCollection(early_images).mean()
        late_mean = ee.ImageCollection(late_images).mean()

        early_stats = early_mean.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=1000,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()

        late_stats = late_mean.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=1000,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()

        early_ndvi = early_stats.get(NDVI_BAND)
        late_ndvi = late_stats.get(NDVI_BAND)

        # Compute trend per decade
        trend_per_decade = slope * 10

        # Determine direction
        if trend_per_decade > 0.005:
            direction = 'improving'
        elif trend_per_decade < -0.005:
            direction = 'declining'
        else:
            direction = 'stable'

        result.update({
            'data_available': True,
            'mean_ndvi_2000_2005': round(early_ndvi, 4) if early_ndvi is not None else None,
            'mean_ndvi_2018_2023': round(late_ndvi, 4) if late_ndvi is not None else None,
            'trend_per_year': round(slope, 6),
            'trend_per_decade': round(trend_per_decade, 4),
            'trend_direction': direction,
            'period': f'{START_YEAR}-{END_YEAR}',
            'n_years': len(years),
        })

        return result

    except Exception as e:
        result['error'] = str(e)
        return result


def process_anp(anp_id, use_database=True):
    """Process a single coastal ANP for NDVI trend data."""
    anp_data = load_anp_data(anp_id)
    if not anp_data:
        print(f"  {anp_id}: No data file found, skipping")
        return 'skipped'

    name = anp_data.get('metadata', {}).get('name', anp_id)

    # Check if already has ndvi_trend data
    existing = anp_data.get('datasets', {}).get('ndvi_trend', {})
    if existing and existing.get('data_available') and 'error' not in existing:
        print(f"  {name}: Already has NDVI trend data, skipping")
        return 'skipped'

    # Get geometry
    boundary_geojson = load_anp_boundary(anp_id)
    geometry = get_geometry(anp_data, boundary_geojson)

    if not geometry:
        print(f"  {name}: No geometry available, skipping")
        return 'skipped'

    print(f"  {name}: Extracting NDVI trend...", end=" ", flush=True)

    try:
        ndvi_data = extract_ndvi_trend(anp_id, geometry)

        # Save to database if available
        if use_database and HAS_DATABASE:
            upsert_dataset(anp_id, 'ndvi_trend', ndvi_data, source='gee')
            export_anp_to_json(anp_id, DATA_DIR)
        else:
            # Legacy: update JSON file directly
            if 'datasets' not in anp_data:
                anp_data['datasets'] = {}
            anp_data['datasets']['ndvi_trend'] = ndvi_data
            data_file = os.path.join(DATA_DIR, f'{anp_id}_data.json')
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(anp_data, f, indent=2, ensure_ascii=False)

        # Print summary
        if ndvi_data.get('data_available'):
            early = ndvi_data.get('mean_ndvi_2000_2005')
            late = ndvi_data.get('mean_ndvi_2018_2023')
            trend = ndvi_data.get('trend_per_decade')
            direction = ndvi_data.get('trend_direction', '?')
            parts = []
            if early is not None:
                parts.append(f"early={early:.3f}")
            if late is not None:
                parts.append(f"late={late:.3f}")
            if trend is not None:
                parts.append(f"trend={trend:+.4f}/decade")
            parts.append(direction)
            print(f"OK ({', '.join(parts)})")
        else:
            print(f"OK (no data: {ndvi_data.get('error', 'unknown')})")

        return 'success'

    except Exception as e:
        print(f"ERROR: {e}")
        return 'error'


def main():
    print("\n" + "=" * 60)
    print("NDVI Vegetation Health Trend Extraction")
    print("=" * 60)
    print(f"Source: MODIS MOD13A2 v061 ({START_YEAR}-{END_YEAR})")

    init_ee()
    print("GEE initialized")

    # Parse arguments
    args = sys.argv[1:]
    use_database = HAS_DATABASE
    test_mode = False
    single_anp = None

    if '--no-db' in args:
        use_database = False
        args.remove('--no-db')
        print("NO-DB MODE: Saving directly to JSON files")

    if '--test' in args:
        test_mode = True
        args.remove('--test')

    if args:
        single_anp = args[0]

    # Load coastal ANP list
    coastal_ids = load_coastal_anps()
    print(f"Loaded {len(coastal_ids)} coastal ANPs from {COASTAL_ANPS_FILE}")

    if single_anp:
        if single_anp in coastal_ids:
            coastal_ids = [single_anp]
        else:
            matches = [aid for aid in coastal_ids if single_anp.lower() in aid.lower()]
            if matches:
                coastal_ids = matches
                print(f"Matched: {matches}")
            else:
                print(f"ANP '{single_anp}' not found in coastal subset")
                return

    if test_mode:
        coastal_ids = coastal_ids[:3]
        print(f"TEST MODE: Processing first 3 coastal ANPs")

    if use_database:
        print("Mode: Database (source of truth) + JSON export")
    else:
        print("Mode: JSON files only")

    print(f"Processing {len(coastal_ids)} coastal ANPs...\n")

    success = 0
    skipped = 0
    errors = 0

    for i, anp_id in enumerate(coastal_ids, 1):
        if i > 1:
            time.sleep(1.0)

        result = process_anp(anp_id, use_database=use_database)
        if result == 'success':
            success += 1
        elif result == 'skipped':
            skipped += 1
        else:
            errors += 1

    print("\n" + "=" * 60)
    print(f"Complete: {success} updated, {skipped} skipped, {errors} errors")
    print("=" * 60)


if __name__ == '__main__':
    main()
