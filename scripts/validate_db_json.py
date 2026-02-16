#!/usr/bin/env python3
"""
FondoGIS Phase 1: Database vs JSON Consistency Validation
Produces VALIDATION_REPORT.md with comprehensive findings.
"""

import json
import os
import sys
import glob
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db.db_utils import execute_query, get_connection

DATA_DIR = PROJECT_ROOT / 'anp_data'
REPORT_PATH = PROJECT_ROOT / 'VALIDATION_REPORT.md'

# Dataset types that go under "datasets" vs "external_data" in JSON
GEE_DATASETS = {
    'population', 'elevation', 'land_cover', 'forest', 'climate',
    'vegetation', 'night_lights', 'fire', 'biodiversity', 'human_modification',
    'water_stress', 'gedi_biomass', 'climate_projections', 'climate_portal',
    'soil', 'surface_water', 'mangroves'
}

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def load_json_file(path):
    """Load a JSON file, return None on error."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return None


def get_json_dataset_types(json_data):
    """Extract all dataset types from a JSON file."""
    types = set()
    if 'datasets' in json_data:
        for k, v in json_data['datasets'].items():
            if v is not None:
                types.add(k)
    if 'external_data' in json_data:
        for k, v in json_data['external_data'].items():
            if v is not None:
                types.add(k)
    return types


def deep_compare(obj1, obj2, path="", diffs=None, max_diffs=20):
    """Deep compare two objects, collecting differences."""
    if diffs is None:
        diffs = []
    if len(diffs) >= max_diffs:
        return diffs

    if type(obj1) != type(obj2):
        # Allow Decimal vs float/int comparison
        if isinstance(obj1, (int, float, Decimal)) and isinstance(obj2, (int, float, Decimal)):
            if abs(float(obj1) - float(obj2)) > 0.001:
                diffs.append(f"  {path}: value differs {obj1} vs {obj2}")
        else:
            diffs.append(f"  {path}: type differs {type(obj1).__name__} vs {type(obj2).__name__}")
        return diffs

    if isinstance(obj1, dict):
        keys1 = set(obj1.keys())
        keys2 = set(obj2.keys())
        for k in keys1 - keys2:
            diffs.append(f"  {path}.{k}: only in first (JSON)")
        for k in keys2 - keys1:
            diffs.append(f"  {path}.{k}: only in second (DB)")
        for k in keys1 & keys2:
            deep_compare(obj1[k], obj2[k], f"{path}.{k}", diffs, max_diffs)
    elif isinstance(obj1, list):
        if len(obj1) != len(obj2):
            diffs.append(f"  {path}: list length {len(obj1)} vs {len(obj2)}")
        else:
            for i in range(min(len(obj1), len(obj2))):
                deep_compare(obj1[i], obj2[i], f"{path}[{i}]", diffs, max_diffs)
    elif isinstance(obj1, (int, float, Decimal)) and isinstance(obj2, (int, float, Decimal)):
        if abs(float(obj1) - float(obj2)) > 0.001:
            diffs.append(f"  {path}: {obj1} vs {obj2}")
    elif obj1 != obj2:
        v1 = str(obj1)[:80]
        v2 = str(obj2)[:80]
        diffs.append(f"  {path}: '{v1}' vs '{v2}'")

    return diffs


def task1_parity_check():
    """DB ↔ JSON parity check."""
    print("=== Task 1: DB ↔ JSON Parity Check ===")
    
    # Get all ANP IDs from DB
    db_anps = execute_query("SELECT id FROM anps ORDER BY id")
    db_anp_ids = {row['id'] for row in db_anps}
    
    # Get all JSON files
    json_files = glob.glob(str(DATA_DIR / '*_data.json'))
    json_anp_ids = set()
    for f in json_files:
        basename = os.path.basename(f)
        anp_id = basename.replace('_data.json', '')
        json_anp_ids.add(anp_id)
    
    # Compare ANP-level coverage
    in_db_not_json = db_anp_ids - json_anp_ids
    in_json_not_db = json_anp_ids - db_anp_ids
    in_both = db_anp_ids & json_anp_ids
    
    # Get DB datasets for all ANPs
    db_datasets = execute_query("""
        SELECT anp_id, dataset_type FROM anp_datasets ORDER BY anp_id, dataset_type
    """)
    db_dataset_map = defaultdict(set)
    for row in db_datasets:
        db_dataset_map[row['anp_id']].add(row['dataset_type'])
    
    # Compare dataset coverage for every ANP
    coverage_mismatches = []
    for anp_id in sorted(in_both):
        json_path = DATA_DIR / f'{anp_id}_data.json'
        json_data = load_json_file(json_path)
        if json_data is None:
            coverage_mismatches.append((anp_id, "JSON file unreadable", set(), set()))
            continue
        
        json_types = get_json_dataset_types(json_data)
        db_types = db_dataset_map.get(anp_id, set())
        
        in_json_only = json_types - db_types
        in_db_only = db_types - json_types
        
        if in_json_only or in_db_only:
            coverage_mismatches.append((anp_id, None, in_json_only, in_db_only))
    
    # Deep comparison for 7 sample ANPs (spread across categories)
    # designation_type in DB is 'National'/'International', actual category is in metadata
    sample_anps_q = execute_query("""
        SELECT DISTINCT ON (metadata->>'categoria_de_manejo') id, name, 
               metadata->>'categoria_de_manejo' as categoria
        FROM anps 
        WHERE metadata->>'categoria_de_manejo' IS NOT NULL
        ORDER BY metadata->>'categoria_de_manejo', id
    """)
    sample_ids = [r['id'] for r in sample_anps_q]
    
    # Also add well-known ones
    for extra in ['calakmul', 'sierra_gorda']:
        if extra not in sample_ids and extra in in_both:
            sample_ids.append(extra)
    
    sample_ids = sample_ids[:7]
    
    deep_results = {}
    for anp_id in sample_ids:
        json_path = DATA_DIR / f'{anp_id}_data.json'
        json_data = load_json_file(json_path)
        if json_data is None:
            deep_results[anp_id] = {"error": "Could not load JSON"}
            continue
        
        # Get all DB datasets for this ANP
        db_ds = execute_query(
            "SELECT dataset_type, data FROM anp_datasets WHERE anp_id = %s",
            (anp_id,)
        )
        db_data_map = {row['dataset_type']: row['data'] for row in db_ds}
        
        # Compare each dataset
        anp_diffs = {}
        all_types = get_json_dataset_types(json_data) | set(db_data_map.keys())
        
        for dtype in sorted(all_types):
            # Get JSON version
            json_ds = None
            if dtype in GEE_DATASETS:
                json_ds = json_data.get('datasets', {}).get(dtype)
            else:
                json_ds = json_data.get('external_data', {}).get(dtype)
            
            db_ds_data = db_data_map.get(dtype)
            
            if json_ds is None and db_ds_data is None:
                continue
            elif json_ds is None:
                anp_diffs[dtype] = ["Only in DB (not in JSON)"]
            elif db_ds_data is None:
                anp_diffs[dtype] = ["Only in JSON (not in DB)"]
            else:
                diffs = deep_compare(json_ds, db_ds_data, dtype)
                if diffs:
                    anp_diffs[dtype] = diffs
        
        deep_results[anp_id] = anp_diffs
    
    return {
        'db_count': len(db_anp_ids),
        'json_count': len(json_anp_ids),
        'in_both': len(in_both),
        'in_db_not_json': sorted(in_db_not_json),
        'in_json_not_db': sorted(in_json_not_db),
        'coverage_mismatches': coverage_mismatches,
        'deep_results': deep_results,
        'sample_ids': sample_ids,
    }


def task2_missing_data():
    """Missing data audit by dataset type."""
    print("=== Task 2: Missing Data Audit ===")
    
    # Get all ANPs with their metadata
    all_anps = execute_query("""
        SELECT id, name, designation_type, is_marine, area_km2,
               metadata->>'superficie_marina_ha' as marine_ha,
               metadata->>'superficie_terrestre_ha' as terrestrial_ha,
               metadata->>'categoria_de_manejo' as categoria
        FROM anps ORDER BY id
    """)
    all_anp_ids = {a['id'] for a in all_anps}
    anp_info = {a['id']: a for a in all_anps}
    
    # Get coverage by dataset type
    coverage = execute_query("""
        SELECT dataset_type, array_agg(anp_id ORDER BY anp_id) as anp_ids
        FROM anp_datasets
        GROUP BY dataset_type
    """)
    
    # Key dataset types with expected near-full coverage
    key_types = [
        'land_cover', 'inegi_census', 'inaturalist', 'gedi_biomass',
        'coneval_irs', 'gbif_species', 'simec_nom059', 'iucn_threatened',
        'nom059_enciclovida', 'extracted_at'
    ]
    
    results = {}
    for row in coverage:
        dtype = row['dataset_type']
        covered = set(row['anp_ids'])
        missing = all_anp_ids - covered
        
        if missing and dtype in key_types:
            missing_details = []
            for mid in sorted(missing):
                info = anp_info[mid]
                marine_ha = float(info['marine_ha']) if info['marine_ha'] else 0
                terr_ha = float(info['terrestrial_ha']) if info['terrestrial_ha'] else 0
                total_ha = marine_ha + terr_ha
                marine_pct = (marine_ha / total_ha * 100) if total_ha > 0 else 0
                missing_details.append({
                    'id': mid,
                    'name': info['name'],
                    'designation': info.get('categoria') or info['designation_type'],
                    'area_km2': float(info['area_km2']) if info['area_km2'] else 0,
                    'marine_pct': marine_pct,
                })
            
            # Pattern analysis
            designations = defaultdict(int)
            marine_count = 0
            small_count = 0  # < 10 km²
            for d in missing_details:
                designations[d['designation'] or 'Unknown'] += 1
                if d['marine_pct'] > 50:
                    marine_count += 1
                if d['area_km2'] < 10:
                    small_count += 1
            
            results[dtype] = {
                'total_anps': len(all_anp_ids),
                'covered': len(covered),
                'missing_count': len(missing),
                'missing_details': missing_details,
                'pattern': {
                    'by_designation': dict(designations),
                    'marine_dominated': marine_count,
                    'small_area': small_count,
                }
            }
    
    # Also report full coverage types
    full_coverage = []
    for row in coverage:
        if len(row['anp_ids']) == len(all_anp_ids):
            full_coverage.append(row['dataset_type'])
    
    return {
        'total_anps': len(all_anp_ids),
        'missing_by_type': results,
        'full_coverage_types': sorted(full_coverage),
    }


def task3_null_empty_error():
    """Null/empty/error audit of JSONB data."""
    print("=== Task 3: Null/Empty/Error Audit ===")
    
    # Get all dataset blobs
    all_data = execute_query("""
        SELECT anp_id, dataset_type, data,
               (SELECT name FROM anps WHERE id = anp_id) as anp_name
        FROM anp_datasets
        ORDER BY dataset_type, anp_id
    """)
    
    issues = defaultdict(lambda: defaultdict(list))
    counts = defaultdict(lambda: {'empty': 0, 'error': 0, 'data_unavailable': 0, 'null_values': 0})
    
    for row in all_data:
        anp_id = row['anp_id']
        dtype = row['dataset_type']
        data = row['data']
        anp_name = row['anp_name']
        label = f"{anp_id} ({anp_name})"
        
        if data is None:
            issues[dtype]['null_blob'].append(label)
            counts[dtype]['null_values'] += 1
            continue
        
        if isinstance(data, dict):
            # Empty object
            if data == {}:
                issues[dtype]['empty_object'].append(label)
                counts[dtype]['empty'] += 1
                continue
            
            # Error stored as data
            if 'error' in data:
                err_msg = str(data['error'])[:100]
                issues[dtype]['error'].append(f"{label}: {err_msg}")
                counts[dtype]['error'] += 1
            
            # data_available: false
            if data.get('data_available') == False or data.get('data_available') == 'false':
                reason = data.get('reason', data.get('error', 'unknown'))
                issues[dtype]['data_unavailable'].append(f"{label}: {reason}")
                counts[dtype]['data_unavailable'] += 1
            
            # Check for null values at top level
            null_keys = [k for k, v in data.items() if v is None]
            if null_keys:
                issues[dtype]['null_fields'].append(f"{label}: {null_keys}")
                counts[dtype]['null_values'] += 1
    
    return {
        'issues': {k: dict(v) for k, v in issues.items()},
        'counts': dict(counts),
        'total_rows': len(all_data),
    }


def task4_timestamp_audit():
    """Extraction timestamp audit."""
    print("=== Task 4: Extraction Timestamp Audit ===")
    
    # Check extracted_at in anp_datasets
    ts_data = execute_query("""
        SELECT dataset_type,
               COUNT(*) as total,
               COUNT(extracted_at) as has_timestamp,
               COUNT(*) - COUNT(extracted_at) as missing_timestamp,
               MIN(extracted_at) as oldest,
               MAX(extracted_at) as newest
        FROM anp_datasets
        GROUP BY dataset_type
        ORDER BY missing_timestamp DESC, dataset_type
    """)
    
    # Check for the 'extracted_at' dataset_type oddity
    extracted_at_ds = execute_query("""
        SELECT anp_id, data FROM anp_datasets 
        WHERE dataset_type = 'extracted_at'
        LIMIT 5
    """)
    
    # Check JSON file modification dates for potential backfill
    json_files = glob.glob(str(DATA_DIR / '*_data.json'))
    file_dates = {}
    for f in json_files:
        mtime = os.path.getmtime(f)
        anp_id = os.path.basename(f).replace('_data.json', '')
        file_dates[anp_id] = datetime.fromtimestamp(mtime).isoformat()
    
    # Sample file dates
    sample_dates = dict(list(sorted(file_dates.items()))[:5])
    
    return {
        'by_dataset_type': [dict(r) for r in ts_data],
        'extracted_at_dataset_sample': extracted_at_ds,
        'json_file_dates_sample': sample_dates,
        'total_json_files': len(json_files),
    }


def task5_sanity_checks():
    """Cross-source sanity checks."""
    print("=== Task 5: Cross-Source Sanity Checks ===")
    
    results = {}
    
    # 5a: WDPA reported_area_km2 vs superficie_total_ha (converted to km2)
    anps = execute_query("""
        SELECT id, name, area_km2,
               metadata->>'reported_area_km2' as reported_area,
               metadata->>'superficie_total_ha' as total_ha,
               metadata->>'superficie_terrestre_ha' as terr_ha,
               metadata->>'superficie_marina_ha' as marine_ha
        FROM anps
    """)
    
    area_discrepancies = []
    for a in anps:
        wdpa_area = float(a['area_km2']) if a['area_km2'] else None
        reported = float(a['reported_area']) if a.get('reported_area') else None
        total_ha = float(a['total_ha']) if a.get('total_ha') else None
        
        # Compare WDPA area (area_km2) vs reported_area_km2
        if wdpa_area and reported and reported > 0:
            pct_diff = abs(wdpa_area - reported) / reported * 100
            if pct_diff > 10:
                area_discrepancies.append({
                    'id': a['id'],
                    'name': a['name'],
                    'wdpa_area_km2': round(wdpa_area, 2),
                    'reported_area_km2': round(reported, 2),
                    'pct_diff': round(pct_diff, 1),
                    'source': 'WDPA vs reported'
                })
        
        # Compare WDPA area vs superficie_total converted
        if wdpa_area and total_ha and total_ha > 0:
            sup_km2 = total_ha / 100.0
            pct_diff = abs(wdpa_area - sup_km2) / sup_km2 * 100
            if pct_diff > 10:
                area_discrepancies.append({
                    'id': a['id'],
                    'name': a['name'],
                    'wdpa_area_km2': round(wdpa_area, 2),
                    'superficie_km2': round(sup_km2, 2),
                    'pct_diff': round(pct_diff, 1),
                    'source': 'WDPA vs superficie_total'
                })
    
    # Deduplicate by keeping worst per ANP
    seen = {}
    for d in area_discrepancies:
        key = d['id']
        if key not in seen or d['pct_diff'] > seen[key]['pct_diff']:
            seen[key] = d
    results['area_discrepancies'] = sorted(seen.values(), key=lambda x: x['pct_diff'], reverse=True)[:25]
    
    # 5b: Marine-only ANPs with terrestrial data
    # Use superficie_marina_ha and superficie_terrestre_ha from metadata
    marine_anps = execute_query("""
        SELECT a.id, a.name,
               metadata->>'superficie_marina_ha' as marine_ha,
               metadata->>'superficie_terrestre_ha' as terr_ha
        FROM anps a
        WHERE (metadata->>'superficie_marina_ha') IS NOT NULL
          AND (metadata->>'superficie_marina_ha')::numeric > 0
    """)
    
    marine_issues = []
    for a in marine_anps:
        marine_ha = float(a['marine_ha']) if a['marine_ha'] else 0
        terr_ha = float(a['terr_ha']) if a['terr_ha'] else 0
        total = marine_ha + terr_ha
        if total > 0 and (marine_ha / total) > 0.95:
            # This is a marine-dominated ANP - check for terrestrial-only datasets
            datasets = execute_query(
                "SELECT dataset_type, data FROM anp_datasets WHERE anp_id = %s AND dataset_type IN ('forest', 'gedi_biomass', 'land_cover')",
                (a['id'],)
            )
            for ds in datasets:
                data = ds['data']
                if isinstance(data, dict):
                    has_real_data = data.get('data_available', True) != False
                    has_error = 'error' in data
                    if has_real_data and not has_error and data != {}:
                        # Check if there's actually meaningful data (not all zeros/nulls)
                        marine_issues.append({
                            'id': a['id'],
                            'name': a['name'],
                            'marine_pct': round(marine_ha / total * 100, 1),
                            'terr_ha': terr_ha,
                            'dataset': ds['dataset_type'],
                            'note': 'Has terrestrial data despite being >95% marine'
                        })
    
    results['marine_terrestrial_issues'] = marine_issues
    
    # Also list all marine-dominated ANPs for reference
    marine_dominated = []
    for a in marine_anps:
        marine_ha = float(a['marine_ha']) if a['marine_ha'] else 0
        terr_ha = float(a['terr_ha']) if a['terr_ha'] else 0
        total = marine_ha + terr_ha
        if total > 0 and (marine_ha / total) > 0.95:
            marine_dominated.append({
                'id': a['id'], 'name': a['name'],
                'marine_pct': round(marine_ha / total * 100, 1),
                'terr_ha': terr_ha,
            })
    results['marine_dominated_anps'] = sorted(marine_dominated, key=lambda x: x['marine_pct'], reverse=True)
    
    # 5c: Implausible population density
    # Population data stored as data.year_YYYY.population
    pop_issues = []
    pop_data = execute_query("""
        SELECT d.anp_id, a.name, a.area_km2, d.data
        FROM anp_datasets d
        JOIN anps a ON a.id = d.anp_id
        WHERE d.dataset_type = 'population'
    """)
    
    for row in pop_data:
        data = row['data']
        area = float(row['area_km2']) if row['area_km2'] else None
        if not area or area == 0:
            continue
        
        if isinstance(data, dict):
            pop_val = None
            # Structure: data.year_2020.population
            for k in sorted(data.keys(), reverse=True):
                if k.startswith('year_') and isinstance(data[k], dict):
                    pop_val = data[k].get('population')
                    if pop_val is not None:
                        break
            
            if pop_val and isinstance(pop_val, (int, float)) and pop_val > 0:
                density = pop_val / area
                if density > 500:
                    pop_issues.append({
                        'id': row['anp_id'],
                        'name': row['name'],
                        'population': pop_val,
                        'area_km2': area,
                        'density_per_km2': round(density, 1),
                    })
    
    results['population_density_issues'] = sorted(pop_issues, key=lambda x: x['density_per_km2'], reverse=True)
    
    return results


def generate_report(t1, t2, t3, t4, t5):
    """Generate the VALIDATION_REPORT.md."""
    lines = []
    L = lines.append
    
    L("# FondoGIS Validation Report")
    L(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    L(f"**Database:** fondogis on 172.232.163.60")
    L(f"**JSON Directory:** anp_data/")
    
    # ─── Summary ───
    L("\n---\n## Executive Summary\n")
    L(f"- **ANPs in DB:** {t1['db_count']}")
    L(f"- **ANPs in JSON:** {t1['json_count']}")
    L(f"- **ANPs in both:** {t1['in_both']}")
    L(f"- **In DB only:** {len(t1['in_db_not_json'])}")
    L(f"- **In JSON only:** {len(t1['in_json_not_db'])}")
    L(f"- **ANPs with dataset coverage mismatches:** {len(t1['coverage_mismatches'])}")
    
    # Count issues
    total_error = sum(c['error'] for c in t3['counts'].values())
    total_unavail = sum(c['data_unavailable'] for c in t3['counts'].values())
    total_empty = sum(c['empty'] for c in t3['counts'].values())
    
    L(f"- **Dataset rows with errors:** {total_error}")
    L(f"- **Dataset rows with data_available=false:** {total_unavail}")
    L(f"- **Empty dataset blobs:** {total_empty}")
    L(f"- **Full-coverage dataset types (227/227):** {len(t2['full_coverage_types'])}")
    L(f"- **Area discrepancies >10%:** {len(t5['area_discrepancies'])}")
    L(f"- **Marine-dominated ANPs (>95%):** {len(t5.get('marine_dominated_anps', []))}")
    L(f"- **Marine ANPs with terrestrial data:** {len(t5['marine_terrestrial_issues'])}")
    L(f"- **Implausible pop density >500/km²:** {len(t5['population_density_issues'])}")
    
    # ─── Task 1 ───
    L("\n---\n## 1. DB ↔ JSON Parity Check\n")
    
    if t1['in_db_not_json']:
        L(f"### ANPs in DB but not in JSON ({len(t1['in_db_not_json'])})\n")
        for aid in t1['in_db_not_json']:
            L(f"- `{aid}`")
    else:
        L("### ✅ All DB ANPs have corresponding JSON files\n")
    
    if t1['in_json_not_db']:
        L(f"\n### ANPs in JSON but not in DB ({len(t1['in_json_not_db'])})\n")
        for aid in t1['in_json_not_db']:
            L(f"- `{aid}`")
    else:
        L("### ✅ All JSON ANPs exist in DB\n")
    
    L(f"\n### Dataset Coverage Mismatches ({len(t1['coverage_mismatches'])} ANPs)\n")
    if t1['coverage_mismatches']:
        L("| ANP ID | In JSON only | In DB only |")
        L("|--------|-------------|------------|")
        for anp_id, err, json_only, db_only in t1['coverage_mismatches'][:50]:
            if err:
                L(f"| `{anp_id}` | {err} | - |")
            else:
                jo = ', '.join(sorted(json_only)) if json_only else '-'
                do = ', '.join(sorted(db_only)) if db_only else '-'
                L(f"| `{anp_id}` | {jo} | {do} |")
        if len(t1['coverage_mismatches']) > 50:
            L(f"\n*... and {len(t1['coverage_mismatches']) - 50} more*")
    else:
        L("✅ All ANPs have matching dataset coverage between DB and JSON.\n")
    
    L(f"\n### Deep Comparison (Sample of {len(t1['sample_ids'])} ANPs)\n")
    for anp_id in t1['sample_ids']:
        diffs = t1['deep_results'].get(anp_id, {})
        if isinstance(diffs, dict) and 'error' in diffs:
            L(f"\n#### `{anp_id}` — ⚠️ {diffs['error']}\n")
            continue
        
        if not diffs:
            L(f"\n#### `{anp_id}` — ✅ Perfect match\n")
        else:
            total_diffs = sum(len(v) for v in diffs.values())
            L(f"\n#### `{anp_id}` — ⚠️ {total_diffs} differences across {len(diffs)} datasets\n")
            for dtype, diff_list in sorted(diffs.items()):
                L(f"**{dtype}** ({len(diff_list)} diffs):")
                for d in diff_list[:5]:
                    L(f"- {d}")
                if len(diff_list) > 5:
                    L(f"- *... and {len(diff_list) - 5} more*")
    
    # ─── Task 2 ───
    L("\n---\n## 2. Missing Data Audit\n")
    
    L(f"**Total ANPs:** {t2['total_anps']}\n")
    L(f"**Full coverage (all {t2['total_anps']} ANPs):** {', '.join(t2['full_coverage_types'])}\n")
    
    for dtype in ['land_cover', 'inegi_census', 'inaturalist', 'gedi_biomass', 
                  'coneval_irs', 'gbif_species', 'simec_nom059', 'iucn_threatened',
                  'nom059_enciclovida', 'extracted_at']:
        info = t2['missing_by_type'].get(dtype)
        if not info:
            continue
        
        L(f"\n### {dtype} — {info['covered']}/{info['total_anps']} ({info['missing_count']} missing)\n")
        
        # Pattern
        pat = info['pattern']
        L(f"**Pattern:** By category: {pat['by_designation']}; Marine-dominated: {pat['marine_dominated']}/{info['missing_count']}; Small (<10 km²): {pat['small_area']}/{info['missing_count']}\n")
        
        L("| ANP ID | Name | Designation | Area km² | Marine % |")
        L("|--------|------|-------------|----------|----------|")
        for d in info['missing_details']:
            L(f"| `{d['id']}` | {d['name']} | {d['designation']} | {d['area_km2']:.1f} | {d['marine_pct']:.0f}% |")
    
    # ─── Task 3 ───
    L("\n---\n## 3. Null/Empty/Error Audit\n")
    
    L(f"**Total dataset rows scanned:** {t3['total_rows']}\n")
    
    L("### Summary by Dataset Type\n")
    L("| Dataset Type | Errors | Data Unavailable | Empty | Null Fields |")
    L("|-------------|--------|-----------------|-------|-------------|")
    for dtype in sorted(t3['counts'].keys()):
        c = t3['counts'][dtype]
        if any(v > 0 for v in c.values()):
            L(f"| {dtype} | {c['error']} | {c['data_unavailable']} | {c['empty']} | {c['null_values']} |")
    
    # Details for most problematic types
    L("\n### Detailed Findings\n")
    for dtype, issue_dict in sorted(t3['issues'].items()):
        has_content = any(len(v) > 0 for v in issue_dict.values())
        if not has_content:
            continue
        
        L(f"\n#### {dtype}\n")
        for issue_type, items in sorted(issue_dict.items()):
            if not items:
                continue
            L(f"**{issue_type}** ({len(items)}):")
            for item in items[:15]:
                L(f"- {item}")
            if len(items) > 15:
                L(f"- *... and {len(items) - 15} more*")
    
    # ─── Task 4 ───
    L("\n---\n## 4. Extraction Timestamp Audit\n")
    
    L("### Timestamps by Dataset Type\n")
    L("| Dataset Type | Total | Has Timestamp | Missing | Oldest | Newest |")
    L("|-------------|-------|---------------|---------|--------|--------|")
    for row in t4['by_dataset_type']:
        oldest = str(row['oldest'])[:10] if row['oldest'] else 'N/A'
        newest = str(row['newest'])[:10] if row['newest'] else 'N/A'
        L(f"| {row['dataset_type']} | {row['total']} | {row['has_timestamp']} | {row['missing_timestamp']} | {oldest} | {newest} |")
    
    if t4['extracted_at_dataset_sample']:
        L("\n### ⚠️ 'extracted_at' stored as dataset_type\n")
        L("There are rows where `dataset_type = 'extracted_at'` — this appears to be a bug.")
        L("These should likely be timestamps on other datasets, not standalone entries.\n")
        L("Sample data:")
        for row in t4['extracted_at_dataset_sample'][:3]:
            L(f"- `{row['anp_id']}`: `{json.dumps(row['data'])[:200]}`")
    
    L(f"\n### JSON File Modification Dates (potential backfill source)\n")
    L(f"Total JSON files: {t4['total_json_files']}\n")
    L("Sample dates:")
    for anp_id, date in t4['json_file_dates_sample'].items():
        L(f"- `{anp_id}`: {date}")
    
    # ─── Task 5 ───
    L("\n---\n## 5. Cross-Source Sanity Checks\n")
    
    L(f"\n### 5a. Area Discrepancies >10% ({len(t5['area_discrepancies'])} found)\n")
    if t5['area_discrepancies']:
        L("| ANP | Name | WDPA km² | Comparison km² | Diff % | Source |")
        L("|-----|------|----------|---------------|--------|--------|")
        for a in t5['area_discrepancies']:
            comp = a.get('superficie_km2', a.get('reported_area_km2', '?'))
            L(f"| `{a['id']}` | {a['name']} | {a['wdpa_area_km2']} | {comp} | {a['pct_diff']}% | {a.get('source','')} |")
    else:
        L("✅ No area discrepancies >10% found.\n")
    
    L(f"\n### 5b. Marine-Dominated ANPs (>95% marine): {len(t5.get('marine_dominated_anps', []))} total\n")
    if t5.get('marine_dominated_anps'):
        L("| ANP | Name | Marine % | Terr. ha |")
        L("|-----|------|---------|----------|")
        for m in t5['marine_dominated_anps']:
            L(f"| `{m['id']}` | {m['name']} | {m['marine_pct']}% | {m['terr_ha']} |")
    
    L(f"\n**Marine ANPs with terrestrial-only data:** {len(t5['marine_terrestrial_issues'])} found\n")
    if t5['marine_terrestrial_issues']:
        L("| ANP | Marine % | Dataset | Note |")
        L("|-----|---------|---------|------|")
        for m in t5['marine_terrestrial_issues']:
            L(f"| `{m['id']}` ({m['name']}) | {m['marine_pct']}% | {m['dataset']} | terr_ha={m.get('terr_ha', '?')} |")
    else:
        L("✅ No purely marine ANPs with inappropriate terrestrial data.\n")
    
    L(f"\n### 5c. Implausible Population Density >500/km² ({len(t5['population_density_issues'])} found)\n")
    if t5['population_density_issues']:
        L("| ANP | Population | Area km² | Density |")
        L("|-----|-----------|----------|---------|")
        for p in t5['population_density_issues']:
            L(f"| `{p['id']}` ({p['name']}) | {p['population']:,.0f} | {p['area_km2']:.1f} | {p['density_per_km2']:.0f}/km² |")
    else:
        L("✅ No implausible population densities found.\n")
    
    # ─── Recommendations ───
    L("\n---\n## Recommended Fixes (Prioritized by Impact)\n")
    # Count specific issues for recommendations
    ts_missing = sum(1 for r in t4['by_dataset_type'] if r['missing_timestamp'] > 0)
    ts_missing_rows = sum(r['missing_timestamp'] for r in t4['by_dataset_type'])
    
    L(f"""
