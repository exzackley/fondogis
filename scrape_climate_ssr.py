#!/usr/bin/env python3
"""
Fetch climate indicators from climateinformation.org REST API.
No browser scraping needed - direct API calls.

Source: climateinformation.org Site-Specific Report API
Data: CORDEX CAM-44 domain, bias-adjusted using MIdAS method
"""
import requests
import json
import time
import os
import sys
from datetime import datetime

SSR_API = "https://ssr.climateinformation.org/ssr/server/chart"
CLIMATE_DATASET = "/cii-prod_v4.5.1/CAM-44"
HYDRO_DATASET = "/wii-prod_v3.2.1/CAM-44"
DATA_DIR = 'anp_data'
API_DELAY = 0.1  # Rate limiting - 10 requests/second

# All indicators to fetch
INDICATORS = {
    # Climate indicators (grid0.5)
    "temperature": {"var": "tasAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5", "unit": "°C change"},
    "temperature_max": {"var": "tasmaxAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5", "unit": "°C change"},
    "temperature_min": {"var": "tasminAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5", "unit": "°C change"},
    "precipitation": {"var": "prAdjust-tmean", "type": "rel", "dataset": CLIMATE_DATASET, "grid": "grid0.5", "unit": "% change"},
    "frost_days": {"var": "fdAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5", "unit": "days change"},
    "tropical_nights": {"var": "tnAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5", "unit": "days change"},
    "heating_degree_days": {"var": "hddAdjust-tmean", "type": "abs", "dataset": CLIMATE_DATASET, "grid": "grid0.5", "unit": "degree-days"},
    "longest_dry_spell": {"var": "cddAdjust-tmean", "type": "rel", "dataset": CLIMATE_DATASET, "grid": "grid0.5", "unit": "% change"},
    "num_dry_spells": {"var": "ncddAdjust-tmean", "type": "rel", "dataset": CLIMATE_DATASET, "grid": "grid0.5", "unit": "% change"},
    # Hydrology indicators (catch)
    "aridity_actual": {"var": "aridact-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch", "unit": "% change"},
    "aridity_potential": {"var": "aridpot-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch", "unit": "% change"},
    "soil_moisture": {"var": "smoist-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch", "unit": "% change"},
    "soil_moisture_days_below_min": {"var": "smoistnodbm-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch", "unit": "% change"},
    "soil_moisture_annual_min": {"var": "smoistyearmin-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch", "unit": "% change"},
    "water_discharge": {"var": "wdis-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch", "unit": "% change"},
    "water_discharge_max": {"var": "wdisyearmax-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch", "unit": "% change"},
    "water_discharge_min": {"var": "wdisyearmin-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch", "unit": "% change"},
    "water_discharge_days_below_min": {"var": "wdisnodbm-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch", "unit": "% change"},
    "water_runoff": {"var": "wrun-tmean", "type": "rel", "dataset": HYDRO_DATASET, "grid": "catch", "unit": "% change"},
}

SCENARIOS = ["rcp45", "rcp85"]
PERIODS = ["2011-2040", "2041-2070", "2071-2100"]
BASELINE = "1981-2010"

TEST_ANPS = [
    "alto_golfo_de_california_y_delta_del_rio_colorado",
    "arrecife_alacranes", 
    "arrecife_de_puerto_morelos",
    "calakmul",
    "sierra_gorda",
    "sierra_gorda_de_guanajuato"
]


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
            if data and len(data) > 0:
                return data[0]
    except Exception as e:
        print(f"    Error fetching {indicator_key}: {e}")
    return None


def fetch_all_indicators(lat, lon, anp_name):
    """Fetch all indicators for an ANP."""
    results = {
        "source": "climateinformation.org",
        "methodology": "CORDEX CAM-44, bias-adjusted MIdAS method",
        "api_endpoint": SSR_API,
        "anp_name": anp_name,
        "centroid": {"lat": lat, "lon": lon},
        "baseline_period": BASELINE,
        "extracted_at": datetime.now().isoformat(),
        "indicators": {key: INDICATORS[key]["unit"] for key in INDICATORS},
        "data": {}
    }
    
    total_calls = len(SCENARIOS) * len(PERIODS) * len(INDICATORS)
    call_num = 0
    null_count = 0
    
    for scenario in SCENARIOS:
        results["data"][scenario] = {}
        for period in PERIODS:
            results["data"][scenario][period] = {}
            for ind_key in INDICATORS:
                call_num += 1
                print(f"  [{call_num}/{total_calls}] {scenario} {period} {ind_key}...", end=" ", flush=True)
                
                value = get_indicator(lat, lon, ind_key, scenario, period)
                
                if value is not None:
                    results["data"][scenario][period][ind_key] = round(value, 4)
                    print(f"{value:.2f}")
                else:
                    results["data"][scenario][period][ind_key] = None
                    null_count += 1
                    print("NULL")
                
                time.sleep(API_DELAY)  # Rate limiting
    
    results["null_values_count"] = null_count
    results["total_values"] = total_calls
    
    return results


def load_anp_centroid(anp_slug):
    """Load centroid from ANP data file."""
    data_file = f"{DATA_DIR}/{anp_slug}_data.json"
    
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"ANP data file not found: {data_file}")
    
    with open(data_file) as f:
        data = json.load(f)
    
    centroid = data['geometry']['centroid']
    name = data['metadata']['name']
    return centroid[1], centroid[0], name  # [lon, lat] -> lat, lon, name


def main():
    force = '--force' in sys.argv
    
    if '--test6' in sys.argv or len(sys.argv) == 1:
        anp_list = TEST_ANPS
    elif len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        anp_list = [sys.argv[1]]
    else:
        anp_list = TEST_ANPS
    
    print(f"\n{'='*60}")
    print("Climate SSR Data Extraction")
    print(f"Source: climateinformation.org REST API")
    print(f"ANPs to process: {len(anp_list)}")
    print(f"Indicators: {len(INDICATORS)} x {len(SCENARIOS)} scenarios x {len(PERIODS)} periods")
    print(f"Total API calls per ANP: {len(INDICATORS) * len(SCENARIOS) * len(PERIODS)}")
    print('='*60)
    
    for anp_slug in anp_list:
        print(f"\n{'='*60}")
        print(f"Processing: {anp_slug}")
        print('='*60)
        
        output_file = f"{DATA_DIR}/{anp_slug}_climate_ssr.json"
        
        # Check if already done
        if os.path.exists(output_file) and not force:
            print(f"  Already exists: {output_file}")
            print("  Use --force to re-fetch")
            continue
        
        # Load centroid
        try:
            lat, lon, name = load_anp_centroid(anp_slug)
        except FileNotFoundError as e:
            print(f"  Skipping: {e}")
            continue
        
        print(f"  Name: {name}")
        print(f"  Centroid: {lat:.4f}, {lon:.4f}")
        
        # Fetch all indicators
        results = fetch_all_indicators(lat, lon, name)
        
        # Save
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n  Saved: {output_file}")
        print(f"  NULL values: {results['null_values_count']}/{results['total_values']}")
    
    print(f"\n{'='*60}")
    print("COMPLETE")
    print('='*60)


if __name__ == "__main__":
    main()
