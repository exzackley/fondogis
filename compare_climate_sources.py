#!/usr/bin/env python3
import json
import os

DATA_DIR = 'anp_data'

TEST_ANPS = [
    "alto_golfo_de_california_y_delta_del_rio_colorado",
    "arrecife_alacranes",
    "arrecife_de_puerto_morelos", 
    "calakmul",
    "sierra_gorda",
    "sierra_gorda_de_guanajuato"
]

PERIOD_YEARS = {
    "baseline": ["1980", "1985", "1990", "1995", "2000", "2005", "2010"],
    "2011-2040": ["2015", "2020", "2025", "2030", "2035", "2040"],
    "2041-2070": ["2045", "2050", "2055", "2060", "2065", "2070"],
    "2071-2100": ["2075", "2080", "2085", "2090", "2095"]
}


def load_ssr_data(anp_slug):
    filepath = f"{DATA_DIR}/{anp_slug}_climate_ssr.json"
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        return json.load(f)


def load_timeseries_data(anp_slug):
    filepath = f"{DATA_DIR}/{anp_slug}_climate_timeseries.json"
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        return json.load(f)


def calculate_gee_period_average(ts_data, scenario, period):
    if 'scenarios' not in ts_data:
        years_data = ts_data.get('years', {})
        if not years_data:
            return None
    else:
        scenario_data = ts_data.get('scenarios', {}).get(scenario, {})
        years_data = scenario_data.get('years', {})
    
    all_temps = []
    
    for year in PERIOD_YEARS[period]:
        if year in years_data:
            valid = [t for t in years_data[year] if t is not None]
            all_temps.extend(valid)
    
    return sum(all_temps) / len(all_temps) if all_temps else None


def compare_anp(anp_slug):
    ssr = load_ssr_data(anp_slug)
    ts = load_timeseries_data(anp_slug)
    
    if not ssr:
        return {"anp": anp_slug, "error": "No SSR data"}
    if not ts:
        return {"anp": anp_slug, "error": "No timeseries data"}
    
    anp_name = ssr.get('anp_name', anp_slug)
    
    print(f"\n{'='*60}")
    print(f"ANP: {anp_name}")
    print(f"Centroid: {ssr['centroid']['lat']:.4f}, {ssr['centroid']['lon']:.4f}")
    print('='*60)
    
    results = {
        "anp": anp_slug,
        "name": anp_name,
        "comparisons": {}
    }
    
    scenario_map = [
        ("RCP 4.5 vs SSP2-4.5", "rcp45", "ssp245"),
        ("RCP 8.5 vs SSP5-8.5", "rcp85", "ssp585"),
    ]
    
    periods = ["2011-2040", "2041-2070", "2071-2100"]
    
    for label, rcp, ssp in scenario_map:
        print(f"\n{label}:")
        print("-" * 50)
        print(f"{'Period':<15} {'SSR (°C)':<12} {'GEE (°C)':<12} {'Diff (°C)':<10}")
        print("-" * 50)
        
        gee_baseline = calculate_gee_period_average(ts, ssp, 'baseline')
        results["comparisons"][label] = {"baseline_temp": gee_baseline, "periods": {}}
        
        for period in periods:
            ssr_temp = None
            if 'data' in ssr and rcp in ssr['data'] and period in ssr['data'][rcp]:
                ssr_temp = ssr['data'][rcp][period].get('temperature')
            
            gee_future = calculate_gee_period_average(ts, ssp, period)
            gee_change = (gee_future - gee_baseline) if (gee_future and gee_baseline) else None
            
            if ssr_temp is not None and gee_change is not None:
                diff = gee_change - ssr_temp
                print(f"{period:<15} {ssr_temp:<12.2f} {gee_change:<12.2f} {diff:<+10.2f}")
                results["comparisons"][label]["periods"][period] = {
                    "ssr_change": ssr_temp,
                    "gee_change": round(gee_change, 2),
                    "difference": round(diff, 2)
                }
            else:
                ssr_str = f"{ssr_temp:.2f}" if ssr_temp is not None else "N/A"
                gee_str = f"{gee_change:.2f}" if gee_change is not None else "N/A"
                print(f"{period:<15} {ssr_str:<12} {gee_str:<12} {'N/A':<10}")
                results["comparisons"][label]["periods"][period] = {
                    "ssr_change": ssr_temp,
                    "gee_change": round(gee_change, 2) if gee_change else None,
                    "difference": None
                }
    
    return results


def main():
    print("\n" + "="*60)
    print("CLIMATE DATA SOURCE COMPARISON")
    print("climateinformation.org (RCP) vs GEE CMIP6 (SSP)")
    print("="*60)
    
    all_results = []
    
    for anp_slug in TEST_ANPS:
        try:
            result = compare_anp(anp_slug)
            all_results.append(result)
        except Exception as e:
            print(f"\nError processing {anp_slug}: {e}")
            all_results.append({"anp": anp_slug, "error": str(e)})
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    max_diffs = []
    for result in all_results:
        if 'error' in result:
            print(f"{result['anp']}: {result['error']}")
            continue
        
        for comp_name, comp_data in result.get('comparisons', {}).items():
            for period, period_data in comp_data.get('periods', {}).items():
                diff = period_data.get('difference')
                if diff is not None:
                    max_diffs.append(abs(diff))
    
    if max_diffs:
        print(f"\nMax absolute difference: {max(max_diffs):.2f}°C")
        print(f"Mean absolute difference: {sum(max_diffs)/len(max_diffs):.2f}°C")
        
        if max(max_diffs) < 0.5:
            print("\nResult: ACCEPTABLE (<0.5°C threshold)")
        elif max(max_diffs) < 1.0:
            print("\nResult: INVESTIGATE (0.5-1.0°C differences)")
        else:
            print("\nResult: SIGNIFICANT (>1.0°C differences - review data)")
    else:
        print("\nNo valid comparisons available")
    
    print("\n" + "="*60)
    print("Interpretation Guide:")
    print("  < 0.3°C: Excellent agreement")
    print("  0.3-0.5°C: Good agreement (expected)")
    print("  0.5-1.0°C: Moderate difference (investigate)")
    print("  > 1.0°C: Significant difference (problem)")
    print("="*60)
    
    output_file = f"{DATA_DIR}/climate_comparison_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