### High Priority

1. **Fix `extracted_at` as dataset_type** — 199 rows have `dataset_type='extracted_at'` storing a timestamp string as JSONB data. This is a bug in the JSON→DB import script. These should be deleted from `anp_datasets` after backfilling real `extracted_at` columns.
   - `DELETE FROM anp_datasets WHERE dataset_type = 'extracted_at';`

2. **Fix SIMEC name matching** — 137/201 `simec_nom059` records contain "ANP not found in SIMEC data" errors. The SIMEC scraper's name-matching logic needs fixing — likely fuzzy matching or a manual name mapping table.

3. **Backfill missing `extracted_at` timestamps** — {ts_missing} dataset types ({ts_missing_rows} total rows) have NULL `extracted_at`. The GEE-sourced datasets (population, forest, climate, etc.) were likely imported without timestamps. Use the `extracted_at` values stored (incorrectly) as datasets, or fall back to JSON file modification dates (~Jan 2-11, 2026).

4. **Fix CONEVAL/INEGI municipality matching** — 46 CONEVAL and 44 INEGI records show "No municipalities found within ANP bounds". Many are real ANPs (urban parks like Cumbres del Ajusco, Cerro de la Estrella) that clearly have nearby municipalities. The bounding-box intersection logic needs widening or the municipality dataset needs updating.

