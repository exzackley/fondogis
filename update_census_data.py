#!/usr/bin/env python3
"""
Update Census Data for Mexican Protected Areas
===============================================

This script updates ONLY the INEGI census data for existing ANP files.
Much faster than re-running full extraction since it uses local CSV files.

Usage:
    python3 update_census_data.py "Calakmul"     # Single ANP
    python3 update_census_data.py --all          # All ANPs
    python3 update_census_data.py --test         # First 3 ANPs only
"""

import json
import os
import sys
import re
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("ERROR: pandas is required. Install with: pip install pandas")
    sys.exit(1)

DATA_DIR = 'anp_data'
INDEX_FILE = 'anp_index.json'
REFERENCE_DIR = 'reference_data'


def parse_dms_coordinate(dms_str):
    """Convert degrees-minutes-seconds string to decimal degrees."""
    if not dms_str or pd.isna(dms_str):
        return None
    
    dms_str = str(dms_str).strip()
    match = re.match(r"(\d+)°(\d+)'([\d.]+)\"?\s*([NSEW])", dms_str)
    if not match:
        return None
    
    degrees = float(match.group(1))
    minutes = float(match.group(2))
    seconds = float(match.group(3))
    direction = match.group(4)
    
    decimal = degrees + minutes/60 + seconds/3600
    if direction in ['S', 'W']:
        decimal = -decimal
    
    return decimal


def load_iter_data_for_state(state_code):
    """Load ITER census data for a specific state."""
    filepath = f"{REFERENCE_DIR}/ITER_{state_code:02d}CSV20.csv"
    if not os.path.exists(filepath):
        return None
    
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig', low_memory=False)
        df['lat_decimal'] = df['LATITUD'].apply(parse_dms_coordinate)
        df['lon_decimal'] = df['LONGITUD'].apply(parse_dms_coordinate)
        return df
    except Exception as e:
        print(f"    Warning: Could not load ITER data for state {state_code}: {e}")
        return None


def get_bounding_box_from_data(data):
    """Extract bounding box from ANP data file."""
    geom = data.get('geometry', {})
    bounds = geom.get('bounds')
    
    if bounds and len(bounds) >= 2:
        lons = [b[0] for b in bounds]
        lats = [b[1] for b in bounds]
        return {
            'minLon': min(lons),
            'maxLon': max(lons),
            'minLat': min(lats),
            'maxLat': max(lats)
        }
    
    centroid = geom.get('centroid')
    if centroid:
        buffer = 0.5
        return {
            'minLon': centroid[0] - buffer,
            'maxLon': centroid[0] + buffer,
            'minLat': centroid[1] - buffer,
            'maxLat': centroid[1] + buffer
        }
    
    return None


