#!/usr/bin/env python3
"""
Retry failed climate extractions with longer timeout (60 min instead of 30).
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime

PROGRESS_FILE = '/root/fondogis/climate_extraction_progress.json'
LOG_FILE = '/root/fondogis/climate_extraction.log'

def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')

def main():
    # Load progress
    with open(PROGRESS_FILE) as f:
        progress = json.load(f)
    
    failed = progress['failed']
    log("=" * 60)
    log(f"RETRYING {len(failed)} FAILED ANPs (60 min timeout)")
    log("=" * 60)
    
    newly_completed = []
    still_failed = []
    
    for i, anp in enumerate(failed, 1):
        log(f"[{i}/{len(failed)}] {anp}: Starting extraction (60 min timeout)...")
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ['/root/fondogis/venv/bin/python', '/root/fondogis/add_climate_projections.py', '--force', anp],
                capture_output=True,
                text=True,
                timeout=3600  # 60 minute timeout
            )
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                log(f"[{i}/{len(failed)}] {anp}: SUCCESS ({elapsed:.1f}s)")
                newly_completed.append(anp)
            else:
                log(f"[{i}/{len(failed)}] {anp}: FAILED - Script error ({elapsed:.1f}s)")
                if result.stderr:
                    log(f"  Error: {result.stderr[:200]}")
                still_failed.append(anp)
                
        except subprocess.TimeoutExpired:
            log(f"[{i}/{len(failed)}] {anp}: FAILED - Timeout (>60min)")
            still_failed.append(anp)
        except Exception as e:
            log(f"[{i}/{len(failed)}] {anp}: FAILED - {str(e)}")
            still_failed.append(anp)
        
        time.sleep(2)
    
    # Update progress
    progress['completed'].extend(newly_completed)
    progress['failed'] = still_failed
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)
    
    log("=" * 60)
    log("RETRY COMPLETE")
    log(f"Newly completed: {len(newly_completed)}")
    log(f"Still failed: {len(still_failed)}")
    if still_failed:
        log(f"Still failed ANPs: {', '.join(still_failed)}")
    log("=" * 60)

if __name__ == '__main__':
    main()
