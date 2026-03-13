#!/usr/bin/env python3
"""
Add Sea Level Rise Data to Coastal ANP Files
=============================================

Extracts three sea level rise metrics for coastal ANPs:

1. Observed SLR trend (mm/year) — from IPCC AR6 SLP 2020 calibrated rate
2. Projected SLR by 2050 (cm) — from IPCC AR6 SLP SSP5-8.5, median
3. Coastal inundation risk (%) — fraction of ANP below 1m elevation (Copernicus DEM)

Data sources:
- IPCC AR6 Sea Level Projections (Medium Confidence): ee.ImageCollection('IPCC/AR6/SLP')
  - total_rates_quantile_0_5: median rate in mm/year
  - total_values_quantile_0_5: median cumulative change in mm
- Copernicus DEM GLO-30: ee.ImageCollection('COPERNICUS/DEM/GLO30')

Note on observed SLR: No satellite altimetry dataset (AVISO, etc.) exists natively in GEE.
HYCOM/sea_surface_elevation has 27K+ images making batch processing impractical.
Instead, the IPCC AR6 SLP 2020 rate is calibrated to observed data and serves as
the best available proxy for the current observed SLR trend in GEE.

Usage:
    python3 add_sea_level_rise.py              # Process all coastal ANPs
    python3 add_sea_level_rise.py --test       # Test with first 3 coastal ANPs
    python3 add_sea_level_rise.py --no-db      # JSON-only mode (no database)
    python3 add_sea_level_rise.py "sian_ka_an" # Process single ANP
"""

import ee
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

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

# GEE Dataset IDs
IPCC_SLP_COLLECTION = 'IPCC/AR6/SLP'
COPERNICUS_DEM_COLLECTION = 'COPERNICUS/DEM/GLO30'

# Bands to extract from IPCC AR6 SLP
RATE_BAND = 'total_rates_quantile_0_5'       # median rate (mm/yr)
RATE_BAND_LOW = 'total_rates_quantile_0_17'  # 17th percentile (likely range low)
RATE_BAND_HIGH = 'total_rates_quantile_0_83' # 83rd percentile (likely range high)
VALUE_BAND = 'total_values_quantile_0_5'     # median cumulative (mm)
VALUE_BAND_LOW = 'total_values_quantile_0_17'
VALUE_BAND_HIGH = 'total_values_quantile_0_83'


def load_coastal_anps():
    """Load list of coastal ANP IDs from the subset file."""
    with open(COASTAL_ANPS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Only include ANPs that have data files
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


def get_centroid_point(data):
    """Get an ee.Geometry.Point from the ANP's centroid."""
    centroid = data.get('geometry', {}).get('centroid')
    if centroid and len(centroid) == 2:
        return ee.Geometry.Point(centroid)
    return None


def get_bounds_geometry(data):
    """Get an ee.Geometry from the ANP's bounds."""
    bounds = data.get('geometry', {}).get('bounds')
    if bounds:
        return ee.Geometry.Polygon(bounds)
    return None


def get_boundary_geometry(boundary_geojson):
    """Convert boundary GeoJSON to an ee.Geometry."""
    if not boundary_geojson:
        return None
    try:
        if boundary_geojson['type'] == 'FeatureCollection':
            features = boundary_geojson.get('features', [])
            if not features:
                return None
            geom = features[0]['geometry']
        elif boundary_geojson['type'] == 'Feature':
            geom = boundary_geojson['geometry']
        else:
            geom = boundary_geojson

        if geom['type'] == 'Polygon':
            return ee.Geometry.Polygon(geom['coordinates'])
        elif geom['type'] == 'MultiPolygon':
            return ee.Geometry.MultiPolygon(geom['coordinates'])
        else:
            return ee.Geometry(geom)
    except Exception as e:
        print(f"    Warning: Could not parse boundary geometry: {e}")
        return None


def extract_slr_rate(centroid_point, buffer_km=50):
    """Extract observed SLR rate from IPCC AR6 SLP at 2020.

    The IPCC AR6 SLP 2020 total_rates represent the current rate of sea level
    change, calibrated to historical observations. This serves as a proxy for
    the "observed" trend since no satellite altimetry dataset exists in GEE.

    Args:
        centroid_point: ee.Geometry.Point near the coast
        buffer_km: Buffer radius in km to search for ocean pixels

    Returns:
        dict with rate info or None
    """
    try:
        slp = ee.ImageCollection(IPCC_SLP_COLLECTION)
        img_2020 = slp.filter(ee.Filter.eq('system:index', 'ssp585_2020')).first()

        bands = [RATE_BAND, RATE_BAND_LOW, RATE_BAND_HIGH]
        buffered = centroid_point.buffer(buffer_km * 1000)

        result = img_2020.select(bands).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=buffered,
            scale=50000,  # IPCC SLP is coarse resolution
            maxPixels=1e6
        ).getInfo()

        rate = result.get(RATE_BAND)
        if rate is not None:
            return {
                'rate_mm_per_year': round(rate, 2),
                'rate_low_mm_per_year': round(result.get(RATE_BAND_LOW, 0), 2),
                'rate_high_mm_per_year': round(result.get(RATE_BAND_HIGH, 0), 2),
                'source': 'IPCC AR6 SLP (2020 calibrated rate)',
                'period': '~1993-2020',
            }

        # If no data at centroid, try larger buffer (ANP might be inland from coast)
        if buffer_km < 200:
            return extract_slr_rate(centroid_point, buffer_km=200)

        return None

    except Exception as e:
        print(f"    Warning: SLR rate extraction failed: {e}")
        return None