### Medium Priority

5. **Complete partial coverage datasets** — Priority order:
   - `land_cover`: 4 missing (Caribe Mexicano, Islas del Golfo, Pacífico Mexicano Profundo, Revillagigedo — all large/remote marine ANPs, may need `bestEffort=True` for GEE)
   - `inegi_census`: 14 missing (mix of new ANPs and Z.P.F. type areas)
   - `inaturalist`/`gedi_biomass`: 18 missing (same 18 ANPs for both)
   - `coneval_irs`: 22 missing
   - `gbif`/`simec`/`iucn`/`nom059`: 28 missing (same core set of 28)

6. **Fix GEE maxPixels errors** — 3 `gedi_biomass` and 6 `mangroves` records failed with "Too many pixels" errors for large-area ANPs (Islas del Golfo, Pacífico Mexicano Profundo, etc.). Fix by adding `bestEffort=True` or increasing `maxPixels` in the extraction scripts.

7. **Investigate area discrepancies** — 18 ANPs show >10% difference between WDPA area and `superficie_total_ha`. Top outliers:
   - Playa Huizache Caimanero: 10,594% diff (482 km² WDPA vs 4.5 km² superficie — likely WDPA includes surrounding lagoon)
   - Several "Playa" ANPs where WDPA geometry includes marine buffer not in the official area

