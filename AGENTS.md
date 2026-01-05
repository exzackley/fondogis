# AGENTS.md - Coding Agent Guidelines for fondogis

## Project Overview

Environmental data dashboard for FMCN analyzing Mexico's 232 federal protected areas (ANPs). Extracts data from Google Earth Engine, GBIF, CONANP SIMEC, INEGI Census, CONEVAL, and iNaturalist.

### ANP Categories (232 total)
| Category | Count | Full Name |
|----------|-------|-----------|
| PN | 79 | Parque Nacional |
| RB | 48 | Reserva de la Biósfera |
| APFF | 57 | Área de Protección de Flora y Fauna |
| Sant | 28 | Santuario |
| APRN | 15 | Área de Protección de Recursos Naturales |
| MN | 5 | Monumento Natural |

### ANP Registry (`anp_registry.py`)
Central source of truth for all ANP names and IDs. All scripts should import from here:

```python
from anp_registry import get_all_anps, get_anp_by_name, get_anps_by_category
```

## Quick Start

```bash
# Start local server
python3 -m http.server 8000
# Dashboard: http://localhost:8000/index.html
# Admin: http://localhost:8000/admin.html

# GEE authentication (if needed)
python3 -c "import ee; ee.Authenticate()"
```

## Build/Run Commands

```bash
# GEE data extraction
python3 add_anp.py "Calakmul"           # Single ANP
python3 add_anp.py --list               # List available ANPs
python3 batch_add_anps.py               # All ANPs

# Additional data sources
python3 add_water_stress.py             # WRI Aqueduct water stress
python3 add_climate_projections.py      # NASA CMIP6 climate projections (2041-2070)
python3 add_gedi_biomass.py             # NASA GEDI forest biomass
python3 add_mangrove_data.py            # ESA WorldCover mangroves
python3 add_coneval_poverty.py          # CONEVAL social lag index
python3 add_inaturalist_data.py         # iNaturalist citizen science
python3 extract_external_data.py --all  # GBIF, SIMEC, INEGI

# Test single ANP (all scripts support this pattern)
python3 <script>.py "calakmul"          # By name
python3 <script>.py --test              # First 3 ANPs only
```

## No Formal Test Suite

Verify changes by:
1. Running the affected script with `--test` flag
2. Checking generated JSON in `anp_data/`
3. Loading dashboard and inspecting browser console (F12)

## Dependencies

```bash
pip install earthengine-api pandas requests openpyxl
```

## File Structure

```
fondogis/
├── anp_registry.py             # Central ANP list (import from here, not hardcoded lists)
├── add_anp.py                  # Core GEE extraction (population, elevation, land cover, etc.)
├── add_water_stress.py         # WRI Aqueduct V4
├── add_climate_projections.py  # NASA CMIP6 climate projections
├── add_gedi_biomass.py         # NASA GEDI L4A biomass
├── add_mangrove_data.py        # ESA WorldCover mangroves (coastal ANPs)
├── add_coneval_poverty.py      # CONEVAL municipal poverty index
├── add_inaturalist_data.py     # iNaturalist API
├── extract_external_data.py    # GBIF, SIMEC NOM-059, INEGI Census
├── gee_auth.py                 # GEE authentication helper
├── index.html                  # Main visualization dashboard
├── admin.html                  # Data admin panel
├── anp_data/                   # Generated JSON per ANP (DO NOT HAND-EDIT)
├── reference_data/             # Downloaded Excel/CSV reference files
│   └── official_anp_list.json  # Authoritative 234 ANP list (used by anp_registry.py)
├── data_sources.json           # Data source documentation (21 sources)
└── service_account.json        # GEE service account key (gitignored)
```

## Code Style Guidelines

### Python Imports
```python
# Standard library first, then third-party, then local
import json
import os
from datetime import datetime

import ee
import pandas as pd
import requests

from gee_auth import init_ee
```

### Constants
```python
DATA_DIR = 'anp_data'
REFERENCE_DIR = 'reference_data'
API_DELAY = 1.0  # Rate limiting
```

### Optional Dependencies
```python
try:
    import pandas as pd  # type: ignore
    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore
    HAS_PANDAS = False
```

### Functions
- Use `snake_case` for functions and variables
- Docstrings for public functions (brief, one-line preferred)
- Return `None` on API/file errors, not exceptions

### Error Handling
```python
try:
    response = requests.get(url, timeout=30)  # type: ignore
    if response.status_code == 200:
        return response.json()
    return None
except Exception:
    return None
```

### JavaScript (in HTML)
- Inline `<script>` at end of body
- `camelCase` for variables/functions
- `async/await` with `Promise.all` for parallel fetches
- Check for `null`/`undefined` with `!= null` (not `!== null`)

## Key Patterns

### ANP Data File Structure
```json
{
  "metadata": { "name": "...", "designation": "...", "reported_area_km2": ... },
  "geometry": { "centroid": [lon, lat], "bounds": [[lon,lat], ...] },
  "datasets": { "population": {...}, "land_cover": {...}, "forest": {...} },
  "external_data": { "gbif_species": {...}, "inaturalist": {...} }
}
```