def extract_slr_projection(centroid_point, buffer_km=50):
    """Extract projected SLR by 2050 under SSP5-8.5 from IPCC AR6 SLP.

    Args:
        centroid_point: ee.Geometry.Point near the coast
        buffer_km: Buffer radius in km

    Returns:
        dict with projection info or None
    """
    try:
        slp = ee.ImageCollection(IPCC_SLP_COLLECTION)
        img_2050 = slp.filter(ee.Filter.eq('system:index', 'ssp585_2050')).first()

        bands = [VALUE_BAND, VALUE_BAND_LOW, VALUE_BAND_HIGH]
        buffered = centroid_point.buffer(buffer_km * 1000)

        result = img_2050.select(bands).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=buffered,
            scale=50000,
            maxPixels=1e6
        ).getInfo()

        value_mm = result.get(VALUE_BAND)
        if value_mm is not None:
            return {
                'slr_2050_mm': round(value_mm, 1),
                'slr_2050_cm': round(value_mm / 10.0, 1),
                'slr_2050_low_cm': round(result.get(VALUE_BAND_LOW, 0) / 10.0, 1),
                'slr_2050_high_cm': round(result.get(VALUE_BAND_HIGH, 0) / 10.0, 1),
                'scenario': 'SSP5-8.5',
                'quantile': 0.5,
                'source': 'IPCC AR6 Sea Level Projections (Medium Confidence)',
            }

        # Try larger buffer
        if buffer_km < 200:
            return extract_slr_projection(centroid_point, buffer_km=200)

        return None

    except Exception as e:
        print(f"    Warning: SLR projection extraction failed: {e}")
        return None


