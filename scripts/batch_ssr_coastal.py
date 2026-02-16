#!/usr/bin/env python3
"""Batch run SSR climate extraction for all coastal ANPs missing SSR data."""
import json, os, sys, subprocess

subset = json.load(open('coastal_anps_subset.json'))
missing = []
for anp in subset['matched_anps']:
    if anp['id'] not in subset['anp_ids_with_data']:
        continue
    data_file = anp['data_file'].replace('_data.json', '')
    ssr_file = f'anp_data/{data_file}_climate_ssr.json'
    if not os.path.exists(ssr_file):
        missing.append(data_file)

print(f"Processing {len(missing)} coastal ANPs missing SSR data...")
successes = 0
failures = []

for i, slug in enumerate(missing):
    print(f"\n[{i+1}/{len(missing)}] {slug}")
    result = subprocess.run(
        [sys.executable, 'scrape_climate_ssr.py', slug],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0:
        successes += 1
        # Print last few lines of output
        lines = result.stdout.strip().split('\n')
        for line in lines[-3:]:
            print(f"  {line}")
    else:
        failures.append(slug)
        print(f"  FAILED: {result.stderr[-200:] if result.stderr else 'unknown error'}")

print(f"\n{'='*60}")
print(f"DONE: {successes} succeeded, {len(failures)} failed")
if failures:
    print(f"Failed: {', '.join(failures)}")
