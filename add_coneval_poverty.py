#!/usr/bin/env python3
"""
Add CONEVAL Poverty Indices (Indice de Rezago Social) to ANP data files.

Uses locality-level INEGI ITER data to identify which municipalities intersect
each ANP, then looks up poverty indicators for those municipalities from CONEVAL.

Data source: CONEVAL IRS 2020 (Indice de Rezago Social)
- Downloaded from: https://www.coneval.org.mx/Medicion/IRS/Paginas/Indice_Rezago_Social_2020.aspx
- Resolution: Municipal level
- Indicators: Illiteracy, education, health access, housing conditions
- Index: -2.5 (very low lag) to +4.0 (very high lag)

Usage:
    python3 add_coneval_poverty.py              # Process all ANPs
    python3 add_coneval_poverty.py --test       # Test with first 3 ANPs
    python3 add_coneval_poverty.py "calakmul"   # Process single ANP
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Optional

try:
    import pandas as pd  # type: ignore
    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore
    HAS_PANDAS = False
    print("Warning: pandas not installed. Install with: pip install pandas openpyxl")

# Constants
DATA_DIR = 'anp_data'
REFERENCE_DIR = 'reference_data'
CONEVAL_FILE = f'{REFERENCE_DIR}/coneval_irs/IRS_entidades_mpios_2020.xlsx'

# IRS category mapping
IRS_CATEGORIES = {
    'Muy bajo': 1,
    'Bajo': 2,
    'Medio': 3,
    'Alto': 4,
    'Muy alto': 5
}


def parse_dms_coordinate(dms_str):
    """Parse DMS coordinate string to decimal degrees."""
    if pd.isna(dms_str) or not isinstance(dms_str, str):  # type: ignore
        return None
    
    # Pattern allows optional space before direction (e.g., "20°22'16.414\" N")
    match = re.match(r"(\d+)°(\d+)'([\d.]+)\"\s*([NSEW])", dms_str.strip())
    if not match:
        return None
    
    degrees = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    direction = match.group(4)
    
    decimal = degrees + minutes/60 + seconds/3600
    if direction in ['S', 'W']:
        decimal = -decimal
    
    return decimal


def load_coneval_data():
    """Load CONEVAL IRS 2020 municipal data."""
    if not HAS_PANDAS:
        return None
    
    if not os.path.exists(CONEVAL_FILE):
        print(f"Error: CONEVAL file not found: {CONEVAL_FILE}")
        return None
    
    try:
        df = pd.read_excel(  # type: ignore
            CONEVAL_FILE,
            sheet_name='Municipios',
            header=4,
            skiprows=[5]  # Skip sub-header row
        )
        
        # Clean column names
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
        # Drop empty rows
        df = df.dropna(subset=['Clave entidad', 'Clave municipio'])
        
        # Create composite key: use Clave municipio (already includes state prefix)
        # Format: EEMMM (5 digits) where EE=state, MMM=municipality
        df['state_mun_key'] = df['Clave municipio'].astype(int).astype(str).str.zfill(5)
        
        print(f"Loaded {len(df)} municipalities from CONEVAL")
        return df
    except Exception as e:
        print(f"Error loading CONEVAL data: {e}")
        return None


def load_iter_data_for_state(state_code):
    """Load ITER census data for a specific state."""
    if not HAS_PANDAS:
        return None
    
    filepath = f"{REFERENCE_DIR}/ITER_{state_code:02d}CSV20.csv"
    if not os.path.exists(filepath):
        return None
    
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig', low_memory=False)  # type: ignore
        df['lat_decimal'] = df['LATITUD'].apply(parse_dms_coordinate)
        df['lon_decimal'] = df['LONGITUD'].apply(parse_dms_coordinate)
        # Create composite key
        df['state_mun_key'] = (
            df['ENTIDAD'].astype(str).str.zfill(2) + 
            df['MUN'].astype(str).str.zfill(3)
        )
        return df
    except Exception as e:
        return None


def get_municipalities_for_anp(bbox):
    """Find unique municipalities that have localities within ANP bounding box."""
    municipalities = set()
    mun_info = {}  # state_mun_key -> {name, state_name, pop}
    
    for state_code in range(1, 33):
        df = load_iter_data_for_state(state_code)
        if df is None:
            continue
        
        # Filter to localities within bbox (exclude totals where MUN=0)
        in_bbox = df[
            (df['MUN'] > 0) &  # Exclude state totals
            (df['lat_decimal'].notna()) &
            (df['lon_decimal'].notna()) &
            (df['lat_decimal'] >= bbox['minLat']) &
            (df['lat_decimal'] <= bbox['maxLat']) &
            (df['lon_decimal'] >= bbox['minLon']) &
            (df['lon_decimal'] <= bbox['maxLon'])
        ]
        
        if len(in_bbox) > 0:
            for _, row in in_bbox.drop_duplicates(subset=['state_mun_key']).iterrows():  # type: ignore
                key = row['state_mun_key']
                if key not in mun_info:
                    municipalities.add(key)
                    mun_info[key] = {
                        'name': row['NOM_MUN'],
                        'state': row['NOM_ENT'],
                        'state_code': str(row['ENTIDAD']).zfill(2),
                        'mun_code': str(row['MUN']).zfill(3)
                    }
    
    return list(municipalities), mun_info


def get_coneval_for_anp(anp_data, coneval_df):
    """Extract CONEVAL poverty indicators for an ANP."""
    if coneval_df is None:
        return {'error': 'CONEVAL data not loaded'}
    
    # Get bounding box from ANP data
    bounds = anp_data.get('geometry', {}).get('bounds')
    if not bounds:
        return {'error': 'No bounding box in ANP data'}
    
    # Convert bounds to bbox dict
    lons = [p[0] for p in bounds]
    lats = [p[1] for p in bounds]
    bbox = {
        'minLon': min(lons),
        'maxLon': max(lons),
        'minLat': min(lats),
        'maxLat': max(lats)
    }
    
    # Find municipalities that intersect ANP
    mun_keys, mun_info = get_municipalities_for_anp(bbox)
    
    if not mun_keys:
        return {
            'source': 'CONEVAL IRS 2020',
            'data_available': False,
            'reason': 'No municipalities found within ANP bounds',
            'note': 'This may be expected for marine ANPs or remote islands'
        }
    
    # Look up municipalities in CONEVAL
    matched = coneval_df[coneval_df['state_mun_key'].isin(mun_keys)]
    
    if len(matched) == 0:
        return {
            'source': 'CONEVAL IRS 2020',
            'data_available': False,
            'municipalities_checked': len(mun_keys),
            'reason': 'No CONEVAL data found for intersecting municipalities'
        }
    
    # Calculate summary statistics
    # Population-weighted average IRS
    total_pop = matched['Población total'].sum()
    if total_pop > 0:
        weighted_irs = (matched['Índice de rezago social'] * matched['Población total']).sum() / total_pop
    else:
        weighted_irs = matched['Índice de rezago social'].mean()
    
    # Get IRS category distribution
    category_counts = matched['Grado de rezago social'].value_counts().to_dict()
    
    # Get most common category (mode)
    predominant_category = matched['Grado de rezago social'].mode().iloc[0] if len(matched) > 0 else None
    
    # Build municipalities list with details
    municipalities = []
    for _, row in matched.iterrows():
        key = row['state_mun_key']
        info = mun_info.get(key, {})
        municipalities.append({
            'name': row['Municipio'],
            'state': info.get('state', row['Entidad federativa']),
            'population': int(row['Población total']) if pd.notna(row['Población total']) else 0,  # type: ignore
            'irs_index': round(row['Índice de rezago social'], 4) if pd.notna(row['Índice de rezago social']) else None,  # type: ignore
            'irs_category': row['Grado de rezago social'],
            'national_rank': int(row['Lugar que ocupa en el contexto nacional']) if pd.notna(row['Lugar que ocupa en el contexto nacional']) else None  # type: ignore
        })
    
    # Sort by population descending
    municipalities.sort(key=lambda x: x['population'], reverse=True)
    
    return {
        'source': 'CONEVAL IRS 2020 (Indice de Rezago Social)',
        'data_available': True,
        'municipalities_count': len(matched),
        'total_population': int(total_pop),
        'irs_weighted_mean': round(weighted_irs, 4),
        'irs_predominant_category': predominant_category,
        'irs_category_distribution': category_counts,
        'municipalities': municipalities[:20],  # Top 20 by population
        'interpretation': {
            'irs_index': 'Social Lag Index: negative values = low lag (better conditions), positive = high lag (worse conditions)',
            'categories': 'Muy bajo (best) → Bajo → Medio → Alto → Muy alto (worst)',
            'weighted_mean': 'Population-weighted average across all municipalities intersecting ANP'
        },
        'extracted_at': datetime.now().isoformat()
    }


def process_anp(anp_file, coneval_df):
    """Add CONEVAL data to a single ANP file."""
    filepath = os.path.join(DATA_DIR, anp_file)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            anp_data = json.load(f)
    except Exception as e:
        print(f"  Error reading {anp_file}: {e}")
        return False
    
    anp_name = anp_data.get('metadata', {}).get('name', anp_file)
    
    # Check if already has CONEVAL data
    existing = anp_data.get('external_data', {}).get('coneval_irs')
    if existing and existing.get('data_available'):
        print(f"  {anp_name}: Already has CONEVAL data, skipping")
        return True
    
    print(f"  {anp_name}: Extracting...", end=' ', flush=True)
    
    # Get CONEVAL data
    coneval_result = get_coneval_for_anp(anp_data, coneval_df)
    
    # Add to external_data
    if 'external_data' not in anp_data:
        anp_data['external_data'] = {}
    anp_data['external_data']['coneval_irs'] = coneval_result
    
    # Save
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(anp_data, f, indent=2, ensure_ascii=False)
        
        if coneval_result.get('data_available'):
            count = coneval_result.get('municipalities_count', 0)
            pop = coneval_result.get('total_population', 0)
            irs = coneval_result.get('irs_weighted_mean', 'N/A')
            cat = coneval_result.get('irs_predominant_category', 'N/A')
            print(f"OK ({count} municipalities, pop: {pop:,}, IRS: {irs} [{cat}])")
        else:
            reason = coneval_result.get('reason', 'unknown')
            print(f"No data ({reason})")
        return True
    except Exception as e:
        print(f"Error saving: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Add CONEVAL poverty indices to ANP data')
    parser.add_argument('anp_name', nargs='?', help='Specific ANP to process (optional)')
    parser.add_argument('--test', action='store_true', help='Test mode: process first 3 ANPs only')
    args = parser.parse_args()
    
    if not HAS_PANDAS:
        print("Error: pandas is required. Install with: pip install pandas openpyxl")
        sys.exit(1)
    
    print("Loading CONEVAL IRS 2020 data...")
    coneval_df = load_coneval_data()
    if coneval_df is None:
        sys.exit(1)
    
    # Get list of ANP files
    anp_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('_data.json')])
    print(f"Found {len(anp_files)} ANP data files\n")
    
    if args.anp_name:
        # Process single ANP
        pattern = args.anp_name.lower().replace(' ', '_')
        matching = [f for f in anp_files if pattern in f.lower()]
        if not matching:
            print(f"No ANP found matching '{args.anp_name}'")
            sys.exit(1)
        anp_files = matching
    elif args.test:
        anp_files = anp_files[:3]
        print("Test mode: processing first 3 ANPs\n")
    
    print("Processing ANPs...")
    success = 0
    for anp_file in anp_files:
        if process_anp(anp_file, coneval_df):
            success += 1
    
    print(f"\nDone! Processed {success}/{len(anp_files)} ANPs")


if __name__ == '__main__':
    main()
