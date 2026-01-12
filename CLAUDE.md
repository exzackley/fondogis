# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Environmental data dashboard for analyzing Mexico's 232 federal protected areas (ANPs - Áreas Naturales Protegidas). Extracts and visualizes multi-source environmental data including:
- Google Earth Engine satellite imagery (population, forest, climate, land cover)
- NASA CMIP6 climate projections (multi-period forecasts)
- External APIs (GBIF biodiversity, iNaturalist citizen science, CONEVAL poverty indices)
- Government data (CONANP SIMEC, INEGI Census)

Built for FMCN (Fondo Mexicano para la Conservación de la Naturaleza).

## Quick Start

```bash
# Activate virtual environment
source venv/bin/activate  # or: . venv/bin/activate

# Install dependencies
pip install earthengine-api geemap pandas requests openpyxl

# GEE authentication (first time only)
python3 -c "import ee; ee.Authenticate()"

# Start local development server
python3 -m http.server 8000
# Then visit: http://localhost:8000/index.html
```

## Core Commands

### Data Extraction

```bash
# Add single ANP with all GEE data sources
python3 add_anp.py "Calakmul"           # Takes 2-3 minutes
python3 add_anp.py --list               # List available ANPs

# Additional data layers (run after add_anp.py)
python3 add_climate_projections.py "calakmul"  # NASA CMIP6 multi-period projections
python3 add_water_stress.py                     # WRI Aqueduct water stress
python3 add_gedi_biomass.py                     # NASA GEDI forest biomass
python3 add_mangrove_data.py                    # ESA WorldCover mangroves
python3 add_coneval_poverty.py                  # CONEVAL social lag index
python3 add_inaturalist_data.py                 # iNaturalist observations
python3 extract_external_data.py --all          # GBIF, SIMEC, INEGI

# Climate data (3 separate systems - see Climate Data Architecture)
python3 add_climate_projections.py "sierra_gorda"   # GEE multi-period projections
python3 scrape_climate_ssr.py "sierra_gorda"        # SSR API 19 indicators
python3 extract_climate_timeseries.py "sierra_gorda" # Heatmap grid timeseries
python3 compare_climate_sources.py                   # Validate SSR vs GEE

# Batch processing
python3 batch_add_anps.py               # All ANPs (slow - use tmux)
python3 batch_climate_extraction.py     # Climate data for all ANPs

# Test mode (processes first 3 ANPs only)
python3 <script>.py --test
```

### Development Server

```bash
# Static file server for HTML dashboards
python3 -m http.server 8000

# Main dashboard:  http://localhost:8000/index.html
# Admin panel:     http://localhost:8000/admin.html
# Climate heatmap: http://localhost:8000/climate_heatmap.html
```

## Architecture

### Central ANP Registry (`anp_registry.py`)

**IMPORTANT**: All scripts must import from `anp_registry.py` instead of maintaining hardcoded ANP lists.

```python
from anp_registry import (
    get_all_anps,           # Returns list of all 232 ANPs
    get_anp_by_id,          # Get by normalized ID: "calakmul"
    get_anp_by_name,        # Fuzzy search: "Sian Ka'an"
    get_anps_by_category,   # Get by category: "RB", "PN", etc.
    name_to_id              # Convert name to file-safe ID
)
```

Categories: `RB` (48), `PN` (79), `APFF` (57), `Sant` (28), `APRN` (15), `MN` (5)

### Data Flow

1. **Extraction**: Scripts write to `anp_data/{anp_id}_data.json`
2. **Dashboard**: HTML files fetch JSON via JavaScript
3. **Registry**: `reference_data/official_anp_list.json` is the authoritative source

### GEE Authentication (`gee_auth.py`)

Handles multiple auth methods automatically:
1. Service account from `service_account.json` (best for server/headless)
2. Existing persistent credentials from `ee.Authenticate()`
3. Application Default Credentials from gcloud

```python
from gee_auth import init_ee
init_ee()  # Handles all auth methods automatically
```

**GEE Project ID**: `gen-lang-client-0866285082` (project name: "fondo")

### Climate Data Architecture

Three separate climate data systems with different purposes and data sources:

1. **Multi-period projections** (`add_climate_projections.py`)
   - Stores in: `datasets.climate_projections.scenarios.ssp245["2041-2070"]`
   - Periods: 2011-2040, 2041-2070, 2071-2100 vs baseline 1981-2010
   - Scenarios: SSP2-4.5, SSP5-8.5
   - Source: NASA NEX-GDDP-CMIP6 via GEE
   - Model: CMIP6 (newest generation)

2. **SSR Climate Portal data** (`scrape_climate_ssr.py`)
   - Stores in: `{anp}_climate_ssr.json` (separate file)
   - Source: climateinformation.org REST API (CORDEX bias-adjusted)
   - **Important**: Uses REST API endpoint `https://ssr.climateinformation.org/ssr/server/chart`
   - Provides: **19 climate indicators** (temp, precipitation, tropical nights, frost days, aridity, soil moisture, water discharge, runoff, etc.)
   - Scenarios: RCP 4.5, RCP 8.5 (older CMIP5 generation)
   - Periods: Same 3 future periods as GEE data
   - Note: RCP scenarios roughly map to SSP (RCP 4.5 ≈ SSP2-4.5, RCP 8.5 ≈ SSP5-8.5)

3. **Heatmap timeseries** (`extract_climate_timeseries.py`)
   - Stores in: `{anp}_climate_timeseries.json` (separate file)
   - Yearly grid points (0.05° resolution) for 1980-2095, every 5 years
   - Scenarios: Both SSP2-4.5 AND SSP5-8.5
   - Used for: Animated heatmap visualizations in dashboard
   - Source: Same NASA CMIP6 as #1, different extraction method

