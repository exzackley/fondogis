#!/usr/bin/env python3
"""
Extract External Data for Mexican Protected Areas
==================================================

This script extracts additional data from external APIs:
1. GBIF - Species occurrences within ANP boundaries
2. Enciclovida - NOM-059 conservation status for Mexican species
3. INEGI - Socioeconomic indicators (requires API token)

Usage:
    python3 extract_external_data.py "Calakmul"
    python3 extract_external_data.py --all  # Process all ANPs
    python3 extract_external_data.py --update-existing  # Add to existing data files
"""

import json
import os
import sys
import time
import re
import requests
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

DATA_DIR = 'anp_data'
INDEX_FILE = 'anp_index.json'
REFERENCE_DIR = 'reference_data'

# API Endpoints
GBIF_API = "https://api.gbif.org/v1"
ENCICLOVIDA_API = "https://enciclovida.mx"
INEGI_API = "https://www.inegi.org.mx/app/api/indicadores"

# Rate limiting
GBIF_DELAY = 0.5  # seconds between requests
ENCICLOVIDA_DELAY = 1.0


def load_boundary(boundary_file):
    """Load ANP boundary from GeoJSON file."""
    with open(boundary_file) as f:
        geojson = json.load(f)
    return geojson


def geojson_to_wkt(geojson):
    """Convert GeoJSON polygon to WKT string for GBIF API."""
    if geojson.get('type') == 'FeatureCollection':
        feature = geojson['features'][0]
    else:
        feature = geojson
    
    geom = feature.get('geometry', feature)
    coords = geom.get('coordinates', [])
    
    if geom['type'] == 'Polygon':
        ring = coords[0]
        wkt_coords = ', '.join(f"{c[0]} {c[1]}" for c in ring)
        return f"POLYGON(({wkt_coords}))"
    elif geom['type'] == 'MultiPolygon':
        # Use the largest polygon (first one usually)
        ring = coords[0][0]
        wkt_coords = ', '.join(f"{c[0]} {c[1]}" for c in ring)
        return f"POLYGON(({wkt_coords}))"
    
    return None


def get_bounding_box(geojson):
    """Get bounding box from GeoJSON for simpler queries."""
    if geojson.get('type') == 'FeatureCollection':
        feature = geojson['features'][0]
    else:
        feature = geojson
    
    geom = feature.get('geometry', feature)
    coords = geom.get('coordinates', [])
    
    all_coords = []
    def extract_coords(c):
        if isinstance(c[0], (int, float)):
            all_coords.append(c)
        else:
            for item in c:
                extract_coords(item)
    
    extract_coords(coords)
    
    if not all_coords:
        return None
    
    lons = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]
    
    return {
        'minLon': min(lons),
        'maxLon': max(lons),
        'minLat': min(lats),
        'maxLat': max(lats)
    }


