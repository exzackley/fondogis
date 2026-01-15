#!/usr/bin/env python3
"""
Add New Protected Area to Dashboard
=====================================

Usage:
    python3 add_anp.py "Sian Ka'an"
    python3 add_anp.py "Mariposa Monarca"
    python3 add_anp.py --list  # Show available ANPs

This extracts all GEE data for the specified ANP and adds it to the dashboard.
"""

import ee
import json
import sys
import os
from datetime import datetime

# Use shared auth helper
try:
    from gee_auth import init_ee
except ImportError:
    def init_ee():
        ee.Initialize(project='gen-lang-client-0866285082')

# Use central ANP registry
try:
    from anp_registry import get_all_anps, get_anps_by_category, get_anp_count, get_category_counts
    HAS_REGISTRY = True
except ImportError:
    HAS_REGISTRY = False

# Database support (optional but recommended)
try:
    from db.db_utils import save_anp_data, export_anp_to_json, test_connection
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False

DATA_DIR = 'anp_data'
INDEX_FILE = 'anp_index.json'


def init():
    init_ee()


def get_anp_by_name(name_search):
    """Search for ANP by name in WDPA."""
    wdpa = ee.FeatureCollection('WCMC/WDPA/current/polygons')
    return wdpa.filter(ee.Filter.eq('ISO3', 'MEX')) \
               .filter(ee.Filter.stringContains('NAME', name_search))


def list_mexican_anps():
    """List FEDERAL Mexican ANPs from central registry (or WDPA fallback)."""
    print("\n" + "=" * 70)
    print("FEDERAL Mexican Protected Areas (CONANP)")
    print("=" * 70)
    
    # Use central registry if available (fast, authoritative)
    if HAS_REGISTRY:
        total = get_anp_count()
        counts = get_category_counts()
        
        print(f"\nTotal Federal ANPs: {total}")
        print("(Source: official_anp_list.json - CONANP registry)\n")
        
        # Category display order and full names
        categories = [
            ('PN', 'Parque Nacional'),
            ('RB', 'Reserva de la Biósfera'),
            ('APFF', 'Área de Protección de Flora y Fauna'),
            ('Sant', 'Santuario'),
            ('APRN', 'Área de Protección de Recursos Naturales'),
            ('MN', 'Monumento Natural')
        ]
        
        for abbrev, full_name in categories:
            cat_anps = get_anps_by_category(abbrev)
            cat_count = len(cat_anps)
            print(f"\n{abbrev} - {full_name} ({cat_count}):")
            # Show first 10
            for anp in cat_anps[:10]:
                print(f"    {anp['name']}")
            if cat_count > 10:
                print(f"    ... and {cat_count - 10} more")
    else:
        # Fallback to GEE query (slow)
        print("\n(Note: anp_registry.py not found, querying GEE directly...)\n")
        wdpa = ee.FeatureCollection('WCMC/WDPA/current/polygons')
        mexico = wdpa.filter(ee.Filter.eq('ISO3', 'MEX'))
        
        federal_filter = ee.Filter.Or(
            ee.Filter.eq('DESIG', 'Reserva de la Biósfera'),
            ee.Filter.eq('DESIG', 'Parque Nacional'),
            ee.Filter.eq('DESIG', 'Monumento Natural'),
            ee.Filter.eq('DESIG', 'Área de Protección de Recursos Naturales'),
            ee.Filter.eq('DESIG', 'Área de Protección de Flora y Fauna'),
            ee.Filter.eq('DESIG', 'Santuario')
        )
        
        federal_anps = mexico.filter(federal_filter)
        count = federal_anps.size().getInfo()
        
        print(f"\nTotal Federal ANPs: {count}")
        print("(CONANP officially reports 232)\n")
        
        categories = [
            ('Reserva de la Biósfera', 'RB'),
            ('Parque Nacional', 'PN'),
            ('Área de Protección de Flora y Fauna', 'APFF'),
            ('Santuario', 'SANT'),
            ('Monumento Natural', 'MN'),
            ('Área de Protección de Recursos Naturales', 'APRN')
        ]
        
        for desig, abbrev in categories:
            filtered = federal_anps.filter(ee.Filter.eq('DESIG', desig))
            cat_count = filtered.size().getInfo()
            print(f"\n{abbrev} - {desig} ({cat_count}):")
            names = filtered.limit(10).aggregate_array('NAME').getInfo()
            for name in sorted(names):
                print(f"    {name}")
            if cat_count > 10:
                print(f"    ... and {cat_count - 10} more")
    
    print("\n" + "=" * 70)
    print("Usage: python3 add_anp.py \"<name>\"")
    print("Example: python3 add_anp.py \"Montes Azules\"")
    print("=" * 70)


