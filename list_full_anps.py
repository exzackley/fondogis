
import ee
import sys

# Use shared auth helper
try:
    from gee_auth import init_ee
except ImportError:
    def init_ee():
        ee.Initialize(project='new-newconsensus')

def list_all():
    init_ee()
    print("Listing ALL ANPs...")
    wdpa = ee.FeatureCollection('WCMC/WDPA/current/polygons')
    mexico = wdpa.filter(ee.Filter.eq('ISO3', 'MEX'))
    
    # Filter for federal designations to reduce noise if needed, but let's get all
    federal_filter = ee.Filter.Or(
        ee.Filter.eq('DESIG', 'Reserva de la Biósfera'),
        ee.Filter.eq('DESIG', 'Parque Nacional'),
        ee.Filter.eq('DESIG', 'Monumento Natural'),
        ee.Filter.eq('DESIG', 'Área de Protección de Recursos Naturales'),
        ee.Filter.eq('DESIG', 'Área de Protección de Flora y Fauna'),
        ee.Filter.eq('DESIG', 'Santuario')
    )
    federal_anps = mexico.filter(federal_filter)
    
    # Get all names list
    names = federal_anps.aggregate_array('NAME').getInfo()
    names = sorted(list(set(names)))
    
    print(f"Total found: {len(names)}")
    for name in names:
        print(name)

if __name__ == '__main__':
    list_all()