### GEE Script Pattern
```python
def extract_something(geometry):
    """Extract data for a geometry."""
    try:
        geom = ee.Geometry.Polygon(geometry)
        # ... GEE operations ...
        return {"data_available": True, "value": result, "extracted_at": datetime.now().isoformat()}
    except Exception as e:
        return {"data_available": False, "error": str(e)}
```

### Rate Limiting
```python
INAT_DELAY = 1.1  # iNaturalist: 1 req/sec
GBIF_DELAY = 0.5  # GBIF: 2 req/sec
time.sleep(DELAY)
```

### ANP Name Normalization
```python
def normalize_anp_name(name):
    name = name.lower().strip()
    name = re.sub(r'^(rb|pn|apff|aprn|sant|mn|santuario)\s+', '', name)
    # Remove accents, articles, punctuation...
```

## Important Notes

1. **GEE Project ID**: `gen-lang-client-0866285082` (project name: fondo)
2. **Coordinates**: All WGS84 (EPSG:4326)
3. **Spanish Content**: ANP names and SIMEC data contain Spanish with accents
4. **Generated Files**: Never hand-edit files in `anp_data/` - regenerate instead
5. **Service Account**: Place `service_account.json` in project root for headless GEE auth

## Adding New Data Sources

1. Create `add_<source>.py` following existing script patterns
2. Add source documentation to `data_sources.json`
3. Update this file's command list
4. Test with `--test` flag before running on all ANPs

## Climate Data Architecture

Three separate climate data sources with different granularities:

### 1. GEE Climate Projections (`add_climate_projections.py`)
- **Source**: NASA NEX-GDDP-CMIP6 via Google Earth Engine
- **Granularity**: Multi-period averages (baseline 1981-2010 vs 3 future periods)
- **Future Periods**: 2011-2040, 2041-2070, 2071-2100
- **Output**: `datasets.climate_projections` in `{anp}_data.json`
- **Contains**: Temperature, precipitation, tropical nights, drought indicators
- **Data Structure**: `scenarios.ssp245["2041-2070"].temperature` (nested by period)
- **Coverage**: 6 ANPs as of Jan 2024

### 2. Climate Portal / SSR Data (`scrape_climate_ssr.py`)
- **Source**: climateinformation.org (SMHI/GCF/WMO) - CORDEX bias-adjusted
- **Granularity**: Multi-period (2011-2040, 2041-2070, 2071-2100)
- **Output**: SEPARATE FILE `{anp}_climate_ssr.json`
- **Contains**: Temp, precip, soil moisture, aridity, water discharge/runoff, tropical nights
- **Note**: Requires Playwright browser automation
- **Coverage**: 6 ANPs

