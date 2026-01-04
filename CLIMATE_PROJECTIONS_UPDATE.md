# Instructions: Update `add_climate_projections.py` to Standard Time Periods

## Background

The current script uses arbitrary 10-year periods (2005-2014 baseline, 2055-2064 future). We need to align with the **standard 30-year periods** used by climateinformation.org for consistency and comparison.

## Changes Required

### 1. Update Time Period Constants (lines 28-31)

**Current:**
```python
BASELINE_START = '2005-01-01'
BASELINE_END = '2014-12-31'
FUTURE_START = '2055-01-01'
FUTURE_END = '2064-12-31'
```

**Change to:**
```python
# Standard 30-year periods (aligned with climateinformation.org)
BASELINE_START = '1981-01-01'
BASELINE_END = '2010-12-31'

# Three standard future periods
FUTURE_PERIODS = {
    "2011-2040": ("2011-01-01", "2040-12-31"),
    "2041-2070": ("2041-01-01", "2070-12-31"),
    "2071-2100": ("2071-01-01", "2100-12-31"),
}
```

### 2. Update `extract_climate_projections()` function (around line 52)

**Change the results structure to include all 3 periods:**

```python
def extract_climate_projections(geometry):
    try:
        geom = ee.Geometry.Polygon(geometry)
        cmip6 = ee.ImageCollection(CMIP6_COLLECTION)
        
        results = {
            "source": "NASA NEX-GDDP-CMIP6",
            "resolution": "0.25 degrees (~27km)",
            "baseline_period": "1981-2010",
            "future_periods": list(FUTURE_PERIODS.keys()),
            "models_used": len(MODELS),
            "model_list": MODELS,
            "scenarios": {},
            "extracted_at": datetime.now().isoformat()
        }
        
        for scenario in SCENARIOS:
            print(f"      {scenario.upper()}:", end=" ", flush=True)
            results["scenarios"][scenario] = {}
            
            for period_name, (period_start, period_end) in FUTURE_PERIODS.items():
                print(f"{period_name}...", end=" ", flush=True)
                scenario_data = extract_scenario_data(cmip6, geom, scenario, period_start, period_end)
                results["scenarios"][scenario][period_name] = scenario_data
            
            print("OK")
        
        results["data_available"] = True
        return results
        
    except Exception as e:
        return {
            "data_available": False,
            "error": str(e),
            "extracted_at": datetime.now().isoformat()
        }
```

### 3. Update `extract_scenario_data()` function (around line 85)

**Change to accept period parameters:**

```python
def extract_scenario_data(cmip6, geom, scenario, future_start, future_end):
    model_filter = ee.Filter.inList('model', MODELS)
    
    baseline = cmip6.filter(model_filter) \
        .filter(ee.Filter.eq('scenario', 'historical')) \
        .filter(ee.Filter.date(BASELINE_START, BASELINE_END))
    
    future = cmip6.filter(model_filter) \
        .filter(ee.Filter.eq('scenario', scenario)) \
        .filter(ee.Filter.date(future_start, future_end))
    
    return {
        "temperature": extract_temperature_stats(baseline, future, geom),
        "precipitation": extract_precipitation_stats(baseline, future, geom),
        "heat_stress": extract_heat_indicators(baseline, future, geom),
        "drought_indicators": extract_drought_indicators(baseline, future, geom)
    }
```

### 4. Update the print statements in `main()` (around line 343)

**Change:**
```python
print(f"Baseline: {BASELINE_START[:4]}-{BASELINE_END[:4]}")
print(f"Future: {FUTURE_START[:4]}-{FUTURE_END[:4]}")
```

**To:**
```python
print(f"Baseline: 1981-2010 (30 years)")
print(f"Future periods: {', '.join(FUTURE_PERIODS.keys())}")
```

### 5. Update summary output in `process_anp()` (around line 318)

**Change the summary to show one period (or loop through all):**

```python
if projections.get('data_available'):
    ssp245 = projections.get('scenarios', {}).get('ssp245', {})
    # Show mid-century as representative
    mid_century = ssp245.get('2041-2070', {})
    temp_change = mid_century.get('temperature', {}).get('change_c')
    precip_change = mid_century.get('precipitation', {}).get('change_percent')
    if temp_change is not None and precip_change is not None:
        print(f"    Summary (SSP2-4.5, 2041-2070): Temp +{temp_change}°C, Precip {precip_change:+.1f}%")
    else:
        print("    Data extracted")
```

## New Output Structure

After these changes, the output in `anp_data/{anp}_data.json` will be:

```json
{
  "datasets": {
    "climate_projections": {
      "source": "NASA NEX-GDDP-CMIP6",
      "baseline_period": "1981-2010",
      "future_periods": ["2011-2040", "2041-2070", "2071-2100"],
      "scenarios": {
        "ssp245": {
          "2011-2040": {
            "temperature": {"baseline_mean_c": 22.5, "future_mean_c": 23.7, "change_c": 1.2},
            "precipitation": {...},
            "heat_stress": {...},
            "drought_indicators": {...}
          },
          "2041-2070": {...},
          "2071-2100": {...}
        },
        "ssp585": {
          "2011-2040": {...},
          "2041-2070": {...},
          "2071-2100": {...}
        }
      }
    }
  }
}
```

## Testing

After making changes:

```bash
# Test with one ANP first
python add_climate_projections.py "sierra_gorda" --force

# Verify the output structure
python -c "import json; d=json.load(open('anp_data/sierra_gorda_data.json')); print(json.dumps(d['datasets']['climate_projections'], indent=2))"

# If successful, run on all 6 test ANPs
python add_climate_projections.py "alto_golfo" --force
python add_climate_projections.py "arrecife_alacranes" --force
python add_climate_projections.py "arrecife_de_puerto_morelos" --force
python add_climate_projections.py "calakmul" --force
python add_climate_projections.py "sierra_gorda_de_guanajuato" --force
```

## Important Notes

1. **Use `--force`** flag to re-extract since these ANPs may already have the old format data
2. **GEE rate limits** - the script already has 1-second delays between ANPs
3. **Extraction time** - 3 periods x 2 scenarios = 6x more API calls, expect ~2-3 min per ANP
4. **Historical data** - baseline period uses `scenario='historical'`, same for all future scenarios

## Dashboard Update Required

After updating the script, the dashboard (`index.html`) will also need updates to display the new 3-period structure. The current dashboard expects a single `future_period`, not three.

## Summary of Changes

| Aspect | Before | After |
|--------|--------|-------|
| Baseline | 2005-2014 (10 years) | 1981-2010 (30 years) |
| Future | Single: 2055-2064 | Three: 2011-2040, 2041-2070, 2071-2100 |
| Output structure | Flat by scenario | Nested by scenario AND period |
| Alignment | Arbitrary | Matches climateinformation.org |
