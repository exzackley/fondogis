#!/usr/bin/env python3
"""
Database utilities for FondoGIS PostgreSQL connection.

Usage:
    from db.db_utils import get_connection, execute_query

    # Context manager (recommended)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM anps WHERE id = %s", ['calakmul'])
            row = cur.fetchone()

    # Simple query helper
    rows = execute_query("SELECT id, name FROM anps WHERE designation_type = %s", ['RB'])

Environment variables:
    FONDOGIS_DB_HOST - Database host (default: 172.232.163.60)
    FONDOGIS_DB_PORT - Database port (default: 5432)
    FONDOGIS_DB_NAME - Database name (default: fondogis)
    FONDOGIS_DB_USER - Database user (default: zack)
    POSTGRES_PASSWORD - Database password (from ~/.zshrc)
"""

import os
import json
from contextlib import contextmanager
from typing import Any, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("Warning: psycopg2 not installed. Run: pip install psycopg2-binary")

# Database configuration with defaults
DB_CONFIG = {
    'host': os.environ.get('FONDOGIS_DB_HOST', '172.232.163.60'),
    'port': int(os.environ.get('FONDOGIS_DB_PORT', 5432)),
    'dbname': os.environ.get('FONDOGIS_DB_NAME', 'fondogis'),
    'user': os.environ.get('FONDOGIS_DB_USER', 'postgres'),
    'password': os.environ.get('POSTGRES_PASSWORD', ''),
}

# Connection pool (simple implementation)
_connection_pool = []
_max_pool_size = 5


def get_db_config() -> dict:
    """Return current database configuration (without password)."""
    return {k: v for k, v in DB_CONFIG.items() if k != 'password'}


@contextmanager
def get_connection(autocommit: bool = False):
    """
    Get a database connection.

    Args:
        autocommit: If True, each statement commits immediately.

    Yields:
        psycopg2 connection object

    Example:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM anps")
    """
    if not PSYCOPG2_AVAILABLE:
        raise ImportError("psycopg2 is required. Install with: pip install psycopg2-binary")

    if not DB_CONFIG['password']:
        raise ValueError(
            "Database password not set. Ensure POSTGRES_PASSWORD is in your environment.\n"
            "Add to ~/.zshrc: export POSTGRES_PASSWORD='your_password'"
        )

    conn = None
    try:
        # Create fresh connection each time (simpler, more reliable)
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = autocommit
        yield conn

        if not autocommit:
            conn.commit()

    except Exception:
        if conn and not autocommit:
            try:
                conn.rollback()
            except Exception:
                pass
        raise

    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def execute_query(query: str, params: Optional[tuple] = None, fetch: str = 'all') -> Any:
    """
    Execute a query and return results.

    Args:
        query: SQL query string
        params: Query parameters (tuple or list)
        fetch: 'all', 'one', or 'none'

    Returns:
        Query results as list of dicts (fetch='all'),
        single dict (fetch='one'), or None (fetch='none')

    Example:
        rows = execute_query(
            "SELECT * FROM anps WHERE designation_type = %s",
            ('RB',)
        )
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)

            if fetch == 'all':
                return [dict(row) for row in cur.fetchall()]
            elif fetch == 'one':
                row = cur.fetchone()
                return dict(row) if row else None
            else:
                return None


def execute_many(query: str, params_list: list) -> int:
    """
    Execute a query with multiple parameter sets.

    Args:
        query: SQL query string with placeholders
        params_list: List of parameter tuples

    Returns:
        Number of rows affected

    Example:
        execute_many(
            "INSERT INTO anps (id, name) VALUES (%s, %s)",
            [('anp1', 'Name 1'), ('anp2', 'Name 2')]
        )
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, params_list)
            return cur.rowcount


