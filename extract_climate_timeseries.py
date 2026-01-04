#!/usr/bin/env python3
import ee  # type: ignore
import json
import sys
import os
from datetime import datetime

try:
    from gee_auth import init_ee
except ImportError:
    def init_ee():
        ee.Initialize(project='gen-lang-client-0866285082')
        return True

CMIP6_COLLECTION = 'NASA/GDDP-CMIP6'
MODEL = 'ACCESS-CM2'
GRID_RESOLUTION_DEG = 0.05
DATA_DIR = 'anp_data'

HISTORICAL_YEARS = list(range(1980, 2015, 5))
FUTURE_YEARS = list(range(2015, 2100, 5))

SCENARIOS_TO_EXTRACT = ['ssp245', 'ssp585']

TEST_ANPS = [
    "alto_golfo_de_california_y_delta_del_rio_colorado",
    "arrecife_alacranes",
    "arrecife_de_puerto_morelos",
    "calakmul",
    "sierra_gorda",
    "sierra_gorda_de_guanajuato"
]


def point_in_polygon(point, polygon):
    x, y = point
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def pixel_overlaps_polygon(center, resolution, polygon):
    x, y = center
    half = resolution / 2
    corners = [
        [x - half, y - half], [x + half, y - half],
        [x + half, y + half], [x - half, y + half], [x, y]
    ]
    return any(point_in_polygon(c, polygon) for c in corners)


def create_grid_points(bounds, resolution_deg, polygon=None):
    lons = [p[0] for p in bounds]
    lats = [p[1] for p in bounds]
    
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    
    min_lon -= resolution_deg
    min_lat -= resolution_deg
    max_lon += resolution_deg
    max_lat += resolution_deg
    
    points = []
    lat = min_lat
    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            if polygon is None or pixel_overlaps_polygon([lon, lat], resolution_deg, polygon):
                points.append([lon, lat])
            lon += resolution_deg
        lat += resolution_deg
    
    return points, (min_lon, min_lat, max_lon, max_lat)


def extract_year_temperatures(year, points, scenario):
    cmip6 = ee.ImageCollection(CMIP6_COLLECTION)
    
    year_data = cmip6 \
        .filter(ee.Filter.eq('model', MODEL)) \
        .filter(ee.Filter.eq('scenario', scenario)) \
        .filter(ee.Filter.calendarRange(year, year, 'year')) \
        .select('tas')
    
    annual_mean = year_data.mean()
    
    fc = ee.FeatureCollection([
        ee.Feature(ee.Geometry.Point(p), {'idx': i}) 
        for i, p in enumerate(points)
    ])
    
    sampled = annual_mean.sampleRegions(
        collection=fc,
        scale=27830,
        geometries=False
    )
    
    results = sampled.getInfo()
    
    temps = [None] * len(points)
    for f in results['features']:
        idx = f['properties']['idx']
        tas_k = f['properties'].get('tas')
        if tas_k is not None:
            temps[idx] = round(tas_k - 273.15, 2)
    
    return temps


def process_anp(anp_slug, force=False):
    data_file = f'{DATA_DIR}/{anp_slug}_data.json'
    output_file = f'{DATA_DIR}/{anp_slug}_climate_timeseries.json'
    
    if os.path.exists(output_file) and not force:
        print(f"  Already exists: {output_file}")
        print("  Use --force to re-extract")
        return None
    
    print(f"Loading {data_file}...")
    with open(data_file) as f:
        anp_data = json.load(f)
    
    name = anp_data['metadata']['name']
    bounds = anp_data['geometry']['bounds']
    
    boundary_file = data_file.replace('_data.json', '_boundary.geojson')
    polygon = None
    try:
        with open(boundary_file) as f:
            geojson = json.load(f)
            coords = geojson['features'][0]['geometry']['coordinates'][0]
            polygon = coords
            print(f"Loaded boundary polygon with {len(polygon)} vertices")
    except Exception as e:
        print(f"No boundary file found, using bounding box: {e}")
    
    print(f"\n=== {name} ===")
    
    points, bbox = create_grid_points(bounds, GRID_RESOLUTION_DEG, polygon)
    print(f"Created grid: {len(points)} points inside ANP at {GRID_RESOLUTION_DEG}deg resolution")
    print(f"Bounding box: {bbox}")
    
    result = {
        "anp_name": name,
        "model": MODEL,
        "grid_resolution_deg": GRID_RESOLUTION_DEG,
        "bbox": {"min_lon": bbox[0], "min_lat": bbox[1], "max_lon": bbox[2], "max_lat": bbox[3]},
        "points": points,
        "scenarios": {},
        "extracted_at": datetime.now().isoformat()
    }
    
    for scenario in SCENARIOS_TO_EXTRACT:
        print(f"\n--- Scenario: {scenario} ---")
        result["scenarios"][scenario] = {"years": {}}
        
        print(f"Extracting historical years (1980-2014)...")
        for year in HISTORICAL_YEARS:
            print(f"  {year}...", end=" ", flush=True)
            try:
                temps = extract_year_temperatures(year, points, 'historical')
                result["scenarios"][scenario]["years"][str(year)] = temps
                valid = len([t for t in temps if t is not None])
                print(f"OK ({valid}/{len(points)} points)")
            except Exception as e:
                print(f"ERROR: {e}")
                result["scenarios"][scenario]["years"][str(year)] = [None] * len(points)
        
        print(f"Extracting future years (2015-2095, {scenario})...")
        for year in FUTURE_YEARS:
            print(f"  {year}...", end=" ", flush=True)
            try:
                temps = extract_year_temperatures(year, points, scenario)
                result["scenarios"][scenario]["years"][str(year)] = temps
                valid = len([t for t in temps if t is not None])
                print(f"OK ({valid}/{len(points)} points)")
            except Exception as e:
                print(f"ERROR: {e}")
                result["scenarios"][scenario]["years"][str(year)] = [None] * len(points)
    
    with open(output_file, 'w') as f:
        json.dump(result, f)
    
    print(f"\n=== COMPLETE ===")
    print(f"Saved to: {output_file}")
    print(f"Grid points: {len(points)}")
    print(f"Scenarios: {', '.join(SCENARIOS_TO_EXTRACT)}")
    
    return result


def main():
    force = '--force' in sys.argv
    
    if '--test6' in sys.argv:
        anp_list = TEST_ANPS
    elif len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        anp_list = [sys.argv[1].replace(f'{DATA_DIR}/', '').replace('_data.json', '')]
    else:
        anp_list = TEST_ANPS
    
    print(f"\n{'='*60}")
    print("GEE Climate Timeseries Extraction")
    print(f"Model: {MODEL}")
    print(f"Scenarios: {', '.join(SCENARIOS_TO_EXTRACT)}")
    print(f"ANPs to process: {len(anp_list)}")
    print('='*60)
    
    init_ee()
    print("GEE initialized")
    
    for anp_slug in anp_list:
        print(f"\n{'='*60}")
        print(f"Processing: {anp_slug}")
        print('='*60)
        
        try:
            process_anp(anp_slug, force)
        except FileNotFoundError as e:
            print(f"  Skipping: {e}")
        except Exception as e:
            print(f"  Error processing {anp_slug}: {e}")


if __name__ == '__main__':
    main()
