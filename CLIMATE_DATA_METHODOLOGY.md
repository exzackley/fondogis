# Climate Data Collection Methodology

## Overview

This document describes our approach to collecting climate projection data for Mexico's protected areas (ANPs). We use **three methods** plus a **validation comparison**.

---

## Test ANPs (Phase 1)

Run all methods on these 6 ANPs first before scaling to all 232.

| ANP Name | Lat | Lon | Type |
|----------|-----|-----|------|
| Alto Golfo de California y Delta del Rio Colorado | 31.5215 | -114.5014 | Marine/Desert |
| Arrecife Alacranes | 22.4798 | -89.6993 | Marine/Reef |
| Arrecife de Puerto Morelos | 20.9049 | -86.8318 | Marine/Reef |
| Calakmul | 18.3642 | -89.6515 | Tropical Forest |
| Sierra Gorda | 21.2888 | -99.4784 | Mountain |
| Sierra Gorda de Guanajuato | 21.4077 | -100.1091 | Mountain |

**Centroids are already in** `anp_data/{anp_name}_data.json` under `geometry.centroid` as `[longitude, latitude]`.

---

## Method 1: climateinformation.org REST API

### What It Provides
- **19 climate/hydrology indicators** (temperature, precipitation, aridity, soil moisture, water discharge, runoff, etc.)
- **2 scenarios**: RCP 4.5, RCP 8.5
- **3 future periods**: 2011-2040, 2041-2070, 2071-2100
- **Baseline**: 1981-2010

### Key Discovery
The Site-Specific Report has a **REST API** - no scraping needed!

### API Endpoint
```
https://ssr.climateinformation.org/ssr/server/chart
```

### API Parameters
| Parameter | Description | Example |
|-----------|-------------|---------|
| `file` | NetCDF filename | `tasAdjust-tmean_abs_CAM-44_ens_rcp85_ens_2071-2100_1981-2010_grid0.5_ensmed.nc` |
| `variable` | Variable name | `tasAdjust-tmean` |
| `lat` | Latitude | `21.29` |
| `lon` | Longitude | `-99.48` |
| `dataset` | Dataset path | `/cii-prod_v4.5.1/CAM-44` or `/wii-prod_v3.2.1/CAM-44` |

### Response Format
```json
[3.7693996]
```

### Complete Indicator List

**Climate indicators** (dataset: `/cii-prod_v4.5.1/CAM-44`, grid: `grid0.5`):

| Indicator | Variable | Type | Unit |
|-----------|----------|------|------|
| Temperature (annual mean) | `tasAdjust-tmean` | `abs` | °C change |
| Max temperature | `tasmaxAdjust-tmean` | `abs` | °C change |
| Min temperature | `tasminAdjust-tmean` | `abs` | °C change |
| Precipitation | `prAdjust-tmean` | `rel` | % change |
| Frost days | `fdAdjust-tmean` | `abs` | days change |
| Tropical nights | `tnAdjust-tmean` | `abs` | days change |
| Heating degree days | `hddAdjust-tmean` | `abs` | degree-days |
| Longest dry spell | `cddAdjust-tmean` | `rel` | % change |
| Number of dry spells | `ncddAdjust-tmean` | `rel` | % change |

**Hydrology indicators** (dataset: `/wii-prod_v3.2.1/CAM-44`, grid: `catch`):

| Indicator | Variable | Type | Unit |
|-----------|----------|------|------|
| Aridity actual | `aridact-tmean` | `rel` | % change |
| Aridity potential | `aridpot-tmean` | `rel` | % change |
| Soil moisture | `smoist-tmean` | `rel` | % change |
| Soil moisture (days below min) | `smoistnodbm-tmean` | `rel` | % change |
| Soil moisture (annual min) | `smoistyearmin-tmean` | `rel` | % change |
| Water discharge | `wdis-tmean` | `rel` | % change |
| Water discharge (max) | `wdisyearmax-tmean` | `rel` | % change |
| Water discharge (min) | `wdisyearmin-tmean` | `rel` | % change |
| Water discharge (days below min) | `wdisnodbm-tmean` | `rel` | % change |
| Water runoff | `wrun-tmean` | `rel` | % change |

