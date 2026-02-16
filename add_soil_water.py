#!/usr/bin/env python3
"""
Add Soil + Surface Water data to existing ANP data files.
==========================================================

Usage:
    python3 add_soil_water.py --test          # First 3 ANPs
    python3 add_soil_water.py --all           # All 227 ANPs
    python3 add_soil_water.py <anp_id>        # Single ANP by ID
"""

import ee
import json
import sys
import os
import time
import argparse

from gee_auth import init_ee

DATA_DIR = 'anp_data'
ALL_ANPS_FILE = 'all_anps_subset.json'


def safe_reduce(image, geometry, scale, reducer=None):
    """Safely reduce an image over a geometry."""
    if reducer is None:
        reducer = ee.Reducer.mean()
    result = image.reduceRegion(
        reducer=reducer,
        geometry=geometry,
        scale=scale,
        maxPixels=1e9
    ).getInfo()
    return result


def extract_soil(geom):
    """Extract soil data from OpenLandMap."""
    soil_organic = ee.Image('OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02').select('b0')
    soil_ph = ee.Image('OpenLandMap/SOL/SOL_PH-H2O_USDA-4C1A2A_M/v02').select('b0')
    organic_stats = safe_reduce(soil_organic, geom, 250)
    ph_stats = safe_reduce(soil_ph, geom, 250)
    return {
        "source": "OpenLandMap",
        "resolution": "250m",
        "organic_carbon_g_kg": organic_stats.get('b0'),
        "ph_h2o": ph_stats.get('b0', 0) / 10 if ph_stats.get('b0') else None
    }


def extract_surface_water(geom):
    """Extract surface water data from JRC Global Surface Water."""
    water = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
    occurrence = water.select('occurrence')
    water_mask = occurrence.gt(50)
    water_area = water_mask.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geom,
        scale=30,
        maxPixels=1e9
    ).getInfo()
    return {
        "source": "JRC Global Surface Water",
        "resolution": "30m",
        "permanent_water_km2": round(water_area.get('occurrence', 0) / 1e6, 2)
    }


def has_valid_data(datasets, key):
    """Check if a dataset key exists and has no error."""
    return key in datasets and 'error' not in datasets[key]


def process_anp(anp_id):
    """Process a single ANP. Returns: 'success', 'skipped', or 'failed'."""
    data_file = os.path.join(DATA_DIR, f'{anp_id}_data.json')
    boundary_file = os.path.join(DATA_DIR, f'{anp_id}_boundary.geojson')

    if not os.path.exists(data_file):
        print(f"  ✗ No data file: {data_file}")
        return 'failed'

    if not os.path.exists(boundary_file):
        print(f"  ✗ No boundary file: {boundary_file}")
        return 'failed'

    # Load existing data
    with open(data_file) as f:
        data = json.load(f)

    datasets = data.get('datasets', {})

    # Skip if already has both
    if has_valid_data(datasets, 'soil') and has_valid_data(datasets, 'surface_water'):
        print(f"  ⊘ Already has soil + surface_water, skipping")
        return 'skipped'

    # Load boundary and convert to ee.Geometry
    with open(boundary_file) as f:
        boundary_geojson = json.load(f)

    # Handle both Feature and FeatureCollection
    if boundary_geojson.get('type') == 'FeatureCollection':
        features = boundary_geojson['features']
        if len(features) == 1:
            geom = ee.Geometry(features[0]['geometry'])
        else:
            # Merge multiple features
            geom = ee.FeatureCollection([
                ee.Feature(ee.Geometry(f['geometry'])) for f in features
            ]).geometry()
    elif boundary_geojson.get('type') == 'Feature':
        geom = ee.Geometry(boundary_geojson['geometry'])
    else:
        geom = ee.Geometry(boundary_geojson)

    # Extract soil if missing
    if not has_valid_data(datasets, 'soil'):
        print(f"    Soil (OpenLandMap)...", end=" ", flush=True)
        try:
            datasets['soil'] = extract_soil(geom)
            print("OK")
        except Exception as e:
            datasets['soil'] = {"error": str(e)}
            print(f"ERROR: {e}")

    # Extract surface water if missing
    if not has_valid_data(datasets, 'surface_water'):
        print(f"    Surface Water (JRC)...", end=" ", flush=True)
        try:
            datasets['surface_water'] = extract_surface_water(geom)
            print("OK")
        except Exception as e:
            datasets['surface_water'] = {"error": str(e)}
            print(f"ERROR: {e}")

    # Save back
    data['datasets'] = datasets
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Check if both succeeded
    if has_valid_data(datasets, 'soil') and has_valid_data(datasets, 'surface_water'):
        return 'success'
    else:
        return 'failed'


def main():
    parser = argparse.ArgumentParser(description='Add soil + surface water to ANP data files')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--test', action='store_true', help='Process first 3 ANPs')
    group.add_argument('--all', action='store_true', help='Process all ANPs')
    group.add_argument('anp_id', nargs='?', help='Single ANP ID to process')
    args = parser.parse_args()

    # Initialize GEE
    print("Initializing Google Earth Engine...")
    init_ee()
    print()

    # Load ANP IDs
    with open(ALL_ANPS_FILE) as f:
        all_anps = json.load(f)
    anp_ids = all_anps['anp_ids_with_data']

    if args.anp_id:
        anp_ids = [args.anp_id]
    elif args.test:
        anp_ids = anp_ids[:3]
    # else --all uses all

    total = len(anp_ids)
    succeeded = 0
    failed = 0
    skipped = 0

    print(f"Processing {total} ANPs for soil + surface water...\n")

    for i, anp_id in enumerate(anp_ids, 1):
        print(f"[{i}/{total}] {anp_id}")
        result = process_anp(anp_id)

        if result == 'success':
            succeeded += 1
        elif result == 'skipped':
            skipped += 1
        else:
            failed += 1

        # Rate limit (skip delay on last item or skipped)
        if i < total and result != 'skipped':
            time.sleep(2)

    print(f"\n{'='*50}")
    print(f"DONE: {succeeded} succeeded, {failed} failed, {skipped} skipped (of {total} total)")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
