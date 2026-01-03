#!/usr/bin/env python3
"""
Add Water Stress Data to Existing ANP Files
============================================

Uses WRI Aqueduct Water Risk Atlas V4 (FeatureCollection) to extract
water stress indicators for each ANP.

Note: Many protected areas show "No Data" because they are pristine
wilderness with minimal water withdrawals - this is expected.

Usage:
    python3 add_water_stress.py              # Process all ANPs
    python3 add_water_stress.py --test       # Test with first 3 ANPs
    python3 add_water_stress.py "calakmul"   # Process single ANP
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
    # Fallback if helper not available
    def init_ee():
        ee.Initialize(project='gen-lang-client-0866285082')

DATA_DIR = 'anp_data'

# WRI Aqueduct V4 baseline annual FeatureCollection
AQUEDUCT_PATH = 'WRI/Aqueduct_Water_Risk/V4/baseline_annual'


def init():
    """Initialize Earth Engine."""
    init_ee()


def extract_water_stress(geometry):
    """Extract WRI Aqueduct water stress data for a geometry.
    
    Returns area-weighted average if multiple sub-basins intersect.
    """
    try:
        aqueduct = ee.FeatureCollection(AQUEDUCT_PATH)
        geom = ee.Geometry.Polygon(geometry)
        
        # Get features that intersect the ANP
        intersecting = aqueduct.filterBounds(geom)
        count = intersecting.size().getInfo()
        
        if count == 0:
            return {
                "source": "WRI Aqueduct Water Risk Atlas V4",
                "resolution": "Sub-basin (HydroBASINS level 6)",
                "data_available": False,
                "note": "No Aqueduct sub-basins intersect this area",
                "extracted_at": datetime.now().isoformat()
            }
        
        # Get all intersecting features
        features = intersecting.getInfo()['features']
        
        # Calculate area-weighted averages for key indicators
        total_area = 0
        weighted_bws = 0
        weighted_drr = 0
        valid_bws = False
        valid_drr = False
        
        bws_labels = []
        drr_labels = []
        
        for f in features:
            props = f['properties']
            area = props.get('area_km2', 1)
            
            bws_raw = props.get('bws_raw', -9999)
            drr_raw = props.get('drr_raw', -9999)
            
            if bws_raw != -9999 and bws_raw is not None:
                weighted_bws += bws_raw * area
                valid_bws = True
                bws_labels.append(props.get('bws_label', 'Unknown'))
            
            if drr_raw != -9999 and drr_raw is not None:
                weighted_drr += drr_raw * area
                valid_drr = True
                drr_labels.append(props.get('drr_label', 'Unknown'))
            
            if bws_raw != -9999 or drr_raw != -9999:
                total_area += area
        
        # Calculate weighted averages
        if valid_bws and total_area > 0:
            bws_avg = weighted_bws / total_area
            # Determine category from average
            if bws_avg < 0.1:
                bws_cat = "Low (<10%)"
            elif bws_avg < 0.2:
                bws_cat = "Low-Medium (10-20%)"
            elif bws_avg < 0.4:
                bws_cat = "Medium-High (20-40%)"
            elif bws_avg < 0.8:
                bws_cat = "High (40-80%)"
            else:
                bws_cat = "Extremely High (>80%)"
        else:
            bws_avg = None
            bws_cat = None
        
        if valid_drr and total_area > 0:
            drr_avg = weighted_drr / total_area
            # Determine category
            if drr_avg < 0.2:
                drr_cat = "Low"
            elif drr_avg < 0.4:
                drr_cat = "Low-Medium"
            elif drr_avg < 0.6:
                drr_cat = "Medium"
            elif drr_avg < 0.8:
                drr_cat = "Medium-High"
            else:
                drr_cat = "High"
        else:
            drr_avg = None
            drr_cat = None
        
        return {
            "source": "WRI Aqueduct Water Risk Atlas V4",
            "resolution": "Sub-basin (HydroBASINS level 6)",
            "data_available": valid_bws or valid_drr,
            "sub_basins_count": count,
            "baseline_water_stress": round(bws_avg, 4) if bws_avg else None,
            "baseline_water_stress_category": bws_cat,
            "drought_risk": round(drr_avg, 4) if drr_avg else None,
            "drought_risk_category": drr_cat,
            "interpretation": {
                "BWS": "Ratio of total water withdrawals to available supply. Protected areas often show 'No Data' due to minimal human water use.",
                "DRR": "Probability-weighted drought severity (0-1 scale)."
            },
            "note": "No water stress data" if not (valid_bws or valid_drr) else None,
            "extracted_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e), "extracted_at": datetime.now().isoformat()}


def process_anp(data_file):
    """Add water stress data to a single ANP file."""
    with open(data_file) as f:
        data = json.load(f)
    
    name = data.get('metadata', {}).get('name', os.path.basename(data_file))
    
    # Check if already has valid water_stress data
    existing = data.get('datasets', {}).get('water_stress', {})
    if existing and 'error' not in existing and existing.get('source') == 'WRI Aqueduct Water Risk Atlas V4':
        print(f"  {name}: Already has V4 data, skipping")
        return 'skipped'
    
    # Get geometry from bounds
    bounds = data.get('geometry', {}).get('bounds')
    if not bounds:
        print(f"  {name}: No bounds found, skipping")
        return 'skipped'
    
    print(f"  {name}: Extracting...", end=" ", flush=True)
    
    try:
        water_stress = extract_water_stress(bounds)
        
        if 'datasets' not in data:
            data['datasets'] = {}
        
        data['datasets']['water_stress'] = water_stress
        
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        if water_stress.get('data_available'):
            bws = water_stress.get('baseline_water_stress')
            cat = water_stress.get('baseline_water_stress_category', '')
            print(f"OK (BWS: {bws:.2f} - {cat})" if bws else "OK (drought data only)")
        else:
            print("OK (no water stress in area - pristine)")
        
        return 'success'
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 'error'


def main():
    print("\n" + "="*60)
    print("WRI Aqueduct Water Stress Data Extraction (V4)")
    print("="*60)
    
    init()
    print("GEE initialized\n")
    
    # Get list of data files
    data_files = sorted(glob(f"{DATA_DIR}/*_data.json"))
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
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
    
    print(f"Processing {len(data_files)} ANP files...\n")
    
    success = 0
    skipped = 0
    errors = 0
    
    for i, data_file in enumerate(data_files, 1):
        # Rate limit to avoid GEE quotas
        if i > 1:
            time.sleep(0.3)
        
        result = process_anp(data_file)
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
