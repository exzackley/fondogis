#!/usr/bin/env python3
"""
Identify Coastal/Marine ANPs for Report Generation
==================================================

Fuzzy matches a list of ANP names against the official registry
and creates a tagged subset for targeted report generation.

Usage:
    python3 identify_coastal_anps.py
"""

import json
import os
from anp_registry import get_all_anps, get_anp_by_name, normalize_anp_name, name_to_id

# List of coastal/marine ANPs provided by user
COASTAL_ANPS_RAW = [
    "Alto Golfo de California y Delta del Río Colorado",
    "Bajos de Coyula",
    "Bajos de Coyula II",
    "Barra de la Cruz–Playa Grande",
    "Chamela–Cuixmala",
    "El Vizcaíno",
    "Hermenegildo Galeana",
    "Huatulco",
    "Huatulco II",
    "La Encrucijada",
    "La porción norte y la franja costera oriental, terrestres y marinas de la Isla de Cozumel",
    "Laguna de Términos",
    "Laguna Madre y Delta del Río Bravo",
    "Lagunas de Chacahua",
    "Los Petenes",
    "Los Tuxtlas",
    "Manglares de Nichupté",
    "Marismas Nacionales Nayarit",
    "Meseta de Cacaxtla",
    "Playa Cahuítan",
    "Playa Chacahua",
    "Playa Colola",
    "Playa Cuixmala",  # Likely typo for "Playa Cuitzmala"
    "Playa El Tecuán",
    "Playa Escobilla",
    "Playa Huizache Caimanero",
    "Playa Maruata",
    "Playa Mexiquillo",
    "Playa Mismaloya",
    "Playa Morro Ayuta",
    "Playa Piedra de Tlacoyunque",
    "Playa Puerto Arista",
    "Playa Leopa",  # Possible typo - maybe "Playa Ceuta"?
    "Playa Tierra Colorada",
    "Ría Lagartos",
    "Ricardo Flores Magón",
    "Sian Ka'an",
    "Tangolunda",
    "Valle de los Cirios"
]

# Manual corrections for known spelling variations
MANUAL_CORRECTIONS = {
    "Playa Cuixmala": "Playa Cuitzmala",
    "Playa Leopa": "Playa Teopa",  # Typo: L → T
}

# Map registry IDs to actual data file names (for cases where they differ)
DATA_FILE_OVERRIDES = {
    "sian_ka_an": "sian_kaan",  # Registry has underscore, file doesn't
}

OUTPUT_FILE = 'coastal_anps_subset.json'


def fuzzy_match_anp(search_name):
    """Try to match an ANP name using registry's fuzzy matching."""
    # Check manual corrections first
    corrected_name = MANUAL_CORRECTIONS.get(search_name)
    if corrected_name:
        match = get_anp_by_name(corrected_name)
        if match:
            return match, "manual_correction"

    # First try exact match using registry function
    match = get_anp_by_name(search_name)
    if match:
        return match, "exact"

    # Try with common variations
    variations = [
        search_name,
        search_name.replace("–", "-"),  # Different dashes
        search_name.replace("—", "-"),
        search_name.replace("  ", " "),  # Double spaces
    ]

    for variant in variations:
        match = get_anp_by_name(variant)
        if match:
            return match, "variant"

    # Try manual matching for known problematic cases
    search_norm = normalize_anp_name(search_name)

    for anp in get_all_anps():
        anp_norm = normalize_anp_name(anp['name'])
        # Check if normalized names are very similar
        if search_norm in anp_norm or anp_norm in search_norm:
            return anp, "fuzzy"

    return None, None


def main():
    print("=" * 70)
    print("COASTAL/MARINE ANPS IDENTIFICATION")
    print("=" * 70)
    print(f"\nTotal ANPs to match: {len(COASTAL_ANPS_RAW)}")

    matched = []
    unmatched = []

    print("\nMatching ANPs...")
    print("-" * 70)

    for search_name in COASTAL_ANPS_RAW:
        anp, match_type = fuzzy_match_anp(search_name)

        if anp:
            matched.append({
                "search_name": search_name,
                "matched_name": anp['name'],
                "id": anp['id'],
                "category": anp['category'],
                "match_type": match_type
            })
            status = f"✓ [{match_type}]"
            print(f"{status:<15} {search_name}")
            if search_name != anp['name']:
                print(f"                → {anp['name']}")
        else:
            unmatched.append(search_name)
            print(f"✗ [NO MATCH]    {search_name}")

    print("\n" + "=" * 70)
    print(f"RESULTS: {len(matched)} matched, {len(unmatched)} unmatched")
    print("=" * 70)

    # Category breakdown
    if matched:
        print("\nMatched ANPs by Category:")
        categories = {}
        for m in matched:
            cat = m['category']
            categories[cat] = categories.get(cat, 0) + 1
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}")

    # Show unmatched
    if unmatched:
        print(f"\n⚠️  UNMATCHED ANPs ({len(unmatched)}):")
        for name in unmatched:
            print(f"    - {name}")
        print("\nThese may need manual review or may not exist in the registry.")

    # Check which matched ANPs have data files
    print("\nChecking for existing data files...")
    has_data = []
    missing_data = []

    for m in matched:
        # Check for data file override
        file_id = DATA_FILE_OVERRIDES.get(m['id'], m['id'])
        data_file = f"anp_data/{file_id}_data.json"

        if os.path.exists(data_file):
            has_data.append(m['id'])
            m['data_file'] = f"{file_id}_data.json"  # Store actual filename
            m['has_data'] = True
        else:
            missing_data.append(m['id'])
            m['data_file'] = None
            m['has_data'] = False

    print(f"  {len(has_data)} ANPs have data files")
    if missing_data:
        print(f"  ⚠️  {len(missing_data)} ANPs missing data files:")
        for anp_id in missing_data[:5]:
            print(f"      - {anp_id}")
        if len(missing_data) > 5:
            print(f"      ... and {len(missing_data) - 5} more")

    # Create output file (after data file check so it includes data_file field)
    output = {
        "_meta": {
            "description": "Subset of coastal/marine ANPs for targeted report generation",
            "total_anps": len(matched),
            "anps_with_data": len(has_data),
            "anps_missing_data": len(missing_data),
            "unmatched_count": len(unmatched),
            "created_at": __import__('datetime').datetime.now().isoformat()
        },
        "matched_anps": matched,
        "unmatched_names": unmatched,
        "anp_ids": [m['id'] for m in matched],
        "anp_names": [m['matched_name'] for m in matched],
        "anp_ids_with_data": has_data,
        "anp_ids_missing_data": missing_data
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved to: {OUTPUT_FILE}")
    print(f"\nUse these IDs in other scripts:")
    print(f"  anp_ids = {output['anp_ids'][:3]} + ... ({len(matched)} total)")


if __name__ == '__main__':
    main()