### URL Construction

**Climate indicators:**
```
{variable}_{type}_CAM-44_ens_{scenario}_ens_{period}_{baseline}_grid0.5_ensmed.nc
```

**Hydrology indicators:**
```
{variable}_{type}_CAM-44_ens_{scenario}_ens_{period}_{baseline}_catch_ensmed.nc
```

### Scenarios & Periods
- **Scenarios**: `rcp45`, `rcp85`
- **Periods**: `2011-2040`, `2041-2070`, `2071-2100`
- **Baseline**: `1981-2010`

### Example API Call
```bash
curl "https://ssr.climateinformation.org/ssr/server/chart?file=tasAdjust-tmean_abs_CAM-44_ens_rcp85_ens_2071-2100_1981-2010_grid0.5_ensmed.nc&variable=tasAdjust-tmean&lat=21.29&lon=-99.48&dataset=/cii-prod_v4.5.1/CAM-44"

# Returns: [3.7693996]  (meaning +3.77°C)
```

### Script to Create: `scrape_climate_ssr.py`

```python
#!/usr/bin/env python3
"""
Fetch climate indicators from climateinformation.org REST API.
No browser scraping needed - direct API calls.
"""
import requests
import json
import time
import os
from datetime import datetime

SSR_API = "https://ssr.climateinformation.org/ssr/server/chart"
CLIMATE_DATASET = "/cii-prod_v4.5.1/CAM-44"
HYDRO_DATASET = "/wii-prod_v3.2.1/CAM-44"

# All indicators to fetch
INDICATORS = {
    # Climate indicators (grid0.5)
    "temperature": {"var": "tasAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5"},
    "temperature_max": {"var": "tasmaxAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5"},
    "temperature_min": {"var": "tasminAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5"},
    "precipitation": {"var": "prAdjust-tmean", "type": "rel", "dataset": CLIMATE_DATASET, "grid": "grid0.5"},
    "frost_days": {"var": "fdAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5"},
    "tropical_nights": {"var": "tnAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5"},
    "heating_degree_days": {"var": "hddAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5"},
    "longest_dry_spell": {"var": "cddAdjust-tmean", "type": "rel", "dataset": CLIMATE_DATASET, "grid": "grid0.5"},
    "num_dry_spells": {"var": "ncddAdjust-tmean", "type": "rel", "dataset": CLIMATE_DATASET, "grid": "grid0.5"},
    # Hydrology indicators (catch)
    "aridity_actual": {"var": "aridact-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch"},
    "aridity_potential": {"var": "aridpot-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch"},
    "soil_moisture": {"var": "smoist-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch"},
    "soil_moisture_days_below_min": {"var": "smoistnodbm-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch"},
    "soil_moisture_annual_min": {"var": "smoistyearmin-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch"},
    "water_discharge": {"var": "wdis-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch"},
    "water_discharge_max": {"var": "wdisyearmax-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch"},
    "water_discharge_min": {"var": "wdisyearmin-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch"},
    "water_discharge_days_below_min": {"var": "wdisnodbm-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch"},
    "water_runoff": {"var": "wrun-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch"},
}

SCENARIOS = ["rcp45", "rcp85"]
PERIODS = ["2011-2040", "2041-2070", "2071-2100"]
BASELINE = "1981-2010"

def get_indicator(lat, lon, indicator_key, scenario, period):
    """Fetch single indicator from SSR API."""
    ind = INDICATORS[indicator_key]
    filename = f"{ind['var']}_{ind['type']}_CAM-44_ens_{scenario}_ens_{period}_{BASELINE}_{ind['grid']}_ensmed.nc"
    
    params = {
        "file": filename,
        "variable": ind["var"],
        "lat": round(lat, 2),
        "lon": round(lon, 2),
        "dataset": ind["dataset"]
    }
    
    try:
        response = requests.get(SSR_API, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data[0] if data else None
    except Exception as e:
        print(f"    Error fetching {indicator_key}: {e}")
    return None


def fetch_all_indicators(lat, lon, anp_name):
    """Fetch all indicators for an ANP."""
    results = {
        "source": "climateinformation.org",
        "api_endpoint": SSR_API,
        "anp_name": anp_name,
        "centroid": {"lat": lat, "lon": lon},
        "baseline_period": BASELINE,
        "extracted_at": datetime.now().isoformat(),
        "data": {}
    }
    
    total_calls = len(SCENARIOS) * len(PERIODS) * len(INDICATORS)
    call_num = 0
    
    for scenario in SCENARIOS:
        results["data"][scenario] = {}
        for period in PERIODS:
            results["data"][scenario][period] = {}
            for ind_key in INDICATORS:
                call_num += 1
                print(f"  [{call_num}/{total_calls}] {scenario} {period} {ind_key}...", end=" ", flush=True)
                
                value = get_indicator(lat, lon, ind_key, scenario, period)
                results["data"][scenario][period][ind_key] = round(value, 4) if value is not None else None
                
                print(f"{value:.2f}" if value is not None else "NULL")
                time.sleep(0.1)  # Rate limiting
    
    return results


def load_anp_centroid(anp_name):
    """Load centroid from ANP data file."""
    slug = anp_name.lower().replace(' ', '_')
    data_file = f"anp_data/{slug}_data.json"
    
    with open(data_file) as f:
        data = json.load(f)
    
    centroid = data['geometry']['centroid']
    return centroid[1], centroid[0]  # [lon, lat] -> lat, lon


def main():
    import sys
    
    TEST_ANPS = [
        "alto_golfo_de_california_y_delta_del_rio_colorado",
        "arrecife_alacranes", 
        "arrecife_de_puerto_morelos",
        "calakmul",
        "sierra_gorda",
        "sierra_gorda_de_guanajuato"
    ]
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test6":
            anp_list = TEST_ANPS
        else:
            anp_list = [sys.argv[1]]
    else:
        anp_list = TEST_ANPS
    
    for anp_slug in anp_list:
        print(f"\n{'='*60}")
        print(f"Processing: {anp_slug}")
        print('='*60)
        
        # Check if already done
        output_file = f"anp_data/{anp_slug}_climate_ssr.json"
        if os.path.exists(output_file):
            print(f"  Already exists: {output_file}")
            print("  Use --force to re-fetch")
            continue
        
        # Load centroid
        data_file = f"anp_data/{anp_slug}_data.json"
        with open(data_file) as f:
            data = json.load(f)
        
        centroid = data['geometry']['centroid']
        lat, lon = centroid[1], centroid[0]
        name = data['metadata']['name']
        
        print(f"  Centroid: {lat:.4f}, {lon:.4f}")
        
        # Fetch all indicators
        results = fetch_all_indicators(lat, lon, name)
        
        # Save
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n  Saved: {output_file}")


if __name__ == "__main__":
    main()
```

