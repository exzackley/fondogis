#!/usr/bin/env python3
"""
ANP Registry - Central Source of Truth for Protected Areas

All scripts should import from here instead of maintaining their own ANP lists.

Usage:
    from anp_registry import get_all_anps, get_anp_by_id, get_anps_by_category

    # Optional: read from database instead of JSON file
    from anp_registry import get_all_anps_from_db
"""

import json
import os
import re
import unicodedata
from typing import Dict, List, Optional, Iterator

# Database support (optional)
try:
    from db.db_utils import execute_query
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False

_REGISTRY_FILE = os.path.join(os.path.dirname(__file__), 'reference_data', 'official_anp_list.json')
_cache: Dict = {}
_db_cache: List[Dict] = []
_use_database: bool = False


def _load_registry() -> Dict:
    global _cache
    if not _cache:
        with open(_REGISTRY_FILE, 'r', encoding='utf-8') as f:
            _cache = json.load(f)
    return _cache


def _load_from_database() -> List[Dict]:
    """Load ANP list from database."""
    global _db_cache
    if not _db_cache and HAS_DATABASE:
        rows = execute_query(
            """SELECT id, name, designation, designation_type,
                      area_km2, estados, region, metadata
               FROM anps ORDER BY name"""
        )
        _db_cache = []
        for row in rows:
            metadata = row.get('metadata') or {}
            _db_cache.append({
                'id': row['id'],
                'name': row['name'],
                'category': row['designation_type'] or metadata.get('designation_type'),
                'designation': row['designation'] or metadata.get('designation'),
                'area_km2': row['area_km2'],
                'states': row['estados'] or metadata.get('estados', []),
                'region': row['region'] or metadata.get('region'),
            })
    return _db_cache


def use_database(enable: bool = True) -> None:
    """Enable or disable database as the source for ANP registry.

    Args:
        enable: If True, get_all_anps() will read from database instead of JSON file.

    Example:
        from anp_registry import use_database, get_all_anps
        use_database(True)  # Switch to database mode
        anps = get_all_anps()  # Now reads from database
    """
    global _use_database
    if enable and not HAS_DATABASE:
        raise ImportError("Database module not available. Install psycopg2-binary and configure db/db_utils.py")
    _use_database = enable


def get_all_anps_from_db() -> List[Dict]:
    """Get all ANPs directly from database (bypasses normal registry source)."""
    if not HAS_DATABASE:
        raise ImportError("Database module not available")
    return _load_from_database()


def normalize_anp_name(name: str) -> str:
    """Normalize an ANP name for matching by removing accents, prefixes, and articles."""
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    name = name.lower().strip()
    
    prefixes = [
        'rb ', 'pn ', 'apff ', 'aprn ', 'sant ', 'mn ', 'santuario ',
        'reserva de la biosfera ', 'parque nacional ', 
        'area de proteccion de flora y fauna ',
        'area de proteccion de recursos naturales ',
        'monumento natural '
    ]
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):]
    
    for article in ['el ', 'la ', 'los ', 'las ', 'de ', 'del ', 'y ']:
        name = name.replace(article, ' ')
    
    return re.sub(r'\s+', ' ', name).strip()


def name_to_id(name: str) -> str:
    """Convert an ANP name to a standardized ID."""
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '_', name)
    return re.sub(r'_+', '_', name).strip('_')


def get_all_anps() -> List[Dict]:
    """Get all ANPs from the official registry.

    By default reads from JSON file. Use use_database(True) to switch to database.
    """
    if _use_database:
        return _load_from_database()
    return _load_registry()['anps']


def get_anp_ids() -> List[str]:
    """Get list of all ANP IDs."""
    return [anp['id'] for anp in get_all_anps()]


def get_anp_names() -> List[str]:
    """Get list of all ANP names."""
    return [anp['name'] for anp in get_all_anps()]


def get_anp_by_id(anp_id: str) -> Optional[Dict]:
    """Get a single ANP by its ID."""
    for anp in get_all_anps():
        if anp['id'] == anp_id:
            return anp
    return None


def get_anp_by_name(name: str) -> Optional[Dict]:
    """Get a single ANP by name (fuzzy matching)."""
    search_norm = normalize_anp_name(name)
    
    for anp in get_all_anps():
        if normalize_anp_name(anp['name']) == search_norm:
            return anp
    
    for anp in get_all_anps():
        anp_norm = normalize_anp_name(anp['name'])
        if search_norm in anp_norm or anp_norm in search_norm:
            return anp
    
    return None


def get_anps_by_category(category: str) -> List[Dict]:
    """Get all ANPs in a specific category (RB, PN, MN, APRN, APFF, Sant)."""
    # Normalize category name (handle both 'Sant' and 'SANT')
    cat_upper = category.upper()
    cat_map = {'SANT': 'Sant', 'RB': 'RB', 'PN': 'PN', 'MN': 'MN', 'APRN': 'APRN', 'APFF': 'APFF'}
    cat_normalized = cat_map.get(cat_upper, category)
    return [anp for anp in get_all_anps() if anp['category'] == cat_normalized]


def get_anps_by_state(state: str) -> List[Dict]:
    """Get all ANPs in a specific state."""
    state_lower = state.lower()
    return [
        anp for anp in get_all_anps() 
        if any(s.lower() == state_lower for s in anp.get('states', []))
    ]


def iter_anps() -> Iterator[Dict]:
    """Iterate through all ANPs."""
    yield from get_all_anps()


def get_categories() -> Dict[str, Dict]:
    """Get category metadata."""
    return _load_registry()['categories']


def get_registry_metadata() -> Dict:
    """Get metadata about the registry (version, source, etc.)."""
    return _load_registry()['_meta']


def get_anp_count() -> int:
    """Get total number of ANPs in the registry."""
    return len(get_all_anps())


def get_category_counts() -> Dict[str, int]:
    """Get count of ANPs per category."""
    counts: Dict[str, int] = {}
    for anp in get_all_anps():
        cat = anp['category']
        counts[cat] = counts.get(cat, 0) + 1
    return counts


CATEGORY_RB = 'RB'
CATEGORY_PN = 'PN'
CATEGORY_MN = 'MN'
CATEGORY_APRN = 'APRN'
CATEGORY_APFF = 'APFF'
CATEGORY_SANT = 'Sant'
ALL_CATEGORIES = [CATEGORY_RB, CATEGORY_PN, CATEGORY_MN, CATEGORY_APRN, CATEGORY_APFF, CATEGORY_SANT]


if __name__ == '__main__':
    print("ANP Registry Summary")
    print("=" * 50)

    print(f"Database available: {HAS_DATABASE}")
    print(f"Using database: {_use_database}")

    meta = get_registry_metadata()
    print(f"Version: {meta.get('version')}")
    print(f"Source: {meta.get('source')}")
    print(f"Total ANPs: {get_anp_count()}")

    print("\nBy Category:")
    for cat, count in sorted(get_category_counts().items()):
        cat_info = get_categories().get(cat, {})
        name = cat_info.get('name_es', cat)
        print(f"  {cat}: {count} ({name})")

    print("\nSample ANPs:")
    for anp in list(iter_anps())[:5]:
        print(f"  [{anp['category']}] {anp['name']}")

    # Show database ANP count if available
    if HAS_DATABASE:
        try:
            db_anps = get_all_anps_from_db()
            print(f"\nDatabase ANPs: {len(db_anps)}")
        except Exception as e:
            print(f"\nDatabase error: {e}")
