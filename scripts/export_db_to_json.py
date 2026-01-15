#!/usr/bin/env python3
"""
Export FondoGIS data from PostgreSQL database back to JSON files.

This script regenerates the JSON files from the database, allowing
verification that no data was lost during import.

Usage:
    python3 scripts/export_db_to_json.py                    # Export all to anp_data_export/
    python3 scripts/export_db_to_json.py --output anp_data/ # Export to specific directory
    python3 scripts/export_db_to_json.py --anp calakmul     # Export single ANP
    python3 scripts/export_db_to_json.py --test             # Export first 5 ANPs only
    python3 scripts/export_db_to_json.py --diff             # Compare exported vs original
"""

import argparse
import json
import os
import sys
from pathlib import Path
from difflib import unified_diff

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db_utils import get_connection, execute_query

DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / 'anp_data_export'
ORIGINAL_DIR = Path(__file__).parent.parent / 'anp_data'

# Dataset types that go in 'datasets' section
GEE_DATASETS = {
    'population', 'elevation', 'land_cover', 'forest', 'climate',
    'vegetation', 'night_lights', 'fire', 'biodiversity', 'human_modification',
    'water_stress', 'gedi_biomass', 'climate_projections', 'climate_portal',
    'soil', 'surface_water', 'mangroves'
}

# Dataset types that go in 'external_data' section
EXTERNAL_DATASETS = {
    'gbif_species', 'iucn_threatened', 'simec_nom059', 'nom059_enciclovida',
    'inegi_census', 'coneval_irs', 'inaturalist', 'nom059', 'extracted_at'
}


def export_anp(anp_id: str, output_dir: Path) -> dict:
    """
    Export a single ANP from database to JSON files.

    Args:
        anp_id: ANP identifier
        output_dir: Directory to write files

    Returns:
        Dict with export results
    """
    # Get ANP metadata
    anp = execute_query(
        "SELECT * FROM anps WHERE id = %s",
        (anp_id,),
        fetch='one'
    )

    if not anp:
        return {'success': False, 'error': f'ANP not found: {anp_id}'}

    # Get all datasets for this ANP
    datasets_rows = execute_query(
        "SELECT dataset_type, data FROM anp_datasets WHERE anp_id = %s",
        (anp_id,)
    )

    # Get boundary
    boundary = execute_query(
        "SELECT geojson FROM anp_boundaries WHERE anp_id = %s",
        (anp_id,),
        fetch='one'
    )

    # Reconstruct the JSON structure
    metadata = anp.get('metadata') or {}

    # Also add queryable fields back to metadata if they exist
    if anp.get('name'):
        metadata['name'] = anp['name']
    if anp.get('designation'):
        metadata['designation'] = anp['designation']
    if anp.get('designation_type'):
        metadata['designation_type'] = anp['designation_type']
    if anp.get('area_km2'):
        metadata['reported_area_km2'] = float(anp['area_km2'])
    if anp.get('estados'):
        metadata['estados'] = anp['estados']
    if anp.get('region'):
        metadata['region'] = anp['region']
    if anp.get('iucn_category'):
        metadata['iucn_category'] = anp['iucn_category']
    if anp.get('governance'):
        metadata['governance'] = anp['governance']
    if anp.get('management_authority'):
        metadata['management_authority'] = anp['management_authority']
    if anp.get('primer_decreto'):
        metadata['primer_decreto'] = str(anp['primer_decreto'])

    # Build geometry section - prefer stored geometry from metadata
    geometry = metadata.pop('_geometry', {})
    # Fallback to column values if no stored geometry
    if not geometry:
        if anp.get('centroid'):
            geometry['centroid'] = anp['centroid']
        if anp.get('bounds'):
            geometry['bounds'] = anp['bounds']

    # Build datasets and external_data sections
    datasets = {}
    external_data = {}

    for row in datasets_rows:
        dtype = row['dataset_type']
        data = row['data']

        if dtype in GEE_DATASETS:
            datasets[dtype] = data
        elif dtype in EXTERNAL_DATASETS:
            external_data[dtype] = data
        else:
            # Unknown type - put in datasets
            datasets[dtype] = data

    # Build final JSON structure
    anp_data = {
        'metadata': metadata,
        'geometry': geometry,
        'datasets': datasets
    }

    # Only add external_data if there's content
    if external_data:
        anp_data['external_data'] = external_data

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write data file
    data_file = output_dir / f'{anp_id}_data.json'
    with open(data_file, 'w') as f:
        json.dump(anp_data, f, indent=2, ensure_ascii=False)

    # Write boundary file if exists
    boundary_file = None
    if boundary and boundary.get('geojson'):
        boundary_file = output_dir / f'{anp_id}_boundary.geojson'
        with open(boundary_file, 'w') as f:
            json.dump(boundary['geojson'], f, indent=2, ensure_ascii=False)

    return {
        'success': True,
        'data_file': str(data_file),
        'boundary_file': str(boundary_file) if boundary_file else None,
        'datasets_count': len(datasets) + len(external_data)
    }


def get_all_anp_ids():
    """Get list of all ANP IDs from database."""
    rows = execute_query("SELECT id FROM anps ORDER BY id")
    return [row['id'] for row in rows]