### Output: `anp_data/{anp_name}_climate_ssr.json`
```json
{
  "source": "climateinformation.org",
  "anp_name": "Sierra Gorda",
  "centroid": {"lat": 21.29, "lon": -99.48},
  "baseline_period": "1981-2010",
  "extracted_at": "2025-01-04T12:00:00",
  "data": {
    "rcp45": {
      "2011-2040": {
        "temperature": 1.2,
        "precipitation": -5.3,
        "aridity_actual": 2.1,
        "soil_moisture": -8.5,
        "water_discharge": -6.2,
        "water_runoff": -5.8
      },
      "2041-2070": {...},
      "2071-2100": {...}
    },
    "rcp85": {...}
  }
}
```

---

## Method 2: GEE Pixel Timeseries

### What It Provides
- **Temperature data** at ~5.5km grid resolution across entire ANP
- **Full timeseries**: 1980-2095 (every 5 years)
- **Both scenarios**: SSP2-4.5 AND SSP5-8.5
- Powers the animated heatmap visualization

### Data Source
- **GEE Dataset**: `NASA/GDDP-CMIP6`
- **Model**: `ACCESS-CM2`
- **Native resolution**: 0.25° (~27km), sampled at 0.05° (~5.5km)

### Script: `extract_climate_timeseries.py` (needs modification)

