#!/usr/bin/env python3
"""
Add Climate Projections Data to ANP Files using NASA NEX-GDDP-CMIP6.

Usage:
    python3 add_climate_projections.py              # Process all ANPs
    python3 add_climate_projections.py --test       # Test with first 3 ANPs
    python3 add_climate_projections.py "calakmul"   # Process single ANP
"""

import ee
import json
import os
import sys
import time
from datetime import datetime
from glob import glob

try:
    from gee_auth import init_ee
except ImportError:
    def init_ee():
        ee.Initialize(project='gen-lang-client-0866285082')

DATA_DIR = 'anp_data'
CMIP6_COLLECTION = 'NASA/GDDP-CMIP6'

BASELINE_START = '2010-01-01'
BASELINE_END = '2010-12-31'
FUTURE_START = '2060-01-01'
FUTURE_END = '2060-12-31'

MODELS = ['ACCESS-CM2']

SCENARIOS = ['ssp245', 'ssp585']

TROPICAL_NIGHT_THRESHOLD_K = 293.15
HOT_DAY_THRESHOLD_K = 308.15
SCALE_METERS = 27830


def init():
    init_ee()


def kelvin_to_celsius(k):
    if k is None:
        return None
    return round(k - 273.15, 2)


def extract_climate_projections(geometry):
    try:
        geom = ee.Geometry.Polygon(geometry)
        cmip6 = ee.ImageCollection(CMIP6_COLLECTION)
        
        results = {
            "source": "NASA NEX-GDDP-CMIP6",
            "resolution": "0.25 degrees (~27km)",
            "baseline_period": "2010",
            "future_period": "2060",
            "models_used": len(MODELS),
            "model_list": MODELS,
            "scenarios": {},
            "extracted_at": datetime.now().isoformat()
        }
        
        for scenario in SCENARIOS:
            print(f"      {scenario.upper()}...", end=" ", flush=True)
            scenario_data = extract_scenario_data(cmip6, geom, scenario)
            results["scenarios"][scenario] = scenario_data
            print("OK")
        
        results["data_available"] = True
        return results
        
    except Exception as e:
        return {
            "data_available": False,
            "error": str(e),
            "extracted_at": datetime.now().isoformat()
        }


def extract_scenario_data(cmip6, geom, scenario):
    model_filter = ee.Filter.inList('model', MODELS)
    
    baseline = cmip6.filter(model_filter) \
        .filter(ee.Filter.eq('scenario', 'historical')) \
        .filter(ee.Filter.date(BASELINE_START, BASELINE_END))
    
    future = cmip6.filter(model_filter) \
        .filter(ee.Filter.eq('scenario', scenario)) \
        .filter(ee.Filter.date(FUTURE_START, FUTURE_END))
    
    return {
        "temperature": extract_temperature_stats(baseline, future, geom),
        "precipitation": extract_precipitation_stats(baseline, future, geom),
        "heat_stress": extract_heat_indicators(baseline, future, geom),
        "drought_indicators": extract_drought_indicators(baseline, future, geom)
    }


def extract_temperature_stats(baseline, future, geom):
    baseline_tas = baseline.select('tas').mean()
    future_tas = future.select('tas').mean()
    
    reducer = ee.Reducer.mean().combine(ee.Reducer.min(), '', True) \
                                .combine(ee.Reducer.max(), '', True) \
                                .combine(ee.Reducer.stdDev(), '', True)
    
    baseline_stats = baseline_tas.reduceRegion(
        reducer=reducer, geometry=geom, scale=SCALE_METERS, maxPixels=1e9
    ).getInfo()
    
    future_stats = future_tas.reduceRegion(
        reducer=reducer, geometry=geom, scale=SCALE_METERS, maxPixels=1e9
    ).getInfo()
    
    baseline_mean = baseline_stats.get('tas_mean')
    future_mean = future_stats.get('tas_mean')
    
    change_mean = None
    if baseline_mean and future_mean:
        change_mean = round(future_mean - baseline_mean, 2)
    
    return {
        "baseline_mean_c": kelvin_to_celsius(baseline_mean),
        "future_mean_c": kelvin_to_celsius(future_mean),
        "change_c": change_mean,
        "spatial_variation": {
            "baseline_min_c": kelvin_to_celsius(baseline_stats.get('tas_min')),
            "baseline_max_c": kelvin_to_celsius(baseline_stats.get('tas_max')),
            "future_min_c": kelvin_to_celsius(future_stats.get('tas_min')),
            "future_max_c": kelvin_to_celsius(future_stats.get('tas_max'))
        }
    }