def upsert_anp(anp_id: str, data: dict) -> bool:
    """
    Insert or update an ANP record.

    Args:
        anp_id: ANP identifier (e.g., 'calakmul')
        data: Full ANP data dict (from JSON file)

    Returns:
        True if successful
    """
    metadata = data.get('metadata', {})

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO anps (
                    id, name, designation, designation_type,
                    area_km2, area_terrestrial_ha, area_marine_ha,
                    wdpa_id, conanp_id, estados, region,
                    iucn_category, governance, management_authority,
                    metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """, (
                anp_id,
                metadata.get('name'),
                metadata.get('designation'),
                metadata.get('designation_type'),
                metadata.get('reported_area_km2'),
                metadata.get('official_terrestre_ha'),
                metadata.get('official_marina_ha'),
                metadata.get('wdpa_id'),
                metadata.get('conanp_id'),
                metadata.get('estados', []),
                metadata.get('region'),
                metadata.get('iucn_category'),
                metadata.get('governance'),
                metadata.get('management_authority'),
                Json(metadata)
            ))
    return True


def upsert_dataset(anp_id: str, dataset_type: str, data: dict, source: str = None) -> bool:
    """
    Insert or update a dataset for an ANP.

    Args:
        anp_id: ANP identifier
        dataset_type: Dataset type (e.g., 'population', 'forest', 'climate_projections')
        data: Dataset data dict
        source: Data source (e.g., 'gee', 'gbif')

    Returns:
        True if successful
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO anp_datasets (anp_id, dataset_type, data, source, extracted_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (anp_id, dataset_type) DO UPDATE SET
                    data = EXCLUDED.data,
                    source = COALESCE(EXCLUDED.source, anp_datasets.source),
                    extracted_at = NOW()
            """, (anp_id, dataset_type, Json(data), source))
    return True


def upsert_boundary(anp_id: str, geojson: dict) -> bool:
    """
    Insert or update a boundary geometry for an ANP.

    Args:
        anp_id: ANP identifier
        geojson: GeoJSON dict with boundary geometry

    Returns:
        True if successful
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Convert GeoJSON to PostGIS geometry
            cur.execute("""
                INSERT INTO anp_boundaries (anp_id, boundary, geojson)
                VALUES (
                    %s,
                    ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
                    %s
                )
                ON CONFLICT (anp_id) DO UPDATE SET
                    boundary = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
                    geojson = EXCLUDED.geojson,
                    created_at = NOW()
            """, (
                anp_id,
                json.dumps(geojson.get('geometry', geojson)),
                Json(geojson),
                json.dumps(geojson.get('geometry', geojson))
            ))
    return True


def log_extraction(anp_id: str, dataset_type: str, script_name: str,
                   status: str, error_message: str = None, rows_affected: int = None):
    """Log an extraction operation."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO extraction_log
                    (anp_id, dataset_type, script_name, status, error_message, rows_affected, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (anp_id, dataset_type, script_name, status, error_message, rows_affected))


def save_anp_data(anp_id: str, data: dict, boundary_geojson: dict = None, source: str = 'gee') -> dict:
    """
    Save complete ANP data structure to database.

    This is the main function to call after extracting data from GEE or other sources.
    It handles metadata, geometry, all datasets, and boundary in one transaction.

    Args:
        anp_id: ANP identifier (e.g., 'calakmul')
        data: Full ANP data dict with keys: metadata, geometry, datasets, external_data
        boundary_geojson: Optional boundary GeoJSON FeatureCollection
        source: Data source identifier (default: 'gee')

    Returns:
        Dict with save results: {'success': bool, 'datasets_saved': int, 'error': str}

    Example:
        data = extract_all_data(anp_feature)  # From add_anp.py
        boundary = extract_boundary_geojson(anp_feature)
        result = save_anp_data('calakmul', data, boundary)
    """
    metadata = data.get('metadata', {})
    geometry = data.get('geometry', {})
    datasets = data.get('datasets', {})
    external_data = data.get('external_data', {})

    # Store geometry in metadata for perfect round-trip export
    metadata['_geometry'] = geometry

    datasets_saved = 0

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Save ANP record
                cur.execute("""
                    INSERT INTO anps (
                        id, name, designation, designation_type,
                        area_km2, wdpa_id, estados, region,
                        iucn_category, governance, management_authority,
                        centroid, bounds, metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        designation = EXCLUDED.designation,
                        designation_type = EXCLUDED.designation_type,
                        area_km2 = EXCLUDED.area_km2,
                        wdpa_id = EXCLUDED.wdpa_id,
                        estados = EXCLUDED.estados,
                        region = EXCLUDED.region,
                        iucn_category = EXCLUDED.iucn_category,
                        governance = EXCLUDED.governance,
                        management_authority = EXCLUDED.management_authority,
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
                    metadata.get('wdpa_id'),
                    metadata.get('estados', []),
                    metadata.get('region'),
                    metadata.get('iucn_category'),
                    metadata.get('governance'),
                    metadata.get('management_authority'),
                    json.dumps(geometry.get('centroid')),
                    json.dumps(geometry.get('bounds')),
                    Json(metadata)
                ))

                # 2. Save all datasets
                for dataset_type, dataset_data in datasets.items():
                    if dataset_data:
                        cur.execute("""
                            INSERT INTO anp_datasets (anp_id, dataset_type, data, source, extracted_at)
                            VALUES (%s, %s, %s, %s, NOW())
                            ON CONFLICT (anp_id, dataset_type) DO UPDATE SET
                                data = EXCLUDED.data,
                                source = COALESCE(EXCLUDED.source, anp_datasets.source),
                                extracted_at = NOW()
                        """, (anp_id, dataset_type, Json(dataset_data), source))
                        datasets_saved += 1

                # 3. Save external data as datasets
                for dataset_type, dataset_data in external_data.items():
                    if dataset_data:
                        ext_source = {
                            'gbif_species': 'gbif',
                            'inaturalist': 'inaturalist',
                            'inegi_census': 'inegi',
                            'coneval_irs': 'coneval',
                            'simec_nom059': 'simec'
                        }.get(dataset_type, 'external')
                        cur.execute("""
                            INSERT INTO anp_datasets (anp_id, dataset_type, data, source, extracted_at)
                            VALUES (%s, %s, %s, %s, NOW())
                            ON CONFLICT (anp_id, dataset_type) DO UPDATE SET
                                data = EXCLUDED.data,
                                source = COALESCE(EXCLUDED.source, anp_datasets.source),
                                extracted_at = NOW()
                        """, (anp_id, dataset_type, Json(dataset_data), ext_source))
                        datasets_saved += 1

                # 4. Save boundary if provided
                if boundary_geojson:
                    cur.execute("""
                        INSERT INTO anp_boundaries (anp_id, geojson)
                        VALUES (%s, %s)
                        ON CONFLICT (anp_id) DO UPDATE SET
                            geojson = EXCLUDED.geojson,
                            created_at = NOW()
                    """, (anp_id, Json(boundary_geojson)))

            conn.commit()

        return {'success': True, 'datasets_saved': datasets_saved}

    except Exception as e:
        return {'success': False, 'datasets_saved': datasets_saved, 'error': str(e)}


def export_anp_to_json(anp_id: str, output_dir: str = 'anp_data') -> dict:
    """
    Export a single ANP from database to JSON files.

    Args:
        anp_id: ANP identifier
        output_dir: Directory to write files (default: 'anp_data')

    Returns:
        Dict with export results: {'success': bool, 'data_file': str, 'boundary_file': str}
    """
    from pathlib import Path

    # Get ANP data
    anp = execute_query(
        "SELECT * FROM anps WHERE id = %s",
        (anp_id,),
        fetch='one'
    )

    if not anp:
        return {'success': False, 'error': f'ANP not found: {anp_id}'}

    # Get datasets
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

    # Reconstruct JSON structure
    metadata = anp.get('metadata') or {}

    # Build geometry from stored _geometry
    geometry = metadata.pop('_geometry', {})
    if not geometry:
        if anp.get('centroid'):
            geometry['centroid'] = anp['centroid']
        if anp.get('bounds'):
            geometry['bounds'] = anp['bounds']

    # Categorize datasets
    gee_datasets = {
        'population', 'elevation', 'land_cover', 'forest', 'climate',
        'vegetation', 'night_lights', 'fire', 'biodiversity', 'human_modification',
        'water_stress', 'gedi_biomass', 'climate_projections', 'climate_portal',
        'soil', 'surface_water', 'mangroves'
    }

    datasets = {}
    external_data = {}

    for row in datasets_rows:
        dtype = row['dataset_type']
        if dtype in gee_datasets:
            datasets[dtype] = row['data']
        else:
            external_data[dtype] = row['data']

    # Build final structure
    anp_data = {
        'metadata': metadata,
        'geometry': geometry,
        'datasets': datasets
    }
    if external_data:
        anp_data['external_data'] = external_data

    # Write files
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    data_file = output_path / f'{anp_id}_data.json'
    with open(data_file, 'w') as f:
        json.dump(anp_data, f, indent=2, ensure_ascii=False)

    boundary_file = None
    if boundary and boundary.get('geojson'):
        boundary_file = output_path / f'{anp_id}_boundary.geojson'
        with open(boundary_file, 'w') as f:
            json.dump(boundary['geojson'], f, indent=2, ensure_ascii=False)

    return {
        'success': True,
        'data_file': str(data_file),
        'boundary_file': str(boundary_file) if boundary_file else None
    }


def test_connection() -> bool:
    """Test database connection."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                print(f"Connected to: {version}")
                return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False


if __name__ == '__main__':
    # Test connection when run directly
    print(f"Database config: {get_db_config()}")
    test_connection()