def safe_reduce(image, geometry, scale, reducer=None):
    """Safely reduce an image over a geometry."""
    if reducer is None:
        reducer = ee.Reducer.mean()
    try:
        result = image.reduceRegion(
            reducer=reducer,
            geometry=geometry,
            scale=scale,
            maxPixels=1e9
        ).getInfo()
        return result
    except Exception as e:
        return {"error": str(e)}


def extract_boundary_geojson(anp_feature):
    """Extract boundary as GeoJSON."""
    return anp_feature.getInfo()


def extract_all_data(anp_feature):
    """Extract all available data for the ANP."""
    
    geom = anp_feature.geometry()
    props = anp_feature.getInfo()['properties']
    
    data = {
        "metadata": {
            "name": props.get('NAME'),
            "original_name": props.get('ORIG_NAME'),
            "designation": props.get('DESIG'),
            "designation_type": props.get('DESIG_TYPE'),
            "iucn_category": props.get('IUCN_CAT'),
            "status": props.get('STATUS'),
            "status_year": props.get('STATUS_YR'),
            "governance": props.get('GOV_TYPE'),
            "management_authority": props.get('MANG_AUTH'),
            "reported_area_km2": props.get('REP_AREA'),
            "marine": props.get('MARINE'),
            "country": props.get('ISO3'),
            "wdpa_id": props.get('WDPAID'),
            "extracted_at": datetime.now().isoformat()
        },
        "geometry": {
            "centroid": geom.centroid().coordinates().getInfo(),
            "bounds": geom.bounds().coordinates().getInfo()[0],
            "area_m2": geom.area().getInfo()
        },
        "datasets": {}
    }
    
    datasets = data["datasets"]
    
    # 1. POPULATION
    print("    Population (WorldPop)...", end=" ", flush=True)
    try:
        worldpop = ee.ImageCollection('WorldPop/GP/100m/pop').filter(ee.Filter.eq('country', 'MEX'))
        pop_2015 = worldpop.filter(ee.Filter.eq('year', 2015)).first()
        pop_2020 = worldpop.filter(ee.Filter.eq('year', 2020)).first()
        datasets["population"] = {
            "source": "WorldPop Global Project",
            "resolution": "100m",
            "year_2015": safe_reduce(pop_2015, geom, 100, ee.Reducer.sum()),
            "year_2020": safe_reduce(pop_2020, geom, 100, ee.Reducer.sum()),
        }
        print("OK")
    except Exception as e:
        datasets["population"] = {"error": str(e)}
        print("ERROR")
    
    # 2. ELEVATION
    print("    Elevation (SRTM)...", end=" ", flush=True)
    try:
        srtm = ee.Image('USGS/SRTMGL1_003')
        elev_stats = srtm.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.min(), '', True)
                                     .combine(ee.Reducer.max(), '', True)
                                     .combine(ee.Reducer.stdDev(), '', True),
            geometry=geom, scale=30, maxPixels=1e9
        ).getInfo()
        datasets["elevation"] = {
            "source": "SRTM Digital Elevation Model",
            "resolution": "30m",
            "mean_meters": elev_stats.get('elevation_mean'),
            "min_meters": elev_stats.get('elevation_min'),
            "max_meters": elev_stats.get('elevation_max'),
            "std_dev": elev_stats.get('elevation_stdDev')
        }
        print("OK")
    except Exception as e:
        datasets["elevation"] = {"error": str(e)}
        print("ERROR")
    
    # 3. LAND COVER
    print("    Land Cover (ESA WorldCover)...", end=" ", flush=True)
    try:
        worldcover = ee.Image('ESA/WorldCover/v200/2021')
        area_image = ee.Image.pixelArea().addBands(worldcover)
        areas = area_image.reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName='class'),
            geometry=geom, scale=10, maxPixels=1e9
        ).getInfo()
        
        class_names = {
            10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland",
            50: "Built-up", 60: "Bare/sparse vegetation", 70: "Snow and ice",
            80: "Permanent water bodies", 90: "Herbaceous wetland", 95: "Mangroves", 100: "Moss and lichen"
        }
        
        land_cover = {}
        for group in areas.get('groups', []):
            class_id = group['class']
            area_m2 = group['sum']
            class_name = class_names.get(class_id, f"Class {class_id}")
            land_cover[class_name] = {"class_id": class_id, "area_km2": round(area_m2 / 1e6, 2)}
        
        datasets["land_cover"] = {"source": "ESA WorldCover 2021", "resolution": "10m", "classes": land_cover}
        print("OK")
    except Exception as e:
        datasets["land_cover"] = {"error": str(e)}
        print("ERROR")
    
    # 4. FOREST
    print("    Forest (Hansen)...", end=" ", flush=True)
    try:
        hansen = ee.Image('UMD/hansen/global_forest_change_2023_v1_11')
        tree_cover_2000 = hansen.select('treecover2000')
        loss = hansen.select('loss')
        gain = hansen.select('gain')
        loss_year = hansen.select('lossyear')
        
        tc_stats = tree_cover_2000.reduceRegion(reducer=ee.Reducer.mean(), geometry=geom, scale=30, maxPixels=1e9).getInfo()
        loss_area = loss.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=geom, scale=30, maxPixels=1e9).getInfo()
        gain_area = gain.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=geom, scale=30, maxPixels=1e9).getInfo()
        
        loss_by_year = {}
        for year in range(1, 24):
            year_mask = loss_year.eq(year)
            year_loss = year_mask.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=geom, scale=30, maxPixels=1e9).getInfo()
            loss_km2 = year_loss.get('lossyear', 0) / 1e6
            if loss_km2 > 0:
                loss_by_year[f"20{year:02d}"] = round(loss_km2, 2)
        
        datasets["forest"] = {
            "source": "Hansen Global Forest Change v1.11", "resolution": "30m",
            "tree_cover_2000_percent": tc_stats.get('treecover2000'),
            "total_loss_km2": round(loss_area.get('loss', 0) / 1e6, 2),
            "total_gain_km2": round(gain_area.get('gain', 0) / 1e6, 2),
            "loss_by_year": loss_by_year
        }
        print("OK")
    except Exception as e:
        datasets["forest"] = {"error": str(e)}
        print("ERROR")
    
    # 5. CLIMATE
    print("    Climate (TerraClimate)...", end=" ", flush=True)
    try:
        terraclimate = ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE').filter(ee.Filter.date('2020-01-01', '2020-12-31'))
        annual_precip = terraclimate.select('pr').sum()
        annual_temp = terraclimate.select('tmmx').mean()
        annual_temp_min = terraclimate.select('tmmn').mean()
        
        precip_stats = safe_reduce(annual_precip, geom, 4000)
        temp_stats = safe_reduce(annual_temp, geom, 4000)
        temp_min_stats = safe_reduce(annual_temp_min, geom, 4000)
        
        datasets["climate"] = {
            "source": "TerraClimate", "resolution": "4km", "year": 2020,
            "annual_precipitation_mm": precip_stats.get('pr'),
            "mean_max_temp_c": temp_stats.get('tmmx', 0) * 0.1 if temp_stats.get('tmmx') else None,
            "mean_min_temp_c": temp_min_stats.get('tmmn', 0) * 0.1 if temp_min_stats.get('tmmn') else None
        }
        print("OK")
    except Exception as e:
        datasets["climate"] = {"error": str(e)}
        print("ERROR")
    
    # 6. VEGETATION
    print("    Vegetation (MODIS NDVI)...", end=" ", flush=True)
    try:
        modis_ndvi = ee.ImageCollection('MODIS/061/MOD13A2').filter(ee.Filter.date('2020-01-01', '2020-12-31')).select('NDVI')
        mean_ndvi = modis_ndvi.mean().multiply(0.0001)
        ndvi_stats = mean_ndvi.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.min(), '', True).combine(ee.Reducer.max(), '', True),
            geometry=geom, scale=1000, maxPixels=1e9
        ).getInfo()
        datasets["vegetation"] = {
            "source": "MODIS NDVI (MOD13A2)", "resolution": "1km", "year": 2020,
            "mean_ndvi": ndvi_stats.get('NDVI_mean'),
            "min_ndvi": ndvi_stats.get('NDVI_min'),
            "max_ndvi": ndvi_stats.get('NDVI_max')
        }
        print("OK")
    except Exception as e:
        datasets["vegetation"] = {"error": str(e)}
        print("ERROR")
    
    # 7. NIGHT LIGHTS
    print("    Night Lights (VIIRS)...", end=" ", flush=True)
    try:
        viirs = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG').filter(ee.Filter.date('2020-01-01', '2020-12-31')).select('avg_rad')
        mean_lights = viirs.mean()
        lights_stats = mean_lights.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.max(), '', True),
            geometry=geom, scale=500, maxPixels=1e9
        ).getInfo()
        datasets["night_lights"] = {
            "source": "VIIRS Day/Night Band", "resolution": "500m", "year": 2020,
            "mean_radiance": lights_stats.get('avg_rad_mean'),
            "max_radiance": lights_stats.get('avg_rad_max')
        }
        print("OK")
    except Exception as e:
        datasets["night_lights"] = {"error": str(e)}
        print("ERROR")
    
    # 8. FIRE
    print("    Fire History (MODIS)...", end=" ", flush=True)
    try:
        fire_data = {}
        for year in [2019, 2020, 2021, 2022, 2023]:
            burned = ee.ImageCollection('MODIS/061/MCD64A1').filter(ee.Filter.date(f'{year}-01-01', f'{year}-12-31')).select('BurnDate')
            burn_mask = burned.max().gt(0)
            burn_area = burn_mask.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=geom, scale=500, maxPixels=1e9).getInfo()
            fire_data[str(year)] = round(burn_area.get('BurnDate', 0) / 1e6, 2)
        datasets["fire"] = {"source": "MODIS Burned Area (MCD64A1)", "resolution": "500m", "burned_area_km2_by_year": fire_data}
        print("OK")
    except Exception as e:
        datasets["fire"] = {"error": str(e)}
        print("ERROR")
    
    # 9. SOIL
    print("    Soil (OpenLandMap)...", end=" ", flush=True)
    try:
        soil_organic = ee.Image('OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02').select('b0')
        soil_ph = ee.Image('OpenLandMap/SOL/SOL_PH-H2O_USDA-4C1A2A_M/v02').select('b0')
        organic_stats = safe_reduce(soil_organic, geom, 250)
        ph_stats = safe_reduce(soil_ph, geom, 250)
        datasets["soil"] = {
            "source": "OpenLandMap", "resolution": "250m",
            "organic_carbon_g_kg": organic_stats.get('b0'),
            "ph_h2o": ph_stats.get('b0', 0) / 10 if ph_stats.get('b0') else None
        }
        print("OK")
    except Exception as e:
        datasets["soil"] = {"error": str(e)}
        print("ERROR")
    
    # 10. WATER
    print("    Surface Water (JRC)...", end=" ", flush=True)
    try:
        water = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
        occurrence = water.select('occurrence')
        water_mask = occurrence.gt(50)
        water_area = water_mask.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=geom, scale=30, maxPixels=1e9).getInfo()
        datasets["surface_water"] = {
            "source": "JRC Global Surface Water", "resolution": "30m",
            "permanent_water_km2": round(water_area.get('occurrence', 0) / 1e6, 2)
        }
        print("OK")
    except Exception as e:
        datasets["surface_water"] = {"error": str(e)}
        print("ERROR")
    
    # 11. BIODIVERSITY
    print("    Biodiversity (RESOLVE)...", end=" ", flush=True)
    try:
        ecoregions = ee.FeatureCollection('RESOLVE/ECOREGIONS/2017')
        intersecting = ecoregions.filterBounds(geom)
        eco_list = intersecting.aggregate_array('ECO_NAME').getInfo()
        biome_list = intersecting.aggregate_array('BIOME_NAME').getInfo()
        datasets["biodiversity"] = {"source": "RESOLVE Ecoregions 2017", "ecoregions": list(set(eco_list)), "biomes": list(set(biome_list))}
        print("OK")
    except Exception as e:
        datasets["biodiversity"] = {"error": str(e)}
        print("ERROR")
    
    # 12. HUMAN MODIFICATION
    print("    Human Modification...", end=" ", flush=True)
    try:
        hmi = ee.ImageCollection('CSP/HM/GlobalHumanModification').first()
        hmi_stats = hmi.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.max(), '', True),
            geometry=geom, scale=1000, maxPixels=1e9
        ).getInfo()
        datasets["human_modification"] = {
            "source": "Global Human Modification Index", "resolution": "1km",
            "mean_index": hmi_stats.get('gHM_mean'),
            "max_index": hmi_stats.get('gHM_max'),
            "interpretation": "0 = no modification, 1 = completely modified"
        }
        print("OK")
    except Exception as e:
        datasets["human_modification"] = {"error": str(e)}
        print("ERROR")
    
    # 13. WATER STRESS (WRI Aqueduct V4)
    print("    Water Stress (WRI Aqueduct)...", end=" ", flush=True)
    try:
        # WRI Aqueduct V4 is a FeatureCollection (not Image)
        aqueduct = ee.FeatureCollection('WRI/Aqueduct_Water_Risk/V4/baseline_annual')
        intersecting = aqueduct.filterBounds(geom)
        count = intersecting.size().getInfo()
        
        if count == 0:
            datasets["water_stress"] = {
                "source": "WRI Aqueduct Water Risk Atlas V4",
                "data_available": False,
                "note": "No Aqueduct sub-basins intersect this area"
            }
            print("OK (no data)")
        else:
            features = intersecting.getInfo()['features']
            total_area = 0
            weighted_bws = 0
            weighted_drr = 0
            valid_bws = False
            valid_drr = False
            
            for f in features:
                props = f['properties']
                area = props.get('area_km2', 1)
                bws_raw = props.get('bws_raw', -9999)
                drr_raw = props.get('drr_raw', -9999)
                
                if bws_raw != -9999 and bws_raw is not None:
                    weighted_bws += bws_raw * area
                    valid_bws = True
                if drr_raw != -9999 and drr_raw is not None:
                    weighted_drr += drr_raw * area
                    valid_drr = True
                if bws_raw != -9999 or drr_raw != -9999:
                    total_area += area
            
            bws_avg = (weighted_bws / total_area) if valid_bws and total_area > 0 else None
            drr_avg = (weighted_drr / total_area) if valid_drr and total_area > 0 else None
            
            # Categorize BWS
            if bws_avg is not None:
                if bws_avg < 0.1: bws_cat = "Low (<10%)"
                elif bws_avg < 0.2: bws_cat = "Low-Medium (10-20%)"
                elif bws_avg < 0.4: bws_cat = "Medium-High (20-40%)"
                elif bws_avg < 0.8: bws_cat = "High (40-80%)"
                else: bws_cat = "Extremely High (>80%)"
            else:
                bws_cat = None
            
            datasets["water_stress"] = {
                "source": "WRI Aqueduct Water Risk Atlas V4",
                "resolution": "Sub-basin (HydroBASINS level 6)",
                "data_available": valid_bws or valid_drr,
                "sub_basins_count": count,
                "baseline_water_stress": round(bws_avg, 4) if bws_avg else None,
                "baseline_water_stress_category": bws_cat,
                "drought_risk": round(drr_avg, 4) if drr_avg else None,
                "interpretation": {
                    "BWS": "Ratio of water withdrawals to supply. Protected areas may show no data due to minimal human water use.",
                    "DRR": "Probability-weighted drought severity (0-1 scale)."
                }
            }
            print(f"OK (BWS: {bws_avg:.2f})" if bws_avg else "OK")
    except Exception as e:
        datasets["water_stress"] = {"error": str(e)}
        print("ERROR")
    
    return data