def extract_precipitation_stats(baseline, future, geom):
    seconds_per_year = 86400 * 365
    
    baseline_pr = baseline.select('pr').mean().multiply(seconds_per_year)
    future_pr = future.select('pr').mean().multiply(seconds_per_year)
    
    baseline_stats = baseline_pr.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=geom, scale=SCALE_METERS, maxPixels=1e9
    ).getInfo()
    
    future_stats = future_pr.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=geom, scale=SCALE_METERS, maxPixels=1e9
    ).getInfo()
    
    baseline_mm = baseline_stats.get('pr')
    future_mm = future_stats.get('pr')
    
    change_percent = None
    change_mm = None
    if baseline_mm and future_mm and baseline_mm > 0:
        change_mm = round(future_mm - baseline_mm, 1)
        change_percent = round((future_mm - baseline_mm) / baseline_mm * 100, 1)
    
    return {
        "baseline_annual_mm": round(baseline_mm, 1) if baseline_mm else None,
        "future_annual_mm": round(future_mm, 1) if future_mm else None,
        "change_mm": change_mm,
        "change_percent": change_percent
    }


def extract_heat_indicators(baseline, future, geom):
    baseline_tasmin = baseline.select('tasmin').mean()
    future_tasmin = future.select('tasmin').mean()
    
    baseline_min_stats = baseline_tasmin.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=geom, scale=SCALE_METERS, maxPixels=1e9
    ).getInfo()
    
    future_min_stats = future_tasmin.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=geom, scale=SCALE_METERS, maxPixels=1e9
    ).getInfo()
    
    baseline_min_c = kelvin_to_celsius(baseline_min_stats.get('tasmin'))
    future_min_c = kelvin_to_celsius(future_min_stats.get('tasmin'))
    
    tropical_nights_baseline = estimate_tropical_nights(baseline_min_c) if baseline_min_c else None
    tropical_nights_future = estimate_tropical_nights(future_min_c) if future_min_c else None
    
    change = None
    if tropical_nights_baseline is not None and tropical_nights_future is not None:
        change = tropical_nights_future - tropical_nights_baseline
    
    return {
        "mean_min_temp_baseline_c": baseline_min_c,
        "mean_min_temp_future_c": future_min_c,
        "tropical_nights_baseline_estimate": tropical_nights_baseline,
        "tropical_nights_future_estimate": tropical_nights_future,
        "change_days_estimate": change,
        "note": "Tropical nights estimated from mean minimum temperature"
    }


def estimate_tropical_nights(mean_min_temp_c):
    """Empirical estimation: mean_min_temp -> annual tropical nights (>20°C)."""
    if mean_min_temp_c is None:
        return None
    
    # Piecewise linear approximation based on climate literature
    if mean_min_temp_c < 10:
        return 0
    elif mean_min_temp_c < 15:
        return int((mean_min_temp_c - 10) * 6)
    elif mean_min_temp_c < 20:
        return int(30 + (mean_min_temp_c - 15) * 18)
    elif mean_min_temp_c < 25:
        return int(120 + (mean_min_temp_c - 20) * 26)
    else:
        return int(250 + (mean_min_temp_c - 25) * 20)


def extract_drought_indicators(baseline, future, geom):
    baseline_pr = baseline.select('pr').mean()
    future_pr = future.select('pr').mean()
    
    baseline_stats = baseline_pr.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=geom, scale=SCALE_METERS, maxPixels=1e9
    ).getInfo()
    
    future_stats = future_pr.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=geom, scale=SCALE_METERS, maxPixels=1e9
    ).getInfo()
    
    baseline_mm_day = baseline_stats.get('pr', 0) * 86400 if baseline_stats.get('pr') else None
    future_mm_day = future_stats.get('pr', 0) * 86400 if future_stats.get('pr') else None
    
    cdd_baseline = estimate_dry_days(baseline_mm_day) if baseline_mm_day else None
    cdd_future = estimate_dry_days(future_mm_day) if future_mm_day else None
    
    change = None
    if cdd_baseline and cdd_future:
        change = cdd_future - cdd_baseline
    
    return {
        "mean_daily_precip_baseline_mm": round(baseline_mm_day, 2) if baseline_mm_day else None,
        "mean_daily_precip_future_mm": round(future_mm_day, 2) if future_mm_day else None,
        "consecutive_dry_days_baseline_estimate": cdd_baseline,
        "consecutive_dry_days_future_estimate": cdd_future,
        "change_days_estimate": change,
        "drought_risk_baseline": categorize_drought_risk(baseline_mm_day),
        "drought_risk_future": categorize_drought_risk(future_mm_day),
        "note": "Drought indicators estimated from mean precipitation patterns"
    }