**Current behavior**: Extracts SSP2-4.5 only

**Modification needed**: Also extract SSP5-8.5 for comparison with RCP 8.5

### Modifications Required

```python
# Change from single scenario to both scenarios

SCENARIOS_TO_EXTRACT = ['ssp245', 'ssp585']

# Historical years (same for both scenarios)
HISTORICAL_YEARS = [1980, 1985, 1990, 1995, 2000, 2005, 2010]

# Future years (extracted for each scenario)  
FUTURE_YEARS = [2015, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 
                2055, 2060, 2065, 2070, 2075, 2080, 2085, 2090, 2095]

# Output structure should include both scenarios:
result = {
    "anp_name": name,
    "model": "ACCESS-CM2",
    "grid_resolution_deg": 0.05,
    "points": [...],
    "scenarios": {
        "ssp245": {
            "years": {
                "1980": [temps...],
                "1985": [temps...],
                ...
            }
        },
        "ssp585": {
            "years": {
                "1980": [temps...],  # Same as ssp245 for historical
                ...
            }
        }
    }
}
```

### Output: `anp_data/{anp_name}_climate_timeseries.json`

```json
{
  "anp_name": "Sierra Gorda",
  "model": "ACCESS-CM2",
  "grid_resolution_deg": 0.05,
  "bbox": {"min_lon": -100.5, "max_lon": -98.5, "min_lat": 20.5, "max_lat": 22.0},
  "points": [[-100.45, 20.55], [-100.40, 20.55], ...],
  "scenarios": {
    "ssp245": {
      "years": {
        "1980": [18.2, 18.5, 19.1, ...],
        "2095": [20.8, 21.1, 21.7, ...]
      }
    },
    "ssp585": {
      "years": {
        "1980": [18.2, 18.5, 19.1, ...],
        "2095": [22.1, 22.4, 23.0, ...]
      }
    }
  },
  "extracted_at": "2025-01-04T14:00:00"
}
```

---

## Method 3: Comparison Analysis

### Purpose
Compare temperature projections from climateinformation.org (RCP) vs GEE (SSP) to validate our understanding of both sources.

### Comparison Mapping

| climateinformation.org | GEE | Expected Similarity |
|------------------------|-----|---------------------|
| RCP 4.5 | SSP2-4.5 | ~0.2-0.5°C difference |
| RCP 8.5 | SSP5-8.5 | ~0.2-0.5°C difference |

### How to Derive GEE Period Averages

From the pixel timeseries, calculate:

```python
def calculate_period_average(timeseries_data, scenario, period):
    """Calculate average temperature for a period from timeseries data."""
    years = timeseries_data['scenarios'][scenario]['years']
    
    # Define which years fall in each period
    PERIOD_YEARS = {
        "baseline": [1980, 1985, 1990, 1995, 2000, 2005, 2010],
        "2011-2040": [2015, 2020, 2025, 2030, 2035, 2040],
        "2041-2070": [2045, 2050, 2055, 2060, 2065, 2070],
        "2071-2100": [2075, 2080, 2085, 2090, 2095]
    }
    
    period_years = PERIOD_YEARS[period]
    all_temps = []
    
    for year in period_years:
        year_temps = years.get(str(year), [])
        valid_temps = [t for t in year_temps if t is not None]
        all_temps.extend(valid_temps)
    
    return sum(all_temps) / len(all_temps) if all_temps else None


def calculate_temperature_change(timeseries_data, scenario, future_period):
    """Calculate temperature change from baseline."""
    baseline = calculate_period_average(timeseries_data, scenario, "baseline")
    future = calculate_period_average(timeseries_data, scenario, future_period)
    
    if baseline and future:
        return future - baseline
    return None
```

### Script to Create: `compare_climate_sources.py`

