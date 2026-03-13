#!/usr/bin/env python3
"""
add_declaratorias_riesgo.py — Download and parse Declaratorias de Desastre and Emergencia
from datos.gob.mx, match to ANPs using municipality overlap.

Data sources:
  - Declaratorias de Desastre: SSPC/CNPC via datos.gob.mx
  - Declaratorias de Emergencia: SSPC/CNPC via datos.gob.mx

Usage:
    ./venv/bin/python3 add_declaratorias_riesgo.py           # Process all ANPs
    ./venv/bin/python3 add_declaratorias_riesgo.py --test     # Process first 3 ANPs only
    ./venv/bin/python3 add_declaratorias_riesgo.py --no-db    # Skip database, JSON only

Output: dataset_type 'declaratorias_riesgo' in database + anp_data JSON
"""

import csv
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from collections import defaultdict

import requests

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
ALL_ANPS_PATH = os.path.join(BASE_DIR, 'all_anps_subset.json')
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'reference_data', 'declaratorias')

# CSV URLs
URL_DESASTRE = 'https://repodatos.atdt.gob.mx/api_update/secretaria_seguridad/gestion_riesgos/declaratorias_desastre_4to_trim_2025.csv'
URL_EMERGENCIA = 'https://repodatos.atdt.gob.mx/api_update/secretaria_seguridad/gestion_riesgos/declaratorias_emergencia_4to_trim_2025.csv'

# State name normalization
STATE_ALIASES = {
    'veracruz de ignacio de la llave': 'veracruz',
    'michoacán de ocampo': 'michoacan',
    'michoacan de ocampo': 'michoacan',
    'coahuila de zaragoza': 'coahuila',
    'estado de méxico': 'mexico',
    'estado de mexico': 'mexico',
    'ciudad de méxico': 'ciudad de mexico',
    'ciudad de mexico': 'ciudad de mexico',
    'campeche': 'campeche',
    'michoacan': 'michoacan',
    'mexico': 'mexico',
    'nuevo leon': 'nuevo leon',
    'queretaro': 'queretaro',
    'quintana roo': 'quintana roo',
    'san luis potosi': 'san luis potosi',
    'yucatan': 'yucatan',
    'veracruz': 'veracruz',
}


def normalize_state(name):
    """Normalize a state name to a canonical form for matching."""
    if not name:
        return ''
    name = name.strip().lower()
    # Remove accents
    name_no_accent = unicodedata.normalize('NFD', name)
    name_no_accent = ''.join(c for c in name_no_accent if unicodedata.category(c) != 'Mn')
    if name in STATE_ALIASES:
        return STATE_ALIASES[name]
    if name_no_accent in STATE_ALIASES:
        return STATE_ALIASES[name_no_accent]
    return name_no_accent


def normalize_municipality(name):
    """Normalize a municipality name for fuzzy matching."""
    if not name:
        return ''
    name = name.strip().lower()
    # Remove accents
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return name


def parse_cost(val):
    """Parse a cost string like '$12,274,813.19' or '$-' to float."""
    if not val:
        return 0.0
    val = str(val).strip()
    if val in ('', '$-', '-', 'N/A', 'NA', 'SD', 'sd'):
        return 0.0
    # Remove $ and commas
    val = val.replace('$', '').replace(',', '').strip()
    if val in ('', '-'):
        return 0.0
    try:
        return float(val)
    except ValueError:
        return 0.0


def safe_int(val):
    """Safely convert to int."""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    val = str(val).strip()
    if val in ('', 'SD', 'sd', 'N/A', 'NA', '-'):
        return 0
    # Remove commas
    val = val.replace(',', '')
    try:
        return int(float(val))
    except ValueError:
        return 0


