#!/usr/bin/env python3
"""
add_cenapred_disasters.py — Parse CENAPRED historical disaster data and match to coastal ANPs.

Reads the CENAPRED base histórica 2000-2023 Excel file, filters to hydrometeorological
events (cyclones, floods, rain, storms), and matches them to coastal ANPs using
municipality overlap from CONEVAL data, with state-level fallback.

Usage:
    ./venv/bin/python3 add_cenapred_disasters.py           # Process all 38 coastal ANPs
    ./venv/bin/python3 add_cenapred_disasters.py --test     # Process first 3 ANPs only
    ./venv/bin/python3 add_cenapred_disasters.py --no-db    # Skip database, JSON only

Data source: reference_data/cenapred/basehistorica_2000_2023.xlsx
Output: dataset_type 'cenapred_disasters' in database + anp_data JSON
"""

import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from collections import defaultdict

import openpyxl

# Database support
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from db.db_utils import upsert_dataset, export_anp_to_json
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    print("Warning: db_utils not available. Use --no-db or install psycopg2-binary.")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'anp_data')
EXCEL_PATH = os.path.join(BASE_DIR, 'reference_data', 'cenapred', 'basehistorica_2000_2023.xlsx')
COASTAL_ANPS_PATH = os.path.join(BASE_DIR, 'coastal_anps_subset.json')
ALL_ANPS_PATH = os.path.join(BASE_DIR, 'all_anps_subset.json')

# Column indices in Excel (0-indexed)
COL_FECHA_INICIO = 0
COL_FECHA_FIN = 1
COL_ANO = 2
COL_CLASIFICACION = 3
COL_TIPO = 4
COL_ESTADO = 5
COL_MUNICIPIOS = 6
COL_DESCRIPCION = 7
COL_DEFUNCIONES = 8
COL_POBLACION = 9
COL_VIVIENDAS = 10
COL_ESCUELAS = 11
COL_HOSPITALES = 12
COL_COMERCIOS = 13
COL_AREA_CULTIVO = 14
COL_TOTAL_DANOS = 15

# State name normalization: maps various forms to a canonical short name
STATE_ALIASES = {
    # CONEVAL full names → canonical
    'veracruz de ignacio de la llave': 'veracruz',
    'michoacán de ocampo': 'michoacán',
    'michoacan de ocampo': 'michoacán',
    'coahuila de zaragoza': 'coahuila',
    'estado de méxico': 'méxico',
    'estado de mexico': 'méxico',
    'ciudad de méxico': 'ciudad de méxico',
    'ciudad de mexico': 'ciudad de méxico',
    # CENAPRED variations
    'campeche': 'campeche',  # Sometimes has trailing space in data
    'michoacan': 'michoacán',
    'mexico': 'méxico',
    'nuevo leon': 'nuevo león',
    'queretaro': 'querétaro',
    'quintana roo': 'quintana roo',
    'san luis potosi': 'san luis potosí',
    'yucatan': 'yucatán',
}


def normalize_state(name):
    """Normalize a state name to a canonical form for matching."""
    if not name:
        return ''
    # Strip whitespace and lowercase
    name = name.strip().lower()
    # Remove accents for lookup
    name_no_accent = unicodedata.normalize('NFD', name)
    name_no_accent = ''.join(c for c in name_no_accent if unicodedata.category(c) != 'Mn')
    # Check aliases (with and without accents)
    if name in STATE_ALIASES:
        return STATE_ALIASES[name]
    if name_no_accent in STATE_ALIASES:
        return STATE_ALIASES[name_no_accent]
    # Return the accent-stripped lowercase version
    return name_no_accent


def normalize_municipality(name):
    """Normalize a municipality name for fuzzy matching."""
    if not name:
        return ''
    name = name.strip().lower()
    # Remove accents
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    # Remove common prefixes
    for prefix in ['san ', 'santa ', 'santo ', 'villa de ', 'santiago ']:
        if name.startswith(prefix):
            # Keep both versions for matching
            pass
    return name


