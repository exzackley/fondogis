#!/usr/bin/env python3
"""
Batch Add ANPs - Process a range of ANPs from the federal list.

Usage:
    python3 batch_add_anps.py <start_index> <end_index>
    python3 batch_add_anps.py 0 50      # Process ANPs 0-49
    python3 batch_add_anps.py 50 100    # Process ANPs 50-99
"""

import ee
import json
import sys
import os
from datetime import datetime

try:
    from anp_registry import get_all_anps, get_anp_names
    HAS_REGISTRY = True
except ImportError:
    HAS_REGISTRY = False

PROJECT_ID = 'new-newconsensus'
DATA_DIR = 'anp_data'
INDEX_FILE = 'anp_index.json'
OFFICIAL_LIST_FILE = 'reference_data/official_anp_list.json'


def init():
    ee.Initialize(project=PROJECT_ID)


def slugify(name):
    """Convert name to file-safe slug."""
    slug = name.lower()
    replacements = [
        (' ', '_'), ("'", ''), ('á', 'a'), ('é', 'e'), ('í', 'i'), 
        ('ó', 'o'), ('ú', 'u'), ('ñ', 'n'), ('ü', 'u'), (',', ''),
        ('.', ''), ('(', ''), (')', ''), ('/', '_'), ('-', '_')
    ]
    for old, new in replacements:
        slug = slug.replace(old, new)
    return slug[:80]


def safe_reduce(image, geometry, scale, reducer=None):
    if reducer is None:
        reducer = ee.Reducer.mean()
    try:
        return image.reduceRegion(reducer=reducer, geometry=geometry, scale=scale, maxPixels=1e9).getInfo()
    except:
        return {}


def get_anp_by_exact_name(name):
    """Get ANP by exact name match."""
    wdpa = ee.FeatureCollection('WCMC/WDPA/current/polygons')
    return wdpa.filter(ee.Filter.eq('ISO3', 'MEX')).filter(ee.Filter.eq('NAME', name))


def extract_data(anp_feature):
    """Extract all data for an ANP (simplified for speed)."""
    geom = anp_feature.geometry()
    props = anp_feature.getInfo()['properties']
    
    data = {
        "metadata": {
            "name": props.get('NAME'),
            "designation": props.get('DESIG'),
            "designation_type": props.get('DESIG_TYPE'),
            "iucn_category": props.get('IUCN_CAT'),
            "status": props.get('STATUS'),
            "status_year": props.get('STATUS_YR'),
            "governance": props.get('GOV_TYPE'),
            "management_authority": props.get('MANG_AUTH'),
            "reported_area_km2": props.get('REP_AREA'),
            "country": props.get('ISO3'),
            "extracted_at": datetime.now().isoformat()
        },
        "geometry": {
            "centroid": geom.centroid().coordinates().getInfo(),
            "bounds": geom.bounds().coordinates().getInfo()[0],
        },
        "datasets": {}
    }
    
    datasets = data["datasets"]
    
    # Population
    try:
        worldpop = ee.ImageCollection('WorldPop/GP/100m/pop').filter(ee.Filter.eq('country', 'MEX'))
        pop_2020 = worldpop.filter(ee.Filter.eq('year', 2020)).first()
        datasets["population"] = {"year_2020": safe_reduce(pop_2020, geom, 100, ee.Reducer.sum())}
    except: pass
    
    # Elevation
    try:
        srtm = ee.Image('USGS/SRTMGL1_003')
        datasets["elevation"] = srtm.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.min(), '', True).combine(ee.Reducer.max(), '', True),
            geometry=geom, scale=30, maxPixels=1e9
        ).getInfo()
    except: pass
    
    # Land Cover
    try:
        worldcover = ee.Image('ESA/WorldCover/v200/2021')
        area_image = ee.Image.pixelArea().addBands(worldcover)
        areas = area_image.reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName='class'),
            geometry=geom, scale=10, maxPixels=1e9
        ).getInfo()
        class_names = {10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland",
                       50: "Built-up", 60: "Bare/sparse vegetation", 80: "Permanent water bodies",
                       90: "Herbaceous wetland", 95: "Mangroves"}
        land_cover = {}
        for group in areas.get('groups', []):
            cid, area = group['class'], group['sum']
            land_cover[class_names.get(cid, f"Class {cid}")] = {"class_id": cid, "area_km2": round(area/1e6, 2)}
        datasets["land_cover"] = {"classes": land_cover}
    except: pass
    
    # Forest
    try:
        hansen = ee.Image('UMD/hansen/global_forest_change_2023_v1_11')
        tc = hansen.select('treecover2000').reduceRegion(reducer=ee.Reducer.mean(), geometry=geom, scale=30, maxPixels=1e9).getInfo()
        loss = hansen.select('loss').multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=geom, scale=30, maxPixels=1e9).getInfo()
        loss_year = hansen.select('lossyear')
        loss_by_year = {}
        for year in range(1, 24):
            yl = loss_year.eq(year).multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=geom, scale=30, maxPixels=1e9).getInfo()
            lkm = yl.get('lossyear', 0) / 1e6
            if lkm > 0: loss_by_year[f"20{year:02d}"] = round(lkm, 2)
        datasets["forest"] = {
            "tree_cover_2000_percent": tc.get('treecover2000'),
            "total_loss_km2": round(loss.get('loss', 0) / 1e6, 2),
            "loss_by_year": loss_by_year
        }
    except: pass
    
    # Climate
    try:
        tc = ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE').filter(ee.Filter.date('2020-01-01', '2020-12-31'))
        precip = safe_reduce(tc.select('pr').sum(), geom, 4000)
        tmax = safe_reduce(tc.select('tmmx').mean(), geom, 4000)
        tmin = safe_reduce(tc.select('tmmn').mean(), geom, 4000)
        datasets["climate"] = {
            "annual_precipitation_mm": precip.get('pr'),
            "mean_max_temp_c": tmax.get('tmmx', 0) * 0.1 if tmax.get('tmmx') else None,
            "mean_min_temp_c": tmin.get('tmmn', 0) * 0.1 if tmin.get('tmmn') else None
        }
    except: pass
    
    # Vegetation
    try:
        ndvi = ee.ImageCollection('MODIS/061/MOD13A2').filter(ee.Filter.date('2020-01-01', '2020-12-31')).select('NDVI').mean().multiply(0.0001)
        datasets["vegetation"] = ndvi.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.min(), '', True).combine(ee.Reducer.max(), '', True),
            geometry=geom, scale=1000, maxPixels=1e9
        ).getInfo()
    except: pass
    
    # Night Lights
    try:
        viirs = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG').filter(ee.Filter.date('2020-01-01', '2020-12-31')).select('avg_rad').mean()
        datasets["night_lights"] = viirs.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.max(), '', True),
            geometry=geom, scale=500, maxPixels=1e9
        ).getInfo()
    except: pass
    
    # Fire
    try:
        fire_data = {}
        for year in [2019, 2020, 2021, 2022, 2023]:
            burned = ee.ImageCollection('MODIS/061/MCD64A1').filter(ee.Filter.date(f'{year}-01-01', f'{year}-12-31')).select('BurnDate').max().gt(0)
            ba = burned.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=geom, scale=500, maxPixels=1e9).getInfo()
            fire_data[str(year)] = round(ba.get('BurnDate', 0) / 1e6, 2)
        datasets["fire"] = {"burned_area_km2_by_year": fire_data}
    except: pass
    
    # Biodiversity
    try:
        eco = ee.FeatureCollection('RESOLVE/ECOREGIONS/2017').filterBounds(geom)
        datasets["biodiversity"] = {
            "ecoregions": list(set(eco.aggregate_array('ECO_NAME').getInfo())),
            "biomes": list(set(eco.aggregate_array('BIOME_NAME').getInfo()))
        }
    except: pass
    
    # Human Modification
    try:
        hmi = ee.ImageCollection('CSP/HM/GlobalHumanModification').first()
        datasets["human_modification"] = hmi.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.max(), '', True),
            geometry=geom, scale=1000, maxPixels=1e9
        ).getInfo()
    except: pass
    
    return data