def extract_slr_rate_coastal(anp_boundary, buffer_km=75):
    """Extract SLR rate from the nearest ocean pixel to the ANP boundary.

    Uses inverse-distance-squared weighting so the closest ocean pixel
    dominates the result (~90%+ of weight). This is more accurate for
    coastal ANPs whose centroids may be inland.

    Args:
        anp_boundary: ee.Geometry of the ANP polygon
        buffer_km: Buffer radius in km to search for ocean pixels

    Returns:
        dict with coastal rate info or None
    """
    try:
        slp = ee.ImageCollection(IPCC_SLP_COLLECTION)
        img_2020 = slp.filter(ee.Filter.eq('system:index', 'ssp585_2020')).first()

        search_zone = anp_boundary.buffer(buffer_km * 1000)
        boundary_fc = ee.FeatureCollection([ee.Feature(anp_boundary)])

        # Distance from each pixel to the ANP boundary (meters), min 1m to avoid /0
        distance = boundary_fc.distance(buffer_km * 1000).max(1)
        # Inverse-square weight — closest pixels dominate
        weight = distance.pow(-2)

        rate_img = img_2020.select([RATE_BAND, RATE_BAND_LOW, RATE_BAND_HIGH])

        # Weighted rate: sum(rate * w) / sum(w)
        weighted = rate_img.multiply(weight)
        combined = weighted.addBands(weight.rename('weight'))

        stats = combined.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=search_zone,
            scale=50000,
            maxPixels=1e6
        ).getInfo()

        w_sum = stats.get('weight')
        rate_sum = stats.get(RATE_BAND)

        if w_sum and w_sum > 0 and rate_sum is not None:
            rate = rate_sum / w_sum
            low_sum = stats.get(RATE_BAND_LOW, 0) or 0
            high_sum = stats.get(RATE_BAND_HIGH, 0) or 0
            return {
                'rate_mm_per_year': round(rate, 2),
                'rate_low_mm_per_year': round(low_sum / w_sum, 2),
                'rate_high_mm_per_year': round(high_sum / w_sum, 2),
                'method': 'inverse_distance_weighted',
                'buffer_km': buffer_km,
                'source': 'IPCC AR6 SLP (2020, nearest-coast IDW)',
            }

        # Try larger buffer if no ocean pixels found
        if buffer_km < 150:
            return extract_slr_rate_coastal(anp_boundary, buffer_km=150)

        return None

    except Exception as e:
        print(f"    Warning: Coastal SLR rate extraction failed: {e}")
        return None


def extract_slr_projection_coastal(anp_boundary, buffer_km=75):
    """Extract projected SLR by 2050 from the nearest ocean pixel to the ANP boundary.

    Same inverse-distance weighting approach as extract_slr_rate_coastal.

    Args:
        anp_boundary: ee.Geometry of the ANP polygon
        buffer_km: Buffer radius in km

    Returns:
        dict with coastal projection info or None
    """
    try:
        slp = ee.ImageCollection(IPCC_SLP_COLLECTION)
        img_2050 = slp.filter(ee.Filter.eq('system:index', 'ssp585_2050')).first()

        search_zone = anp_boundary.buffer(buffer_km * 1000)
        boundary_fc = ee.FeatureCollection([ee.Feature(anp_boundary)])

        distance = boundary_fc.distance(buffer_km * 1000).max(1)
        weight = distance.pow(-2)

        value_img = img_2050.select([VALUE_BAND, VALUE_BAND_LOW, VALUE_BAND_HIGH])
        weighted = value_img.multiply(weight)
        combined = weighted.addBands(weight.rename('weight'))

        stats = combined.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=search_zone,
            scale=50000,
            maxPixels=1e6
        ).getInfo()

        w_sum = stats.get('weight')
        value_sum = stats.get(VALUE_BAND)

        if w_sum and w_sum > 0 and value_sum is not None:
            value_mm = value_sum / w_sum
            low_sum = stats.get(VALUE_BAND_LOW, 0) or 0
            high_sum = stats.get(VALUE_BAND_HIGH, 0) or 0
            return {
                'slr_2050_mm': round(value_mm, 1),
                'slr_2050_cm': round(value_mm / 10.0, 1),
                'slr_2050_low_cm': round((low_sum / w_sum) / 10.0, 1),
                'slr_2050_high_cm': round((high_sum / w_sum) / 10.0, 1),
                'scenario': 'SSP5-8.5',
                'method': 'inverse_distance_weighted',
                'buffer_km': buffer_km,
                'source': 'IPCC AR6 Sea Level Projections (nearest-coast IDW)',
            }

        if buffer_km < 150:
            return extract_slr_projection_coastal(anp_boundary, buffer_km=150)

        return None

    except Exception as e:
        print(f"    Warning: Coastal SLR projection extraction failed: {e}")
        return None


