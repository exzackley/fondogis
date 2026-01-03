
import os
import json

# Load index
with open('anp_index.json') as f:
    anp_index = json.load(f)

# Slug list
slugs = {a['id'] for a in anp_index['anps']}

decree_map = {}
files = os.listdir('anp_docs')

for filename in files:
    if not filename.endswith('.pdf'):
        continue
    
    # Check if filename corresponds to a slug
    slug_candidate = filename.replace('_decree.pdf', '')
    
    if slug_candidate in slugs:
        decree_map[slug_candidate] = f"anp_docs/{filename}"
    
    # Also check simec files if I can map them later
    # For now, only mapped ones

print(f"Mapped {len(decree_map)} decrees.")

# Save to JS file or JSON
with open('anp_decrees.json', 'w') as f:
    json.dump(decree_map, f, indent=2)