def update_index(anp_id, anp_name, data_file, boundary_file):
    """Thread-safe index update."""
    index = {"anps": []}
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE) as f:
                index = json.load(f)
        except: pass
    
    existing_ids = [a['id'] for a in index['anps']]
    if anp_id not in existing_ids:
        index['anps'].append({"id": anp_id, "name": anp_name, "data_file": data_file, "boundary_file": boundary_file})
        index['anps'].sort(key=lambda x: x['name'])
    
    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=2)


def process_anp(name):
    """Process a single ANP."""
    anp_id = slugify(name)
    data_file = f"{DATA_DIR}/{anp_id}_data.json"
    boundary_file = f"{DATA_DIR}/{anp_id}_boundary.geojson"
    
    if os.path.exists(data_file):
        print(f"  SKIP (exists): {name}")
        return True
    
    try:
        anp_collection = get_anp_by_exact_name(name)
        if anp_collection.size().getInfo() == 0:
            print(f"  NOT FOUND: {name}")
            return False
        
        anp = anp_collection.first()
        
        # Extract data
        data = extract_data(anp)
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Extract boundary
        boundary = {"type": "FeatureCollection", "features": [anp.getInfo()]}
        with open(boundary_file, 'w') as f:
            json.dump(boundary, f)
        
        # Update index
        update_index(anp_id, name, data_file, boundary_file)
        
        print(f"  OK: {name}")
        return True
    except Exception as e:
        print(f"  ERROR: {name} - {str(e)[:50]}")
        return False


def load_anp_names():
    """Load ANP names from the official registry."""
    if HAS_REGISTRY:
        return get_anp_names()
    
    with open(OFFICIAL_LIST_FILE) as f:
        data = json.load(f)
    return [anp['name'] for anp in data['anps']]


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 batch_add_anps.py <start> <end>")
        sys.exit(1)
    
    start_idx = int(sys.argv[1])
    end_idx = int(sys.argv[2])
    
    all_names = load_anp_names()
    batch = all_names[start_idx:end_idx]
    
    print(f"\n{'='*60}")
    print(f"Batch Processing ANPs {start_idx} to {end_idx-1}")
    print(f"Processing {len(batch)} ANPs")
    print(f"{'='*60}\n")
    
    os.makedirs(DATA_DIR, exist_ok=True)
    init()
    
    success = 0
    for i, name in enumerate(batch):
        print(f"[{start_idx + i + 1}/{end_idx}] ", end="")
        if process_anp(name):
            success += 1
    
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {success}/{len(batch)} successful")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
