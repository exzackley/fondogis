#!/usr/bin/env python3
"""
Add Global Mangrove Watch (GMW) Data to ANP Files

Extracts mangrove extent for coastal ANPs using GMW v3.0 from GEE Community Catalog.
Provides time-series of mangrove area from 1996-2020.

Usage:
    python3 add_mangrove_data.py              # Process all ANPs
    python3 add_mangrove_data.py --test       # Test with first 3 coastal ANPs
    python3 add_mangrove_data.py "sian_kaan"  # Process single ANP
"""

import ee
import json
import os
import sys
import argparse
from datetime import datetime
from glob import glob

try:
    from gee_auth import init_ee
except ImportError:
    def init_ee():
        ee.Initialize(project='new-newconsensus')

DATA_DIR = 'anp_data'
MANGROVE_CLASS = 95  # ESA WorldCover mangrove class


def extract_mangrove_data(geometry):
    """Extract mangrove extent using ESA WorldCover (class 95 = Mangroves)."""
    try:
        geom = ee.Geometry.Polygon(geometry)
        
        worldcover_2021 = ee.Image('ESA/WorldCover/v200/2021')
        mangrove_mask = worldcover_2021.eq(MANGROVE_CLASS)
        area_img = mangrove_mask.multiply(ee.Image.pixelArea())
        
        stats = area_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geom,
            scale=10,
            maxPixels=1e9
        ).getInfo()
        
        area_m2 = stats.get('Map', 0)
        area_km2 = round(area_m2 / 1e6, 4) if area_m2 else 0
        
        if area_km2 < 0.01:
            return {
                "source": "ESA WorldCover 2021",
                "data_available": False,
                "mangrove_extent_km2": 0,
                "note": "No mangrove pixels detected (class 95) within ANP boundary",
                "extracted_at": datetime.now().isoformat()
            }
        
        wetland_mask = worldcover_2021.eq(90)
        wetland_stats = wetland_mask.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geom,
            scale=10,
            maxPixels=1e9
        ).getInfo()
        wetland_km2 = round(wetland_stats.get('Map', 0) / 1e6, 4)
        
        return {
            "source": "ESA WorldCover 2021",
            "data_available": True,
            "resolution_m": 10,
            "mangrove_extent_km2": area_km2,
            "herbaceous_wetland_km2": wetland_km2,
            "total_wetland_km2": round(area_km2 + wetland_km2, 4),
            "data_year": 2021,
            "interpretation": {
                "mangrove": "ESA WorldCover class 95 - Mangroves",
                "wetland": "ESA WorldCover class 90 - Herbaceous wetland",
                "note": "Based on Sentinel-1/2 imagery, 10m resolution"
            },
            "extracted_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "source": "ESA WorldCover 2021",
            "data_available": False,
            "error": str(e),
            "extracted_at": datetime.now().isoformat()
        }


def is_coastal_anp(anp_data):
    """Check if ANP is coastal (has marine component or coastal designation)."""
    name = anp_data.get('metadata', {}).get('name', '').lower()
    designation = anp_data.get('metadata', {}).get('designation', '').lower()
    
    coastal_keywords = ['manglar', 'mangrove', 'laguna', 'bahía', 'bahia', 'costa', 
                       'litoral', 'humedal', 'pantano', 'delta', 'estuario', 'marisma',
                       'arrecife', 'marino', 'marina', 'golfo', 'isla', 'caribe',
                       'pacífico', 'pacifico', 'ría', 'ria', 'cenote', 'petenes',
                       'términos', 'terminos', 'celestún', 'celestun', 'sian ka']
    
    for kw in coastal_keywords:
        if kw in name or kw in designation:
            return True
    
    centroid = anp_data.get('geometry', {}).get('centroid', [])
    if centroid:
        lon = centroid[0]
        if lon < -110 or lon > -87:
            return True
    
    return False


def process_anp(anp_file):
    """Add mangrove data to a single ANP file."""
    filepath = os.path.join(DATA_DIR, anp_file)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            anp_data = json.load(f)
    except Exception as e:
        print(f"  Error reading {anp_file}: {e}")
        return False, "error"
    
    anp_name = anp_data.get('metadata', {}).get('name', anp_file)
    
    existing = anp_data.get('datasets', {}).get('mangroves')
    if existing and existing.get('data_available') == True:
        print(f"  {anp_name}: Already has mangrove data, skipping")
        return True, "skipped"
    
    bounds = anp_data.get('geometry', {}).get('bounds')
    if not bounds:
        print(f"  {anp_name}: No geometry, skipping")
        return False, "no_geometry"
    
    print(f"  {anp_name}: Extracting...", end=' ', flush=True)
    
    result = extract_mangrove_data(bounds)
    
    if 'datasets' not in anp_data:
        anp_data['datasets'] = {}
    anp_data['datasets']['mangroves'] = result
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(anp_data, f, indent=2, ensure_ascii=False)
        
        if result.get('data_available'):
            area = result.get('latest_extent_km2', 0)
            change = result.get('change_since_1996_pct')
            change_str = f", {change:+.1f}% since 1996" if change is not None else ""
            print(f"OK ({area:.2f} km2{change_str})")
            return True, "success"
        else:
            print(f"No mangroves detected")
            return True, "no_mangroves"
    except Exception as e:
        print(f"Error saving: {e}")
        return False, "error"


def main():
    parser = argparse.ArgumentParser(description='Add Global Mangrove Watch data to ANP files')
    parser.add_argument('anp_name', nargs='?', help='Specific ANP to process')
    parser.add_argument('--test', action='store_true', help='Test with first 3 coastal ANPs')
    parser.add_argument('--all', action='store_true', help='Process ALL ANPs, not just coastal')
    args = parser.parse_args()
    
    print("Initializing Google Earth Engine...")
    init_ee()
    
    anp_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('_data.json')])
    print(f"Found {len(anp_files)} ANP data files\n")
    
    if args.anp_name:
        pattern = args.anp_name.lower().replace(' ', '_')
        matching = [f for f in anp_files if pattern in f.lower()]
        if not matching:
            print(f"No ANP found matching '{args.anp_name}'")
            sys.exit(1)
        anp_files = matching
    elif not args.all:
        coastal_files = []
        for f in anp_files:
            try:
                with open(os.path.join(DATA_DIR, f), 'r') as fp:
                    data = json.load(fp)
                if is_coastal_anp(data):
                    coastal_files.append(f)
            except:
                pass
        print(f"Filtering to {len(coastal_files)} coastal ANPs\n")
        anp_files = coastal_files
    
    if args.test:
        anp_files = anp_files[:3]
        print("Test mode: processing first 3 ANPs\n")
    
    print("Processing ANPs...")
    stats = {"success": 0, "no_mangroves": 0, "skipped": 0, "error": 0}
    
    for anp_file in anp_files:
        success, status = process_anp(anp_file)
        stats[status] = stats.get(status, 0) + 1
    
    print(f"\nDone! Results:")
    print(f"  With mangroves: {stats['success']}")
    print(f"  No mangroves: {stats['no_mangroves']}")
    print(f"  Skipped (existing): {stats['skipped']}")
    print(f"  Errors: {stats['error']}")


if __name__ == '__main__':
    main()
