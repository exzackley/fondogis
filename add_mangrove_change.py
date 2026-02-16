#!/usr/bin/env python3
"""
Add Mangrove Extent Change to ANP Files
========================================

Uses Global Mangrove Watch (GMW) v3.0 raster data from GEE community catalog
to compute mangrove extent change between 1996 and 2020 for ANPs that have
existing mangrove data.

Data source:
- Global Mangrove Watch v3.0 (community catalog)
  GEE: projects/sat-io/open-datasets/GMW/extent/GMW_V3
  Epochs: 1996, 2007-2010, 2015-2020
  Resolution: ~25m (0.000222°)
  Band: b1 (1 = mangrove, 0 = non-mangrove)

Only processes ANPs that already have mangrove data (datasets.mangroves.data_available=True
in their data JSON), since those are the ANPs known to contain mangroves.

Output dataset_type: mangrove_change

Usage:
    python3 add_mangrove_change.py              # Process all ANPs with mangroves
    python3 add_mangrove_change.py --test       # Test with first 3 ANPs
    python3 add_mangrove_change.py --no-db      # JSON-only mode (no database)
    python3 add_mangrove_change.py "sian_ka_an" # Process single ANP
"""

import ee
import json
import os
import sys
import time
from datetime import datetime
from glob import glob

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

# GEE Dataset - Global Mangrove Watch v3.0 (community catalog)
GMW_COLLECTION = 'projects/sat-io/open-datasets/GMW/extent/GMW_V3'
GMW_BAND = 'b1'

# Pixel area in km² (0.000222° ≈ 24.7m at equator)
# We compute actual area using ee.Image.pixelArea() for accuracy
EARLY_EPOCH = 'gmw_v3_1996'
LATE_EPOCH = 'gmw_v3_2020'

# All available epochs for full timeseries
ALL_EPOCHS = {
    'gmw_v3_1996': 1996,
    'gmw_v3_2007': 2007,
    'gmw_v3_2008': 2008,
    'gmw_v3_2009': 2009,
    'gmw_v3_2010': 2010,
    'gmw_v3_2015': 2015,
    'gmw_v3_2016': 2016,
    'gmw_v3_2017': 2017,
    'gmw_v3_2018': 2018,
    'gmw_v3_2019': 2019,
    'gmw_v3_2020': 2020,
}


def find_anps_with_mangroves():
    """Find all ANP IDs that have existing mangrove data (data_available=True)."""
    anp_ids = []
    for f in sorted(glob(f'{DATA_DIR}/*_data.json')):
        anp_id = os.path.basename(f).replace('_data.json', '')
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            mg = data.get('datasets', {}).get('mangroves', {})
            if mg and mg.get('data_available', False):
                anp_ids.append(anp_id)
        except Exception:
            continue
    return anp_ids


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
    """Get ee.Geometry from boundary GeoJSON or bounds."""
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

    bounds = anp_data.get('geometry', {}).get('bounds')
    if bounds:
        return ee.Geometry.Polygon(bounds)

    return None


def compute_mangrove_area_km2(epoch_id, geometry):
    """Compute mangrove extent in km² for a specific GMW epoch.

    Uses pixel area for accurate area calculation regardless of latitude.

    Args:
        epoch_id: GMW epoch image ID (e.g., 'gmw_v3_1996')
        geometry: ee.Geometry for the ANP

    Returns:
        float area in km², or None if no data
    """
    try:
        gmw_col = ee.ImageCollection(GMW_COLLECTION)
        img = gmw_col.filter(ee.Filter.eq('system:index', epoch_id)).first()

        # Create binary mangrove mask (b1 >= 1 = mangrove)
        mangrove_mask = img.select(GMW_BAND).gt(0)

        # Compute area of mangrove pixels using pixelArea
        mangrove_area = mangrove_mask.multiply(ee.Image.pixelArea())

        # Sum area within the ANP geometry
        area_stats = mangrove_area.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=25,  # Native resolution ~25m
            maxPixels=1e10,
            bestEffort=True
        ).getInfo()

        area_m2 = area_stats.get(GMW_BAND)
        if area_m2 is not None:
            return area_m2 / 1e6  # Convert m² to km²
        return None

    except Exception as e:
        print(f"    Warning: Could not compute area for {epoch_id}: {e}")
        return None


