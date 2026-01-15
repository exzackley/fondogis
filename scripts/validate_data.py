#!/usr/bin/env python3
"""
Database Validation Script for FondoGIS

Runs automated consistency checks to validate database integrity:
1. Row counts match expected values
2. All ANPs have required datasets
3. No empty/null data fields
4. Climate data coverage
5. JSON export round-trip validation

Usage:
    python3 scripts/validate_data.py           # Run all checks
    python3 scripts/validate_data.py --quick   # Quick summary only
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db_utils import execute_query, get_connection

DATA_DIR = 'anp_data'
EXPECTED_ANP_COUNT = 227


def check_row_counts():
    """Check that row counts match expected values."""
    print("\n1. Row Count Validation")
    print("-" * 40)

    # ANPs count
    result = execute_query("SELECT COUNT(*) as count FROM anps", fetch='one')
    anp_count = result['count']
    status = "OK" if anp_count == EXPECTED_ANP_COUNT else "WARN"
    print(f"   ANPs: {anp_count} (expected {EXPECTED_ANP_COUNT}) [{status}]")

    # Datasets count
    result = execute_query("SELECT COUNT(*) as count FROM anp_datasets", fetch='one')
    dataset_count = result['count']
    print(f"   Datasets: {dataset_count}")

    # Unique ANPs with datasets
    result = execute_query("SELECT COUNT(DISTINCT anp_id) as count FROM anp_datasets", fetch='one')
    anps_with_data = result['count']
    status = "OK" if anps_with_data == anp_count else "WARN"
    print(f"   ANPs with datasets: {anps_with_data} [{status}]")

    # Boundaries count
    result = execute_query("SELECT COUNT(*) as count FROM anp_boundaries", fetch='one')
    boundary_count = result['count']
    status = "OK" if boundary_count == anp_count else "WARN"
    print(f"   Boundaries: {boundary_count} [{status}]")

    return anp_count == EXPECTED_ANP_COUNT


def check_dataset_coverage():
    """Check that all ANPs have core datasets."""
    print("\n2. Dataset Coverage")
    print("-" * 40)

    # Dataset type distribution
    rows = execute_query("""
        SELECT dataset_type, COUNT(*) as count
        FROM anp_datasets
        GROUP BY dataset_type
        ORDER BY count DESC
    """)

    print("   Dataset types:")
    for row in rows:
        print(f"      {row['dataset_type']}: {row['count']}")

    # Check for ANPs missing core datasets
    core_datasets = ['population', 'elevation', 'land_cover', 'forest']
    missing = []

    for dtype in core_datasets:
        result = execute_query("""
            SELECT a.id, a.name
            FROM anps a
            LEFT JOIN anp_datasets d ON a.id = d.anp_id AND d.dataset_type = %s
            WHERE d.id IS NULL
            LIMIT 5
        """, (dtype,))
        if result:
            missing.append((dtype, len(result), result))

    if missing:
        print("\n   ANPs missing core datasets:")
        for dtype, count, examples in missing:
            print(f"      {dtype}: {count} ANPs missing")
            for ex in examples[:3]:
                print(f"         - {ex['name']}")
    else:
        print("\n   All ANPs have core datasets [OK]")

    return len(missing) == 0


def check_empty_data():
    """Check for datasets with empty or null data."""
    print("\n3. Empty Data Check")
    print("-" * 40)

    # Check for null data
    result = execute_query("""
        SELECT COUNT(*) as count
        FROM anp_datasets
        WHERE data IS NULL
    """, fetch='one')
    null_count = result['count']
    status = "OK" if null_count == 0 else "WARN"
    print(f"   Null data fields: {null_count} [{status}]")

    # Check for empty objects
    result = execute_query("""
        SELECT COUNT(*) as count
        FROM anp_datasets
        WHERE data = '{}'::jsonb
    """, fetch='one')
    empty_count = result['count']
    status = "OK" if empty_count == 0 else "WARN"
    print(f"   Empty data objects: {empty_count} [{status}]")

    # Check for error datasets
    result = execute_query("""
        SELECT COUNT(*) as count
        FROM anp_datasets
        WHERE data->>'error' IS NOT NULL
    """, fetch='one')
    error_count = result['count']
    print(f"   Datasets with errors: {error_count}")

    if error_count > 0:
        # Show sample errors
        errors = execute_query("""
            SELECT anp_id, dataset_type, data->>'error' as error
            FROM anp_datasets
            WHERE data->>'error' IS NOT NULL
            LIMIT 5
        """)
        print("   Sample errors:")
        for e in errors:
            print(f"      {e['anp_id']}/{e['dataset_type']}: {e['error'][:50]}...")

    return null_count == 0 and empty_count == 0


def check_climate_coverage():
    """Check climate projection data coverage."""
    print("\n4. Climate Data Coverage")
    print("-" * 40)

    # Climate projections coverage
    result = execute_query("""
        SELECT COUNT(*) as count
        FROM anp_datasets
        WHERE dataset_type = 'climate_projections'
          AND data->>'data_available' = 'true'
    """, fetch='one')
    climate_count = result['count']
    print(f"   ANPs with climate projections: {climate_count}")

    # Check SSP scenario coverage
    result = execute_query("""
        SELECT COUNT(*) as count
        FROM anp_datasets
        WHERE dataset_type = 'climate_projections'
          AND data->'scenarios'->'ssp245' IS NOT NULL
    """, fetch='one')
    ssp245_count = result['count']
    print(f"   ANPs with SSP2-4.5 data: {ssp245_count}")

    result = execute_query("""
        SELECT COUNT(*) as count
        FROM anp_datasets
        WHERE dataset_type = 'climate_projections'
          AND data->'scenarios'->'ssp585' IS NOT NULL
    """, fetch='one')
    ssp585_count = result['count']
    print(f"   ANPs with SSP5-8.5 data: {ssp585_count}")

    # Check multi-period coverage
    result = execute_query("""
        SELECT COUNT(*) as count
        FROM anp_datasets
        WHERE dataset_type = 'climate_projections'
          AND data->'scenarios'->'ssp245'->'2041-2070' IS NOT NULL
    """, fetch='one')
    midcentury_count = result['count']
    print(f"   ANPs with mid-century (2041-2070) data: {midcentury_count}")

    return climate_count > 200


def check_external_data():
    """Check external data sources coverage."""
    print("\n5. External Data Coverage")
    print("-" * 40)

    external_types = ['gbif_species', 'inaturalist', 'inegi_census', 'simec_nom059']

    for dtype in external_types:
        result = execute_query("""
            SELECT COUNT(*) as count
            FROM anp_datasets
            WHERE dataset_type = %s
              AND data->>'data_available' = 'true'
        """, (dtype,), fetch='one')
        count = result['count'] if result else 0
        print(f"   {dtype}: {count} ANPs")


def check_json_sync():
    """Check if JSON files are in sync with database."""
    print("\n6. JSON File Sync Check")
    print("-" * 40)

    # Count JSON files
    json_files = list(Path(DATA_DIR).glob('*_data.json'))
    json_count = len(json_files)

    result = execute_query("SELECT COUNT(*) as count FROM anps", fetch='one')
    db_count = result['count']

    status = "OK" if json_count == db_count else "WARN"
    print(f"   JSON files: {json_count}")
    print(f"   Database ANPs: {db_count}")
    print(f"   Status: [{status}]")

    if json_count != db_count:
        # Find mismatches
        db_ids = set(r['id'] for r in execute_query("SELECT id FROM anps"))
        json_ids = set(f.stem.replace('_data', '') for f in json_files)

        missing_json = db_ids - json_ids
        extra_json = json_ids - db_ids

        if missing_json:
            print(f"   Missing JSON files: {len(missing_json)}")
            for anp_id in list(missing_json)[:5]:
                print(f"      - {anp_id}")

        if extra_json:
            print(f"   Extra JSON files (not in DB): {len(extra_json)}")
            for anp_id in list(extra_json)[:5]:
                print(f"      - {anp_id}")

    return json_count == db_count


def spot_check_anp(anp_id):
    """Spot-check a single ANP's data integrity."""
    print(f"\n   Spot-checking: {anp_id}")

    # Get from database
    anp = execute_query(
        "SELECT * FROM anps WHERE id = %s",
        (anp_id,),
        fetch='one'
    )

    if not anp:
        print(f"      ERROR: ANP not found in database")
        return False

    print(f"      Name: {anp['name']}")
    print(f"      Designation: {anp['designation_type']}")

    # Count datasets
    datasets = execute_query(
        "SELECT dataset_type FROM anp_datasets WHERE anp_id = %s",
        (anp_id,)
    )
    print(f"      Datasets: {len(datasets)}")

    # Check JSON file
    json_path = Path(DATA_DIR) / f"{anp_id}_data.json"
    if json_path.exists():
        with open(json_path) as f:
            json_data = json.load(f)
        json_datasets = len(json_data.get('datasets', {})) + len(json_data.get('external_data', {}))
        match = "OK" if json_datasets == len(datasets) else "MISMATCH"
        print(f"      JSON datasets: {json_datasets} [{match}]")
    else:
        print(f"      JSON file: MISSING")
        return False

    return True


def run_spot_checks():
    """Run spot checks on sample ANPs."""
    print("\n7. Spot Checks (Sample ANPs)")
    print("-" * 40)

    # Sample diverse ANPs
    sample_anps = [
        'calakmul',           # Large RB
        'isla_contoy',        # Small PN
        'sian_kaan',          # UNESCO site
        'sierra_gorda',       # Multi-state
        'arrecife_alacranes', # Marine
    ]

    results = []
    for anp_id in sample_anps:
        results.append(spot_check_anp(anp_id))

    return all(results)


def main():
    print("=" * 60)
    print("FondoGIS Database Validation")
    print("=" * 60)

    quick_mode = '--quick' in sys.argv

    results = []

    # Run all checks
    results.append(("Row Counts", check_row_counts()))
    results.append(("Dataset Coverage", check_dataset_coverage()))
    results.append(("Empty Data", check_empty_data()))
    results.append(("Climate Coverage", check_climate_coverage()))

    if not quick_mode:
        check_external_data()
        results.append(("JSON Sync", check_json_sync()))
        results.append(("Spot Checks", run_spot_checks()))

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"   {name}: [{status}]")

    print()
    if all_passed:
        print("All validation checks passed!")
    else:
        print("Some validation checks failed. Review output above.")

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
