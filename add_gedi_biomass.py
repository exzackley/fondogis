#!/usr/bin/env python3
"""
Add GEDI Forest Biomass Data to Existing ANP Files
===================================================

Uses NASA GEDI L4A dataset to extract aboveground biomass density (AGBD)
for each ANP. This quantifies the carbon stock in forests.

GEDI data is sparse (orbital tracks) so coverage varies by ANP.

Usage:
    python3 add_gedi_biomass.py              # Process all ANPs
    python3 add_gedi_biomass.py --test       # Test with first 3 ANPs
    python3 add_gedi_biomass.py "calakmul"   # Process single ANP
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


def extract_gedi_biomass(geometry):
    """Extract GEDI aboveground biomass density for a geometry.
    
    GEDI provides footprint-level data, so we aggregate all available
    measurements within the ANP boundary.
    """
    try:
        geom = ee.Geometry.Polygon(geometry)
        
        # GEDI L4A monthly composite - agbd band is aboveground biomass density (Mg/ha)
        gedi = ee.ImageCollection('LARSE/GEDI/GEDI04_A_002_MONTHLY') \
            .filterBounds(geom) \
            .select(['agbd', 'agbd_se'])
        
        count = gedi.size().getInfo()
        
        if count == 0:
            return {
                "source": "NASA GEDI L4A",
                "data_available": False,
                "note": "No GEDI observations for this area",
                "extracted_at": datetime.now().isoformat()
            }
        
        # Composite: use mean of all monthly composites
        composite = gedi.mean()
        
        # Calculate statistics within the ANP
        stats = composite.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.stdDev(), '', True
            ).combine(
                ee.Reducer.max(), '', True
            ).combine(
                ee.Reducer.count(), '', True
            ),
            geometry=geom,
            scale=25,  # GEDI footprint ~25m
            maxPixels=1e9
        ).getInfo()
        
        agbd_mean = stats.get('agbd_mean')
        agbd_max = stats.get('agbd_max')
        agbd_std = stats.get('agbd_stdDev')
        pixel_count = stats.get('agbd_count')
        
        # Calculate total carbon stock estimate
        # AGBD is in Mg/ha, convert to total for the ANP
        if agbd_mean and pixel_count:
            # Rough estimate: pixel_count * 25m * 25m = area sampled in m2
            # area_sampled_ha = (pixel_count * 625) / 10000
            # But better to get actual ANP area from geometry
            area_ha = geom.area().divide(10000).getInfo()
            total_carbon_estimate_mt = (agbd_mean * area_ha) / 1000 if area_ha else None
        else:
            total_carbon_estimate_mt = None
            area_ha = None
        
        return {
            "source": "NASA GEDI L4A (Aboveground Biomass Density)",
            "resolution": "25m footprints",
            "data_available": agbd_mean is not None,
            "gedi_images_used": count,
            "agbd_mean_mg_ha": round(agbd_mean, 2) if agbd_mean else None,
            "agbd_max_mg_ha": round(agbd_max, 2) if agbd_max else None,
            "agbd_std_mg_ha": round(agbd_std, 2) if agbd_std else None,
            "sampled_pixels": pixel_count,
            "anp_area_ha": round(area_ha, 0) if area_ha else None,
            "total_carbon_estimate_mt": round(total_carbon_estimate_mt, 0) if total_carbon_estimate_mt else None,
            "interpretation": {
                "agbd": "Aboveground Biomass Density in Megagrams (tonnes) per hectare",
                "total_carbon": "Rough estimate of total aboveground carbon stock in megatonnes"
            },
            "extracted_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e), "extracted_at": datetime.now().isoformat()}


def process_anp(data_file, use_database=True):
    """Add GEDI biomass data to a single ANP file.

    Args:
        data_file: Path to the ANP data JSON file
        use_database: If True, save to database and regenerate JSON
    """
    # Get ANP ID from filename
    anp_id = os.path.basename(data_file).replace('_data.json', '')

    with open(data_file) as f:
        data = json.load(f)

    name = data.get('metadata', {}).get('name', os.path.basename(data_file))

    # Check if already has GEDI data
    existing = data.get('datasets', {}).get('gedi_biomass', {})
    if existing and 'error' not in existing and existing.get('source') == 'NASA GEDI L4A (Aboveground Biomass Density)':
        print(f"  {name}: Already has GEDI data, skipping")
        return 'skipped'

    # Get geometry from bounds
    bounds = data.get('geometry', {}).get('bounds')
    if not bounds:
        print(f"  {name}: No bounds found, skipping")
        return 'skipped'

    print(f"  {name}: Extracting...", end=" ", flush=True)

    try:
        gedi_data = extract_gedi_biomass(bounds)

        # Save to database if available
        if use_database and HAS_DATABASE:
            upsert_dataset(anp_id, 'gedi_biomass', gedi_data, source='gee')
            # Regenerate JSON from database
            export_anp_to_json(anp_id, DATA_DIR)
        else:
            # Legacy: update JSON file directly
            if 'datasets' not in data:
                data['datasets'] = {}

            data['datasets']['gedi_biomass'] = gedi_data

            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2)

        if gedi_data.get('data_available'):
            agbd = gedi_data.get('agbd_mean_mg_ha')
            carbon = gedi_data.get('total_carbon_estimate_mt')
            print(f"OK (AGBD: {agbd} Mg/ha, ~{carbon} MT carbon)")
        else:
            print("OK (no GEDI coverage)")

        return 'success'

    except Exception as e:
        print(f"ERROR: {e}")
        return 'error'


def main():
    print("\n" + "="*60)
    print("NASA GEDI Aboveground Biomass Extraction")
    print("="*60)

    init_ee()
    print("GEE initialized")

    # Get list of data files
    data_files = sorted(glob(f"{DATA_DIR}/*_data.json"))
    use_database = HAS_DATABASE  # Default to using database if available

    if len(sys.argv) > 1:
        args = sys.argv[1:]
        if '--no-db' in args:
            use_database = False
            args.remove('--no-db')
            print("NO-DB MODE: Saving directly to JSON files")

        if args:
            arg = args[0]
            if arg == '--test':
                data_files = data_files[:3]
                print(f"TEST MODE: Processing first 3 ANPs")
            else:
                # Find specific ANP
                search = arg.lower().replace(' ', '_')
                data_files = [f for f in data_files if search in f.lower()]
                if not data_files:
                    print(f"No ANP found matching '{arg}'")
                    return

    if use_database:
        print("Mode: Database (source of truth) + JSON export")
    else:
        print("Mode: JSON files only")

    print(f"Processing {len(data_files)} ANP files...\n")

    success = 0
    skipped = 0
    errors = 0

    for i, data_file in enumerate(data_files, 1):
        # Rate limit
        if i > 1:
            time.sleep(0.5)

        result = process_anp(data_file, use_database=use_database)
        if result == 'success':
            success += 1
        elif result == 'skipped':
            skipped += 1
        else:
            errors += 1

    print("\n" + "="*60)
    print(f"Complete: {success} updated, {skipped} skipped, {errors} errors")
    print("="*60)


if __name__ == '__main__':
    main()