def extract_census_data(bbox):
    """Extract INEGI census indicators for localities within bounding box."""
    all_localities = []
    
    for state_code in range(1, 33):
        df = load_iter_data_for_state(state_code)
        if df is None:
            continue
        
        in_bbox = df[
            (df['lat_decimal'].notna()) &
            (df['lon_decimal'].notna()) &
            (df['lat_decimal'] >= bbox['minLat']) &
            (df['lat_decimal'] <= bbox['maxLat']) &
            (df['lon_decimal'] >= bbox['minLon']) &
            (df['lon_decimal'] <= bbox['maxLon'])
        ]
        
        if len(in_bbox) > 0:
            all_localities.append(in_bbox)
    
    if not all_localities:
        return {'error': 'No localities found in bounding box'}
    
    combined = pd.concat(all_localities, ignore_index=True)
    
    def safe_sum(col):
        if col not in combined.columns:
            return 0
        numeric = pd.to_numeric(combined[col], errors='coerce')
        return int(numeric.sum()) if numeric.notna().any() else 0
    
    def safe_mean(col):
        if col not in combined.columns:
            return None
        numeric = pd.to_numeric(combined[col], errors='coerce')
        if numeric.notna().any():
            return round(numeric.mean(), 1)
        return None
    
    pop_total = safe_sum('POBTOT')
    pop_female = safe_sum('POBFEM')
    pop_male = safe_sum('POBMAS')
    
    return {
        'source': 'INEGI Censo 2020 (ITER)',
        'localities_in_area': len(combined),
        'total_population': pop_total,
        'female_population': pop_female,
        'male_population': pop_male,
        'female_percent': round((pop_female / pop_total * 100), 1) if pop_total > 0 else None,
        'indigenous_speakers_3plus': safe_sum('P3YM_HLI'),
        'indigenous_speakers_5plus': safe_sum('P5_HLI'),
        'indigenous_households_pop': safe_sum('PHOG_IND'),
        'afromexican_population': safe_sum('POB_AFRO'),
        'population_60plus': safe_sum('P_60YMAS'),
        'economically_active': safe_sum('PEA'),
        'employed': safe_sum('POCUPADA'),
        'unemployed': safe_sum('PDESOCUP'),
        'illiterate_15plus': safe_sum('P15YM_AN'),
        'no_schooling_15plus': safe_sum('P15YM_SE'),
        'post_basic_education_18plus': safe_sum('P18YM_PB'),
        'avg_schooling_years': safe_mean('GRAPROES'),
        'no_health_services': safe_sum('PSINDER'),
        'with_health_services': safe_sum('PDER_SS'),
        'with_disability': safe_sum('PCON_DISC'),
        'homes_dirt_floor': safe_sum('VPH_PISOTI'),
        'homes_no_electricity': safe_sum('VPH_S_ELEC'),
        'homes_no_water': safe_sum('VPH_AGUAFV'),
        'homes_no_drainage': safe_sum('VPH_NODREN'),
        'homes_no_services': safe_sum('VPH_NDEAED'),
        'total_households': safe_sum('TOTHOG'),
        'female_headed_households': safe_sum('HOGJEF_F'),
        'sample_localities': combined['NOM_LOC'].head(10).tolist() if 'NOM_LOC' in combined.columns else []
    }


def update_anp_census(anp_id, anp_info):
    """Update census data for a single ANP."""
    data_file = anp_info['data_file']
    
    with open(data_file) as f:
        data = json.load(f)
    
    bbox = get_bounding_box_from_data(data)
    if not bbox:
        print(f"    ERROR: Could not determine bounding box")
        return False
    
    census_result = extract_census_data(bbox)
    
    if census_result.get('error'):
        print(f"    No census data: {census_result['error']}")
        return False
    
    if 'external_data' not in data:
        data['external_data'] = {}
    
    data['external_data']['inegi_census'] = census_result
    
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    pop = census_result.get('total_population', 0)
    locs = census_result.get('localities_in_area', 0)
    print(f"    Updated: {locs} localities, pop {pop:,}")
    
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 update_census_data.py \"<ANP name>\"")
        print("       python3 update_census_data.py --all")
        print("       python3 update_census_data.py --test")
        sys.exit(1)
    
    with open(INDEX_FILE) as f:
        index = json.load(f)
    
    arg = sys.argv[1]
    
    if arg == '--all':
        anps_to_process = index['anps']
    elif arg == '--test':
        anps_to_process = index['anps'][:3]
    else:
        anps_to_process = [a for a in index['anps'] if arg.lower() in a['name'].lower()]
        if not anps_to_process:
            print(f"ERROR: ANP '{arg}' not found")
            sys.exit(1)
    
    total = len(anps_to_process)
    success = 0
    
    print(f"\nUpdating census data for {total} ANPs...")
    print("=" * 60)
    
    for i, anp in enumerate(anps_to_process, 1):
        print(f"\n[{i}/{total}] {anp['name']}")
        if update_anp_census(anp['id'], anp):
            success += 1
    
    print("\n" + "=" * 60)
    print(f"COMPLETE: Updated {success}/{total} ANPs")


if __name__ == '__main__':
    main()