def slugify(name):
    """Convert name to file-safe slug."""
    return name.lower().replace(' ', '_').replace("'", '').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n').replace('ü', 'u')


def update_index(anp_id, anp_name, data_file, boundary_file):
    """Update the ANP index file."""
    index = {"anps": []}
    
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE) as f:
            index = json.load(f)
    
    existing_ids = [a['id'] for a in index['anps']]
    if anp_id not in existing_ids:
        index['anps'].append({
            "id": anp_id,
            "name": anp_name,
            "data_file": data_file,
            "boundary_file": boundary_file
        })
        index['anps'].sort(key=lambda x: x['name'])
    
    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=2)
    
    print(f"\n  Updated {INDEX_FILE}")


def add_anp(search_name, use_database=True):
    """Add a new ANP to the dashboard.

    Args:
        search_name: Name to search for in WDPA
        use_database: If True (default), save to PostgreSQL and regenerate JSON.
                      If False, save directly to JSON files (legacy mode).
    """
    print(f"\n{'='*60}")
    print(f"Adding Protected Area: {search_name}")
    print('='*60)

    init()

    # Check database availability
    if use_database and not HAS_DATABASE:
        print("\n  WARNING: Database not available, falling back to JSON-only mode")
        print("  (Install psycopg2-binary and check db/db_utils.py)")
        use_database = False

    if use_database:
        print("  Mode: Database (source of truth) + JSON export")
    else:
        print("  Mode: JSON files only (legacy)")

    print("\n  Searching WDPA...")
    anp_collection = get_anp_by_name(search_name)
    count = anp_collection.size().getInfo()

    if count == 0:
        print(f"\n  ERROR: No ANP found matching '{search_name}'")
        print("  Try: python3 add_anp.py --list")
        return None

    anp = anp_collection.first()
    info = anp.getInfo()
    name = info['properties'].get('NAME', search_name)

    print(f"  Found: {name}")

    os.makedirs(DATA_DIR, exist_ok=True)

    anp_id = slugify(name)
    data_file = f"{DATA_DIR}/{anp_id}_data.json"
    boundary_file = f"{DATA_DIR}/{anp_id}_boundary.geojson"

    print(f"\n  Extracting data (this takes 2-3 minutes)...\n")
    data = extract_all_data(anp)

    print("  Extracting boundary...")
    boundary = {
        "type": "FeatureCollection",
        "features": [extract_boundary_geojson(anp)]
    }

    if use_database:
        # Save to database first
        print("\n  Saving to database...")
        result = save_anp_data(anp_id, data, boundary, source='gee')
        if result['success']:
            print(f"    Saved {result['datasets_saved']} datasets to PostgreSQL")
        else:
            print(f"    ERROR saving to database: {result.get('error')}")
            print("    Falling back to JSON-only mode")
            use_database = False

        # Export from database to JSON
        if use_database:
            print("  Exporting to JSON...")
            export_result = export_anp_to_json(anp_id, DATA_DIR)
            if export_result['success']:
                print(f"    Saved: {export_result['data_file']}")
                if export_result.get('boundary_file'):
                    print(f"    Saved: {export_result['boundary_file']}")
            else:
                print(f"    ERROR exporting JSON: {export_result.get('error')}")

    if not use_database:
        # Legacy JSON-only mode
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n  Saved: {data_file}")

        with open(boundary_file, 'w') as f:
            json.dump(boundary, f)
        print(f"  Saved: {boundary_file}")

    update_index(anp_id, name, data_file, boundary_file)

    print(f"\n{'='*60}")
    print(f"SUCCESS! Added: {name}")
    if use_database:
        print("  (Data saved to database and exported to JSON)")
    print('='*60)

    return anp_id


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 add_anp.py \"<ANP name>\"")
        print("       python3 add_anp.py --list")
        print("       python3 add_anp.py --no-db \"<ANP name>\"  # Skip database, JSON only")
        sys.exit(1)

    args = sys.argv[1:]
    use_database = True

    if '--no-db' in args:
        use_database = False
        args.remove('--no-db')

    if not args:
        print("Error: No ANP name provided")
        sys.exit(1)

    arg = args[0]

    if arg == '--list':
        init()
        list_mexican_anps()
    else:
        add_anp(arg, use_database=use_database)


if __name__ == '__main__':
    main()