def parse_year(val):
    """Parse a year value, returning None for non-numeric values."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        y = int(val)
        if 1900 <= y <= 2100:
            return y
        return None
    val = str(val).strip()
    try:
        y = int(float(val))
        if 1900 <= y <= 2100:
            return y
        return None
    except ValueError:
        return None


def parse_municipalities_field(muni_field):
    """
    Parse the nombre_municipios_corroborados field.
    Municipalities come as comma-separated or " y " separated text.
    Returns list of normalized municipality names.
    """
    if not muni_field:
        return []
    muni_str = str(muni_field).strip()
    lower = muni_str.lower()
    if lower in ('', 'sd', 'none', 'n/a', 'na', 'sin datos', 'varios municipios'):
        return []
    # Check if it's just a number
    try:
        int(muni_str)
        return []
    except ValueError:
        pass
    # Split by comma first, then by " y " within each part
    parts = []
    for segment in muni_str.split(','):
        segment = segment.strip()
        if not segment:
            continue
        # Split by " y " only if it looks like a separator (not part of a name like "San Juan y ...")
        sub_parts = re.split(r'\s+y\s+', segment)
        parts.extend(sub_parts)
    return [normalize_municipality(p) for p in parts if p.strip()]


def download_csv(url, filename):
    """Download a CSV file if not already present."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(filepath):
        print(f"  Using cached: {filepath}")
        return filepath
    print(f"  Downloading: {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with open(filepath, 'wb') as f:
        f.write(resp.content)
    print(f"  Saved to: {filepath}")
    return filepath


def detect_encoding(filepath):
    """Try common encodings for Mexican government CSVs."""
    for enc in ('utf-8', 'latin-1', 'cp1252', 'iso-8859-1'):
        try:
            with open(filepath, 'r', encoding=enc) as f:
                f.read(2000)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 'latin-1'


def load_desastre_csv(filepath):
    """Load declaratorias de desastre CSV. Returns list of event dicts."""
    encoding = detect_encoding(filepath)
    print(f"  Reading desastre CSV (encoding: {encoding})...")
    events = []
    skipped = 0
    with open(filepath, 'r', encoding=encoding) as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = parse_year(row.get('anio', ''))
            if year is None:
                skipped += 1
                continue

            estado_raw = row.get('entidad_federativa', '').strip()
            estado_norm = normalize_state(estado_raw)
            munis_raw = row.get('nombre_municipios_corroborados', '')
            munis = parse_municipalities_field(munis_raw)
            tipo_fenomeno = row.get('tipo_fenomeno', '').strip()
            evento = row.get('evento', '').strip()
            sectores = row.get('sectores_afectados', '').strip()

            events.append({
                'ano': year,
                'estado_raw': estado_raw,
                'estado': estado_norm,
                'evento': evento,
                'tipo_fenomeno': tipo_fenomeno,
                'municipios_raw': munis_raw.strip() if munis_raw else '',
                'municipios': munis,
                'numero_municipios': safe_int(row.get('numero_municipios_corroborados', 0)),
                'sectores_afectados': sectores,
                'fecha_publicacion_dof': row.get('fecha_publicacion_dof', '').strip(),
            })

    print(f"  Desastre events loaded: {len(events)} (skipped {skipped} invalid rows)")
    return events


def load_emergencia_csv(filepath):
    """Load declaratorias de emergencia CSV. Returns list of event dicts."""
    encoding = detect_encoding(filepath)
    print(f"  Reading emergencia CSV (encoding: {encoding})...")
    events = []
    skipped = 0
    with open(filepath, 'r', encoding=encoding) as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = parse_year(row.get('anio_ocurrencia_evento', ''))
            if year is None:
                skipped += 1
                continue

            estado_raw = row.get('entidad_federativa', '').strip()
            estado_norm = normalize_state(estado_raw)
            munis_raw = row.get('nombre_municipios_corroborados', '')
            munis = parse_municipalities_field(munis_raw)
            tipo_fenomeno = row.get('tipo_fenomeno', '').strip()
            amenaza = row.get('amenaza_natural', '').strip()
            pob_afectada = safe_int(row.get('poblacion_afectada', 0))
            pob_atendida = safe_int(row.get('poblacion_atendida', 0))
            costo = parse_cost(row.get('costo_total_declaratoria', ''))

            events.append({
                'ano': year,
                'estado_raw': estado_raw,
                'estado': estado_norm,
                'amenaza_natural': amenaza,
                'tipo_fenomeno': tipo_fenomeno,
                'municipios_raw': munis_raw.strip() if munis_raw else '',
                'municipios': munis,
                'numero_municipios': safe_int(row.get('numero_municipios_corroborados', 0)),
                'poblacion_afectada': pob_afectada,
                'poblacion_atendida': pob_atendida,
                'costo_total': costo,
            })

    print(f"  Emergencia events loaded: {len(events)} (skipped {skipped} invalid rows)")
    return events


def load_anp_municipalities(anp_id, data_file_path):
    """
    Load municipality info for an ANP from its data file.
    For coastal ANPs, uses the authoritative FMCN municipality list.
    For non-coastal ANPs, falls back to CONEVAL data.
    Returns dict with 'estados', 'municipalities', and 'match_method'.
    """
    # For coastal ANPs, use authoritative municipality list
    try:
        from coastal_anps_registry import is_coastal_anp, get_coastal_anp_municipalities
        if is_coastal_anp(anp_id):
            coastal_munis = get_coastal_anp_municipalities(anp_id)
            if coastal_munis:
                muni_names = []
                estados = []
                for m in coastal_munis:
                    norm_name = normalize_municipality(m['municipio'])
                    norm_state = normalize_state(m['state'])
                    muni_names.append({
                        'name': m['municipio'],
                        'name_normalized': norm_name,
                        'state': m['state'],
                        'state_normalized': norm_state,
                    })
                    if norm_state and norm_state not in estados:
                        estados.append(norm_state)
                return {
                    'estados': estados,
                    'municipalities': muni_names,
                    'match_method': 'authoritative_coastal_list',
                }
    except ImportError:
        pass

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
            'match_method': 'no_municipalities',
        }


