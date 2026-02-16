#!/usr/bin/env python3
"""
Add Hurricane/Tropical Cyclone Exposure to Coastal ANP Files
=============================================================

Uses IBTrACS v4 (International Best Track Archive for Climate Stewardship)
from GEE to analyze tropical cyclone history near each coastal ANP.

For each coastal ANP: counts tropical cyclones that passed within 100km
of the ANP centroid since 1990, breaks down by category (TS, Cat 1-5),
and records the strongest and most recent storms.

Data source:
- NOAA IBTrACS v4: ee.FeatureCollection('NOAA/IBTrACS/v4')
  - Each feature is a 6-hourly track point with storm properties
  - Key fields: SID (storm ID), NAME, SEASON, BASIN, USA_SSHS, USA_WIND

USA_SSHS (Saffir-Simpson Hurricane Scale):
  -5 = Unknown, -4 = Post-tropical, -3 = Misc disturbance,
  -2 = Subtropical, -1 = Tropical depression,
   0 = Tropical storm, 1-5 = Hurricane Category 1-5

Output dataset_type: hurricane_exposure

Usage:
    python3 add_hurricane_exposure.py              # Process all coastal ANPs
    python3 add_hurricane_exposure.py --test       # Test with first 3 coastal ANPs
    python3 add_hurricane_exposure.py --no-db      # JSON-only mode (no database)
    python3 add_hurricane_exposure.py "sian_ka_an" # Process single ANP
"""

import ee
import json
import os
import sys
import time
import math
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
IBTRACS_COLLECTION = 'NOAA/IBTrACS/v4'

# Analysis parameters
BUFFER_KM = 100          # Search radius around ANP centroid
MIN_SEASON = 1990         # Start year for analysis
# Basins: EP = Eastern Pacific, NA = North Atlantic (both affect Mexico)
BASINS = ['EP', 'NA']

# USA_SSHS category mapping
SSHS_CATEGORIES = {
    0: 'TS',     # Tropical Storm
    1: 'Cat1',
    2: 'Cat2',
    3: 'Cat3',
    4: 'Cat4',
    5: 'Cat5',
}

# Also track these as "sub-tropical-storm" events
SSHS_SUB_CATEGORIES = {
    -1: 'TD',    # Tropical Depression
    -2: 'ST',    # Subtropical
}


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


def haversine_km(lon1, lat1, lon2, lat2):
    """Calculate great-circle distance in km between two points."""
    R = 6371.0  # Earth radius in km
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_sshs_label(sshs_value):
    """Convert USA_SSHS integer to category label."""
    if sshs_value is None:
        return None
    sshs_value = int(sshs_value)
    if sshs_value in SSHS_CATEGORIES:
        return SSHS_CATEGORIES[sshs_value]
    if sshs_value in SSHS_SUB_CATEGORIES:
        return SSHS_SUB_CATEGORIES[sshs_value]
    return None


def sshs_rank(label):
    """Return numeric rank for sorting categories. Higher = stronger."""
    rank = {'TD': 0, 'ST': 0.5, 'TS': 1, 'Cat1': 2, 'Cat2': 3, 'Cat3': 4, 'Cat4': 5, 'Cat5': 6}
    return rank.get(label, -1)