def extract_mangrove_change(anp_id, geometry):
    """Extract mangrove extent change between 1996 and 2020.

    Args:
        anp_id: ANP identifier
        geometry: ee.Geometry for the ANP

    Returns:
        dict with mangrove change data
    """
    result = {
        'data_available': False,
        'extracted_at': datetime.now().isoformat(),
        'source': 'Global Mangrove Watch v3.0',
        'resolution_m': 25,
    }

    try:
        # Compute extent for early and late epochs
        extent_1996 = compute_mangrove_area_km2(EARLY_EPOCH, geometry)
        extent_2020 = compute_mangrove_area_km2(LATE_EPOCH, geometry)

        if extent_1996 is None and extent_2020 is None:
            result['error'] = 'No mangrove data found in GMW for this area'
            return result

        result['data_available'] = True
        result['extent_1996_km2'] = round(extent_1996, 4) if extent_1996 is not None else None
        result['extent_2020_km2'] = round(extent_2020, 4) if extent_2020 is not None else None

        # Compute change
        if extent_1996 is not None and extent_2020 is not None:
            change_km2 = extent_2020 - extent_1996
            if extent_1996 > 0:
                change_pct = (change_km2 / extent_1996) * 100
            else:
                change_pct = None

            result['change_km2'] = round(change_km2, 4)
            result['change_percent'] = round(change_pct, 2) if change_pct is not None else None

            # Determine direction
            if change_pct is not None:
                if change_pct > 2:
                    result['change_direction'] = 'gain'
                elif change_pct < -2:
                    result['change_direction'] = 'loss'
                else:
                    result['change_direction'] = 'stable'
        else:
            result['change_km2'] = None
            result['change_percent'] = None

        # Also get intermediate epoch (2010) for context
        extent_2010 = compute_mangrove_area_km2('gmw_v3_2010', geometry)
        if extent_2010 is not None:
            result['extent_2010_km2'] = round(extent_2010, 4)

        return result

    except Exception as e:
        result['error'] = str(e)
        return result


def process_anp(anp_id, use_database=True):
    """Process a single ANP for mangrove change data."""
    anp_data = load_anp_data(anp_id)
    if not anp_data:
        print(f"  {anp_id}: No data file found, skipping")
        return 'skipped'

    name = anp_data.get('metadata', {}).get('name', anp_id)

    # Check if already has mangrove_change data
    existing = anp_data.get('datasets', {}).get('mangrove_change', {})
    if existing and existing.get('data_available') and 'error' not in existing:
        print(f"  {name}: Already has mangrove change data, skipping")
        return 'skipped'

    # Get geometry
    boundary_geojson = load_anp_boundary(anp_id)
    geometry = get_geometry(anp_data, boundary_geojson)

    if not geometry:
        print(f"  {name}: No geometry available, skipping")
        return 'skipped'

    print(f"  {name}: Extracting mangrove change...", end=" ", flush=True)

    try:
        change_data = extract_mangrove_change(anp_id, geometry)

        # Save to database if available
        if use_database and HAS_DATABASE:
            upsert_dataset(anp_id, 'mangrove_change', change_data, source='gee')
            export_anp_to_json(anp_id, DATA_DIR)
        else:
            if 'datasets' not in anp_data:
                anp_data['datasets'] = {}
            anp_data['datasets']['mangrove_change'] = change_data
            data_file = os.path.join(DATA_DIR, f'{anp_id}_data.json')
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(anp_data, f, indent=2, ensure_ascii=False)

        # Print summary
        if change_data.get('data_available'):
            e96 = change_data.get('extent_1996_km2')
            e20 = change_data.get('extent_2020_km2')
            chg = change_data.get('change_percent')
            parts = []
            if e96 is not None:
                parts.append(f"1996={e96:.2f}km²")
            if e20 is not None:
                parts.append(f"2020={e20:.2f}km²")
            if chg is not None:
                parts.append(f"change={chg:+.1f}%")
            print(f"OK ({', '.join(parts)})")
        else:
            print(f"OK (no GMW data: {change_data.get('error', 'unknown')})")

        return 'success'

    except Exception as e:
        print(f"ERROR: {e}")
        return 'error'


def main():
    print("\n" + "=" * 60)
    print("Mangrove Extent Change (Global Mangrove Watch v3.0)")
    print("=" * 60)
    print(f"Epochs: 1996 → 2020")

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

    # Find ANPs with existing mangrove data
    mangrove_anp_ids = find_anps_with_mangroves()
    print(f"Found {len(mangrove_anp_ids)} ANPs with existing mangrove data")

    if single_anp:
        if single_anp in mangrove_anp_ids:
            mangrove_anp_ids = [single_anp]
        else:
            matches = [aid for aid in mangrove_anp_ids if single_anp.lower() in aid.lower()]
            if matches:
                mangrove_anp_ids = matches
                print(f"Matched: {matches}")
            else:
                print(f"ANP '{single_anp}' not found in mangrove ANPs")
                return

    if test_mode:
        mangrove_anp_ids = mangrove_anp_ids[:3]
        print(f"TEST MODE: Processing first 3 ANPs")

    if use_database:
        print("Mode: Database (source of truth) + JSON export")
    else:
        print("Mode: JSON files only")

    print(f"Processing {len(mangrove_anp_ids)} ANPs...\n")

    success = 0
    skipped = 0
    errors = 0

    for i, anp_id in enumerate(mangrove_anp_ids, 1):
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