def export_all(output_dir: Path, test_mode=False, single_anp=None, verbose=True):
    """
    Export all ANPs from database to JSON files.

    Args:
        output_dir: Directory to write files
        test_mode: If True, only export first 5 ANPs
        single_anp: If set, only export this specific ANP
        verbose: Print progress

    Returns:
        Dict with export statistics
    """
    anp_ids = get_all_anp_ids()

    if single_anp:
        if single_anp not in anp_ids:
            print(f"ERROR: ANP '{single_anp}' not found in database")
            return {'success': False, 'error': f'ANP not found: {single_anp}'}
        anp_ids = [single_anp]
    elif test_mode:
        anp_ids = anp_ids[:5]

    total = len(anp_ids)
    exported = 0
    failed = 0
    errors = []

    if verbose:
        print(f"Exporting {total} ANPs to {output_dir}...")

    for i, anp_id in enumerate(anp_ids, 1):
        try:
            result = export_anp(anp_id, output_dir)

            if result['success']:
                exported += 1
                if verbose:
                    print(f"  [{i}/{total}] {anp_id}: {result['datasets_count']} datasets")
            else:
                failed += 1
                errors.append({'anp_id': anp_id, 'error': result.get('error', 'Unknown error')})
                if verbose:
                    print(f"  [{i}/{total}] {anp_id}: ERROR - {result.get('error')}")

        except Exception as e:
            failed += 1
            errors.append({'anp_id': anp_id, 'error': str(e)})
            if verbose:
                print(f"  [{i}/{total}] {anp_id}: ERROR - {e}")

    if verbose:
        print(f"\nExport complete:")
        print(f"  ANPs exported: {exported}/{total}")
        if failed:
            print(f"  Failed: {failed}")

    return {
        'success': failed == 0,
        'total': total,
        'exported': exported,
        'failed': failed,
        'output_dir': str(output_dir),
        'errors': errors
    }


def compare_json_files(file1: Path, file2: Path) -> tuple:
    """
    Compare two JSON files for structural equality.

    Returns:
        Tuple of (are_equal: bool, diff_lines: list)
    """
    try:
        with open(file1, 'r') as f:
            data1 = json.load(f)
        with open(file2, 'r') as f:
            data2 = json.load(f)

        # Normalize and compare
        json1 = json.dumps(data1, sort_keys=True, indent=2)
        json2 = json.dumps(data2, sort_keys=True, indent=2)

        if json1 == json2:
            return True, []

        # Generate diff
        diff = list(unified_diff(
            json1.splitlines(keepends=True),
            json2.splitlines(keepends=True),
            fromfile=str(file1),
            tofile=str(file2),
            lineterm=''
        ))

        return False, diff[:50]  # Limit diff output

    except Exception as e:
        return False, [f"Error comparing files: {e}"]


def diff_exports(export_dir: Path, original_dir: Path, verbose=True):
    """
    Compare exported files against original JSON files.

    Args:
        export_dir: Directory with exported files
        original_dir: Directory with original files
        verbose: Print progress

    Returns:
        Dict with comparison results
    """
    if verbose:
        print(f"\nComparing {export_dir} vs {original_dir}...")

    # Get list of exported files
    exported_files = list(export_dir.glob('*_data.json'))

    total = len(exported_files)
    matching = 0
    different = 0
    missing = 0
    differences = []

    for i, export_file in enumerate(exported_files, 1):
        anp_id = export_file.stem.replace('_data', '')
        original_file = original_dir / export_file.name

        if not original_file.exists():
            missing += 1
            if verbose:
                print(f"  [{i}/{total}] {anp_id}: MISSING original")
            continue

        are_equal, diff = compare_json_files(original_file, export_file)

        if are_equal:
            matching += 1
            if verbose and i % 50 == 0:
                print(f"  [{i}/{total}] Progress: {matching} matching so far...")
        else:
            different += 1
            differences.append({
                'anp_id': anp_id,
                'diff_preview': diff[:10] if diff else []
            })
            if verbose:
                print(f"  [{i}/{total}] {anp_id}: DIFFERENT")

    if verbose:
        print(f"\nComparison Results:")
        print(f"  Matching: {matching}/{total}")
        print(f"  Different: {different}")
        print(f"  Missing original: {missing}")

    return {
        'total': total,
        'matching': matching,
        'different': different,
        'missing': missing,
        'differences': differences[:10]  # Limit to first 10
    }


def main():
    parser = argparse.ArgumentParser(description='Export FondoGIS data from PostgreSQL to JSON')
    parser.add_argument('--output', '-o', type=str, default=str(DEFAULT_OUTPUT_DIR),
                        help='Output directory for exported files')
    parser.add_argument('--test', action='store_true', help='Test mode: only export first 5 ANPs')
    parser.add_argument('--anp', type=str, help='Export single ANP by ID')
    parser.add_argument('--diff', action='store_true', help='Compare exported vs original files')
    parser.add_argument('--quiet', action='store_true', help='Suppress progress output')

    args = parser.parse_args()

    output_dir = Path(args.output)

    result = export_all(
        output_dir=output_dir,
        test_mode=args.test,
        single_anp=args.anp,
        verbose=not args.quiet
    )

    if args.diff and result['success']:
        diff_results = diff_exports(output_dir, ORIGINAL_DIR, verbose=not args.quiet)
        if diff_results['different'] > 0:
            print(f"\nWARNING: {diff_results['different']} files have differences!")
            sys.exit(1)

    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
