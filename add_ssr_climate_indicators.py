#!/usr/bin/env python3
"""
Add comprehensive SSR-style climate indicators to ANP files using NASA NEX-GDDP-CMIP6.

Extracts indicators matching climateinformation.org SSR tool:
- Temperature (mean, min, max) + tropical nights, frost days
- Precipitation + dry spell analysis
- Soil moisture (if available)
- Runoff (if available)

For scenarios: SSP2-4.5 (RCP4.5) and SSP5-8.5 (RCP8.5)
For periods: Reference (1981-2010), Early (2011-2040), Mid (2041-2070), End (2071-2100)

Usage:
    python3 add_ssr_climate_indicators.py              # Process all ANPs
    python3 add_ssr_climate_indicators.py --test       # Test with first 3 ANPs
    python3 add_ssr_climate_indicators.py "sierra_gorda"  # Process single ANP
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

TIME_PERIODS = {
    'reference': {'start': '1981-01-01', 'end': '2010-12-31', 'scenario': 'historical'},
    'early_century': {'start': '2011-01-01', 'end': '2040-12-31', 'scenario': None},
    'mid_century': {'start': '2041-01-01', 'end': '2070-12-31', 'scenario': None},
    'end_century': {'start': '2071-01-01', 'end': '2100-12-31', 'scenario': None},
}

SCENARIOS = {
    'ssp245': 'SSP2-4.5 (moderate)',
    'ssp585': 'SSP5-8.5 (high emissions)'
}

MODELS = ['ACCESS-CM2', 'GFDL-ESM4', 'MRI-ESM2-0', 'MIROC6', 'UKESM1-0-LL']

SCALE_METERS = 27830

TROPICAL_NIGHT_THRESHOLD_K = 293.15
FROST_DAY_THRESHOLD_K = 273.15
HOT_DAY_THRESHOLD_K = 308.15


def kelvin_to_celsius(k):
    """Convert Kelvin to Celsius."""
    if k is None:
        return None
    return round(k - 273.15, 2)


def extract_temperature_indicators(cmip6, geom, period_key, scenario=None):
    """Extract temperature indicators for a given period."""
    period = TIME_PERIODS[period_key]
    
    if period['scenario'] == 'historical':
        scenario_filter = ee.Filter.eq('scenario', 'historical')
    else:
        scenario_filter = ee.Filter.eq('scenario', scenario)
    
    filtered = cmip6.filter(ee.Filter.inList('model', MODELS)) \
        .filter(scenario_filter) \
        .filter(ee.Filter.date(period['start'], period['end']))
    
    tas_mean = filtered.select('tas').mean()
    tas_stats = tas_mean.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.min(), '', True)
                                    .combine(ee.Reducer.max(), '', True)
                                    .combine(ee.Reducer.stdDev(), '', True),
        geometry=geom,
        scale=SCALE_METERS,
        maxPixels=1e9
    ).getInfo()
    
    tasmax_mean = filtered.select('tasmax').mean()
    tasmax_stats = tasmax_mean.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom,
        scale=SCALE_METERS,
        maxPixels=1e9
    ).getInfo()
    
    tasmin_mean = filtered.select('tasmin').mean()
    tasmin_stats = tasmin_mean.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom,
        scale=SCALE_METERS,
        maxPixels=1e9
    ).getInfo()
    
    tasmin_c = kelvin_to_celsius(tasmin_stats.get('tasmin'))
    tasmax_c = kelvin_to_celsius(tasmax_stats.get('tasmax'))
    
    return {
        'mean_c': kelvin_to_celsius(tas_stats.get('tas_mean')),
        'min_c': kelvin_to_celsius(tas_stats.get('tas_min')),
        'max_c': kelvin_to_celsius(tas_stats.get('tas_max')),
        'std_c': round(tas_stats.get('tas_stdDev', 0), 2) if tas_stats.get('tas_stdDev') else None,
        'daily_max_mean_c': tasmax_c,
        'daily_min_mean_c': tasmin_c,
        'tropical_nights_est': estimate_tropical_nights(tasmin_c),
        'frost_days_est': estimate_frost_days(tasmin_c),
    }


def extract_precipitation_indicators(cmip6, geom, period_key, scenario=None):
    """Extract precipitation indicators for a given period."""
    period = TIME_PERIODS[period_key]
    
    if period['scenario'] == 'historical':
        scenario_filter = ee.Filter.eq('scenario', 'historical')
    else:
        scenario_filter = ee.Filter.eq('scenario', scenario)
    
    filtered = cmip6.filter(ee.Filter.inList('model', MODELS)) \
        .filter(scenario_filter) \
        .filter(ee.Filter.date(period['start'], period['end']))
    
    pr_mean = filtered.select('pr').mean()
    pr_stats = pr_mean.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), '', True),
        geometry=geom,
        scale=SCALE_METERS,
        maxPixels=1e9
    ).getInfo()
    
    pr_mm_year = None
    pr_mean_val = pr_stats.get('pr_mean')
    if pr_mean_val is not None:
        pr_mm_year = round(pr_mean_val * 86400 * 365, 1)
    
    pr_mm_day = pr_mean_val * 86400 if pr_mean_val else None
    
    return {
        'annual_mm': pr_mm_year,
        'daily_mean_mm': round(pr_mm_day, 2) if pr_mm_day else None,
        'consecutive_dry_days_est': estimate_dry_days(pr_mm_day),
    }


def extract_soil_moisture_indicators(cmip6, geom, period_key, scenario=None):
    """Extract soil moisture indicators (mrso) if available."""
    period = TIME_PERIODS[period_key]
    
    if period['scenario'] == 'historical':
        scenario_filter = ee.Filter.eq('scenario', 'historical')
    else:
        scenario_filter = ee.Filter.eq('scenario', scenario)
    
    try:
        filtered = cmip6.filter(ee.Filter.inList('model', MODELS)) \
            .filter(scenario_filter) \
            .filter(ee.Filter.date(period['start'], period['end']))
        
        mrso_mean = filtered.select('mrso').mean()
        mrso_stats = mrso_mean.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), '', True),
            geometry=geom,
            scale=SCALE_METERS,
            maxPixels=1e9
        ).getInfo()
        
        return {
            'mean_kg_m2': round(mrso_stats.get('mrso_mean', 0), 2) if mrso_stats.get('mrso_mean') else None,
            'std_kg_m2': round(mrso_stats.get('mrso_stdDev', 0), 2) if mrso_stats.get('mrso_stdDev') else None,
        }
    except Exception:
        return {'available': False, 'note': 'Soil moisture (mrso) not available in this dataset'}


def extract_runoff_indicators(cmip6, geom, period_key, scenario=None):
    """Extract runoff indicators (mrro) if available."""
    period = TIME_PERIODS[period_key]
    
    if period['scenario'] == 'historical':
        scenario_filter = ee.Filter.eq('scenario', 'historical')
    else:
        scenario_filter = ee.Filter.eq('scenario', scenario)
    
    try:
        filtered = cmip6.filter(ee.Filter.inList('model', MODELS)) \
            .filter(scenario_filter) \
            .filter(ee.Filter.date(period['start'], period['end']))
        
        mrro_mean = filtered.select('mrro').mean()
        mrro_stats = mrro_mean.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geom,
            scale=SCALE_METERS,
            maxPixels=1e9
        ).getInfo()
        
        mrro_mm_year = None
        if mrro_stats.get('mrro'):
            mrro_mm_year = round(mrro_stats['mrro'] * 86400 * 365, 1)
        
        return {
            'annual_mm': mrro_mm_year,
        }
    except Exception:
        return {'available': False, 'note': 'Runoff (mrro) not available in this dataset'}


def estimate_tropical_nights(mean_min_temp_c):
    """Estimate annual tropical nights (min temp > 20°C) from mean minimum temperature."""
    if mean_min_temp_c is None:
        return None
    
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


def estimate_frost_days(mean_min_temp_c):
    """Estimate annual frost days (min temp < 0°C) from mean minimum temperature."""
    if mean_min_temp_c is None:
        return None
    
    if mean_min_temp_c > 10:
        return 0
    elif mean_min_temp_c > 5:
        return int((10 - mean_min_temp_c) * 3)
    elif mean_min_temp_c > 0:
        return int(15 + (5 - mean_min_temp_c) * 10)
    elif mean_min_temp_c > -5:
        return int(65 + (0 - mean_min_temp_c) * 15)
    else:
        return int(140 + (-5 - mean_min_temp_c) * 10)


def estimate_dry_days(mean_precip_mm_day):
    """Estimate max consecutive dry days from mean precipitation."""
    if mean_precip_mm_day is None or mean_precip_mm_day <= 0:
        return None
    
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


def calculate_change(future_val, baseline_val, is_percent=False):
    """Calculate change between future and baseline values."""
    if future_val is None or baseline_val is None:
        return None
    
    if is_percent and baseline_val != 0:
        return round((future_val - baseline_val) / baseline_val * 100, 1)
    else:
        return round(future_val - baseline_val, 2)


def extract_ssr_climate_indicators(geometry):
    """Extract all SSR-style climate indicators for a geometry."""
    try:
        geom = ee.Geometry.Polygon(geometry)
        cmip6 = ee.ImageCollection(CMIP6_COLLECTION)
        
        results = {
            "source": "NASA NEX-GDDP-CMIP6 (GEE extraction)",
            "methodology": "Direct extraction without bias adjustment",
            "resolution": "0.25 degrees (~27km)",
            "models_used": MODELS,
            "time_periods": {
                "reference": "1981-2010",
                "early_century": "2011-2040", 
                "mid_century": "2041-2070",
                "end_century": "2071-2100"
            },
            "scenarios": {},
            "extracted_at": datetime.now().isoformat()
        }
        
        print("      Extracting reference period (1981-2010)...", end=" ", flush=True)
        ref_temp = extract_temperature_indicators(cmip6, geom, 'reference')
        ref_precip = extract_precipitation_indicators(cmip6, geom, 'reference')
        ref_soil = extract_soil_moisture_indicators(cmip6, geom, 'reference')
        ref_runoff = extract_runoff_indicators(cmip6, geom, 'reference')
        print("OK")
        
        results["reference"] = {
            "temperature": ref_temp,
            "precipitation": ref_precip,
            "soil_moisture": ref_soil,
            "runoff": ref_runoff
        }
        
        for scenario in ['ssp245', 'ssp585']:
            print(f"      Extracting {scenario.upper()}...", flush=True)
            scenario_data = {
                "description": SCENARIOS[scenario],
                "periods": {}
            }
            
            for period_key in ['early_century', 'mid_century', 'end_century']:
                print(f"        {period_key}...", end=" ", flush=True)
                
                temp = extract_temperature_indicators(cmip6, geom, period_key, scenario)
                precip = extract_precipitation_indicators(cmip6, geom, period_key, scenario)
                soil = extract_soil_moisture_indicators(cmip6, geom, period_key, scenario)
                runoff = extract_runoff_indicators(cmip6, geom, period_key, scenario)
                
                period_data = {
                    "temperature": {
                        **temp,
                        "change_c": calculate_change(temp['mean_c'], ref_temp['mean_c']),
                        "change_max_c": calculate_change(temp['daily_max_mean_c'], ref_temp['daily_max_mean_c']),
                        "change_min_c": calculate_change(temp['daily_min_mean_c'], ref_temp['daily_min_mean_c']),
                    },
                    "precipitation": {
                        **precip,
                        "change_percent": calculate_change(precip['annual_mm'], ref_precip['annual_mm'], is_percent=True),
                        "change_mm": calculate_change(precip['annual_mm'], ref_precip['annual_mm']),
                    },
                    "soil_moisture": soil,
                    "runoff": runoff
                }
                
                if ref_soil.get('mean_kg_m2') and soil.get('mean_kg_m2'):
                    period_data["soil_moisture"]["change_percent"] = calculate_change(
                        soil['mean_kg_m2'], ref_soil['mean_kg_m2'], is_percent=True
                    )
                
                if ref_runoff.get('annual_mm') and runoff.get('annual_mm'):
                    period_data["runoff"]["change_percent"] = calculate_change(
                        runoff['annual_mm'], ref_runoff['annual_mm'], is_percent=True
                    )
                
                scenario_data["periods"][period_key] = period_data
                print("OK")
            
            results["scenarios"][scenario] = scenario_data
        
        results["data_available"] = True
        return results
        
    except Exception as e:
        return {
            "data_available": False,
            "error": str(e),
            "extracted_at": datetime.now().isoformat()
        }


def process_anp(data_file, force=False):
    """Process a single ANP file."""
    with open(data_file) as f:
        data = json.load(f)
    
    name = data.get('metadata', {}).get('name', os.path.basename(data_file))
    
    existing = data.get('datasets', {}).get('ssr_climate_indicators', {})
    if existing and existing.get('data_available') and not force:
        print(f"  {name}: Already has SSR climate indicators, skipping")
        return 'skipped'
    
    bounds = data.get('geometry', {}).get('bounds')
    if not bounds:
        print(f"  {name}: No bounds found, skipping")
        return 'skipped'
    
    print(f"  {name}: Extracting SSR climate indicators...")
    
    try:
        indicators = extract_ssr_climate_indicators(bounds)
        
        if 'datasets' not in data:
            data['datasets'] = {}
        
        data['datasets']['ssr_climate_indicators'] = indicators
        
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        if indicators.get('data_available'):
            ssp585_end = indicators.get('scenarios', {}).get('ssp585', {}).get('periods', {}).get('end_century', {})
            temp_change = ssp585_end.get('temperature', {}).get('change_c')
            precip_change = ssp585_end.get('precipitation', {}).get('change_percent')
            
            print(f"    Summary (SSP5-8.5, 2071-2100):")
            print(f"      Temperature: {'+' if temp_change and temp_change > 0 else ''}{temp_change}°C")
            print(f"      Precipitation: {'+' if precip_change and precip_change > 0 else ''}{precip_change}%")
        else:
            print(f"    Warning: {indicators.get('error', 'Unknown error')}")
        
        return 'success'
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return 'error'


def main():
    print("\n" + "="*70)
    print("SSR-Style Climate Indicators Extraction (NASA CMIP6)")
    print("="*70)
    
    init_ee()
    print("GEE initialized")
    print(f"Using {len(MODELS)} climate models: {', '.join(MODELS)}")
    print(f"Time periods: Reference (1981-2010), Early (2011-2040), Mid (2041-2070), End (2071-2100)")
    print(f"Scenarios: {', '.join(SCENARIOS.keys())}\n")
    
    data_files = sorted(glob(f"{DATA_DIR}/*_data.json"))
    force = False
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '--test':
            data_files = data_files[:3]
            print(f"TEST MODE: Processing first 3 ANPs")
        elif arg == '--force':
            force = True
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
            time.sleep(2.0)
        
        result = process_anp(data_file, force)
        if result == 'success':
            success += 1
        elif result == 'skipped':
            skipped += 1
        else:
            errors += 1
    
    print("\n" + "="*70)
    print(f"Complete: {success} updated, {skipped} skipped, {errors} errors")
    print("="*70)


if __name__ == '__main__':
    main()
