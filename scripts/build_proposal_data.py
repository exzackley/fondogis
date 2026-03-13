#!/usr/bin/env python3
"""
build_proposal_data.py — Generate aggregated data for the Loss & Damage Fund proposal page.

Reads coastal ANP JSON files, declaratorias CSVs, and CENAPRED data to produce
a single loss_damage_proposal_data.json with all metrics needed by the proposal HTML.

Usage:
    python3 scripts/build_proposal_data.py
"""

import csv
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from coastal_anps_registry import get_coastal_anps, get_all_coastal_municipalities

DATA_DIR = os.path.join(BASE_DIR, 'anp_data')
DECL_DIR = os.path.join(BASE_DIR, 'reference_data', 'declaratorias')
OUTPUT = os.path.join(BASE_DIR, 'loss_damage_proposal_data.json')


def norm(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower().strip()


def parse_municipios(text):
    if not text or not text.strip():
        return []
    text = re.sub(r'\s+y\s+', ', ', text)
    return [m.strip() for m in text.split(',') if m.strip()]


def load_declaratorias_csv(filename):
    path = os.path.join(DECL_DIR, filename)
    if not os.path.exists(path):
        return []
    for enc in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open(path, 'r', encoding=enc) as f:
                return list(csv.DictReader(f))
        except (UnicodeDecodeError, KeyError):
            continue
    return []


def main():
    coastal_anps = get_coastal_anps()
    all_munis = get_all_coastal_municipalities()

    # Load declaratoria CSVs
    desastre_rows = load_declaratorias_csv('declaratorias_desastre_4to_trim_2025.csv')
    emergencia_rows = load_declaratorias_csv('declaratorias_emergencia_4to_trim_2025.csv')

    # Load existing CENAPRED+SLR table
    cenapred_slr_path = os.path.join(BASE_DIR, 'coastal_cenapred_slr_table.json')
    cenapred_slr = {}
    if os.path.exists(cenapred_slr_path):
        with open(cenapred_slr_path) as f:
            for entry in json.load(f):
                cenapred_slr[entry['name']] = entry

    # State normalization
    STATE_NORM = {
        'veracruz de ignacio de la llave': 'veracruz',
        'michoacan de ocampo': 'michoacan',
        'coahuila de zaragoza': 'coahuila',
        'estado de mexico': 'mexico',
    }

    def norm_state(s):
        n = norm(s)
        return STATE_NORM.get(n, n)

    # Build per-ANP data
    by_anp = []
    total_decl_desastre = 0
    total_decl_emergencia = 0
    total_pob_afectada = 0
    total_costo = 0
    decl_by_year = defaultdict(lambda: {'desastre': 0, 'emergencia': 0})
    decl_by_type = defaultdict(lambda: {'desastre': 0, 'emergencia': 0})
    all_unique_munis = set()

    for anp in coastal_anps:
        anp_id = anp['id']
        anp_name = anp['matched_name']
        munis = all_munis.get(anp_id, [])
        muni_names = [m['municipio'] for m in munis]
        states = list(set(m['state'] for m in munis))
        all_unique_munis.update(muni_names)

        # Match declaratorias to this ANP's municipalities
        n_desastre = 0
        n_emergencia = 0
        anp_pob = 0
        anp_costo = 0
        anp_tipos = defaultdict(lambda: {'desastre': 0, 'emergencia': 0})
        anp_years = defaultdict(lambda: {'desastre': 0, 'emergencia': 0})

        for muni in munis:
            muni_norm = norm(muni['municipio'])
            estado_norm = norm_state(muni['state'])

            for d in desastre_rows:
                d_estado = norm_state(d.get('entidad_federativa', ''))
                if d_estado != estado_norm:
                    continue
                d_munis = [norm(m) for m in parse_municipios(d.get('nombre_municipios_corroborados', ''))]
                if muni_norm in d_munis:
                    n_desastre += 1
                    tipo = d.get('tipo_fenomeno', 'Otro')
                    anio = d.get('anio', '')
                    anp_tipos[tipo]['desastre'] += 1
                    if anio:
                        anp_years[anio]['desastre'] += 1

            for e in emergencia_rows:
                e_estado = norm_state(e.get('entidad_federativa', ''))
                if e_estado != estado_norm:
                    continue
                e_munis = [norm(m) for m in parse_municipios(e.get('nombre_municipios_corroborados', ''))]
                if muni_norm in e_munis:
                    n_emergencia += 1
                    tipo = e.get('tipo_fenomeno', 'Otro')
                    anio = e.get('anio_ocurrencia_evento', '')
                    anp_tipos[tipo]['emergencia'] += 1
                    if anio:
                        anp_years[anio]['emergencia'] += 1
                    try:
                        pob = float(str(e.get('poblacion_afectada', '0')).replace(',', '') or '0')
                        anp_pob += pob
                    except:
                        pass
                    try:
                        for k in e:
                            if 'costo_total' in k.lower():
                                c = float(str(e.get(k, '0')).replace(',', '').replace('$', '') or '0')
                                anp_costo += c
                                break
                    except:
                        pass

        # Load ANP JSON for extra data (centroid, climate, SLR)
        data_file = os.path.join(DATA_DIR, f'{anp_id}_data.json')
        centroid = None
        slr_rate = None
        slr_2050 = None
        inundation = None
        temp_change = None
        temp_baseline = None
        temp_future = None
        precip_change = None
        mangrove_ha = None

        if os.path.exists(data_file):
            with open(data_file) as f:
                adata = json.load(f)
            geo = adata.get('geometry', {})
            centroid = geo.get('centroid')
            # SLR: check both datasets and external_data locations
            slr = adata.get('datasets', {}).get('sea_level_rise', {})
            if not slr or not slr.get('observed_trend_mm_per_year'):
                slr = adata.get('external_data', {}).get('sea_level_rise', {})
            slr_rate = slr.get('observed_trend_coastal_mm_per_year') or slr.get('observed_trend_mm_per_year')
            slr_2050 = slr.get('projected_slr_2050_cm')
            inundation = slr.get('inundation_pct_at_1m')
            # Climate projections
            cp = adata.get('datasets', {}).get('climate_projections', {})
            scenarios = cp.get('scenarios', {})
            ssp245 = scenarios.get('ssp245', {})
            mid = ssp245.get('2041-2070', {})
            temp_obj = mid.get('temperature', {})
            temp_change = temp_obj.get('change_c')
            temp_baseline = temp_obj.get('baseline_mean_c')
            temp_future = temp_obj.get('future_mean_c')
            precip_obj = mid.get('precipitation', {})
            precip_change = precip_obj.get('change_percent')
            # Mangroves
            mg = adata.get('datasets', {}).get('mangrove', {})
            mangrove_ha = mg.get('area_ha')

        # CENAPRED data from pre-built table
        cen = cenapred_slr.get(anp_name, {})

        total_decl_desastre += n_desastre
        total_decl_emergencia += n_emergencia
        total_pob_afectada += anp_pob
        total_costo += anp_costo

        for tipo, counts in anp_tipos.items():
            decl_by_type[tipo]['desastre'] += counts['desastre']
            decl_by_type[tipo]['emergencia'] += counts['emergencia']
        for yr, counts in anp_years.items():
            decl_by_year[yr]['desastre'] += counts['desastre']
            decl_by_year[yr]['emergencia'] += counts['emergencia']

        by_anp.append({
            'name': anp_name,
            'id': anp_id,
            'category': anp['category'],
            'municipalities': muni_names,
            'states': states,
            'centroid': centroid,
            'declaratorias_desastre': n_desastre,
            'declaratorias_emergencia': n_emergencia,
            'declaratorias_total': n_desastre + n_emergencia,
            'poblacion_afectada': int(anp_pob),
            'costo_pesos': round(anp_costo, 2),
            'costo_mdp': round(anp_costo / 1000000, 2) if anp_costo else 0,
            'cenapred_events': cen.get('events_2020_2023', 0),
            'cenapred_deaths': cen.get('deaths_total', 0),
            'cenapred_affected': cen.get('affected_total', 0),
            'cenapred_damage_mdp': cen.get('damage_total_mdp', 0),
            'slr_mm_yr': slr_rate,
            'slr_2050_cm': slr_2050,
            'inundation_pct': inundation,
            'temp_baseline': temp_baseline,
            'temp_future_2050': temp_future,
            'temp_change_2050': temp_change,
            'precip_change_2050': precip_change,
            'mangrove_ha': mangrove_ha,
            'by_type': dict(anp_tipos),
            'by_year': dict(anp_years),
        })

    # Sort by total declaratorias descending
    by_anp.sort(key=lambda x: x['declaratorias_total'], reverse=True)

    # Summary
    cenapred_totals = {
        'events': sum(a.get('cenapred_events', 0) for a in by_anp),
        'deaths': sum(a.get('cenapred_deaths', 0) for a in by_anp),
        'affected': sum(a.get('cenapred_affected', 0) for a in by_anp),
        'damage_mdp': round(sum(a.get('cenapred_damage_mdp', 0) for a in by_anp), 2),
    }

    result = {
        'summary': {
            'total_coastal_anps': len(coastal_anps),
            'total_municipalities': len(all_unique_munis),
            'total_declaratorias_desastre': total_decl_desastre,
            'total_declaratorias_emergencia': total_decl_emergencia,
            'total_declaratorias': total_decl_desastre + total_decl_emergencia,
            'total_poblacion_afectada': int(total_pob_afectada),
            'total_costo_pesos': round(total_costo, 2),
            'total_costo_mdp': round(total_costo / 1000000, 2) if total_costo else 0,
            'cenapred': cenapred_totals,
            'period_declaratorias': '2018-2024',
            'period_cenapred': '2000-2023',
        },
        'by_anp': by_anp,
        'by_year': dict(decl_by_year),
        'by_type': dict(decl_by_type),
    }

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Generated: {OUTPUT}")
    print(f"  Coastal ANPs: {result['summary']['total_coastal_anps']}")
    print(f"  Municipalities: {result['summary']['total_municipalities']}")
    print(f"  Declaratorias: {result['summary']['total_declaratorias']} (D:{total_decl_desastre} E:{total_decl_emergencia})")
    print(f"  Pop affected: {result['summary']['total_poblacion_afectada']:,}")
    print(f"  Cost: ${result['summary']['total_costo_mdp']:,.1f}M MXN")
    print(f"  CENAPRED events: {cenapred_totals['events']}, deaths: {cenapred_totals['deaths']}")


if __name__ == '__main__':
    main()