def query_gbif_species(boundary_geojson, limit=500):
    """
    Query GBIF for species occurrences within an ANP boundary.
    Returns species list with counts and conservation info.
    """
    print("    Querying GBIF for species...", end=" ", flush=True)
    
    bbox = get_bounding_box(boundary_geojson)
    if not bbox:
        print("ERROR: Could not extract bounding box")
        return {"error": "Could not extract bounding box"}
    
    # Query GBIF using bounding box (more reliable than WKT for complex polygons)
    params = {
        'country': 'MX',
        'decimalLatitude': f"{bbox['minLat']},{bbox['maxLat']}",
        'decimalLongitude': f"{bbox['minLon']},{bbox['maxLon']}",
        'hasCoordinate': 'true',
        'limit': limit,
        'facet': 'speciesKey',
        'facetLimit': 200
    }
    
    try:
        response = requests.get(f"{GBIF_API}/occurrence/search", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Extract species counts from facets
        species_counts = {}
        if 'facets' in data:
            for facet in data['facets']:
                if facet['field'] == 'SPECIES_KEY':
                    for count in facet['counts']:
                        species_counts[count['name']] = count['count']
        
        # Get unique species from results
        species_set = {}
        for occ in data.get('results', []):
            species_name = occ.get('species')
            if species_name and species_name not in species_set:
                species_set[species_name] = {
                    'scientific_name': species_name,
                    'kingdom': occ.get('kingdom'),
                    'phylum': occ.get('phylum'),
                    'class': occ.get('class'),
                    'order': occ.get('order'),
                    'family': occ.get('family'),
                    'genus': occ.get('genus'),
                    'taxon_key': occ.get('speciesKey'),
                    'occurrences': species_counts.get(str(occ.get('speciesKey')), 1)
                }
        
        # Group by taxonomic class
        by_class = {}
        for sp in species_set.values():
            cls = sp.get('class') or 'Unknown'
            if cls not in by_class:
                by_class[cls] = []
            by_class[cls].append(sp['scientific_name'])
        
        result = {
            'source': 'GBIF (Global Biodiversity Information Facility)',
            'query_date': datetime.now().isoformat(),
            'total_occurrences': data.get('count', 0),
            'unique_species': len(species_set),
            'bounding_box': bbox,
            'species_by_class': {k: len(v) for k, v in by_class.items()},
            'top_species': sorted(species_set.values(), 
                                  key=lambda x: x.get('occurrences', 0), 
                                  reverse=True)[:50]
        }
        
        print(f"OK ({result['unique_species']} species, {result['total_occurrences']} records)")
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: {e}")
        return {"error": str(e)}


def query_gbif_threatened_species(boundary_geojson):
    """
    Query GBIF for IUCN threatened species in the area.
    """
    print("    Querying GBIF for threatened species (IUCN)...", end=" ", flush=True)
    
    bbox = get_bounding_box(boundary_geojson)
    if not bbox:
        print("ERROR")
        return {"error": "Could not extract bounding box"}
    
    threatened_categories = ['CR', 'EN', 'VU']  # Critically Endangered, Endangered, Vulnerable
    threatened_species = []
    
    for category in threatened_categories:
        params = {
            'country': 'MX',
            'decimalLatitude': f"{bbox['minLat']},{bbox['maxLat']}",
            'decimalLongitude': f"{bbox['minLon']},{bbox['maxLon']}",
            'hasCoordinate': 'true',
            'iucnRedListCategory': category,
            'limit': 100
        }
        
        try:
            time.sleep(GBIF_DELAY)
            response = requests.get(f"{GBIF_API}/occurrence/search", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            seen = set()
            for occ in data.get('results', []):
                species_name = occ.get('species')
                if species_name and species_name not in seen:
                    seen.add(species_name)
                    threatened_species.append({
                        'scientific_name': species_name,
                        'iucn_category': category,
                        'class': occ.get('class'),
                        'family': occ.get('family')
                    })
        except:
            pass
    
    # Group by IUCN category
    by_category = {'CR': [], 'EN': [], 'VU': []}
    for sp in threatened_species:
        cat = sp['iucn_category']
        by_category[cat].append(sp['scientific_name'])
    
    result = {
        'source': 'GBIF IUCN Red List data',
        'critically_endangered': by_category['CR'],
        'endangered': by_category['EN'],
        'vulnerable': by_category['VU'],
        'total_threatened': len(threatened_species)
    }
    
    print(f"OK ({result['total_threatened']} threatened species)")
    return result


def query_enciclovida_nom059(species_list):
    """
    Query Enciclovida for NOM-059 conservation status of species.
    Note: This queries by species name - may be slow for large lists.
    """
    print("    Checking NOM-059 status (Enciclovida)...", end=" ", flush=True)
    
    nom059_species = []
    
    # For efficiency, we'll check a sample of species
    sample_size = min(50, len(species_list))
    sample = species_list[:sample_size]
    
    for species_name in sample:
        try:
            # Search Enciclovida for the species
            params = {'nombre': species_name}
            response = requests.get(f"{ENCICLOVIDA_API}/busquedas/especies.json", 
                                   params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    for sp in data:
                        nom_status = sp.get('nom059') or sp.get('categoria_nom')
                        if nom_status:
                            nom059_species.append({
                                'scientific_name': species_name,
                                'nom059_category': nom_status,
                                'common_name': sp.get('nombre_comun_principal')
                            })
                            break
            
            time.sleep(ENCICLOVIDA_DELAY)
            
        except:
            pass
    
    # Group by NOM-059 category
    by_category = {'P': [], 'A': [], 'Pr': [], 'E': []}
    for sp in nom059_species:
        cat = sp['nom059_category']
        if cat in by_category:
            by_category[cat].append({
                'scientific_name': sp['scientific_name'],
                'common_name': sp.get('common_name')
            })
    
    result = {
        'source': 'NOM-059-SEMARNAT (via Enciclovida)',
        'endangered_P': by_category['P'],  # En peligro de extincion
        'threatened_A': by_category['A'],  # Amenazada
        'special_protection_Pr': by_category['Pr'],  # Proteccion especial
        'probably_extinct_E': by_category['E'],  # Probablemente extinta
        'total_nom059': len(nom059_species),
        'species_checked': sample_size
    }
    
    print(f"OK ({result['total_nom059']} NOM-059 species found)")
    return result


def load_simec_nom059_data():
    """Load and parse all SIMEC NOM-059 Excel files into a lookup dictionary."""
    if not HAS_PANDAS:
        print("    Warning: pandas not installed, skipping SIMEC data")
        return None
    
    simec_data = {}
    
    for region in range(1, 10):
        filepath = f"{REFERENCE_DIR}/simec_region{region}.xlsx"
        if not os.path.exists(filepath):
            continue
        
        try:
            df = pd.read_excel(filepath, engine='openpyxl')  # type: ignore
            
            for col in df.columns:
                if 'Unnamed' in str(col):
                    continue
                
                anp_name = str(col).strip()
                species_list = []
                
                for val in df[col].dropna():
                    val_str = str(val).strip()
                    if not val_str:
                        continue
                    
                    match = re.match(r'^(.+?)\s+([PAEPr]+)$', val_str)
                    if match:
                        species_name = match.group(1).strip()
                        category = match.group(2).strip()
                        species_list.append({
                            'scientific_name': species_name,
                            'nom059_category': category
                        })
                    else:
                        species_list.append({
                            'scientific_name': val_str,
                            'nom059_category': 'unknown'
                        })
                
                if species_list:
                    simec_data[anp_name] = species_list
        except Exception as e:
            print(f"    Warning: Could not load {filepath}: {e}")
    
    return simec_data


def parse_dms_coordinate(dms_str):
    """Convert degrees-minutes-seconds string to decimal degrees."""
    if not dms_str or pd.isna(dms_str):  # type: ignore
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
    if not HAS_PANDAS:
        return None
    
    filepath = f"{REFERENCE_DIR}/ITER_{state_code:02d}CSV20.csv"
    if not os.path.exists(filepath):
        return None
    
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig', low_memory=False)  # type: ignore
        df['lat_decimal'] = df['LATITUD'].apply(parse_dms_coordinate)
        df['lon_decimal'] = df['LONGITUD'].apply(parse_dms_coordinate)
        return df
    except Exception as e:
        print(f"    Warning: Could not load ITER data: {e}")
        return None


def get_inegi_socioeconomic_for_anp(bbox, state_codes=None):
    """Extract INEGI census indicators for localities within ANP bounding box."""
    if not HAS_PANDAS:
        return {'error': 'pandas not installed'}
    
    all_localities = []
    
    states_to_check = state_codes if state_codes else range(1, 33)
    for state_code in states_to_check:
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
        return {'error': 'No ITER data files found or no localities in bbox'}
    
    combined = pd.concat(all_localities, ignore_index=True)  # type: ignore
    
    def safe_sum(col):
        numeric = pd.to_numeric(combined[col], errors='coerce')  # type: ignore
        return int(numeric.sum()) if numeric.notna().any() else 0
    
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
        'avg_schooling_years': round(pd.to_numeric(combined['GRAPROES'], errors='coerce').mean(), 1) if 'GRAPROES' in combined.columns else None,  # type: ignore
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
        'sample_localities': combined['NOM_LOC'].head(10).tolist()
    }


ANP_NAME_ALIASES = {
    'chamelacuixmala': 'islas bahia chamela',
    'ria celestun': 'ria celestum',
}


def normalize_anp_name(name):
    """
    Normalize ANP name for fuzzy matching between WDPA and SIMEC names.
    Handles: prefixes, accents, abbreviations, articles.
    """
    name = name.lower().strip()
    name = re.sub(r'^(rb|pn|apff|aprn|sant|mn|santuario)\s+', '', name)
    name = name.replace('á', 'a').replace('é', 'e').replace('í', 'i')
    name = name.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    name = name.replace('\u00b4', "'").replace('\u2019', "'").replace('`', "'")
    name = re.sub(r'\bocc\.?\b', 'occidental', name)
    name = re.sub(r'\bi\.?\s', 'isla ', name)
    name = re.sub(r'\bpta\.?\b', 'punta', name)
    name = re.sub(r'\b(del|de|la|las|los|el|y)\b', ' ', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = ' '.join(name.split())
    return name


def get_simec_nom059_for_anp(anp_name, simec_data):
    """Get NOM-059 species for an ANP from SIMEC data."""
    if not simec_data:
        return None
    
    anp_normalized = normalize_anp_name(anp_name)
    anp_aliased = ANP_NAME_ALIASES.get(anp_normalized, anp_normalized)
    
    for simec_name, species in simec_data.items():
        simec_normalized = normalize_anp_name(simec_name)
        
        match = (simec_normalized in anp_normalized or 
                 anp_normalized in simec_normalized or
                 simec_normalized in anp_aliased or
                 anp_aliased in simec_normalized)
        
        if match:
            by_category = {'P': [], 'A': [], 'Pr': [], 'E': []}
            for sp in species:
                cat = sp['nom059_category']
                if cat in by_category:
                    by_category[cat].append(sp['scientific_name'])
            
            return {
                'source': 'CONANP SIMEC (NOM-059-SEMARNAT-2010)',
                'matched_simec_name': simec_name,
                'endangered_P': by_category['P'],
                'threatened_A': by_category['A'],
                'special_protection_Pr': by_category['Pr'],
                'probably_extinct_E': by_category['E'],
                'total_species': len(species)
            }
    
    return None


def extract_external_data(anp_id):
    """Extract all external data for an ANP."""
    
    # Load index to find files
    with open(INDEX_FILE) as f:
        index = json.load(f)
    
    anp = next((a for a in index['anps'] if a['id'] == anp_id), None)
    if not anp:
        print(f"ERROR: ANP '{anp_id}' not found in index")
        return None
    
    print(f"\n{'='*60}")
    print(f"Extracting External Data: {anp['name']}")
    print('='*60)
    
    # Load existing data
    data_file = anp['data_file']
    with open(data_file) as f:
        data = json.load(f)
    
    # Load boundary
    boundary = load_boundary(anp['boundary_file'])
    
    # Initialize external_data section
    if 'external_data' not in data:
        data['external_data'] = {}
    
    ext = data['external_data']
    
    # 1. GBIF Species
    print("\n  GBIF Species Data:")
    ext['gbif_species'] = query_gbif_species(boundary)
    time.sleep(GBIF_DELAY)
    
    # 2. GBIF Threatened Species
    ext['iucn_threatened'] = query_gbif_threatened_species(boundary)
    time.sleep(GBIF_DELAY)
    
    # 3. NOM-059 from SIMEC (official CONANP data - more complete)
    print("\n  CONANP SIMEC NOM-059 Species:")
    simec_data = load_simec_nom059_data()
    simec_result = get_simec_nom059_for_anp(anp['name'], simec_data)
    if simec_result:
        ext['simec_nom059'] = simec_result
        print(f"    Found {simec_result['total_species']} NOM-059 species from SIMEC")
    else:
        ext['simec_nom059'] = {'error': 'ANP not found in SIMEC data'}
        print("    ANP not found in SIMEC regional data")
    
    # 4. NOM-059 Status from Enciclovida (as backup/cross-reference)
    if ext['gbif_species'].get('top_species'):
        species_names = [sp['scientific_name'] for sp in ext['gbif_species']['top_species']]
        ext['nom059_enciclovida'] = query_enciclovida_nom059(species_names)
    else:
        ext['nom059_enciclovida'] = {'error': 'No species data to check'}
    
    # 5. INEGI Census data (socioeconomic, indigenous population)
    print("\n  INEGI Census Data:")
    bbox = get_bounding_box(boundary)
    if bbox:
        inegi_result = get_inegi_socioeconomic_for_anp(bbox)
        if not inegi_result.get('error'):
            ext['inegi_census'] = inegi_result
            print(f"    Found {inegi_result.get('localities_in_area', 0)} localities")
            print(f"    Population: {inegi_result.get('total_population', 0):,}")
            print(f"    Indigenous speakers: {inegi_result.get('indigenous_speakers_3plus', 0):,}")
        else:
            ext['inegi_census'] = inegi_result
            print(f"    {inegi_result.get('error')}")
    else:
        ext['inegi_census'] = {'error': 'Could not get bounding box'}
    
    # Add extraction metadata
    ext['extracted_at'] = datetime.now().isoformat()
    
    # Save updated data
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n  Updated: {data_file}")
    print(f"\n{'='*60}")
    print(f"SUCCESS! External data added for: {anp['name']}")
    print('='*60)
    
    return data


def process_all_anps():
    """Process all ANPs in the index."""
    with open(INDEX_FILE) as f:
        index = json.load(f)
    
    total = len(index['anps'])
    print(f"\nProcessing {total} ANPs...")
    
    for i, anp in enumerate(index['anps'], 1):
        print(f"\n[{i}/{total}] {anp['name']}")
        try:
            extract_external_data(anp['id'])
        except Exception as e:
            print(f"  ERROR: {e}")
        
        # Rate limiting between ANPs
        time.sleep(2)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_external_data.py \"<ANP name or ID>\"")
        print("       python3 extract_external_data.py --all")
        print("       python3 extract_external_data.py --list")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    if arg == '--all':
        process_all_anps()
    elif arg == '--list':
        with open(INDEX_FILE) as f:
            index = json.load(f)
        print(f"\nAvailable ANPs ({len(index['anps'])} total):")
        for anp in index['anps'][:20]:
            print(f"  {anp['id']}: {anp['name']}")
        if len(index['anps']) > 20:
            print(f"  ... and {len(index['anps']) - 20} more")
    else:
        # Try to find by ID or name
        with open(INDEX_FILE) as f:
            index = json.load(f)
        
        anp_id = None
        for anp in index['anps']:
            if anp['id'] == arg or arg.lower() in anp['name'].lower():
                anp_id = anp['id']
                break
        
        if anp_id:
            extract_external_data(anp_id)
        else:
            print(f"ERROR: ANP '{arg}' not found")
            print("Use --list to see available ANPs")


if __name__ == '__main__':
    main()