def safe_float(val):
    """Safely convert a value to float, returning 0.0 for None/invalid."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        val = val.strip()
        if val in ('', 'SD', 'sd', 'N/A', 'NA', '-'):
            return 0.0
        try:
            return float(val.replace(',', ''))
        except ValueError:
            return 0.0
    return 0.0


def safe_int(val):
    """Safely convert to int."""
    return int(safe_float(val))


def parse_date(val):
    """Parse a date value from the Excel file."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%d')
    if isinstance(val, str):
        val = val.strip()
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.strptime(val, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
    return str(val)[:10] if val else None


def parse_states_from_cenapred(estado_field):
    """
    Parse the Estado field from CENAPRED, which may contain multiple states.
    Returns a list of normalized state names.

    Examples:
        "Chiapas" → ["chiapas"]
        "Chiapas, Michoacan, Nuevo Leon" → ["chiapas", "michoacan", "nuevo leon"]
        "Veracruz y Tamaulipas" → ["veracruz", "tamaulipas"]
        "Varios Estados" → []
    """
    if not estado_field:
        return []
    estado_field = estado_field.strip()
    if estado_field.lower() in ('varios estados', 'sd', ''):
        return []
    # Split by comma or " y "
    parts = re.split(r',\s*|\s+y\s+', estado_field)
    return [normalize_state(p) for p in parts if p.strip()]


def parse_municipalities_from_cenapred(muni_field):
    """
    Parse the Municipios Afectados field from CENAPRED.
    Returns a list of normalized municipality names, or empty list if non-specific.

    Handles: "Los Cabos, La Paz", "Varios Municipios", "SD", "3", None
    """
    if not muni_field:
        return []
    muni_str = str(muni_field).strip()
    # Check for non-specific values
    lower = muni_str.lower()
    if lower in ('varios municipios', 'sd', 'none', '', 'sin datos', 'n/a'):
        return []
    # Check if it's just a number (count of municipalities)
    try:
        int(muni_str)
        return []  # Just a count, not names
    except ValueError:
        pass
    # Split by comma
    parts = [p.strip() for p in muni_str.split(',')]
    return [normalize_municipality(p) for p in parts if p.strip()]


def load_cenapred_data(excel_path):
    """
    Load and parse CENAPRED disaster data, filtering to hydrometeorological events.
    Returns list of event dicts.
    """
    print(f"Loading CENAPRED data from {excel_path}...")
    wb = openpyxl.load_workbook(excel_path, read_only=True)
    ws = wb.active

    events = []
    skipped = 0
    total = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        total += 1
        clasificacion = row[COL_CLASIFICACION]
        if not clasificacion or str(clasificacion).strip() != 'Hidrometeorológico':
            skipped += 1
            continue

        tipo = str(row[COL_TIPO]).strip() if row[COL_TIPO] else 'Sin clasificación'
        # Skip formula errors
        if tipo.startswith('=+'):
            tipo = 'Sin clasificación'

        event = {
            'fecha_inicio': parse_date(row[COL_FECHA_INICIO]),
            'fecha_fin': parse_date(row[COL_FECHA_FIN]),
            'ano': safe_int(row[COL_ANO]),
            'tipo': tipo,
            'estado_raw': str(row[COL_ESTADO]).strip() if row[COL_ESTADO] else '',
            'estados': parse_states_from_cenapred(row[COL_ESTADO]),
            'municipios_raw': str(row[COL_MUNICIPIOS]).strip() if row[COL_MUNICIPIOS] else '',
            'municipios': parse_municipalities_from_cenapred(row[COL_MUNICIPIOS]),
            'descripcion': str(row[COL_DESCRIPCION])[:500] if row[COL_DESCRIPCION] else '',
            'defunciones': safe_int(row[COL_DEFUNCIONES]),
            'poblacion_afectada': safe_int(row[COL_POBLACION]),
            'viviendas_danadas': safe_int(row[COL_VIVIENDAS]),
            'escuelas': safe_int(row[COL_ESCUELAS]),
            'hospitales': safe_int(row[COL_HOSPITALES]),
            'comercios': safe_int(row[COL_COMERCIOS]),
            'area_cultivo': safe_float(row[COL_AREA_CULTIVO]),
            'total_danos_mdp': safe_float(row[COL_TOTAL_DANOS]),
        }
        events.append(event)

    wb.close()
    print(f"  Total rows: {total}")
    print(f"  Hydrometeorological events: {len(events)}")
    print(f"  Skipped (non-hydro): {skipped}")
    return events


def load_anp_municipalities(anp_id, data_file_path):
    """
    Load municipality info for an ANP from its data file.
    Returns dict with 'estados' (normalized), 'municipalities' (normalized names),
    and 'match_method' indicator.
    """
    if not os.path.exists(data_file_path):
        return {'estados': [], 'municipalities': [], 'match_method': 'no_data'}

    with open(data_file_path) as f:
        data = json.load(f)

    # Get states from metadata
    estados_raw = data.get('metadata', {}).get('estados', [])
    estados = [normalize_state(s) for s in estados_raw]

    # Get municipalities from CONEVAL data
    coneval = data.get('external_data', {}).get('coneval_irs', {})
    munis = coneval.get('municipalities', [])

    if munis:
        # Build normalized municipality name set
        muni_names = []
        for m in munis:
            name = m.get('name', '')
            state = m.get('state', '')
            norm_name = normalize_municipality(name)
            norm_state = normalize_state(state)
            muni_names.append({
                'name': name,
                'name_normalized': norm_name,
                'state': state,
                'state_normalized': norm_state,
            })
            # Also add the state to estados if not already there
            if norm_state and norm_state not in estados:
                estados.append(norm_state)

        return {
            'estados': estados,
            'municipalities': muni_names,
            'match_method': 'municipality_overlap',
        }
    else:
        return {
            'estados': estados,
            'municipalities': [],
            'match_method': 'state_level',
        }


def match_event_to_anp(event, anp_info):
    """
    Check if a CENAPRED event matches an ANP.
    Returns match type: 'municipality', 'state', or None.

    Strategy:
    1. Check if any event state matches any ANP state
    2. If municipality data available, check for municipality overlap
    3. If no municipality data or event has "Varios Municipios", use state-level match
    """
    event_states = event['estados']
    anp_states = anp_info['estados']

    # Step 1: State match
    state_match = False
    for es in event_states:
        if es in anp_states:
            state_match = True
            break

    if not state_match:
        return None

    # Step 2: If ANP has municipality data, try municipality matching
    if anp_info['municipalities'] and event['municipios']:
        anp_muni_names = set(m['name_normalized'] for m in anp_info['municipalities'])
        event_munis = set(event['municipios'])

        # Direct name match
        if anp_muni_names & event_munis:
            return 'municipality'

        # Fuzzy: check if any event municipality name is contained in any ANP municipality name or vice versa
        for em in event_munis:
            for am in anp_muni_names:
                if em and am and (em in am or am in em):
                    return 'municipality'

        # No municipality match - this event is in the same state but different municipalities
        # Don't include it (too far from ANP)
        return None

    # Step 3: No municipality data on event or ANP → state-level match
    if state_match:
        return 'state'

    return None


def aggregate_events(matched_events, match_method):
    """
    Aggregate a list of matched events into summary statistics.
    Returns the aggregated data dict.
    """
    if not matched_events:
        return {
            'source': 'CENAPRED Atlas Nacional de Riesgos 2000-2023',
            'period': '2000-2023',
            'filter': 'Hidrometeorológico only',
            'match_method': match_method,
            'total_events': 0,
            'total_deaths': 0,
            'total_affected': 0,
            'total_houses_damaged': 0,
            'total_damage_million_pesos': 0.0,
            'by_type': {},
            'by_year': {},
            'worst_event': None,
            'data_available': True,
            'extracted_at': datetime.now().isoformat(),
        }

    total_deaths = sum(e['defunciones'] for e in matched_events)
    total_affected = sum(e['poblacion_afectada'] for e in matched_events)
    total_houses = sum(e['viviendas_danadas'] for e in matched_events)
    total_damage = sum(e['total_danos_mdp'] for e in matched_events)

    # By type
    by_type = defaultdict(lambda: {'events': 0, 'deaths': 0, 'affected': 0, 'damage_mdp': 0.0})
    for e in matched_events:
        t = by_type[e['tipo']]
        t['events'] += 1
        t['deaths'] += e['defunciones']
        t['affected'] += e['poblacion_afectada']
        t['damage_mdp'] += e['total_danos_mdp']

    # By year
    by_year = defaultdict(lambda: {'events': 0, 'deaths': 0, 'affected': 0, 'damage_mdp': 0.0})
    for e in matched_events:
        y = by_year[str(e['ano'])]
        y['events'] += 1
        y['deaths'] += e['defunciones']
        y['affected'] += e['poblacion_afectada']
        y['damage_mdp'] += e['total_danos_mdp']

    # Worst event: by deaths first, then affected, then damage
    worst = max(matched_events, key=lambda e: (e['defunciones'], e['poblacion_afectada'], e['total_danos_mdp']))

    worst_event = {
        'date': worst['fecha_inicio'],
        'type': worst['tipo'],
        'description': worst['descripcion'][:300],
        'deaths': worst['defunciones'],
        'affected': worst['poblacion_afectada'],
        'houses_damaged': worst['viviendas_danadas'],
        'damage_mdp': worst['total_danos_mdp'],
        'state': worst['estado_raw'],
        'municipalities': worst['municipios_raw'],
    }

    # Round damage totals
    by_type_clean = {}
    for k, v in sorted(by_type.items(), key=lambda x: x[1]['events'], reverse=True):
        by_type_clean[k] = {
            'events': v['events'],
            'deaths': v['deaths'],
            'affected': v['affected'],
            'damage_mdp': round(v['damage_mdp'], 2),
        }

    by_year_clean = {}
    for k, v in sorted(by_year.items()):
        by_year_clean[k] = {
            'events': v['events'],
            'deaths': v['deaths'],
            'affected': v['affected'],
            'damage_mdp': round(v['damage_mdp'], 2),
        }

    # Count municipality vs state matched
    muni_count = sum(1 for e in matched_events if e.get('_match_type') == 'municipality')
    state_count = sum(1 for e in matched_events if e.get('_match_type') == 'state')

    return {
        'source': 'CENAPRED Atlas Nacional de Riesgos 2000-2023',
        'period': '2000-2023',
        'filter': 'Hidrometeorológico only',
        'match_method': match_method,
        'municipality_matched_events': muni_count,
        'state_matched_events': state_count,
        'total_events': len(matched_events),
        'total_deaths': total_deaths,
        'total_affected': total_affected,
        'total_houses_damaged': total_houses,
        'total_damage_million_pesos': round(total_damage, 2),
        'by_type': by_type_clean,
        'by_year': by_year_clean,
        'worst_event': worst_event,
        'data_available': True,
        'extracted_at': datetime.now().isoformat(),
    }


def process_all_anps(events, test_mode=False, use_database=True, use_all=False, skip_existing=False):
    """
    Match CENAPRED events to each ANP and save results.
    """
    # Load ANPs list
    anps_path = ALL_ANPS_PATH if use_all else COASTAL_ANPS_PATH
    with open(anps_path) as f:
        anps_data = json.load(f)

    anps = [a for a in anps_data['matched_anps'] if a['has_data']]
    if test_mode:
        anps = anps[:3]
        print(f"\n🧪 TEST MODE: Processing first {len(anps)} ANPs only\n")
    else:
        label = "all" if use_all else "coastal"
        print(f"\nProcessing {len(anps)} {label} ANPs...\n")

    results = {}
    total_matched = 0
    skipped_existing = 0

    for anp in anps:
        anp_id = anp['id']
        anp_name = anp.get('matched_name', anp_id)
        data_file = os.path.join(DATA_DIR, anp['data_file']) if anp.get('data_file') else None

        if not data_file or not os.path.exists(data_file):
            print(f"  ⚠️  {anp_name}: No data file found, skipping")
            continue

        # Skip if already has cenapred_disasters data
        if skip_existing:
            try:
                with open(data_file) as f:
                    existing = json.load(f)
                if existing.get('external_data', {}).get('cenapred_disasters'):
                    skipped_existing += 1
                    continue
            except Exception:
                pass

        # Load ANP municipality info
        anp_info = load_anp_municipalities(anp_id, data_file)

        # Match events
        matched_events = []
        for event in events:
            match_type = match_event_to_anp(event, anp_info)
            if match_type:
                event_copy = dict(event)
                event_copy['_match_type'] = match_type
                matched_events.append(event_copy)

        # Determine effective match method
        if anp_info['municipalities']:
            match_method = 'municipality_overlap'
        else:
            match_method = 'state_level'

        # Aggregate
        agg = aggregate_events(matched_events, match_method)
        total_matched += agg['total_events']

        print(f"  {'✅' if agg['total_events'] > 0 else '⚪'} {anp_name}")
        print(f"     States: {anp_info['estados']}, Munis: {len(anp_info['municipalities'])}, "
              f"Method: {match_method}")
        print(f"     Events: {agg['total_events']}, Deaths: {agg['total_deaths']}, "
              f"Affected: {agg['total_affected']:,}, Damage: ${agg['total_damage_million_pesos']:,.1f}M MXN")

        # Save to database
        if use_database and HAS_DATABASE:
            try:
                upsert_dataset(anp_id, 'cenapred_disasters', agg, source='cenapred')
                export_anp_to_json(anp_id, DATA_DIR)
                print(f"     💾 Saved to database + JSON")
            except Exception as e:
                print(f"     ❌ Database error: {e}")
                # Fall back to JSON-only
                _save_to_json(anp_id, data_file, agg)
        else:
            _save_to_json(anp_id, data_file, agg)

        results[anp_id] = agg

    print(f"\n{'='*60}")
    print(f"Summary: {len(results)} ANPs processed, {total_matched} total event matches")
    if skip_existing and skipped_existing:
        print(f"Skipped (already had data): {skipped_existing}")
    print(f"{'='*60}")

    # Save summary
    summary_name = 'cenapred_all_summary.json' if use_all else 'cenapred_coastal_summary.json'
    summary_path = os.path.join(BASE_DIR, 'reference_data', 'cenapred', summary_name)
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSummary saved to {summary_path}")

    return results


def _save_to_json(anp_id, data_file, agg):
    """Save CENAPRED data directly to ANP JSON file (no-db mode)."""
    try:
        with open(data_file) as f:
            data = json.load(f)

        if 'external_data' not in data:
            data['external_data'] = {}
        data['external_data']['cenapred_disasters'] = agg

        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"     💾 Saved to JSON ({data_file})")
    except Exception as e:
        print(f"     ❌ JSON save error: {e}")