**Test ANPs for climate data validation** (6 ANPs with complete climate coverage):
- Alto Golfo de California y Delta del Río Colorado
- Arrecife Alacranes
- Arrecife de Puerto Morelos
- Calakmul
- Sierra Gorda
- Sierra Gorda de Guanajuato

**Scenario Comparison**: Use `compare_climate_sources.py` to validate SSR (RCP) vs GEE (SSP) projections. Expected differences: <0.5°C for matching scenarios.

### JSON Data Structure

```json
{
  "metadata": {
    "name": "Calakmul",
    "designation": "Reserva de la Biósfera",
    "reported_area_km2": 723185.12,
    "wdpa_id": 555521000
  },
  "geometry": {
    "centroid": [-89.8123, 18.3456],
    "bounds": [[...], [...]]
  },
  "datasets": {
    "population": {...},
    "land_cover": {...},
    "forest": {...},
    "climate_projections": {
      "scenarios": {
        "ssp245": {
          "2011-2040": {...},
          "2041-2070": {...}
        }
      }
    }
  },
  "external_data": {
    "gbif_species": {...},
    "inaturalist": {...}
  }
}
```

## Important Notes

### GEE Extraction Timeouts

**CRITICAL**: GEE extraction is slow (2-5 min per ANP). Always run long extractions in a tmux session to avoid SSH/shell timeouts:

```bash
# Start tmux session
tmux new -s climate

# Run extraction
python3 add_climate_projections.py "calakmul"

# Detach: Ctrl+a d
# Reattach: tmux attach -t climate
```

Do NOT run GEE batch operations via automated tool calls - they will timeout.

### File Locations

- `anp_data/` - Generated JSON files (DO NOT hand-edit, regenerate instead)
- `reference_data/` - Static reference files (census, SIMEC, official ANP list)
- `reference_data/fondo/` - Private FONDO internal data (gitignored)
- `service_account.json` - GEE service account key (gitignored)

### ANP Name Normalization

Names contain Spanish characters with accents. Use `anp_registry.normalize_anp_name()` for matching:
- Removes accents: "Sian Ka'an" → "sian kaan"
- Strips prefixes: "RB Calakmul" → "calakmul"
- Handles articles: "de la", "del", "y"

### Coordinate System

All coordinates are WGS84 (EPSG:4326). GEE geometries use `[lon, lat]` order.

## Code Patterns

### Script Template

```python
#!/usr/bin/env python3
import ee
import json
import os
from datetime import datetime

from gee_auth import init_ee
from anp_registry import get_all_anps, get_anp_by_name

DATA_DIR = 'anp_data'

def extract_data(anp_feature):
    """Extract data for a single ANP."""
    try:
        geom = anp_feature.geometry()
        result = {"data_available": True, "extracted_at": datetime.now().isoformat()}
        # ... extraction logic ...
        return result
    except Exception as e:
        return {"data_available": False, "error": str(e)}

def main():
    init_ee()
    for anp in get_all_anps():
        # ... process each ANP ...

if __name__ == '__main__':
    main()
```

### Error Handling

Return `None` or error dicts instead of raising exceptions:

```python
try:
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        return response.json()
    return {"error": f"HTTP {response.status_code}"}
except Exception as e:
    return {"error": str(e)}
```

### Rate Limiting

Always respect API rate limits:

```python
import time

INAT_DELAY = 1.1   # iNaturalist: max 1 req/sec
GBIF_DELAY = 0.5   # GBIF: max 2 req/sec

# After each API call:
time.sleep(INAT_DELAY)
```

## Testing & Verification

No formal test suite. Verify changes by:

1. Run with test flag: `python3 <script>.py --test`
2. Check generated JSON: `cat anp_data/calakmul_data.json | python3 -m json.tool`
3. Load dashboard: `http://localhost:8000/index.html`
4. Check browser console (F12) for JavaScript errors

## Common Issues

### "Please authorize Earth Engine"

```bash
# Interactive auth (creates persistent credentials)
python3 -c "import ee; ee.Authenticate()"

# Or use service account (better for servers)
# Place service_account.json in project root
```

### Charts Not Rendering in Dashboard

Check browser console for errors. Common cause: `undefined.toFixed()` on missing data.
Always use: `value != null` before calling `.toFixed()`.

### Missing Data for ANP

Some data sources don't apply to all ANPs:
- Mangroves: coastal ANPs only
- Census: terrestrial ANPs with nearby settlements only
- Water stress: depends on WRI Aqueduct basin coverage

Check `anp_expectations.json` for expected data availability.

## Dashboard Development

Frontend stack:
- Vanilla JavaScript (no framework)
- Leaflet.js for maps
- Chart.js for visualizations
- Inline `<script>` tags in HTML

JavaScript patterns:
- Use `async/await` with `Promise.all()` for parallel fetches
- Check for null: `if (data != null)` not `if (data !== null)`
- CamelCase for variables: `climateData`, `anpBoundary`

## Adding New Data Sources

1. Create `add_<source>.py` following existing patterns
2. Update `data_sources.json` with source metadata
3. Test with `--test` flag before full run
4. Update this file's command list

## Private FONDO Data Import

When FONDO shares internal data (Excel/CSV):

1. Analyze file structure and map ANP names
2. Fuzzy match against existing ANPs in `anp_data/`
3. Propose data schema: `private_data.fondo_<dataset>`
4. Create import script: `add_fondo_<dataset>.py`
5. Store source files in: `reference_data/fondo/` (gitignored)

See AGENTS.md §"Private Data Import Workflow" for detailed steps.
