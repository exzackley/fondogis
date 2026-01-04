#!/usr/bin/env python3
"""
ANP Characteristics and Data Expectations System
=================================================

Determines which data sources should have data for each ANP based on:
- Location type (marine, terrestrial, coastal, island)
- Size (tiny, small, medium, large)
- Region (CONANP administrative regions)
- SIMEC registration status
- Designation type

Outputs anp_expectations.json with detailed expectations per ANP.

Usage:
    python3 anp_expectations.py           # Generate expectations for all ANPs
    python3 anp_expectations.py --verify  # Verify expectations against actual data
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from anp_registry import get_all_anps, get_anp_count
    HAS_REGISTRY = True
except ImportError:
    HAS_REGISTRY = False

DATA_DIR = 'anp_data'
INDEX_FILE = 'anp_index.json'
OFFICIAL_LIST_FILE = 'reference_data/official_anp_list.json'
SIMEC_LIST_FILE = 'reference_data/simec_anp_list.json'
DATA_SOURCES_FILE = 'data_sources.json'
OUTPUT_FILE = 'anp_expectations.json'


# Marine/coastal indicators in ANP names
MARINE_INDICATORS = [
    'arrecife', 'arrecifes', 'marino', 'marina', 'zona marina', 
    'banco chinchorro', 'isla', 'islas', 'bahia', 'bahía',
    'ventilas hidrotermales', 'pacifico mexicano profundo',
    'playa', 'costa', 'golfo'
]

# Purely marine (no terrestrial component)
PURELY_MARINE = [
    'arrecife alacranes', 'arrecifes de cozumel', 'arrecifes de sian ka',
    'arrecifes de xcalak', 'banco chinchorro', 'caribe mexicano',
    'zona marina', 'ventilas hidrotermales', 'pacifico mexicano profundo',
    'arrecife de puerto morelos', 'costa occ', 'bajos del norte', 'bajos de coyula'
]

# Island ANPs (may have limited census data)
ISLAND_INDICATORS = [
    'isla', 'islas', 'revillagigedo', 'islas marias', 'isla guadalupe'
]

# Tiny ANPs (< 1 km2) - may have limited data
TINY_SIZE_THRESHOLD = 1.0

# Small ANPs (< 100 km2)
SMALL_SIZE_THRESHOLD = 100.0

# Beach/nesting sanctuaries (very small, often just beach strips)
PLAYA_INDICATORS = ['playa', 'santuario']

# CONANP Regional mapping (approximate by state)
STATE_TO_REGION = {
    # Region 1: Peninsula de Baja California
    'baja california': 1, 'baja california sur': 1,
    # Region 2: Noroeste y Alto Golfo de California
    'sonora': 2, 'sinaloa': 2,
    # Region 3: Norte y Sierra Madre Occidental
    'chihuahua': 3, 'durango': 3, 'coahuila': 3,
    # Region 4: Noreste y Sierra Madre Oriental
    'nuevo leon': 4, 'tamaulipas': 4, 'san luis potosi': 4,
    # Region 5: Occidente y Pacifico Centro
    'nayarit': 5, 'jalisco': 5, 'colima': 5, 'michoacan': 5, 'aguascalientes': 5, 'zacatecas': 5,
    # Region 6: Centro y Eje Neovolcanico
    'mexico': 6, 'cdmx': 6, 'ciudad de mexico': 6, 'morelos': 6, 'puebla': 6, 'tlaxcala': 6, 
    'hidalgo': 6, 'queretaro': 6, 'guanajuato': 6,
    # Region 7: Planicie Costera y Golfo de Mexico
    'veracruz': 7, 'tabasco': 7,
    # Region 8: Frontera Sur, Istmo y Pacifico Sur
    'oaxaca': 8, 'chiapas': 8, 'guerrero': 8,
    # Region 9: Peninsula de Yucatan y Caribe Mexicano
    'yucatan': 9, 'campeche': 9, 'quintana roo': 9
}


def normalize_name(name):
    """Normalize ANP name for matching."""
    name = name.lower().strip()
    name = re.sub(r'^(rb|pn|apff|aprn|sant|mn|santuario)\s+', '', name)
    name = name.replace('á', 'a').replace('é', 'e').replace('í', 'i')
    name = name.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    name = name.replace('\u00b4', "'").replace('\u2019', "'")
    return name


def is_marine(anp_name, metadata=None):
    """Determine if ANP is marine."""
    name_lower = anp_name.lower()
    
    # Check for purely marine indicators
    for indicator in PURELY_MARINE:
        if indicator in name_lower:
            return True
    
    # Check designation
    if metadata:
        designation = metadata.get('designation', '').lower()
        if 'marino' in designation or 'arrecife' in designation:
            return True
    
    return False


def is_coastal(anp_name, metadata=None):
    """Determine if ANP is coastal (has both marine and terrestrial)."""
    name_lower = anp_name.lower()
    
    for indicator in MARINE_INDICATORS:
        if indicator in name_lower:
            # But not purely marine
            if not is_marine(anp_name, metadata):
                return True
    
    return False


def is_island(anp_name):
    """Determine if ANP is an island."""
    name_lower = anp_name.lower()
    for indicator in ISLAND_INDICATORS:
        if indicator in name_lower:
            return True
    return False


def is_playa_sanctuary(anp_name):
    """Determine if ANP is a small beach/nesting sanctuary."""
    name_lower = anp_name.lower()
    return 'playa' in name_lower and ('santuario' in name_lower or 'tortuga' in name_lower or name_lower.startswith('playa'))


def get_size_category(area_km2):
    """Categorize ANP by size."""
    if area_km2 is None:
        return 'unknown'
    if area_km2 < TINY_SIZE_THRESHOLD:
        return 'tiny'
    if area_km2 < SMALL_SIZE_THRESHOLD:
        return 'small'
    if area_km2 < 1000:
        return 'medium'
    return 'large'


def load_simec_registered_anps():
    """Load list of ANPs with SIMEC NOM-059 data."""
    simec_path = Path(SIMEC_LIST_FILE)
    if not simec_path.exists():
        return set()
    
    with open(simec_path) as f:
        simec_list = json.load(f)
    
    # Get all normalized variants
    registered = set()
    for entry in simec_list:
        registered.add(entry.get('normalized', ''))
        for variant in entry.get('variants', []):
            registered.add(variant)
    
    return registered


def check_simec_registration(anp_name, simec_registered):
    """Check if ANP has SIMEC registration."""
    normalized = normalize_name(anp_name)
    
    for registered in simec_registered:
        if registered in normalized or normalized in registered:
            return True
    
    return False


def determine_expected_sources(characteristics):
    """Determine which data sources should have data for this ANP."""
    expected = []
    excluded = []
    
    is_marine_anp = characteristics['is_marine']
    is_terrestrial = characteristics['is_terrestrial']
    has_simec = characteristics['has_simec_registration']
    size = characteristics['size_category']
    is_playa = characteristics['is_playa_sanctuary']
    
    # WDPA - always expected
    expected.append({'source': 'wdpa', 'reason': 'All ANPs have WDPA boundaries'})
    
    # GEE datasets
    if is_terrestrial:
        expected.append({'source': 'gee_worldpop', 'reason': 'Terrestrial ANP has population grid'})
        expected.append({'source': 'gee_srtm', 'reason': 'Terrestrial ANP has elevation data'})
        expected.append({'source': 'gee_worldcover', 'reason': 'Land cover analysis possible'})
        expected.append({'source': 'gee_hansen', 'reason': 'Forest monitoring possible'})
        expected.append({'source': 'gee_worldclim', 'reason': 'Climate data available'})
        expected.append({'source': 'gee_modis_ndvi', 'reason': 'Vegetation monitoring possible'})
        expected.append({'source': 'gee_viirs', 'reason': 'Night lights measurable'})
        expected.append({'source': 'gee_modis_fire', 'reason': 'Fire monitoring possible'})
        expected.append({'source': 'gee_resolve_ecoregions', 'reason': 'Terrestrial ecoregion data'})
        expected.append({'source': 'gee_ghm', 'reason': 'Human modification index available'})
        expected.append({'source': 'gee_wri_aqueduct', 'reason': 'Water stress indicators available for terrestrial areas'})
    else:
        # Marine-only ANPs
        excluded.append({'source': 'gee_worldpop', 'reason': 'Marine ANP - no population grid'})
        excluded.append({'source': 'gee_srtm', 'reason': 'Marine ANP - no elevation data'})
        excluded.append({'source': 'gee_hansen', 'reason': 'Marine ANP - no forest'})
        excluded.append({'source': 'gee_worldclim', 'reason': 'Marine ANP - no terrestrial climate'})
        excluded.append({'source': 'gee_modis_ndvi', 'reason': 'Marine ANP - no vegetation'})
        excluded.append({'source': 'gee_modis_fire', 'reason': 'Marine ANP - no fire risk'})
        excluded.append({'source': 'gee_resolve_ecoregions', 'reason': 'Marine ANP - terrestrial ecoregions only'})
        excluded.append({'source': 'gee_ghm', 'reason': 'Marine ANP - no human modification index'})
        excluded.append({'source': 'gee_wri_aqueduct', 'reason': 'Marine ANP - water stress applies to terrestrial only'})
        
        # Some marine data sources may still work
        expected.append({'source': 'gee_worldcover', 'reason': 'May have coastal land cover data'})
        expected.append({'source': 'gee_viirs', 'reason': 'Night lights may show coastal activity'})
    
    # GBIF - expected for all but tiny playas
    if size != 'tiny' or not is_playa:
        expected.append({'source': 'gbif_species', 'reason': 'Species occurrence data available'})
        expected.append({'source': 'gbif_iucn', 'reason': 'IUCN status data via GBIF'})
    else:
        excluded.append({'source': 'gbif_species', 'reason': 'Very small playa sanctuary - limited occurrence data'})
        excluded.append({'source': 'gbif_iucn', 'reason': 'Very small playa sanctuary - limited IUCN data'})
    
    # SIMEC NOM-059 - only if registered
    if has_simec:
        expected.append({'source': 'simec_nom059', 'reason': 'ANP has SIMEC species inventory'})
    else:
        excluded.append({'source': 'simec_nom059', 'reason': 'ANP not in SIMEC inventory (~61 ANPs have inventories)'})
    
    # Enciclovida - fallback for NOM-059
    expected.append({'source': 'enciclovida_nom059', 'reason': 'Cross-reference for NOM-059 status'})
    
    # INEGI Census - only for terrestrial with communities
    if is_terrestrial and not is_marine_anp:
        if characteristics['is_island']:
            excluded.append({'source': 'inegi_census', 'reason': 'Island ANP - few/no permanent communities'})
        elif is_playa:
            excluded.append({'source': 'inegi_census', 'reason': 'Playa sanctuary - no permanent communities'})
        else:
            expected.append({'source': 'inegi_census', 'reason': 'Terrestrial ANP may have communities within bounds'})
    else:
        excluded.append({'source': 'inegi_census', 'reason': 'Marine ANP - no census localities'})
    
    return {
        'expected': expected,
        'excluded': excluded
    }


def analyze_anp(anp, simec_registered):
    """Analyze a single ANP and generate expectations."""
    anp_id = anp['id']
    anp_name = anp['name']
    
    # Load ANP data for metadata
    data_path = Path(anp['data_file'])
    metadata = {}
    area_km2 = None
    
    if data_path.exists():
        with open(data_path) as f:
            data = json.load(f)
            metadata = data.get('metadata', {})
            area_km2 = metadata.get('reported_area_km2')
    
    # Determine characteristics
    marine = is_marine(anp_name, metadata)
    coastal = is_coastal(anp_name, metadata)
    terrestrial = not marine or coastal
    island = is_island(anp_name)
    playa = is_playa_sanctuary(anp_name)
    size = get_size_category(area_km2)
    has_simec = check_simec_registration(anp_name, simec_registered)
    
    characteristics = {
        'is_marine': marine,
        'is_coastal': coastal,
        'is_terrestrial': terrestrial,
        'is_island': island,
        'is_playa_sanctuary': playa,
        'size_category': size,
        'area_km2': area_km2,
        'has_simec_registration': has_simec,
        'designation': metadata.get('designation', 'Unknown'),
        'iucn_category': metadata.get('iucn_category', 'Unknown')
    }
    
    # Generate expectations
    expectations = determine_expected_sources(characteristics)
    
    return {
        'anp_id': anp_id,
        'anp_name': anp_name,
        'characteristics': characteristics,
        'expected_sources': expectations['expected'],
        'excluded_sources': expectations['excluded']
    }


def generate_all_expectations():
    """Generate expectations for all ANPs."""
    print("Generating ANP data expectations...")
    print("=" * 60)
    
    # Load index
    with open(INDEX_FILE) as f:
        index = json.load(f)
    
    # Load SIMEC registered ANPs
    simec_registered = load_simec_registered_anps()
    print(f"Loaded {len(simec_registered)} SIMEC-registered ANP names")
    
    # Analyze each ANP
    expectations = []
    stats = {
        'total': 0,
        'marine': 0,
        'terrestrial': 0,
        'coastal': 0,
        'island': 0,
        'playa': 0,
        'has_simec': 0,
        'by_size': {'tiny': 0, 'small': 0, 'medium': 0, 'large': 0, 'unknown': 0}
    }
    
    for anp in index['anps']:
        result = analyze_anp(anp, simec_registered)
        expectations.append(result)
        
        # Update stats
        stats['total'] += 1
        chars = result['characteristics']
        if chars['is_marine']: stats['marine'] += 1
        if chars['is_terrestrial']: stats['terrestrial'] += 1
        if chars['is_coastal']: stats['coastal'] += 1
        if chars['is_island']: stats['island'] += 1
        if chars['is_playa_sanctuary']: stats['playa'] += 1
        if chars['has_simec_registration']: stats['has_simec'] += 1
        stats['by_size'][chars['size_category']] += 1
    
    # Create output structure
    output = {
        'schema_version': '1.0',
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_anps': stats['total'],
            'marine_anps': stats['marine'],
            'terrestrial_anps': stats['terrestrial'],
            'coastal_anps': stats['coastal'],
            'island_anps': stats['island'],
            'playa_sanctuaries': stats['playa'],
            'simec_registered': stats['has_simec'],
            'by_size': stats['by_size']
        },
        'anp_expectations': expectations
    }
    
    # Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nSummary:")
    print(f"  Total ANPs: {stats['total']}")
    print(f"  Marine: {stats['marine']}")
    print(f"  Terrestrial: {stats['terrestrial']}")
    print(f"  Coastal: {stats['coastal']}")
    print(f"  Islands: {stats['island']}")
    print(f"  Playa sanctuaries: {stats['playa']}")
    print(f"  SIMEC registered: {stats['has_simec']}")
    print(f"  By size: {stats['by_size']}")
    print(f"\nSaved to: {OUTPUT_FILE}")
    
    return output


def verify_expectations():
    """Verify expectations against actual data and report discrepancies."""
    print("Verifying ANP data expectations...")
    print("=" * 60)
    
    # Load expectations
    if not Path(OUTPUT_FILE).exists():
        print(f"Error: {OUTPUT_FILE} not found. Run without --verify first.")
        return
    
    with open(OUTPUT_FILE) as f:
        expectations_data = json.load(f)
    
    # Load index
    with open(INDEX_FILE) as f:
        index = json.load(f)
    
    # Map ANP ID to data
    anp_lookup = {a['id']: a for a in index['anps']}
    
    discrepancies = []
    
    for exp in expectations_data['anp_expectations']:
        anp_id = exp['anp_id']
        anp_info = anp_lookup.get(anp_id)
        if not anp_info:
            continue
        
        # Load actual data
        data_path = Path(anp_info['data_file'])
        if not data_path.exists():
            discrepancies.append({
                'anp_id': anp_id,
                'issue': 'missing_data_file',
                'details': 'No data file exists'
            })
            continue
        
        with open(data_path) as f:
            actual_data = json.load(f)
        
        # Check expected sources
        for expected in exp['expected_sources']:
            source_id = expected['source']
            
            # Map source ID to data path
            has_data = False
            if source_id == 'wdpa':
                has_data = bool(actual_data.get('metadata', {}).get('name'))
            elif source_id.startswith('gee_'):
                dataset_name = source_id.replace('gee_', '')
                datasets = actual_data.get('datasets', {})
                # Map source to dataset key
                dataset_map = {
                    'worldpop': 'population',
                    'srtm': 'elevation',
                    'worldcover': 'land_cover',
                    'hansen': 'forest',
                    'worldclim': 'climate',
                    'modis_ndvi': 'vegetation',
                    'viirs': 'night_lights',
                    'modis_fire': 'fire',
                    'resolve_ecoregions': 'biodiversity',
                    'ghm': 'human_modification'
                }
                key = dataset_map.get(dataset_name, dataset_name)
                has_data = bool(datasets.get(key))
            elif source_id == 'gbif_species':
                ext = actual_data.get('external_data', {})
                gbif = ext.get('gbif_species', {})
                has_data = gbif.get('unique_species', 0) > 0
            elif source_id == 'gbif_iucn':
                ext = actual_data.get('external_data', {})
                has_data = bool(ext.get('iucn_threatened'))
            elif source_id == 'simec_nom059':
                ext = actual_data.get('external_data', {})
                simec = ext.get('simec_nom059', {})
                has_data = simec.get('total_species', 0) > 0
            elif source_id == 'enciclovida_nom059':
                ext = actual_data.get('external_data', {})
                has_data = bool(ext.get('nom059_enciclovida'))
            elif source_id == 'inegi_census':
                ext = actual_data.get('external_data', {})
                census = ext.get('inegi_census', {})
                has_data = census.get('total_population', 0) > 0
            
            if not has_data:
                discrepancies.append({
                    'anp_id': anp_id,
                    'anp_name': exp['anp_name'],
                    'issue': 'missing_expected_data',
                    'source': source_id,
                    'expected_reason': expected['reason']
                })
    
    # Report
    print(f"\nFound {len(discrepancies)} discrepancies")
    
    if discrepancies:
        print("\nDiscrepancies by type:")
        by_source = {}
        for d in discrepancies:
            src = d.get('source', d.get('issue'))
            if src not in by_source:
                by_source[src] = []
            by_source[src].append(d['anp_name'] if 'anp_name' in d else d['anp_id'])
        
        for src, anps in sorted(by_source.items(), key=lambda x: -len(x[1])):
            print(f"\n  {src}: {len(anps)} ANPs missing")
            if len(anps) <= 5:
                for anp in anps:
                    print(f"    - {anp}")
            else:
                for anp in anps[:3]:
                    print(f"    - {anp}")
                print(f"    ... and {len(anps) - 3} more")
    
    return discrepancies


if __name__ == "__main__":
    if '--verify' in sys.argv:
        verify_expectations()
    else:
        generate_all_expectations()