```python
#!/usr/bin/env python3
"""
Compare climate projections from climateinformation.org vs GEE.
"""
import json
import os

def load_ssr_data(anp_slug):
    """Load SSR API data."""
    with open(f"anp_data/{anp_slug}_climate_ssr.json") as f:
        return json.load(f)

def load_timeseries_data(anp_slug):
    """Load GEE timeseries data."""
    with open(f"anp_data/{anp_slug}_climate_timeseries.json") as f:
        return json.load(f)

def calculate_gee_period_average(ts_data, scenario, period):
    """Calculate average from timeseries for a period."""
    PERIOD_YEARS = {
        "baseline": ["1980", "1985", "1990", "1995", "2000", "2005", "2010"],
        "2011-2040": ["2015", "2020", "2025", "2030", "2035", "2040"],
        "2041-2070": ["2045", "2050", "2055", "2060", "2065", "2070"],
        "2071-2100": ["2075", "2080", "2085", "2090", "2095"]
    }
    
    years_data = ts_data['scenarios'][scenario]['years']
    all_temps = []
    
    for year in PERIOD_YEARS[period]:
        if year in years_data:
            valid = [t for t in years_data[year] if t is not None]
            all_temps.extend(valid)
    
    return sum(all_temps) / len(all_temps) if all_temps else None

def compare_anp(anp_slug):
    """Compare SSR vs GEE for one ANP."""
    ssr = load_ssr_data(anp_slug)
    ts = load_timeseries_data(anp_slug)
    
    print(f"\n{'='*60}")
    print(f"ANP: {ssr['anp_name']}")
    print(f"Centroid: {ssr['centroid']['lat']:.4f}, {ssr['centroid']['lon']:.4f}")
    print('='*60)
    
    # Calculate GEE baseline
    gee_baseline_245 = calculate_gee_period_average(ts, 'ssp245', 'baseline')
    gee_baseline_585 = calculate_gee_period_average(ts, 'ssp585', 'baseline')
    
    comparisons = [
        ("RCP 4.5 vs SSP2-4.5", "rcp45", "ssp245"),
        ("RCP 8.5 vs SSP5-8.5", "rcp85", "ssp585"),
    ]
    
    periods = ["2011-2040", "2041-2070", "2071-2100"]
    
    for label, rcp, ssp in comparisons:
        print(f"\n{label}:")
        print("-" * 50)
        print(f"{'Period':<15} {'SSR (°C)':<12} {'GEE (°C)':<12} {'Diff (°C)':<10}")
        print("-" * 50)
        
        gee_baseline = gee_baseline_245 if ssp == 'ssp245' else gee_baseline_585
        
        for period in periods:
            ssr_temp = ssr['data'][rcp][period].get('temperature')
            
            gee_future = calculate_gee_period_average(ts, ssp, period)
            gee_change = (gee_future - gee_baseline) if (gee_future and gee_baseline) else None
            
            if ssr_temp is not None and gee_change is not None:
                diff = gee_change - ssr_temp
                print(f"{period:<15} {ssr_temp:<12.2f} {gee_change:<12.2f} {diff:<+10.2f}")
            else:
                print(f"{period:<15} {'N/A':<12} {'N/A':<12} {'N/A':<10}")
    
    return {
        "anp": anp_slug,
        "ssr_source": "climateinformation.org (CMIP5/CORDEX, RCP)",
        "gee_source": "NASA GDDP-CMIP6 (SSP)",
        "note": "Differences <0.5°C are acceptable due to different models/scenarios"
    }

def main():
    TEST_ANPS = [
        "alto_golfo_de_california_y_delta_del_rio_colorado",
        "arrecife_alacranes",
        "arrecife_de_puerto_morelos", 
        "calakmul",
        "sierra_gorda",
        "sierra_gorda_de_guanajuato"
    ]
    
    print("\n" + "="*60)
    print("CLIMATE DATA SOURCE COMPARISON")
    print("climateinformation.org (RCP) vs GEE CMIP6 (SSP)")
    print("="*60)
    
    for anp_slug in TEST_ANPS:
        try:
            compare_anp(anp_slug)
        except FileNotFoundError as e:
            print(f"\nSkipping {anp_slug}: {e}")

if __name__ == "__main__":
    main()
```