### 3. Heatmap Timeseries (`extract_climate_timeseries.py`)
- **Source**: NASA CMIP6 via GEE (same as #1, different extraction)
- **Granularity**: Yearly data (every 5 years 1980-2095) for spatial grid
- **Output**: SEPARATE FILE `{anp}_climate_timeseries.json`
- **Contains**: Temperature values for ~180 grid points at 0.05° resolution
- **Used by**: Animated heatmap visualization in dashboard
- **Coverage**: 6 ANPs

### ANPs with Full Climate Data (as of Jan 2024)
These 6 ANPs have all three climate data types:
1. Alto Golfo de California y Delta del Río Colorado
2. Arrecife Alacranes
3. Arrecife de Puerto Morelos
4. Calakmul
5. Sierra Gorda
6. Sierra Gorda de Guanajuato

### Climate Scripts Summary
```bash
python3 add_climate_projections.py "sierra_gorda"    # GEE multi-period projections
python3 extract_climate_timeseries.py "sierra_gorda" # Heatmap grid data
python3 scrape_climate_ssr.py "sierra_gorda"         # CORDEX SSR data (requires Playwright)
```

## Batch Climate Data Extraction

To extract/update climate data for the 6 priority ANPs, run these commands in tmux on a server with good connectivity.

**IMPORTANT**: GEE extraction is slow (3-5 min per ANP). Always use an interactive tmux session to avoid timeouts. Do NOT run these via automated agent tool calls - they will time out.

### Step 0: Ensure service account is in place
The file `service_account.json` must be in the project root for headless GEE auth. This file is gitignored - copy it manually to the server if needed.

### Step 1: Start tmux session
```bash
tmux new -s climate
cd /path/to/fondogis
```

### Step 2: Extract GEE Climate Projections (multi-period)
```bash
# IMPORTANT: Run these commands manually in tmux, NOT via automated tools!
# Each takes 3-5 minutes. Run sequentially to avoid GEE rate limits.
python3 add_climate_projections.py "alto_golfo_de_california_y_delta_del_rio_colorado"
python3 add_climate_projections.py "arrecife_alacranes"
python3 add_climate_projections.py "arrecife_de_puerto_morelos"
python3 add_climate_projections.py "calakmul"
python3 add_climate_projections.py "sierra_gorda"
python3 add_climate_projections.py "sierra_gorda_de_guanajuato"
```

### Step 3: Verify multi-period structure
```bash
# Should show "multi" for all 6 ANPs
for f in anp_data/*_data.json; do
  name=$(basename "$f" _data.json)
  has_periods=$(python3 -c "import json; d=json.load(open('$f')); cp=d.get('datasets',{}).get('climate_projections',{}).get('scenarios',{}).get('ssp245',{}); print('multi' if '2041-2070' in cp else 'flat' if 'temperature' in cp else 'none')" 2>/dev/null)
  if [ "$has_periods" != "none" ]; then
    echo "$name: $has_periods"
  fi
done
```

### Step 4: Commit and push
```bash
git add anp_data/
git commit -m "Update climate projections with multi-period data for 6 priority ANPs"
git push
```

### Expected Data Structure After Extraction
```json
{
  "datasets": {
    "climate_projections": {
      "scenarios": {
        "ssp245": {
          "2011-2040": { "temperature": {...}, "precipitation": {...}, ... },
          "2041-2070": { "temperature": {...}, "precipitation": {...}, ... },
          "2071-2100": { "temperature": {...}, "precipitation": {...}, ... }
        },
        "ssp585": { ... }
      }
    }
  }
}
```

### Troubleshooting
- **GEE timeout**: Check internet connectivity. Re-authenticate with `python3 -c "import ee; ee.Authenticate()"`
- **Rate limits**: Wait 1-2 minutes between ANPs if you hit GEE quotas
- **Partial data**: Re-run the script for that ANP; it will overwrite existing data

## Common Issues

### Charts Not Rendering
Check browser console for JS errors. Common cause: `undefined.toFixed()` - use `!= null` checks.

### GEE Auth Fails
```bash
# Re-authenticate
python3 -c "import ee; ee.Authenticate()"
# Or use service account (see gee_auth.py)
```

### Missing Data for ANP
Some data sources don't apply to all ANPs (e.g., mangroves only for coastal, census only for terrestrial). Check `anp_expectations.json` for expected coverage.

## Private Data Import Workflow (FONDO Internal Data)

When FONDO shares an Excel/CSV file for import into the system, follow this workflow:

### Step 1: Receive and Analyze the File
- User shares file (upload, paste, or Dropbox link)
- Read the file structure (columns, rows, data types)
- Identify which column maps to ANP names
- List all unique ANPs in the file

### Step 2: Match ANPs to Existing Data
- Use fuzzy matching against existing ANP names in `anp_data/`
- Report: "Matched X of Y ANPs"
- List any unmatched names and propose corrections
- Handle common variations (with/without accents, abbreviations)

### Step 3: Propose Data Schema
- Show the user proposed field names and structure
- Confirm data types (currency, dates, percentages)
- Ask about any ambiguous columns
- Propose where data will live: `private_data.[dataset_name]`

### Step 4: Generate Import Script
- Create or update `add_fondo_[dataset].py` script
- Script reads from `reference_data/fondo/[filename]`
- Script adds data to `private_data` section of each ANP JSON
- Follow existing script patterns (see `add_coneval_poverty.py`)

### Step 5: Execute and Verify
- Run the script with `--test` flag first
- Report summary: "Updated 45 ANPs with budget data"
- Show sample output for user verification
- Run full import after approval

### Private Data Location

```
reference_data/fondo/          # Source Excel/CSV files from FONDO
anp_data/[anp]_data.json       # Output location
  └── private_data             # New section for FONDO internal data
      └── fondo_budget         # Example: budget/funding data
      └── fondo_surveys        # Example: internal survey data
```

### Private Data JSON Structure

```json
{
  "private_data": {
    "fondo_budget": {
      "_meta": {
        "source_file": "budget_2026.xlsx",
        "imported_at": "2026-01-03T12:00:00",
        "imported_by": "claude"
      },
      "fiscal_year": 2026,
      "total_budget_mxn": 4500000,
      "funded_amount_mxn": 3200000,
      "funding_gap_mxn": 1300000,
      "funding_sources": [
        {"name": "GEF", "amount_mxn": 2000000},
        {"name": "CONANP", "amount_mxn": 1200000}
      ]
    }
  }
}
```

### Notes
- Private data is NOT committed to public repositories
- Add `reference_data/fondo/` to `.gitignore` for sensitive files
- Dashboard can optionally display private data with a `?private=true` URL parameter

## Report Generation Standards

When generating formal reports (PDFs, HTML Appendices, Word docs), adhere to the following standards:

1. **Citations & Footnotes**: 
   - All data points (population, carbon, biodiversity counts, etc.) MUST be cited.
   - Use superscript footnotes in the text (e.g., `Population: 45,000 [1]`).
   - Include a "References" section at the end of the document.
   - Link footnotes to the reference list.

2. **Data Sources**:
   - Cite specific datasets (e.g., "INEGI Censo 2020", "NASA GEDI L4A").
   - Acknowledge GEE and CONANP SIMEC where applicable.

3. **Formatting**:
   - Use professional, formal styling (Times New Roman/Arial, justified text).
   - Maps should be static and high-contrast for printing.
   - Avoid interactive elements in "printable" versions.