def extract_inundation_risk(boundary_geometry, bounds_geometry):
    """Calculate percentage of ANP area below 1m elevation.

    Uses Copernicus GLO-30 DEM at 30m resolution.

    Args:
        boundary_geometry: ee.Geometry from boundary GeoJSON (preferred)
        bounds_geometry: ee.Geometry from bounds (fallback)

    Returns:
        dict with inundation info or None
    """
    geom = boundary_geometry or bounds_geometry
    if geom is None:
        return None

    try:
        dem = ee.ImageCollection(COPERNICUS_DEM_COLLECTION).select('DEM').mosaic()

        # Calculate fraction of pixels below 1 meter
        below_1m = dem.lt(1)

        # Use mean reducer — gives the fraction of pixels that are 1 (below threshold)
        stats = below_1m.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geom,
            scale=30,
            maxPixels=1e9,
            bestEffort=True
        )

        fraction = stats.getInfo().get('DEM')
        if fraction is not None:
            pct = round(fraction * 100.0, 1)
            return {
                'inundation_pct_at_1m': pct,
                'dem_source': 'Copernicus GLO-30',
                'dem_resolution_m': 30,
                'threshold_m': 1.0,
                'used_boundary': boundary_geometry is not None,
            }

        return None

    except Exception as e:
        print(f"    Warning: Inundation calculation failed: {e}")
        return None


def extract_sea_level_rise(anp_id, anp_data, boundary_geojson):
    """Extract all sea level rise metrics for a single ANP.

    Args:
        anp_id: ANP identifier
        anp_data: Dict from the ANP data JSON file
        boundary_geojson: Dict from boundary GeoJSON file (may be None)

    Returns:
        dict with all SLR metrics
    """
    result = {
        'data_available': False,
        'extracted_at': datetime.now().isoformat(),
        'sources': {
            'slr_rate': 'IPCC AR6 SLP (2020 calibrated rate as observed proxy)',
            'slr_projection': 'IPCC AR6 Sea Level Projections (Medium Confidence)',
            'inundation': 'Copernicus DEM GLO-30',
        },
        'notes': [
            'No native satellite altimetry (AVISO) dataset exists in GEE.',
            'HYCOM/sea_surface_elevation (27K+ images) is too slow for batch processing.',
            'IPCC AR6 SLP 2020 rate is calibrated to historical observations.',
        ],
    }

    centroid_point = get_centroid_point(anp_data)
    bounds_geom = get_bounds_geometry(anp_data)
    boundary_geom = get_boundary_geometry(boundary_geojson)

    if not centroid_point:
        result['error'] = 'No centroid geometry available'
        return result

    # 1. Observed SLR rate (centroid-based, for backward compatibility)
    rate_data = extract_slr_rate(centroid_point)
    if rate_data:
        result['observed_trend_mm_per_year'] = rate_data['rate_mm_per_year']
        result['observed_trend_range_mm_per_year'] = [
            rate_data['rate_low_mm_per_year'],
            rate_data['rate_high_mm_per_year']
        ]
        result['observed_period'] = rate_data['period']
        result['data_available'] = True
    else:
        result['observed_trend_mm_per_year'] = None
        result['observed_period'] = None

    # 1b. Coastal SLR rate (nearest ocean pixel to ANP boundary)
    if boundary_geom:
        coastal_rate = extract_slr_rate_coastal(boundary_geom)
        if coastal_rate:
            result['observed_trend_coastal_mm_per_year'] = coastal_rate['rate_mm_per_year']
            result['observed_trend_coastal_range_mm_per_year'] = [
                coastal_rate['rate_low_mm_per_year'],
                coastal_rate['rate_high_mm_per_year']
            ]
            result['coastal_extraction_method'] = coastal_rate['method']
            result['coastal_buffer_km'] = coastal_rate['buffer_km']
            result['data_available'] = True

    # 2. Projected SLR by 2050 (centroid-based)
    proj_data = extract_slr_projection(centroid_point)
    if proj_data:
        result['projected_slr_2050_cm'] = proj_data['slr_2050_cm']
        result['projected_slr_2050_range_cm'] = [
            proj_data['slr_2050_low_cm'],
            proj_data['slr_2050_high_cm']
        ]
        result['projected_scenario'] = proj_data['scenario']
        result['projected_quantile'] = proj_data['quantile']
        result['data_available'] = True
    else:
        result['projected_slr_2050_cm'] = None
        result['projected_scenario'] = 'SSP5-8.5'
        result['projected_quantile'] = 0.5

    # 2b. Coastal SLR projection (nearest ocean pixel)
    if boundary_geom:
        coastal_proj = extract_slr_projection_coastal(boundary_geom)
        if coastal_proj:
            result['projected_slr_2050_coastal_cm'] = coastal_proj['slr_2050_cm']
            result['projected_slr_2050_coastal_range_cm'] = [
                coastal_proj['slr_2050_low_cm'],
                coastal_proj['slr_2050_high_cm']
            ]
            result['data_available'] = True

    # 3. Inundation risk
    inundation_data = extract_inundation_risk(boundary_geom, bounds_geom)
    if inundation_data:
        result['inundation_pct_at_1m'] = inundation_data['inundation_pct_at_1m']
        result['dem_source'] = inundation_data['dem_source']
        result['inundation_used_boundary'] = inundation_data['used_boundary']
        result['data_available'] = True
    else:
        result['inundation_pct_at_1m'] = None
        result['dem_source'] = 'Copernicus GLO-30'

    return result