def match_event_to_anp(event_estado, event_munis, anp_info):
    """
    Check if an event matches an ANP via municipality overlap.
    Returns True if matched, False otherwise.

    Strategy (municipality-only, no state-level fallback):
    1. Check if event state matches any ANP state (quick filter)
    2. Require municipality overlap on both sides
    """
    anp_states = anp_info['estados']

    # State match check
    if event_estado not in anp_states:
        return False

    # Require municipality overlap
    if not anp_info['municipalities'] or not event_munis:
        return False

    anp_muni_names = set(m['name_normalized'] for m in anp_info['municipalities'])

    # Direct name match
    if anp_muni_names & set(event_munis):
        return True

    # Fuzzy: substring containment
    for em in event_munis:
        for am in anp_muni_names:
            if em and am and (em in am or am in em):
                return True

    return False


def get_matched_municipalities(event_munis, anp_info):
    """Return list of municipality names that matched."""
    if not anp_info['municipalities'] or not event_munis:
        return []
    anp_muni_map = {m['name_normalized']: m['name'] for m in anp_info['municipalities']}
    matched = set()
    for em in event_munis:
        for am_norm, am_name in anp_muni_map.items():
            if em and am_norm and (em == am_norm or em in am_norm or am_norm in em):
                matched.add(am_name)
    return sorted(matched)


def aggregate_for_anp(desastre_matched, emergencia_matched, matched_munis, match_method):
    """Aggregate matched declaratorias into summary for one ANP."""
    # Determine year ranges from actual data
    des_years = [e['ano'] for e in desastre_matched]
    eme_years = [e['ano'] for e in emergencia_matched]

    if des_years:
        period_desastre = f"{min(des_years)}-{max(des_years)}"
    else:
        period_desastre = "N/A"

    if eme_years:
        period_emergencia = f"{min(eme_years)}-{max(eme_years)}"
    else:
        period_emergencia = "N/A"

    total_pob_afectada = sum(e['poblacion_afectada'] for e in emergencia_matched)
    total_pob_atendida = sum(e['poblacion_atendida'] for e in emergencia_matched)
    total_costo = sum(e['costo_total'] for e in emergencia_matched)

    # by_type: combine desastre + emergencia counts by tipo_fenomeno
    by_type = defaultdict(lambda: {'desastre': 0, 'emergencia': 0})
    for e in desastre_matched:
        t = e['tipo_fenomeno'] if e['tipo_fenomeno'] else 'Sin clasificar'
        by_type[t]['desastre'] += 1
    for e in emergencia_matched:
        t = e['tipo_fenomeno'] if e['tipo_fenomeno'] else 'Sin clasificar'
        by_type[t]['emergencia'] += 1

    # by_year
    all_years = set(des_years + eme_years)
    by_year = {}
    for y in sorted(all_years):
        yr_str = str(y)
        des_count = sum(1 for e in desastre_matched if e['ano'] == y)
        eme_count = sum(1 for e in emergencia_matched if e['ano'] == y)
        pob_af = sum(e['poblacion_afectada'] for e in emergencia_matched if e['ano'] == y)
        costo = sum(e['costo_total'] for e in emergencia_matched if e['ano'] == y)
        by_year[yr_str] = {
            'desastre': des_count,
            'emergencia': eme_count,
            'poblacion_afectada': pob_af,
            'costo': round(costo, 2),
        }

    # sectores_afectados from desastre
    sectores = set()
    for e in desastre_matched:
        if e['sectores_afectados']:
            for s in re.split(r',\s*', e['sectores_afectados']):
                s = s.strip()
                if s:
                    sectores.add(s)

    # Detail lists
    desastre_detail = []
    for e in desastre_matched:
        desastre_detail.append({
            'ano': e['ano'],
            'estado': e['estado_raw'],
            'evento': e['evento'],
            'municipios': e['municipios_raw'],
            'tipo_fenomeno': e['tipo_fenomeno'],
            'sectores_afectados': e['sectores_afectados'],
        })

    emergencia_detail = []
    for e in emergencia_matched:
        emergencia_detail.append({
            'ano': e['ano'],
            'estado': e['estado_raw'],
            'amenaza_natural': e['amenaza_natural'],
            'municipios': e['municipios_raw'],
            'poblacion_afectada': e['poblacion_afectada'],
            'poblacion_atendida': e['poblacion_atendida'],
            'costo_total': round(e['costo_total'], 2),
            'tipo_fenomeno': e['tipo_fenomeno'],
        })

    by_type_clean = {}
    for k, v in sorted(by_type.items(), key=lambda x: x[1]['desastre'] + x[1]['emergencia'], reverse=True):
        by_type_clean[k] = dict(v)

    has_data = len(desastre_matched) > 0 or len(emergencia_matched) > 0

    return {
        'source': 'datos.gob.mx - Gestion de Riesgos (SSPC/CNPC)',
        'period_desastre': period_desastre,
        'period_emergencia': period_emergencia,
        'total_declaratorias_desastre': len(desastre_matched),
        'total_declaratorias_emergencia': len(emergencia_matched),
        'total_poblacion_afectada': total_pob_afectada,
        'total_poblacion_atendida': total_pob_atendida,
        'total_costo_declaratorias_pesos': round(total_costo, 2),
        'municipios_match': matched_munis,
        'match_method': match_method,
        'by_type': by_type_clean,
        'by_year': by_year,
        'sectores_afectados': sorted(sectores),
        'declaratorias_desastre': desastre_detail,
        'declaratorias_emergencia': emergencia_detail,
        'data_available': has_data,
        'extracted_at': datetime.now().isoformat(),
    }


