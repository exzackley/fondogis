
import requests
import json
import os
import time
import re
from concurrent.futures import ThreadPoolExecutor

# ANP Index to map names to IDs
with open('anp_index.json') as f:
    anp_index = json.load(f)

# Create a mapping of normalized name -> slug
name_to_slug = {}
for anp in anp_index['anps']:
    # Normalize: lower, remove special chars if needed, but simple matching first
    norm = anp['name'].lower().strip()
    name_to_slug[norm] = anp['id']

os.makedirs('anp_docs', exist_ok=True)

BASE_URL = "https://simec.conanp.gob.mx"

def normalize(s):
    return s.lower().strip().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')

def process_id(simec_id):
    try:
        # Get Ficha page to find name
        url = f"{BASE_URL}/ficha.php?anp={simec_id}"
        # We assume the name is in the title or h2
        # Actually, let's just try to download the decree directly first?
        # No, we need the name to rename it.
        
        # Requests
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
            
        content = r.text
        
        # Extract Name from H1
        match = re.search(r'<h1>(.*?)</h1>', content, re.DOTALL)
        if match:
            name = match.group(1).replace('\n', '').strip()
        else:
            # Fallback title
            match = re.search(r'<title>Ficha S I M E C \|\s*(.*?)\s*\|', content)
            name = match.group(1).strip() if match else f"Unknown_ID_{simec_id}"
            
        # Clean name
        name = name.strip()
        if name == "Comisión Nacional de Áreas Naturales Protegidas":
             # This happens if H1 isn't found and title fallback is generic.
             # Try another pattern for H1
             match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
             if match:
                 name = match.group(1).replace('\n', '').strip()
        
        # Skip if still generic
        if "Comisión Nacional" in name and len(name) > 40:
             # Likely failed
             pass

        # Try to match with existing index
        norm_name = normalize(name)
        slug = None
        
        # Fuzzy match or direct
        for existing_name, s in name_to_slug.items():
            if normalize(existing_name) == norm_name:
                slug = s
                break
        
        # If not found, check partial
        if not slug:
            for existing_name, s in name_to_slug.items():
                if norm_name in normalize(existing_name) or normalize(existing_name) in norm_name:
                    slug = s
                    break
        
        if not slug:
            # print(f"  [ID {simec_id}] Name '{name}' not in index. Skipping download or saving as new.")
            slug = f"simec_{simec_id}_{name.replace(' ', '_')}"
            # return None # Skip for now to save time/space, or download?
            
        # Download Decree
        decree_url = f"{BASE_URL}/pdf_decretos/{simec_id}_decreto.pdf"
        r_pdf = requests.head(decree_url, timeout=5)
        if r_pdf.status_code == 200:
            # Download
            pdf_path = f"anp_docs/{slug}_decree.pdf"
            if os.path.exists(pdf_path):
                return f"Exists: {slug}"
                
            r_down = requests.get(decree_url, timeout=30)
            if r_down.status_code == 200:
                with open(pdf_path, 'wb') as f:
                    f.write(r_down.content)
                return f"Downloaded: {slug}"
        
        return None

    except Exception as e:
        return f"Error {simec_id}: {e}"

print("Scanning SIMEC IDs 1..300...")
# Sequential loop to avoid blocking? Or parallel?
# Parallel is better.
with ThreadPoolExecutor(max_workers=10) as executor:
    results = executor.map(process_id, range(1, 260))

for res in results:
    if res:
        print(res)
