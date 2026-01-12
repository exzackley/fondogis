#!/usr/bin/env python3
"""
Coastal/Marine ANPs Registry Helper
===================================

Helper module for working with the coastal/marine ANPs subset.
Import this in report generation scripts.

Usage:
    from coastal_anps_registry import (
        get_coastal_anps,
        get_coastal_anp_ids,
        is_coastal_anp,
        get_coastal_data_file
    )
"""

import json
import os
from typing import List, Dict, Optional

_SUBSET_FILE = os.path.join(os.path.dirname(__file__), 'coastal_anps_subset.json')
_cache: Dict = {}


def _load_subset() -> Dict:
    """Load the coastal ANPs subset file."""
    global _cache
    if not _cache:
        with open(_SUBSET_FILE, 'r', encoding='utf-8') as f:
            _cache = json.load(f)
    return _cache


def get_coastal_anps() -> List[Dict]:
    """Get all coastal/marine ANPs with full metadata."""
    return _load_subset()['matched_anps']


def get_coastal_anp_ids() -> List[str]:
    """Get list of all coastal ANP IDs."""
    return _load_subset()['anp_ids']


def get_coastal_anps_with_data() -> List[str]:
    """Get list of coastal ANP IDs that have data files."""
    return _load_subset()['anp_ids_with_data']


def get_coastal_anps_missing_data() -> List[str]:
    """Get list of coastal ANP IDs that are missing data files."""
    return _load_subset()['anp_ids_missing_data']


def is_coastal_anp(anp_id: str) -> bool:
    """Check if an ANP ID is in the coastal subset."""
    return anp_id in get_coastal_anp_ids()


def get_coastal_anp_by_id(anp_id: str) -> Optional[Dict]:
    """Get coastal ANP metadata by ID."""
    for anp in get_coastal_anps():
        if anp['id'] == anp_id:
            return anp
    return None


def get_coastal_data_file(anp_id: str) -> Optional[str]:
    """Get the data file path for a coastal ANP (returns None if no data file exists)."""
    anp = get_coastal_anp_by_id(anp_id)
    if anp and anp.get('data_file'):
        return f"anp_data/{anp['data_file']}"
    return None


def get_coastal_anps_by_category(category: str) -> List[Dict]:
    """Get all coastal ANPs in a specific category (RB, PN, APFF, Sant)."""
    return [anp for anp in get_coastal_anps() if anp['category'] == category]


def get_coastal_summary() -> Dict:
    """Get summary statistics for coastal ANPs."""
    subset = _load_subset()
    anps = subset['matched_anps']

    # Count by category
    categories = {}
    for anp in anps:
        cat = anp['category']
        categories[cat] = categories.get(cat, 0) + 1

    return {
        'total': subset['_meta']['total_anps'],
        'with_data': subset['_meta']['anps_with_data'],
        'missing_data': subset['_meta']['anps_missing_data'],
        'categories': categories
    }


if __name__ == '__main__':
    print("COASTAL/MARINE ANPs REGISTRY")
    print("=" * 60)

    summary = get_coastal_summary()
    print(f"Total coastal ANPs: {summary['total']}")
    print(f"With data files: {summary['with_data']}")
    print(f"Missing data: {summary['missing_data']}")

    print("\nBy Category:")
    for cat, count in sorted(summary['categories'].items()):
        print(f"  {cat}: {count}")

    print("\nSample ANPs:")
    for anp in get_coastal_anps()[:5]:
        status = "✓" if anp['has_data'] else "✗"
        print(f"  {status} [{anp['category']}] {anp['matched_name']}")

    print("\nMissing Data Files:")
    for anp_id in get_coastal_anps_missing_data():
        anp = get_coastal_anp_by_id(anp_id)
        print(f"  ✗ {anp['matched_name']}")
