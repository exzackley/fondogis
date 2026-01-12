# Coastal/Marine ANPs Subset

This directory contains tools and data for working with a subset of 39 coastal and marine protected areas (ANPs) in Mexico.

## Quick Start

```python
# Import the coastal ANPs helper
from coastal_anps_registry import (
    get_coastal_anps,           # Get all 39 ANPs with metadata
    get_coastal_anp_ids,        # Get list of IDs
    get_coastal_anps_with_data, # Get 38 IDs that have data
    is_coastal_anp,             # Check if an ID is coastal
    get_coastal_data_file       # Get path to ANP's data file
)

# Example: Generate reports for all coastal ANPs with data
for anp_id in get_coastal_anps_with_data():
    data_file = get_coastal_data_file(anp_id)
    # Generate report using data_file
```

## Files

- `coastal_anps_subset.json` - Complete list of 39 coastal ANPs with metadata
- `coastal_anps_registry.py` - Helper module for accessing coastal ANPs
- `identify_coastal_anps.py` - Script that generated the subset (reusable)

## Summary Statistics

- **Total ANPs**: 39
- **ANPs with data**: 38
- **ANPs missing data**: 1 (Bajos de Coyula II)

### By Category

| Category | Count | Description |
|----------|-------|-------------|
| RB | 9 | Reserva de la Biósfera |
| PN | 5 | Parque Nacional |
| APFF | 9 | Área de Protección de Flora y Fauna |
| Sant | 16 | Santuario |

## Complete List of Coastal ANPs

1. Alto Golfo de California y Delta del Río Colorado (RB)
2. Bajos de Coyula (APFF)
3. Bajos de Coyula II (APFF) ⚠️ *No data - too new for WDPA*
4. Barra de la Cruz-Playa Grande (Sant)
5. Chamela-Cuixmala (RB)
6. El Vizcaíno (RB)
7. Hermenegildo Galeana (Sant)
8. Huatulco (PN)
9. Huatulco II (Sant)
10. La Encrucijada (RB)
11. La porción norte y la franja costera oriental, terrestres y marinas de la Isla de Cozumel (APFF)
12. Laguna de Términos (APFF)
13. Laguna Madre y Delta del Río Bravo (APFF)
14. Lagunas de Chacahua (PN)
15. Los Petenes (RB)
16. Los Tuxtlas (RB)
17. Manglares de Nichupté (APFF)
18. Marismas Nacionales Nayarit (RB)
19. Meseta de Cacaxtla (APFF)
20. Playa Cahuitan (Sant)
21. Playa Chacahua (Sant)
22. Playa Colola (Sant)
23. Playa Cuitzmala (Sant)
24. Playa El Tecuán (Sant)
25. Playa Escobilla (Sant)
26. Playa Huizache Caimanero (Sant)
27. Playa Maruata (Sant)
28. Playa Mexiquillo (Sant)
29. Playa Mismaloya (Sant)
30. Playa Morro Ayuta (Sant)
31. Playa Piedra de Tlacoyunque (Sant)
32. Playa Puerto Arista (Sant)
33. Playa Teopa (Sant)
34. Playa Tierra Colorada (Sant)
35. Ría Lagartos (RB)
36. Ricardo Flores Magón (PN)
37. Sian Ka'an (RB)
38. Tangolunda (Sant)
39. Valle de los Cirios (PN)

## Name Corrections Applied

The identification script automatically corrects common spelling variations:

- "Playa Cuixmala" → "Playa Cuitzmala"
- "Playa Leopa" → "Playa Teopa"

## Missing Data

### Bajos de Coyula II ⚠️

**Status**: Identified in registry but no GEE data available yet

**Reason**: This ANP was decreed on September 26, 2024, making it very new (only 3-4 months old). It hasn't been added to WDPA (World Database on Protected Areas) yet, which is the source for GEE boundary data.

**Details**:
- Area: 2,633 hectares
- Location: Oaxaca
- Category: Área de Protección de Flora y Fauna (APFF)
- Decree: 2024-09-26

**Action**: Wait for WDPA to include this ANP (monthly updates), then run:
```bash
python3 add_anp.py "Bajos de Coyula II"
```

For now, reports about this ANP can reference its sister site "Bajos de Coyula" (decreed Aug 2023, 1,923 ha) which is nearby and has similar characteristics.

## Usage Examples

### Generate Individual Reports

```python
from coastal_anps_registry import get_coastal_anps_with_data, get_coastal_anp_by_id
import json

for anp_id in get_coastal_anps_with_data():
    anp = get_coastal_anp_by_id(anp_id)

    # Load ANP data
    data_file = f"anp_data/{anp['data_file']}"
    with open(data_file) as f:
        data = json.load(f)

    # Generate report
    print(f"Generating report for {anp['matched_name']}...")
    # Your report generation code here
```

### Generate Aggregate Report

```python
from coastal_anps_registry import get_coastal_anps_with_data, get_coastal_summary

summary = get_coastal_summary()

print(f"Aggregate Report: {summary['total']} Coastal ANPs")
print(f"Categories: {summary['categories']}")

# Aggregate statistics across all coastal ANPs
total_area = 0
total_population = 0

for anp_id in get_coastal_anps_with_data():
    data_file = f"anp_data/{anp_id}_data.json"
    with open(data_file) as f:
        data = json.load(f)
        total_area += data['metadata'].get('reported_area_km2', 0)
        # ... aggregate other metrics
```

### Filter by Category

```python
from coastal_anps_registry import get_coastal_anps_by_category

# Generate report for all Santuarios only
santuarios = get_coastal_anps_by_category('Sant')
print(f"Found {len(santuarios)} Santuarios")

for anp in santuarios:
    print(f"  - {anp['matched_name']}")
```

## Data Availability by ANP

All 38 ANPs with data files have the following datasets available:

- **Metadata**: Name, designation, area, IUCN category, governance
- **Geometry**: Centroid, bounds, area
- **GEE Datasets**: Population, elevation, land cover, forest, climate, vegetation, night lights, fire, soil, surface water, biodiversity, human modification
- **External Data**: May include water stress, climate projections, GEDI biomass, mangroves (coastal only), CONEVAL poverty, iNaturalist, GBIF, SIMEC, INEGI Census

Check individual data files to see which optional datasets are available for each ANP.

## Next Steps

1. **Extract missing data** (once Bajos de Coyula II appears in WDPA)
2. **Generate individual reports** for each of 39 ANPs
3. **Generate aggregate report** summarizing all coastal/marine ANPs
4. **Add additional coastal-specific datasets** (e.g., mangrove data, coastal climate indicators)

## Related Documentation

- See `CLAUDE.md` for general project architecture
- See `AGENTS.md` for code patterns and data extraction workflows
- See `data_sources.json` for complete list of available datasets
