#!/usr/bin/env python3
"""
Import FondoGIS JSON files to PostgreSQL database.

This script reads all ANP JSON files from anp_data/ and imports them
into the PostgreSQL database as the single source of truth.

Usage:
    python3 scripts/import_json_to_db.py             # Import all ANPs
    python3 scripts/import_json_to_db.py --test      # Import first 5 ANPs only
    python3 scripts/import_json_to_db.py --anp calakmul  # Import single ANP
    python3 scripts/import_json_to_db.py --validate  # Validate after import
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db_utils import get_connection, test_connection

DATA_DIR = Path(__file__).parent.parent / 'anp_data'

# Dataset types that come from 'datasets' section
GEE_DATASETS = [
    'population', 'elevation', 'land_cover', 'forest', 'climate',
    'vegetation', 'night_lights', 'fire', 'biodiversity', 'human_modification',
    'water_stress', 'gedi_biomass', 'climate_projections', 'climate_portal',
    'soil', 'surface_water', 'mangroves'
]

# Dataset types that come from 'external_data' section
EXTERNAL_DATASETS = [
    'gbif_species', 'iucn_threatened', 'simec_nom059', 'nom059_enciclovida',
    'inegi_census', 'coneval_irs', 'inaturalist'
]


def parse_date(date_str):
    """Parse date string to date object, or return None."""
    if not date_str:
        return None
    try:
        # Try YYYY-MM-DD format
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def import_anp(conn, anp_id: str, data: dict, boundary_geojson: dict = None):
    """
    Import a single ANP into the database.

    Args:
        conn: Database connection
        anp_id: ANP identifier (e.g., 'calakmul')
        data: Full ANP data dict from JSON file
        boundary_geojson: Optional boundary GeoJSON dict

    Returns:
        Tuple of (success: bool, datasets_imported: int)
    """
    metadata = data.get('metadata', {})
    geometry = data.get('geometry', {})
    datasets = data.get('datasets', {})
    external_data = data.get('external_data', {})

    # Store full geometry in metadata for perfect round-trip
    metadata['_geometry'] = geometry

    with conn.cursor() as cur:
        # Insert/update main ANP record
        cur.execute("""
            INSERT INTO anps (
                id, name, designation, designation_type,
                area_km2, area_terrestrial_ha, area_marine_ha,
                wdpa_id, conanp_id, estados, region,
                iucn_category, governance, management_authority,
                primer_decreto, centroid, bounds, metadata
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                designation = EXCLUDED.designation,
                designation_type = EXCLUDED.designation_type,
                area_km2 = EXCLUDED.area_km2,
                area_terrestrial_ha = EXCLUDED.area_terrestrial_ha,
                area_marine_ha = EXCLUDED.area_marine_ha,
                wdpa_id = EXCLUDED.wdpa_id,
                conanp_id = EXCLUDED.conanp_id,
                estados = EXCLUDED.estados,
                region = EXCLUDED.region,
                iucn_category = EXCLUDED.iucn_category,
                governance = EXCLUDED.governance,
                management_authority = EXCLUDED.management_authority,
                primer_decreto = EXCLUDED.primer_decreto,
                centroid = EXCLUDED.centroid,
                bounds = EXCLUDED.bounds,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
        """, (
            anp_id,
            metadata.get('name'),
            metadata.get('designation') or metadata.get('categoria_de_manejo'),
            metadata.get('designation_type'),
            metadata.get('reported_area_km2'),
            metadata.get('superficie_terrestre_ha'),
            metadata.get('superficie_marina_ha'),
            metadata.get('wdpa_id'),
            metadata.get('id_anp_conanp'),
            metadata.get('estados', []),
            metadata.get('region'),
            metadata.get('iucn_category'),
            metadata.get('governance'),
            metadata.get('management_authority'),
            parse_date(metadata.get('primer_decreto')),
            json.dumps(geometry.get('centroid')),
            json.dumps(geometry.get('bounds')),
            json.dumps(metadata)
        ))

        # Import datasets from 'datasets' section
        datasets_imported = 0
        for dataset_type, dataset_data in datasets.items():
            if dataset_data:  # Skip None/empty datasets
                # Determine source based on dataset type
                source = 'gee' if dataset_type in GEE_DATASETS else 'external'
                extracted_at = dataset_data.get('extracted_at') if isinstance(dataset_data, dict) else None

                cur.execute("""
                    INSERT INTO anp_datasets (anp_id, dataset_type, data, source, extracted_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (anp_id, dataset_type) DO UPDATE SET
                        data = EXCLUDED.data,
                        source = COALESCE(EXCLUDED.source, anp_datasets.source),
                        extracted_at = COALESCE(EXCLUDED.extracted_at, anp_datasets.extracted_at)
                """, (
                    anp_id,
                    dataset_type,
                    json.dumps(dataset_data),
                    source,
                    extracted_at
                ))
                datasets_imported += 1

        # Import datasets from 'external_data' section
        for dataset_type, dataset_data in external_data.items():
            if dataset_data:  # Skip None/empty datasets
                # Map source based on dataset type
                source_map = {
                    'gbif_species': 'gbif',
                    'iucn_threatened': 'iucn',
                    'simec_nom059': 'simec',
                    'nom059_enciclovida': 'enciclovida',
                    'inegi_census': 'inegi',
                    'coneval_irs': 'coneval',
                    'inaturalist': 'inaturalist'
                }
                source = source_map.get(dataset_type, 'external')

                cur.execute("""
                    INSERT INTO anp_datasets (anp_id, dataset_type, data, source, extracted_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (anp_id, dataset_type) DO UPDATE SET
                        data = EXCLUDED.data,
                        source = COALESCE(EXCLUDED.source, anp_datasets.source)
                """, (
                    anp_id,
                    dataset_type,
                    json.dumps(dataset_data),
                    source
                ))
                datasets_imported += 1

        # Import boundary if provided
        if boundary_geojson:
            cur.execute("""
                INSERT INTO anp_boundaries (anp_id, geojson)
                VALUES (%s, %s)
                ON CONFLICT (anp_id) DO UPDATE SET
                    geojson = EXCLUDED.geojson,
                    created_at = NOW()
            """, (anp_id, json.dumps(boundary_geojson)))

    return True, datasets_imported


def get_all_anp_files():
    """Get list of all ANP data files."""
    files = []
    for f in DATA_DIR.glob('*_data.json'):
        anp_id = f.stem.replace('_data', '')
        boundary_file = DATA_DIR / f'{anp_id}_boundary.geojson'
        files.append({
            'anp_id': anp_id,
            'data_file': f,
            'boundary_file': boundary_file if boundary_file.exists() else None
        })
    return sorted(files, key=lambda x: x['anp_id'])


def import_all(test_mode=False, single_anp=None, verbose=True):
    """
    Import all ANP files to database.

    Args:
        test_mode: If True, only import first 5 ANPs
        single_anp: If set, only import this specific ANP
        verbose: Print progress

    Returns:
        Dict with import statistics
    """
    if not test_connection():
        print("ERROR: Cannot connect to database")
        return {'success': False, 'error': 'Connection failed'}

    anp_files = get_all_anp_files()

    if single_anp:
        anp_files = [f for f in anp_files if f['anp_id'] == single_anp]
        if not anp_files:
            print(f"ERROR: ANP '{single_anp}' not found")
            return {'success': False, 'error': f'ANP not found: {single_anp}'}
    elif test_mode:
        anp_files = anp_files[:5]

    total = len(anp_files)
    imported = 0
    failed = 0
    total_datasets = 0
    errors = []

    if verbose:
        print(f"Importing {total} ANPs to database...")

    with get_connection() as conn:
        for i, anp_info in enumerate(anp_files, 1):
            anp_id = anp_info['anp_id']

            try:
                # Load data file
                with open(anp_info['data_file'], 'r') as f:
                    data = json.load(f)

                # Load boundary if exists
                boundary = None
                if anp_info['boundary_file']:
                    with open(anp_info['boundary_file'], 'r') as f:
                        boundary = json.load(f)

                # Import to database
                success, datasets = import_anp(conn, anp_id, data, boundary)

                if success:
                    imported += 1
                    total_datasets += datasets
                    if verbose:
                        print(f"  [{i}/{total}] {anp_id}: {datasets} datasets")
                else:
                    failed += 1
                    errors.append({'anp_id': anp_id, 'error': 'Import returned False'})

            except Exception as e:
                failed += 1
                errors.append({'anp_id': anp_id, 'error': str(e)})
                if verbose:
                    print(f"  [{i}/{total}] {anp_id}: ERROR - {e}")

        conn.commit()

    if verbose:
        print(f"\nImport complete:")
        print(f"  ANPs imported: {imported}/{total}")
        print(f"  Total datasets: {total_datasets}")
        if failed:
            print(f"  Failed: {failed}")

    return {
        'success': failed == 0,
        'total': total,
        'imported': imported,
        'failed': failed,
        'total_datasets': total_datasets,
        'errors': errors
    }


def validate_import():
    """Validate that import matches source JSON files."""
    print("Validating import...")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Count ANPs
            cur.execute("SELECT COUNT(*) FROM anps")
            db_anp_count = cur.fetchone()[0]

            # Count datasets
            cur.execute("SELECT COUNT(*) FROM anp_datasets")
            db_dataset_count = cur.fetchone()[0]

            # Count boundaries
            cur.execute("SELECT COUNT(*) FROM anp_boundaries")
            db_boundary_count = cur.fetchone()[0]

            # Count by dataset type
            cur.execute("""
                SELECT dataset_type, COUNT(*) as cnt
                FROM anp_datasets
                GROUP BY dataset_type
                ORDER BY cnt DESC
            """)
            dataset_counts = cur.fetchall()

    # Count source files
    anp_files = get_all_anp_files()
    json_anp_count = len(anp_files)
    json_boundary_count = sum(1 for f in anp_files if f['boundary_file'])

    print(f"\nValidation Results:")
    print(f"  ANPs in database: {db_anp_count}")
    print(f"  ANPs in JSON files: {json_anp_count}")
    print(f"  Match: {'YES' if db_anp_count == json_anp_count else 'NO'}")
    print(f"\n  Boundaries in database: {db_boundary_count}")
    print(f"  Boundaries in JSON: {json_boundary_count}")
    print(f"  Match: {'YES' if db_boundary_count == json_boundary_count else 'NO'}")
    print(f"\n  Total datasets in database: {db_dataset_count}")
    print(f"\n  Datasets by type:")
    for dtype, count in dataset_counts:
        print(f"    {dtype}: {count}")

    return db_anp_count == json_anp_count


def main():
    parser = argparse.ArgumentParser(description='Import FondoGIS JSON files to PostgreSQL')
    parser.add_argument('--test', action='store_true', help='Test mode: only import first 5 ANPs')
    parser.add_argument('--anp', type=str, help='Import single ANP by ID')
    parser.add_argument('--validate', action='store_true', help='Validate import after completion')
    parser.add_argument('--quiet', action='store_true', help='Suppress progress output')

    args = parser.parse_args()

    result = import_all(
        test_mode=args.test,
        single_anp=args.anp,
        verbose=not args.quiet
    )

    if args.validate and result['success']:
        validate_import()

    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