def main():
    test_mode = '--test' in sys.argv
    use_database = HAS_DATABASE and '--no-db' not in sys.argv
    use_all = '--all' in sys.argv
    skip_existing = '--skip-existing' in sys.argv

    if use_database:
        print("Database mode: ON")
    else:
        print("Database mode: OFF (JSON only)")

    if use_all:
        print("ANP scope: ALL (227 ANPs)")
    else:
        print("ANP scope: Coastal only (38 ANPs)")

    # Load CENAPRED data
    events = load_cenapred_data(EXCEL_PATH)

    # Show type distribution
    type_counts = defaultdict(int)
    for e in events:
        type_counts[e['tipo']] += 1
    print("\nEvent types:")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    # Process all ANPs
    results = process_all_anps(events, test_mode=test_mode, use_database=use_database,
                               use_all=use_all, skip_existing=skip_existing)

    # Print top ANPs by damage
    print("\n📊 Top 10 ANPs by total damage (million MXN):")
    ranked = sorted(results.items(), key=lambda x: x[1]['total_damage_million_pesos'], reverse=True)
    for i, (anp_id, agg) in enumerate(ranked[:10], 1):
        print(f"  {i:2d}. {anp_id}: ${agg['total_damage_million_pesos']:,.1f}M, "
              f"{agg['total_events']} events, {agg['total_deaths']} deaths")

    print("\n📊 Top 10 ANPs by deaths:")
    ranked = sorted(results.items(), key=lambda x: x[1]['total_deaths'], reverse=True)
    for i, (anp_id, agg) in enumerate(ranked[:10], 1):
        print(f"  {i:2d}. {anp_id}: {agg['total_deaths']} deaths, "
              f"{agg['total_events']} events, {agg['total_affected']:,} affected")


if __name__ == '__main__':
    main()