def extract_hurricane_exposure(anp_id, centroid_lon, centroid_lat):
    """Extract tropical cyclone exposure for a single ANP.

    Strategy:
    1. Create a buffer around the ANP centroid
    2. Use GEE to filter IBTrACS track points within that buffer
    3. Download matching points and process locally (grouping by storm)

    Args:
        anp_id: ANP identifier
        centroid_lon: Longitude of ANP centroid
        centroid_lat: Latitude of ANP centroid

    Returns:
        dict with hurricane exposure data
    """
    result = {
        'data_available': False,
        'extracted_at': datetime.now().isoformat(),
        'source': 'IBTrACS v04',
        'buffer_km': BUFFER_KM,
    }

    try:
        centroid_point = ee.Geometry.Point([centroid_lon, centroid_lat])
        buffer_geom = centroid_point.buffer(BUFFER_KM * 1000)  # meters

        # Filter IBTrACS: basin, season, and spatial proximity
        ibtracs = ee.FeatureCollection(IBTRACS_COLLECTION)

        filtered = (ibtracs
                    .filter(ee.Filter.inList('BASIN', BASINS))
                    .filter(ee.Filter.gte('SEASON', MIN_SEASON))
                    .filterBounds(buffer_geom))

        # Get count first to check if manageable
        count = filtered.size().getInfo()

        if count == 0:
            result['data_available'] = True
            result['total_cyclones_100km'] = 0
            result['period'] = f'{MIN_SEASON}-2024'
            result['by_category'] = {'TS': 0, 'Cat1': 0, 'Cat2': 0, 'Cat3': 0, 'Cat4': 0, 'Cat5': 0}
            result['strongest'] = None
            result['most_recent'] = None
            return result

        # Download track points (limit to prevent memory issues)
        # IBTrACS has 6-hourly points; 100km buffer should give manageable counts
        max_features = 5000
        if count > max_features:
            print(f"\n    Warning: {count} track points found, limiting to {max_features}")

        features = filtered.limit(max_features).getInfo()

        # Process locally: group by storm SID, compute distances
        storms = {}  # SID -> {name, season, max_sshs, min_distance, ...}

        for f in features.get('features', []):
            props = f['properties']
            geom = f['geometry']

            sid = props.get('SID', '')
            name = props.get('NAME', 'UNNAMED')
            season = props.get('SEASON')
            sshs = props.get('USA_SSHS')
            wind = props.get('USA_WIND') or props.get('WMO_WIND')

            # Skip unknown/post-tropical/misc — only TS and above
            if sshs is None or sshs < 0:
                # Still track the storm in case it had higher category elsewhere
                pass

            # Compute distance from centroid
            if geom and geom['type'] == 'Point':
                pt_lon, pt_lat = geom['coordinates']
                dist_km = haversine_km(centroid_lon, centroid_lat, pt_lon, pt_lat)
            else:
                dist_km = BUFFER_KM  # fallback

            # Only count if actually within buffer
            if dist_km > BUFFER_KM * 1.1:  # small tolerance
                continue

            if sid not in storms:
                storms[sid] = {
                    'name': name if name and name != 'NOT_NAMED' else 'UNNAMED',
                    'season': season,
                    'max_sshs': sshs if sshs is not None else -99,
                    'max_wind_kt': wind if wind is not None else 0,
                    'min_distance_km': dist_km,
                }
            else:
                # Update with best values across all track points
                storm = storms[sid]
                if sshs is not None and sshs > storm['max_sshs']:
                    storm['max_sshs'] = sshs
                if wind is not None and wind > storm['max_wind_kt']:
                    storm['max_wind_kt'] = wind
                if dist_km < storm['min_distance_km']:
                    storm['min_distance_km'] = dist_km
                # Keep the non-UNNAMED name
                if name and name != 'NOT_NAMED' and name != 'UNNAMED':
                    storm['name'] = name

        # Filter: only count Tropical Storms and above (SSHS >= 0)
        valid_storms = {sid: s for sid, s in storms.items() if s['max_sshs'] >= 0}

        # Category breakdown
        by_category = {'TS': 0, 'Cat1': 0, 'Cat2': 0, 'Cat3': 0, 'Cat4': 0, 'Cat5': 0}
        for sid, storm in valid_storms.items():
            label = get_sshs_label(storm['max_sshs'])
            if label and label in by_category:
                by_category[label] += 1

        # Find strongest storm
        strongest = None
        if valid_storms:
            strongest_sid = max(valid_storms, key=lambda s: (
                valid_storms[s]['max_sshs'],
                valid_storms[s]['max_wind_kt']
            ))
            s = valid_storms[strongest_sid]
            strongest = {
                'name': s['name'],
                'year': s['season'],
                'category': get_sshs_label(s['max_sshs']) or 'TS',
                'max_wind_kt': s['max_wind_kt'],
                'distance_km': round(s['min_distance_km'], 1),
            }

        # Find most recent storm
        most_recent = None
        if valid_storms:
            recent_sid = max(valid_storms, key=lambda s: valid_storms[s]['season'])
            s = valid_storms[recent_sid]
            most_recent = {
                'name': s['name'],
                'year': s['season'],
                'category': get_sshs_label(s['max_sshs']) or 'TS',
                'max_wind_kt': s['max_wind_kt'],
                'distance_km': round(s['min_distance_km'], 1),
            }

        result.update({
            'data_available': True,
            'total_cyclones_100km': len(valid_storms),
            'period': f'{MIN_SEASON}-2024',
            'by_category': by_category,
            'strongest': strongest,
            'most_recent': most_recent,
            'track_points_analyzed': count,
        })

        return result

    except Exception as e:
        result['error'] = str(e)
        return result


