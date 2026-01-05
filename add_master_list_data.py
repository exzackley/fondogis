#!/usr/bin/env python3
"""Import master list data into ANP JSON files."""

import csv
import json
import os
import re
import unicodedata
from datetime import datetime

DATA_DIR = 'anp_data'
INDEX_FILE = 'anp_index.json'
TSV_FILE = 'master_list_anps.tsv'


def normalize_name(name):
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    name = name.lower().strip()
    name = re.sub(r'^(rb|pn|apff|aprn|sant|mn|santuario)\s+', '', name)
    for article in [' el ', ' la ', ' los ', ' las ', ' de ', ' del ', ' y ']:
        name = name.replace(article, ' ')
    name = re.sub(r'^(el|la|los|las)\s+', '', name)
    return re.sub(r'\s+', ' ', name).strip()


def parse_states(estados_str):
    if not estados_str:
        return []
    states = re.split(r',\s*|\s+y\s+', estados_str)
    return [s.strip() for s in states if s.strip()]


def parse_float(val):
    if not val:
        return None
    try:
        return round(float(val), 2)
    except (ValueError, TypeError):
        return None


def load_tsv_data():
    data = {}
    with open(TSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            name = row.get('NOMBRE', '').strip()
            if not name:
                continue
            
            norm_name = normalize_name(name)
            data[norm_name] = {
                'original_name': name,
                'num_anp': row.get('NUM_ANP', '').strip(),
                'id_anp': row.get('ID_ANP', '').strip(),
                'categoria_de_manejo': row.get('CATEGORIA DE MANEJO', '').strip(),
                'estados': parse_states(row.get('ESTADOS', '')),
                'region': row.get('REGION', '').strip(),
                'superficie_total_ha': parse_float(row.get('SUPERFICIE', '')),
                'superficie_terrestre_ha': parse_float(row.get('SUPERFICIE TERRESTRE', '')),
                'superficie_marina_ha': parse_float(row.get('SUPERFICIE MARINA', '')),
                'primer_decreto': row.get('PRIMER DECRETO', '').strip(),
                'designaciones_internacionales': row.get('DESIGNACIONES INTERNACIONALES', '').strip(),
            }
    return data


def find_match(anp_name, tsv_data):
    norm_name = normalize_name(anp_name)
    
    if norm_name in tsv_data:
        return tsv_data[norm_name]
    
    for tsv_norm, tsv_entry in tsv_data.items():
        if norm_name in tsv_norm or tsv_norm in norm_name:
            return tsv_entry
    
    norm_words = set(norm_name.split())
    best_match = None
    best_score = 0
    for tsv_norm, tsv_entry in tsv_data.items():
        tsv_words = set(tsv_norm.split())
        overlap = len(norm_words & tsv_words)
        if overlap > best_score and overlap >= 2:
            best_score = overlap
            best_match = tsv_entry
    
    return best_match


def update_anp_file(anp_id, tsv_entry):
    data_file = os.path.join(DATA_DIR, f'{anp_id}_data.json')
    
    if not os.path.exists(data_file):
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'metadata' not in data:
        data['metadata'] = {}
    
    m = data['metadata']
    m['categoria_de_manejo'] = tsv_entry['categoria_de_manejo']
    m['estados'] = tsv_entry['estados']
    m['region'] = tsv_entry['region']
    m['designaciones_internacionales'] = tsv_entry['designaciones_internacionales']
    
    if tsv_entry['superficie_total_ha'] is not None:
        m['superficie_total_ha'] = tsv_entry['superficie_total_ha']
    if tsv_entry['superficie_terrestre_ha'] is not None:
        m['superficie_terrestre_ha'] = tsv_entry['superficie_terrestre_ha']
    if tsv_entry['superficie_marina_ha'] is not None:
        m['superficie_marina_ha'] = tsv_entry['superficie_marina_ha']
    if tsv_entry['primer_decreto']:
        m['primer_decreto'] = tsv_entry['primer_decreto']
    if tsv_entry['num_anp']:
        m['num_anp'] = tsv_entry['num_anp']
    if tsv_entry['id_anp']:
        m['id_anp_conanp'] = tsv_entry['id_anp']
    
    m['master_list_updated_at'] = datetime.now().isoformat()
    
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return True


def update_index(tsv_data):
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    all_categories = set()
    all_states = set()
    all_regions = set()
    
    matched = 0
    unmatched = []
    
    for anp in index['anps']:
        tsv_entry = find_match(anp['name'], tsv_data)
        
        if tsv_entry:
            matched += 1
            anp['categoria'] = tsv_entry['categoria_de_manejo']
            anp['estados'] = tsv_entry['estados']
            anp['region'] = tsv_entry['region']
            anp['designaciones'] = tsv_entry['designaciones_internacionales']
            
            if tsv_entry['categoria_de_manejo']:
                all_categories.add(tsv_entry['categoria_de_manejo'])
            for state in tsv_entry['estados']:
                all_states.add(state)
            if tsv_entry['region']:
                all_regions.add(tsv_entry['region'])
            
            update_anp_file(anp['id'], tsv_entry)
        else:
            unmatched.append(anp['name'])
    
    index['filters'] = {
        'categorias': sorted(list(all_categories)),
        'estados': sorted(list(all_states)),
        'regiones': sorted(list(all_regions))
    }
    
    index['master_list_updated_at'] = datetime.now().isoformat()
    
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    return matched, unmatched


def main():
    print("Loading TSV data...")
    tsv_data = load_tsv_data()
    print(f"  Loaded {len(tsv_data)} ANPs from master list")
    
    print("\nUpdating ANP index and data files...")
    matched, unmatched = update_index(tsv_data)
    
    print(f"\n=== Results ===")
    print(f"Matched: {matched} ANPs")
    print(f"Unmatched: {len(unmatched)} ANPs")
    
    if unmatched:
        print("\nUnmatched ANPs:")
        for name in unmatched[:20]:
            print(f"  - {name}")
        if len(unmatched) > 20:
            print(f"  ... and {len(unmatched) - 20} more")


if __name__ == '__main__':
    main()