def process_anp(anp_id, use_database=True):
    """Process a single coastal ANP for sea level rise data.

    Args:
        anp_id: ANP identifier
        use_database: If True, save to database and regenerate JSON

    Returns:
        'success', 'skipped', or 'error'
    """
    # Load ANP data
    anp_data = load_anp_data(anp_id)
    if not anp_data:
        print(f"  {anp_id}: No data file found, skipping")
        return 'skipped'

    name = anp_data.get('metadata', {}).get('name', anp_id)

    # Check if already has sea_level_rise data
    existing = anp_data.get('datasets', {}).get('sea_level_rise', {})
    if existing and existing.get('data_available') and 'error' not in existing:
        print(f"  {name}: Already has SLR data, skipping")
        return 'skipped'

    # Load boundary
    boundary_geojson = load_anp_boundary(anp_id)

    print(f"  {name}: Extracting...", end=" ", flush=True)

    try:
        slr_data = extract_sea_level_rise(anp_id, anp_data, boundary_geojson)

        # Save to database if available
        if use_database and HAS_DATABASE:
            upsert_dataset(anp_id, 'sea_level_rise', slr_data, source='gee')
            export_anp_to_json(anp_id, DATA_DIR)
        else:
            # Legacy: update JSON file directly
            if 'datasets' not in anp_data:
                anp_data['datasets'] = {}
            anp_data['datasets']['sea_level_rise'] = slr_data
            data_file = os.path.join(DATA_DIR, f'{anp_id}_data.json')
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(anp_data, f, indent=2, ensure_ascii=False)

        # Print summary
        if slr_data.get('data_available'):
            rate = slr_data.get('observed_trend_mm_per_year')
            coastal_rate = slr_data.get('observed_trend_coastal_mm_per_year')
            proj = slr_data.get('projected_slr_2050_cm')
            inund = slr_data.get('inundation_pct_at_1m')
            parts = []
            if rate is not None:
                parts.append(f"rate={rate}mm/yr")
            if coastal_rate is not None:
                parts.append(f"coastal={coastal_rate}mm/yr")
            if proj is not None:
                parts.append(f"2050={proj}cm")
            if inund is not None:
                parts.append(f"inund={inund}%")
            print(f"OK ({', '.join(parts)})")
        else:
            print("OK (no data at location)")

        return 'success'

    except Exception as e:
        print(f"ERROR: {e}")
        return 'error'


def main():
    print("\n" + "=" * 60)
    print("Sea Level Rise Data Extraction for Coastal ANPs")
    print("=" * 60)
    print(f"Sources: IPCC AR6 SLP + Copernicus DEM GLO-30")

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
        # Process single ANP
        if single_anp in coastal_ids:
            coastal_ids = [single_anp]
        else:
            # Try fuzzy match
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
        # Rate limit between GEE calls
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
