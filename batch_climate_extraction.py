#!/usr/bin/env python3
"""
Batch Climate Extraction Script
Extracts NASA CMIP6 climate projections for all ANPs.
Tracks progress and can be resumed if interrupted.
"""

import json
import os
import sys
import time
from datetime import datetime
from glob import glob

# Add project to path
sys.path.insert(0, '/root/fondogis')

DATA_DIR = '/root/fondogis/anp_data'
PROGRESS_FILE = '/root/fondogis/climate_extraction_progress.json'
LOG_FILE = '/root/fondogis/climate_extraction.log'

def log(message):
    """Log message to file and stdout with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')

def get_all_anp_files():
    """Get all ANP data files sorted alphabetically."""
    files = sorted(glob(f"{DATA_DIR}/*_data.json"))
    return files

def check_has_multi_period(filepath):
    """Check if ANP already has multi-period climate data."""
    try:
        with open(filepath) as f:
            data = json.load(f)
        cp = data.get('datasets', {}).get('climate_projections', {}).get('scenarios', {}).get('ssp245', {})
        return '2041-2070' in cp
    except Exception:
        return False

def load_progress():
    """Load progress tracking file."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'completed': [], 'failed': [], 'skipped': []}

def save_progress(progress):
    """Save progress tracking file."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def extract_climate_for_anp(anp_name):
    """Run climate extraction for a single ANP."""
    import subprocess
    
    cmd = [
        '/root/fondogis/venv/bin/python',
        '/root/fondogis/add_climate_projections.py',
        '--force',
        anp_name
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=1800  # 30 minute timeout per ANP
    )
    
    return result.returncode == 0, result.stdout, result.stderr

def main():
    log("=" * 60)
    log("BATCH CLIMATE EXTRACTION STARTED")
    log("=" * 60)
    
    # Get all ANP files
    all_files = get_all_anp_files()
    log(f"Found {len(all_files)} ANP data files")
    
    # Load progress
    progress = load_progress()
    log(f"Previously completed: {len(progress['completed'])}")
    log(f"Previously failed: {len(progress['failed'])}")
    log(f"Previously skipped: {len(progress['skipped'])}")
    
    # Process each ANP
    total = len(all_files)
    processed = 0
    
    for filepath in all_files:
        anp_name = os.path.basename(filepath).replace('_data.json', '')
        processed += 1
        
        # Skip if already completed
        if anp_name in progress['completed']:
            continue
        
        # Check if already has multi-period data
        if check_has_multi_period(filepath):
            if anp_name not in progress['skipped']:
                log(f"[{processed}/{total}] {anp_name}: Already has multi-period data, skipping")
                progress['skipped'].append(anp_name)
                save_progress(progress)
            continue
        
        # Extract climate data
        log(f"[{processed}/{total}] {anp_name}: Starting extraction...")
        start_time = time.time()
        
        try:
            success, stdout, stderr = extract_climate_for_anp(anp_name)
            elapsed = time.time() - start_time
            
            if success:
                # Verify extraction worked
                if check_has_multi_period(filepath):
                    log(f"[{processed}/{total}] {anp_name}: SUCCESS ({elapsed:.1f}s)")
                    progress['completed'].append(anp_name)
                else:
                    log(f"[{processed}/{total}] {anp_name}: FAILED - No multi-period data after extraction ({elapsed:.1f}s)")
                    progress['failed'].append(anp_name)
            else:
                log(f"[{processed}/{total}] {anp_name}: FAILED - Script error ({elapsed:.1f}s)")
                if stderr:
                    log(f"  Error: {stderr[:200]}")
                progress['failed'].append(anp_name)
                
        except subprocess.TimeoutExpired:
            log(f"[{processed}/{total}] {anp_name}: FAILED - Timeout (>30min)")
            progress['failed'].append(anp_name)
        except Exception as e:
            log(f"[{processed}/{total}] {anp_name}: FAILED - {str(e)}")
            progress['failed'].append(anp_name)
        
        save_progress(progress)
        
        # Rate limiting - wait between extractions
        time.sleep(2)
    
    # Final summary
    log("=" * 60)
    log("BATCH EXTRACTION COMPLETE")
    log(f"Completed: {len(progress['completed'])}")
    log(f"Skipped (already had data): {len(progress['skipped'])}")
    log(f"Failed: {len(progress['failed'])}")
    if progress['failed']:
        log(f"Failed ANPs: {', '.join(progress['failed'][:10])}{'...' if len(progress['failed']) > 10 else ''}")
    log("=" * 60)

if __name__ == '__main__':
    import subprocess
    main()
