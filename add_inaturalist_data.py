#!/usr/bin/env python3
"""
Add iNaturalist/Naturalista Citizen Science Data to ANP Files

Extracts research-grade species observation counts from iNaturalist API.
Provides species richness and observation counts for each ANP.

Usage:
    python3 add_inaturalist_data.py              # Process all ANPs
    python3 add_inaturalist_data.py --test       # Test with first 3 ANPs
    python3 add_inaturalist_data.py "calakmul"   # Process single ANP
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

try:
    import requests  # type: ignore
    HAS_REQUESTS = True
except ImportError:
    requests = None  # type: ignore
    HAS_REQUESTS = False
    print("Warning: requests not installed. Install with: pip install requests")

# Database support
try:
    from db.db_utils import upsert_dataset, export_anp_to_json
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False

DATA_DIR = 'anp_data'
INAT_API = 'https://api.inaturalist.org/v1'
INAT_DELAY = 1.1
USER_AGENT = 'FondoGIS-FMCN-ANP-Dashboard (github.com/exzackley/fondogis)'


def get_species_counts(bbox, iconic_taxon=None):
    """Get species counts from iNaturalist for a bounding box."""
    url = f"{INAT_API}/observations/species_counts"
    params = {
        'swlat': bbox['minLat'],
        'swlng': bbox['minLon'],
        'nelat': bbox['maxLat'],
        'nelng': bbox['maxLon'],
        'quality_grade': 'research',
        'per_page': 500,
        'locale': 'es-MX'
    }
    if iconic_taxon:
        params['iconic_taxa'] = iconic_taxon
    
    headers = {'User-Agent': USER_AGENT}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)  # type: ignore
        if response.status_code == 429:
            time.sleep(60)
            response = requests.get(url, params=params, headers=headers, timeout=30)  # type: ignore
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return None


def get_observation_stats(bbox):
    """Get observation statistics from iNaturalist for a bounding box."""
    url = f"{INAT_API}/observations"
    params = {
        'swlat': bbox['minLat'],
        'swlng': bbox['minLon'],
        'nelat': bbox['maxLat'],
        'nelng': bbox['maxLon'],
        'quality_grade': 'research',
        'per_page': 0
    }
    headers = {'User-Agent': USER_AGENT}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)  # type: ignore
        if response.status_code == 200:
            return response.json().get('total_results', 0)
        return 0
    except:
        return 0


def extract_inaturalist_data(anp_data):
    """Extract iNaturalist data for an ANP."""
    bounds = anp_data.get('geometry', {}).get('bounds')
    if not bounds:
        return {'error': 'No bounding box in ANP data'}
    
    lons = [p[0] for p in bounds]
    lats = [p[1] for p in bounds]
    bbox = {
        'minLon': min(lons),
        'maxLon': max(lons),
        'minLat': min(lats),
        'maxLat': max(lats)
    }
    
    time.sleep(INAT_DELAY)
    total_obs = get_observation_stats(bbox)
    
    time.sleep(INAT_DELAY)
    species_data = get_species_counts(bbox)
    
    if not species_data:
        return {
            'source': 'iNaturalist (Naturalista)',
            'data_available': False,
            'note': 'API request failed or no data',
            'extracted_at': datetime.now().isoformat()
        }
    
    total_species = species_data.get('total_results', 0)
    results = species_data.get('results', [])
    
    if total_species == 0:
        return {
            'source': 'iNaturalist (Naturalista)',
            'data_available': False,
            'total_observations': total_obs,
            'note': 'No research-grade species observations in this area',
            'extracted_at': datetime.now().isoformat()
        }
    
    species_by_iconic = {}
    for item in results:
        taxon = item.get('taxon', {})
        iconic = taxon.get('iconic_taxon_name', 'Unknown')
        if iconic not in species_by_iconic:
            species_by_iconic[iconic] = 0
        species_by_iconic[iconic] += 1
    
    top_species = []
    for item in results[:30]:
        taxon = item.get('taxon', {})
        top_species.append({
            'scientific_name': taxon.get('name'),
            'common_name': taxon.get('preferred_common_name'),
            'iconic_taxon': taxon.get('iconic_taxon_name'),
            'observations': item.get('count', 0),
            'taxon_id': taxon.get('id')
        })
    
    return {
        'source': 'iNaturalist (Naturalista)',
        'data_available': True,
        'total_observations': total_obs,
        'unique_species': total_species,
        'species_by_group': species_by_iconic,
        'top_species': top_species,
        'bounding_box': bbox,
        'quality_filter': 'research-grade only',
        'interpretation': {
            'observations': 'Total research-grade observations in area',
            'species': 'Unique species identified by community',
            'note': 'Citizen science data - effort varies by accessibility'
        },
        'extracted_at': datetime.now().isoformat()
    }


def process_anp(anp_file, use_database=True):
    """Add iNaturalist data to a single ANP file.

    Args:
        anp_file: Filename of the ANP data JSON file
        use_database: If True, save to database and regenerate JSON
    """
    filepath = os.path.join(DATA_DIR, anp_file)
    # Get ANP ID from filename
    anp_id = anp_file.replace('_data.json', '')

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            anp_data = json.load(f)
    except Exception as e:
        print(f"  Error reading {anp_file}: {e}")
        return False

    anp_name = anp_data.get('metadata', {}).get('name', anp_file)

    existing = anp_data.get('external_data', {}).get('inaturalist')
    if existing and existing.get('data_available') == True:
        print(f"  {anp_name}: Already has iNaturalist data, skipping")
        return True

    print(f"  {anp_name}: Extracting...", end=' ', flush=True)

    result = extract_inaturalist_data(anp_data)

    try:
        # Save to database if available
        if use_database and HAS_DATABASE:
            upsert_dataset(anp_id, 'inaturalist', result, source='inaturalist')
            # Regenerate JSON from database
            export_anp_to_json(anp_id, DATA_DIR)
        else:
            # Legacy: update JSON file directly
            if 'external_data' not in anp_data:
                anp_data['external_data'] = {}
            anp_data['external_data']['inaturalist'] = result

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(anp_data, f, indent=2, ensure_ascii=False)

        if result.get('data_available'):
            species = result.get('unique_species', 0)
            obs = result.get('total_observations', 0)
            print(f"OK ({species} species, {obs:,} observations)")
        else:
            print(f"No data")
        return True
    except Exception as e:
        print(f"Error saving: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Add iNaturalist citizen science data to ANP files')
    parser.add_argument('anp_name', nargs='?', help='Specific ANP to process')
    parser.add_argument('--test', action='store_true', help='Test with first 3 ANPs')
    parser.add_argument('--no-db', action='store_true', help='Save directly to JSON files instead of database')
    args = parser.parse_args()

    if not HAS_REQUESTS:
        print("Error: requests library required. Install with: pip install requests")
        sys.exit(1)

    use_database = HAS_DATABASE and not args.no_db
    if args.no_db:
        print("NO-DB MODE: Saving directly to JSON files")
    elif use_database:
        print("Mode: Database (source of truth) + JSON export")
    else:
        print("Mode: JSON files only")

    anp_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('_data.json')])
    print(f"Found {len(anp_files)} ANP data files\n")

    if args.anp_name:
        pattern = args.anp_name.lower().replace(' ', '_')
        matching = [f for f in anp_files if pattern in f.lower()]
        if not matching:
            print(f"No ANP found matching '{args.anp_name}'")
            sys.exit(1)
        anp_files = matching
    elif args.test:
        anp_files = anp_files[:3]
        print("Test mode: processing first 3 ANPs\n")

    print("Processing ANPs (rate limited to 1 req/sec)...")
    success = 0
    for anp_file in anp_files:
        if process_anp(anp_file, use_database=use_database):
            success += 1

    print(f"\nDone! Processed {success}/{len(anp_files)} ANPs")


if __name__ == '__main__':
    main()