def _save_to_json(anp_id, data_file, agg):
    """Save declaratorias data directly to ANP JSON file (no-db mode)."""
    try:
        with open(data_file) as f:
            data = json.load(f)

        if 'external_data' not in data:
            data['external_data'] = {}
        data['external_data']['declaratorias_riesgo'] = agg

        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"     Saved to JSON ({data_file})")
    except Exception as e:
        print(f"     JSON save error: {e}")


def process_all_anps(desastre_events, emergencia_events, test_mode=False, use_database=True):
    """Match declaratorias to each ANP and save results."""
    with open(ALL_ANPS_PATH) as f:
        anps_data = json.load(f)

    anps = [a for a in anps_data['matched_anps'] if a['has_data']]
    if test_mode:
        anps = anps[:3]
        print(f"\nTEST MODE: Processing first {len(anps)} ANPs only\n")
    else:
        print(f"\nProcessing {len(anps)} ANPs...\n")

    results = {}
    total_des_matched = 0
    total_eme_matched = 0

    for anp in anps:
        anp_id = anp['id']
        anp_name = anp.get('matched_name', anp_id)
        data_file = os.path.join(DATA_DIR, anp['data_file']) if anp.get('data_file') else None

        if not data_file or not os.path.exists(data_file):
            print(f"  SKIP {anp_name}: No data file found")
            continue

        # Load ANP municipality info
        anp_info = load_anp_municipalities(anp_id, data_file)

        if not anp_info['municipalities']:
            print(f"  SKIP {anp_name}: No municipality data (cannot match)")
            continue

        # Match desastre events
        matched_des = []
        all_matched_munis = set()
        for event in desastre_events:
            if match_event_to_anp(event['estado'], event['municipios'], anp_info):
                matched_des.append(event)
                munis = get_matched_municipalities(event['municipios'], anp_info)
                all_matched_munis.update(munis)

        # Match emergencia events
        matched_eme = []
        for event in emergencia_events:
            if match_event_to_anp(event['estado'], event['municipios'], anp_info):
                matched_eme.append(event)
                munis = get_matched_municipalities(event['municipios'], anp_info)
                all_matched_munis.update(munis)

        matched_munis = sorted(all_matched_munis)

        # Aggregate
        agg = aggregate_for_anp(matched_des, matched_eme, matched_munis, anp_info['match_method'])
        total_des_matched += agg['total_declaratorias_desastre']
        total_eme_matched += agg['total_declaratorias_emergencia']

        status = 'OK' if (agg['total_declaratorias_desastre'] > 0 or agg['total_declaratorias_emergencia'] > 0) else '--'
        print(f"  [{status}] {anp_name}")
        print(f"       Munis: {len(anp_info['municipalities'])}, Desastre: {agg['total_declaratorias_desastre']}, "
              f"Emergencia: {agg['total_declaratorias_emergencia']}, "
              f"Pob afectada: {agg['total_poblacion_afectada']:,}, "
              f"Costo: ${agg['total_costo_declaratorias_pesos']:,.2f}")

        # Save to database
        if use_database and HAS_DATABASE:
            try:
                upsert_dataset(anp_id, 'declaratorias_riesgo', agg, source='datos_gob_mx')
                export_anp_to_json(anp_id, DATA_DIR)
                print(f"       Saved to database + JSON")
            except Exception as e:
                print(f"       Database error: {e}")
                _save_to_json(anp_id, data_file, agg)
        else:
            _save_to_json(anp_id, data_file, agg)

        results[anp_id] = agg

    print(f"\n{'='*60}")
    print(f"Summary: {len(results)} ANPs processed")
    print(f"  Total desastre matches: {total_des_matched}")
    print(f"  Total emergencia matches: {total_eme_matched}")
    anps_with_data = sum(1 for a in results.values() if a['data_available'])
    print(f"  ANPs with at least one match: {anps_with_data}")
    print(f"{'='*60}")

    # Save summary
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    summary_path = os.path.join(DOWNLOAD_DIR, 'declaratorias_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSummary saved to {summary_path}")

    return results


def main():
    test_mode = '--test' in sys.argv
    use_database = HAS_DATABASE and '--no-db' not in sys.argv

    if use_database:
        print("Database mode: ON")
    else:
        print("Database mode: OFF (JSON only)")

    # Download CSVs
    print("\nDownloading declaratorias CSVs...")
    desastre_path = download_csv(URL_DESASTRE, 'declaratorias_desastre_4to_trim_2025.csv')
    emergencia_path = download_csv(URL_EMERGENCIA, 'declaratorias_emergencia_4to_trim_2025.csv')

    # Load CSVs
    print("\nParsing CSV data...")
    desastre_events = load_desastre_csv(desastre_path)
    emergencia_events = load_emergencia_csv(emergencia_path)

    # Show tipo_fenomeno distribution
    print("\nDesastre by tipo_fenomeno:")
    type_counts = defaultdict(int)
    for e in desastre_events:
        type_counts[e['tipo_fenomeno'] or 'Sin clasificar'] += 1
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    print("\nEmergencia by tipo_fenomeno:")
    type_counts = defaultdict(int)
    for e in emergencia_events:
        type_counts[e['tipo_fenomeno'] or 'Sin clasificar'] += 1
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    # Show year ranges
    des_years = [e['ano'] for e in desastre_events]
    eme_years = [e['ano'] for e in emergencia_events]
    if des_years:
        print(f"\nDesastre year range: {min(des_years)}-{max(des_years)}")
    if eme_years:
        print(f"Emergencia year range: {min(eme_years)}-{max(eme_years)}")

    # Process all ANPs
    results = process_all_anps(desastre_events, emergencia_events,
                                test_mode=test_mode, use_database=use_database)

    # Print top ANPs
    print("\nTop 10 ANPs by total declaratorias (desastre + emergencia):")
    ranked = sorted(results.items(),
                    key=lambda x: x[1]['total_declaratorias_desastre'] + x[1]['total_declaratorias_emergencia'],
                    reverse=True)
    for i, (anp_id, agg) in enumerate(ranked[:10], 1):
        total = agg['total_declaratorias_desastre'] + agg['total_declaratorias_emergencia']
        print(f"  {i:2d}. {anp_id}: {total} total "
              f"({agg['total_declaratorias_desastre']} desastre, {agg['total_declaratorias_emergencia']} emergencia), "
              f"pob afectada: {agg['total_poblacion_afectada']:,}")

    print("\nTop 10 ANPs by costo total de declaratorias:")
    ranked = sorted(results.items(),
                    key=lambda x: x[1]['total_costo_declaratorias_pesos'],
                    reverse=True)
    for i, (anp_id, agg) in enumerate(ranked[:10], 1):
        if agg['total_costo_declaratorias_pesos'] > 0:
            print(f"  {i:2d}. {anp_id}: ${agg['total_costo_declaratorias_pesos']:,.2f} pesos")


if __name__ == '__main__':
    main()