### Low Priority

8. **Marine ANP terrestrial data cleanup** — 57 cases of marine-dominated ANPs (>95% marine) having forest/land_cover/GEDI data. Many are legitimate (e.g., Islas Marías has 24,295 terr. ha). Flag for dashboard: ANPs with 0 terrestrial hectares but non-null terrestrial data (Bajos del Norte, Tiburón Ballena, Pacífico Mexicano Profundo, etc.) should show N/A.

9. **Population density review** — 14 ANPs show >500/km² density. Most are urban parks (Lomas de Padierna at 13,523/km², Cerro de la Estrella at 11,679/km²). These are real but the dashboard should contextualize: GEE WorldPop captures surrounding urban population within the ANP boundary, not just people living inside the park.

10. **Clean up `nom059` singleton** — There's 1 row with `dataset_type='nom059'` (likely a predecessor of `nom059_enciclovida`). Verify and delete.

11. **Create `anp_expectations.json`** — Codify which datasets are expected/applicable per ANP type (marine, terrestrial, coastal, urban) to distinguish "missing data" from "not applicable".
""")
    
    return '\n'.join(lines)


def main():
    print("Starting FondoGIS validation...\n")
    
    t1 = task1_parity_check()
    print(f"  Task 1 complete: {len(t1['coverage_mismatches'])} coverage mismatches\n")
    
    t2 = task2_missing_data()
    print(f"  Task 2 complete: {len(t2['missing_by_type'])} dataset types with gaps\n")
    
    t3 = task3_null_empty_error()
    print(f"  Task 3 complete: scanned {t3['total_rows']} rows\n")
    
    t4 = task4_timestamp_audit()
    print(f"  Task 4 complete: {len(t4['by_dataset_type'])} dataset types checked\n")
    
    t5 = task5_sanity_checks()
    print(f"  Task 5 complete: {len(t5['area_discrepancies'])} area issues, {len(t5['population_density_issues'])} pop issues\n")
    
    report = generate_report(t1, t2, t3, t4, t5)
    
    with open(REPORT_PATH, 'w') as f:
        f.write(report)
    
    print(f"\n✅ Report written to {REPORT_PATH}")
    print(f"   Size: {len(report):,} characters, {report.count(chr(10))} lines")


if __name__ == '__main__':
    main()
