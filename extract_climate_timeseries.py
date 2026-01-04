#!/usr/bin/env python3
import ee
import json
import sys
from datetime import datetime

try:
    from gee_auth import init_ee
except ImportError:
    def init_ee():
        ee.Initialize(project='gen-lang-client-0866285082')

CMIP6_COLLECTION = 'NASA/GDDP-CMIP6'
MODEL = 'ACCESS-CM2'
GRID_RESOLUTION_DEG = 0.05  # ~5.5km

HISTORICAL_YEARS = list(range(1980, 2015, 5))
FUTURE_YEARS = list(range(2020, 2100, 5))


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


def main():
    anp_file = sys.argv[1] if len(sys.argv) > 1 else 'anp_data/sierra_gorda_data.json'
    
    print(f"Loading {anp_file}...")
    with open(anp_file) as f:
        anp_data = json.load(f)
    
    name = anp_data['metadata']['name']
    bounds = anp_data['geometry']['bounds']
    
    boundary_file = anp_file.replace('_data.json', '_boundary.geojson')
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
    
    init_ee()
    print("GEE initialized")
    
    points, bbox = create_grid_points(bounds, GRID_RESOLUTION_DEG, polygon)
    print(f"Created grid: {len(points)} points inside ANP at {GRID_RESOLUTION_DEG}° resolution")
    print(f"Bounding box: {bbox}")
    
    result = {
        "anp_name": name,
        "model": MODEL,
        "scenario": "ssp245",
        "grid_resolution_deg": GRID_RESOLUTION_DEG,
        "bbox": {"min_lon": bbox[0], "min_lat": bbox[1], "max_lon": bbox[2], "max_lat": bbox[3]},
        "points": points,
        "years": {},
        "extracted_at": datetime.now().isoformat()
    }
    
    all_years = []
    
    print(f"\nExtracting historical years (1980-2010)...")
    for year in HISTORICAL_YEARS:
        print(f"  {year}...", end=" ", flush=True)
        try:
            temps = extract_year_temperatures(year, points, 'historical')
            result["years"][str(year)] = temps
            all_years.append(year)
            valid = len([t for t in temps if t is not None])
            print(f"OK ({valid}/{len(points)} points)")
        except Exception as e:
            print(f"ERROR: {e}")
    
    print(f"\nExtracting future years (2020-2095, SSP2-4.5)...")
    for year in FUTURE_YEARS:
        print(f"  {year}...", end=" ", flush=True)
        try:
            temps = extract_year_temperatures(year, points, 'ssp245')
            result["years"][str(year)] = temps
            all_years.append(year)
            valid = len([t for t in temps if t is not None])
            print(f"OK ({valid}/{len(points)} points)")
        except Exception as e:
            print(f"ERROR: {e}")
    
    slug = name.lower().replace(' ', '_').replace("'", "")
    output_file = f"anp_data/{slug}_climate_timeseries.json"
    
    with open(output_file, 'w') as f:
        json.dump(result, f)
    
    print(f"\n=== COMPLETE ===")
    print(f"Saved to: {output_file}")
    print(f"Years: {min(all_years)} - {max(all_years)}")
    print(f"Grid points: {len(points)}")
    
    if result["years"]:
        first_year = str(all_years[0])
        last_year = str(all_years[-1])
        first_temps = [t for t in result["years"][first_year] if t]
        last_temps = [t for t in result["years"][last_year] if t]
        if first_temps and last_temps:
            print(f"\nTemperature change:")
            print(f"  {first_year} mean: {sum(first_temps)/len(first_temps):.1f}°C")
            print(f"  {last_year} mean: {sum(last_temps)/len(last_temps):.1f}°C")
            print(f"  Change: +{sum(last_temps)/len(last_temps) - sum(first_temps)/len(first_temps):.1f}°C")


if __name__ == '__main__':
    main()
