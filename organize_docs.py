
import os
import json
import re
from difflib import get_close_matches

with open('anp_index.json') as f:
    anp_index = json.load(f)

# Slug -> Name map
slug_to_name = {a['id']: a['name'] for a in anp_index['anps']}
# Name -> Slug map (normalized)
name_to_slug = {}
for a in anp_index['anps']:
    name_to_slug[a['name'].lower()] = a['id']

files = os.listdir('anp_docs')
renamed_count = 0

def normalize(s):
    return s.lower().replace('_', ' ').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')

for filename in files:
    if not filename.endswith('.pdf'):
        continue
    
    # If already a clean slug, skip
    # (Check if filename is "slug_decree.pdf")
    base_name = filename.replace('_decree.pdf', '')
    if base_name in slug_to_name:
        continue

    # Parse simec name
    # simec_ID_Name_decree.pdf or simec_ID_Name
    # Sometimes just Name (if I downloaded manually)
    
    # Check if it starts with simec_
    match = re.match(r'simec_\d+_(.*?)_?decree\.pdf', filename)
    if not match:
        match = re.match(r'simec_\d+_(.*?)$', filename) # No extension? (scrape script saved without ext sometimes if not caught?)
        if not match:
             # Try simec_ID_Name (no decree suffix)
             match = re.match(r'simec_\d+_(.*)', filename)
    
    if match:
        raw_name = match.group(1)
        # Clean up
        clean_name = raw_name.replace('_', ' ').replace('.pdf', '')
        
        # Try to find match in index
        # 1. Exact normalized match
        norm_clean = normalize(clean_name)
        
        # Try to find key in name_to_slug that matches
        best_slug = None
        
        # Exact match
        for name, slug in name_to_slug.items():
            if normalize(name) == norm_clean:
                best_slug = slug
                break
        
        # Close match
        if not best_slug:
            # Create list of normalized names
            candidates = list(name_to_slug.keys())
            # Map back to original name for fuzzy
            # Actually just match on normalized strings
            matches = get_close_matches(norm_clean, [normalize(n) for n in candidates], n=1, cutoff=0.6)
            if matches:
                # Find the slug for this match
                matched_norm = matches[0]
                for name, slug in name_to_slug.items():
                    if normalize(name) == matched_norm:
                        best_slug = slug
                        break
        
        if best_slug:
            new_filename = f"{best_slug}_decree.pdf"
            print(f"Renaming '{filename}' -> '{new_filename}'")
            try:
                os.rename(os.path.join('anp_docs', filename), os.path.join('anp_docs', new_filename))
                renamed_count += 1
            except Exception as e:
                print(f"Error renaming: {e}")
        else:
            print(f"No match for '{clean_name}'")

print(f"Renamed {renamed_count} files.")