def process_anp(anp_id, use_database=True):
    """Process a single coastal ANP for hurricane exposure data."""
    anp_data = load_anp_data(anp_id)
    if not anp_data:
        print(f"  {anp_id}: No data file found, skipping")
        return 'skipped'

    name = anp_data.get('metadata', {}).get('name', anp_id)

    # Check if already has hurricane_exposure data
    existing = anp_data.get('datasets', {}).get('hurricane_exposure', {})
    if existing and existing.get('data_available') and 'error' not in existing:
        print(f"  {name}: Already has hurricane exposure data, skipping")
        return 'skipped'

    # Get centroid
    centroid = anp_data.get('geometry', {}).get('centroid')
    if not centroid or len(centroid) != 2:
        print(f"  {name}: No centroid geometry available, skipping")
        return 'skipped'

    centroid_lon, centroid_lat = centroid

    print(f"  {name}: Extracting hurricane exposure...", end=" ", flush=True)

    try:
        exposure_data = extract_hurricane_exposure(anp_id, centroid_lon, centroid_lat)

        # Save to database if available
        if use_database and HAS_DATABASE:
            upsert_dataset(anp_id, 'hurricane_exposure', exposure_data, source='noaa')
            export_anp_to_json(anp_id, DATA_DIR)
        else:
            if 'datasets' not in anp_data:
                anp_data['datasets'] = {}
            anp_data['datasets']['hurricane_exposure'] = exposure_data
            data_file = os.path.join(DATA_DIR, f'{anp_id}_data.json')
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(anp_data, f, indent=2, ensure_ascii=False)

        # Print summary
        if exposure_data.get('data_available'):
            total = exposure_data.get('total_cyclones_100km', 0)
            cats = exposure_data.get('by_category', {})
            strongest = exposure_data.get('strongest')
            parts = [f"{total} storms"]
            if any(cats.get(f'Cat{i}', 0) > 0 for i in range(1, 6)):
                hurricane_count = sum(cats.get(f'Cat{i}', 0) for i in range(1, 6))
                parts.append(f"{hurricane_count} hurricanes")
            if strongest:
                parts.append(f"strongest: {strongest['name']} ({strongest['category']}, {strongest['year']})")
            print(f"OK ({', '.join(parts)})")
        else:
            print(f"OK (error: {exposure_data.get('error', 'unknown')})")

        return 'success'

    except Exception as e:
        print(f"ERROR: {e}")
        return 'error'


def main():
    print("\n" + "=" * 60)
    print("Hurricane / Tropical Cyclone Exposure Extraction")
    print("=" * 60)
    print(f"Source: IBTrACS v04 (basins: {', '.join(BASINS)}, {MIN_SEASON}+)")
    print(f"Buffer: {BUFFER_KM}km around ANP centroid")

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