### Expected Output

```
============================================================
ANP: Sierra Gorda
Centroid: 21.2888, -99.4784
============================================================

RCP 4.5 vs SSP2-4.5:
--------------------------------------------------
Period          SSR (°C)     GEE (°C)     Diff (°C) 
--------------------------------------------------
2011-2040       1.20         1.35         +0.15     
2041-2070       2.10         2.25         +0.15     
2071-2100       2.80         2.95         +0.15     

RCP 8.5 vs SSP5-8.5:
--------------------------------------------------
Period          SSR (°C)     GEE (°C)     Diff (°C) 
--------------------------------------------------
2011-2040       1.30         1.42         +0.12     
2041-2070       2.50         2.68         +0.18     
2071-2100       3.77         3.95         +0.18     
```

### Interpretation Guide

| Difference | Interpretation |
|------------|----------------|
| < 0.3°C | Excellent agreement |
| 0.3-0.5°C | Good agreement (expected) |
| 0.5-1.0°C | Moderate difference (investigate) |
| > 1.0°C | Significant difference (problem) |

---

## Data Tracking

### Status File: `anp_data/{anp_name}_climate_status.json`

```json
{
  "ssr_api": {
    "completed": true,
    "extracted_at": "2025-01-04T12:00:00",
    "indicators_count": 19,
    "scenarios": ["rcp45", "rcp85"],
    "periods": ["2011-2040", "2041-2070", "2071-2100"]
  },
  "gee_timeseries": {
    "completed": true,
    "extracted_at": "2025-01-04T14:00:00", 
    "scenarios": ["ssp245", "ssp585"],
    "years": "1980-2095",
    "grid_points": 145
  },
  "comparison": {
    "completed": true,
    "compared_at": "2025-01-04T15:00:00",
    "max_difference_c": 0.18
  }
}
```

---

## File Structure

```
anp_data/
├── {anp}_data.json                  # Main ANP data (has centroid)
├── {anp}_boundary.geojson           # ANP polygon boundary
├── {anp}_climate_ssr.json           # Method 1: SSR API data
├── {anp}_climate_timeseries.json    # Method 2: GEE pixel timeseries
├── {anp}_climate_status.json        # Tracking file
```

---

## Execution Order

### Phase 1: Test 6 ANPs

```bash
# Step 1: Fetch SSR API data (19 indicators × 2 scenarios × 3 periods)
python scrape_climate_ssr.py --test6

# Step 2: Extract GEE timeseries (both SSP2-4.5 and SSP5-8.5)
python extract_climate_timeseries.py --test6

# Step 3: Run comparison analysis
python compare_climate_sources.py

# Step 4: Review comparison results
# If differences < 0.5°C → proceed to Phase 2
# If differences > 0.5°C → investigate before proceeding
```

### Phase 2: Full Extraction (232 ANPs)

```bash
python scrape_climate_ssr.py --all
python extract_climate_timeseries.py --all
```

---

## Scripts Summary

| Script | Purpose | Status |
|--------|---------|--------|
| `scrape_climate_ssr.py` | Fetch from climateinformation.org API | **To create** |
| `extract_climate_timeseries.py` | GEE pixel timeseries | **Exists, needs SSP5-8.5** |
| `compare_climate_sources.py` | Compare SSR vs GEE | **To create** |

---

## Key Differences Between Sources

| Aspect | climateinformation.org | GEE CMIP6 |
|--------|------------------------|-----------|
| Model generation | CMIP5 + CORDEX | CMIP6 |
| Scenarios | RCP 4.5, 8.5 | SSP2-4.5, SSP5-8.5 |
| Resolution | 0.5° (~50km) | 0.25° (~27km) |
| Bias correction | DBS method | NASA method |
| Hydrology | HYPE model | Not available |
| Best for | All indicators | Spatial timeseries |

---

## Contact

Questions: [Add contact info]

Last updated: January 2025