def estimate_dry_days(mean_precip_mm_day):
    """Empirical estimation: mean_precip (mm/day) -> max consecutive dry days."""
    if mean_precip_mm_day is None or mean_precip_mm_day <= 0:
        return None
    
    # Inverse relationship: lower precip = more consecutive dry days
    if mean_precip_mm_day < 1:
        return 90
    elif mean_precip_mm_day < 2:
        return int(90 - (mean_precip_mm_day - 0) * 30)
    elif mean_precip_mm_day < 5:
        return int(60 - (mean_precip_mm_day - 2) * 10)
    elif mean_precip_mm_day < 10:
        return int(30 - (mean_precip_mm_day - 5) * 3)
    else:
        return 15


def categorize_drought_risk(mean_precip_mm_day):
    if mean_precip_mm_day is None:
        return None
    if mean_precip_mm_day < 1:
        return "Very High"
    elif mean_precip_mm_day < 2:
        return "High"
    elif mean_precip_mm_day < 4:
        return "Medium"
    elif mean_precip_mm_day < 6:
        return "Low-Medium"
    else:
        return "Low"


def process_anp(data_file):
    with open(data_file) as f:
        data = json.load(f)
    
    name = data.get('metadata', {}).get('name', os.path.basename(data_file))
    
    existing = data.get('datasets', {}).get('climate_projections', {})
    if existing and existing.get('data_available') and 'error' not in existing:
        print(f"  {name}: Already has climate projections, skipping")
        return 'skipped'
    
    bounds = data.get('geometry', {}).get('bounds')
    if not bounds:
        print(f"  {name}: No bounds found, skipping")
        return 'skipped'
    
    print(f"  {name}: Extracting climate projections...")
    
    try:
        projections = extract_climate_projections(bounds)
        
        if 'datasets' not in data:
            data['datasets'] = {}
        
        data['datasets']['climate_projections'] = projections
        
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        if projections.get('data_available'):
            ssp245 = projections.get('scenarios', {}).get('ssp245', {})
            temp_change = ssp245.get('temperature', {}).get('change_c')
            precip_change = ssp245.get('precipitation', {}).get('change_percent')
            if temp_change and precip_change:
                print(f"    Summary (SSP2-4.5): Temp +{temp_change}°C, Precip {precip_change:+.1f}%")
            else:
                print("    Data extracted")
        else:
            print(f"    Warning: {projections.get('error', 'Unknown error')}")
        
        return 'success'
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return 'error'


def main():
    print("\n" + "="*60)
    print("NASA CMIP6 Climate Projections Extraction")
    print("="*60)
    
    init()
    print("GEE initialized")
    print(f"Using {len(MODELS)} climate models")
    print(f"Baseline: {BASELINE_START[:4]}-{BASELINE_END[:4]}")
    print(f"Future: {FUTURE_START[:4]}-{FUTURE_END[:4]}")
    print(f"Scenarios: {', '.join(SCENARIOS)}\n")
    
    data_files = sorted(glob(f"{DATA_DIR}/*_data.json"))
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '--test':
            data_files = data_files[:3]
            print(f"TEST MODE: Processing first 3 ANPs")
        elif arg == '--force':
            print("FORCE MODE: Re-processing all ANPs")
        else:
            search = arg.lower().replace(' ', '_')
            data_files = [f for f in data_files if search in f.lower()]
            if not data_files:
                print(f"No ANP found matching '{arg}'")
                return
    
    print(f"Processing {len(data_files)} ANP files...\n")
    
    success = 0
    skipped = 0
    errors = 0
    
    for i, data_file in enumerate(data_files, 1):
        if i > 1:
            time.sleep(1.0)
        
        result = process_anp(data_file)
        if result == 'success':
            success += 1
        elif result == 'skipped':
            skipped += 1
        else:
            errors += 1
    
    print("\n" + "="*60)
    print(f"Complete: {success} updated, {skipped} skipped, {errors} errors")
    print("="*60)


if __name__ == '__main__':
    main()
