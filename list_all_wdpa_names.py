
import ee
import sys
import os

# Initialize EE
try:
    ee.Initialize(project='new-newconsensus')
except:
    try:
        ee.Authenticate()
        ee.Initialize(project='new-newconsensus')
    except Exception as e:
        print(f"Auth failed: {e}")
        sys.exit(1)

# Get WDPA collection
wdpa = ee.FeatureCollection("WCMC/WDPA/current/polygons")
mexico_anps = wdpa.filter(ee.Filter.eq('PARENT_ISO', 'MEX')) \
                  .filter(ee.Filter.neq('STATUS', 'Proposed')) \
                  .filter(ee.Filter.neq('DESIG_ENG', 'Voluntary Conservation Area')) \
                  .filter(ee.Filter.neq('DESIG_ENG', 'State Reserve')) \
                  .filter(ee.Filter.neq('DESIG_ENG', 'Municipal Reserve'))

# Get all names
names = mexico_anps.aggregate_array('NAME').getInfo()
names = sorted(list(set(names))) # Deduplicate

print(f"Total ANPs found in WDPA: {len(names)}")
for name in names:
    print(name)
