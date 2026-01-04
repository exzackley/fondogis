# Climate Data Collection Methodology

## Overview

This document describes our approach to collecting climate projection data for Mexico's 232 federal protected areas (ANPs). We use two complementary methods to balance accuracy, validation, and spatial detail.

---

## Method 1: Centroid-Based Point Data

### What It Is
Extract climate projections for a single coordinate point (the geographic centroid of each ANP).

### Data Sources
1. **climateinformation.org** - Web scraping of their climate projection interface
2. **Google Earth Engine (NASA GDDP-CMIP6)** - Direct API extraction

### Validation Approach
1. Extract data for **10 test ANPs** from BOTH sources
2. Compare results to verify agreement
3. If values match (within acceptable tolerance), proceed with GEE-only extraction for remaining 222 ANPs
4. If discrepancies exist, investigate and document differences

### Rationale
- **Simple and fast** - one API call per ANP
- **Cross-validation** - two independent sources catch errors
- **Matches common practice** - many climate impact studies use point-based projections
- **Limitations** - doesn't capture spatial variation within large ANPs

### Output
```json
{
  "climate_projections": {
    "method": "centroid_point",
    "centroid": [-99.123, 21.456],
    "source": "NASA GDDP-CMIP6 via GEE",
    "validated_against": "climateinformation.org",
    "baseline_period": "1995-2014",
    "future_period": "2041-2070",
    "scenario": "SSP2-4.5",
    "temperature_change_c": 2.3,
    "precipitation_change_pct": -8.5
  }
}
```

---

## Method 2: Pixel-Based Spatial Data

### What It Is
Create a grid of sample points across the ANP, extract climate data at each point, and calculate area-weighted statistics.

### Technical Details
- **Grid resolution**: 0.05 degrees (~5.5 km pixels)
- **Source data**: NASA GDDP-CMIP6 (native resolution ~0.25 degrees / ~27 km)
- **Interpolation**: GEE applies bilinear interpolation when sampling below native resolution
- **Boundary handling**: Points included if center is inside ANP polygon

### Why Bilinear Interpolation Is Appropriate

The source climate model (CMIP6) runs at ~27 km resolution. We sample at ~5.5 km. This works because:

1. **Spatial autocorrelation**: Climate variables (temperature, precipitation) vary smoothly across space. Neighboring locations have similar values.

2. **Geographic features cluster**: Mountains adjoin mountains, coasts adjoin coasts. If an ANP is in the mountainous corner of a 27 km pixel, neighboring pixels are also mountainous and reflect cooler temperatures. Interpolation naturally captures this.

3. **Better partial-pixel accuracy**: When an ANP covers only part of a native pixel, interpolation provides values specific to that location rather than the pixel-wide average.

**Example:**
```
Scenario: ANP covers mountain portion of mixed-terrain pixel

Native 27km pixel: 24C (averaged across sea level + mountains)
Neighboring mountain pixels: 18C, 19C, 20C

Interpolated value at ANP location: ~20C
(pulled toward cooler neighbors because ANP is spatially near them)

Result: Interpolation gives more accurate value for the actual ANP location
```

### Boundary Pixel Handling

Pixels straddling the ANP boundary are included/excluded based on center point location (binary, not area-weighted). With 5.5 km pixels:

- Edge pixels represent ~5% of total area for typical ANPs
- Error contribution is minimal
- Smaller pixels would reduce this further but with diminishing returns

For official statistics, GEE's `reduceRegion()` function can provide proper fractional pixel weighting if needed.

### Output
```json
{
  "climate_spatial": {
    "method": "interpolated_grid",
    "grid_resolution_deg": 0.05,
    "grid_resolution_km": 5.5,
    "source_resolution_km": 27,
    "num_sample_points": 145,
    "scenario": "SSP2-4.5",
    "baseline_mean_temp_c": 18.5,
    "future_mean_temp_c": 21.2,
    "temperature_change_c": 2.7,
    "spatial_variation": {
      "min_change_c": 2.1,
      "max_change_c": 3.4,
      "std_dev_c": 0.3
    }
  }
}
```

---

## Comparison of Methods

| Aspect | Centroid Point | Pixel Grid |
|--------|---------------|------------|
| Spatial detail | None (single point) | High (captures variation) |
| Computation | Fast | Moderate |
| Validation | Cross-source comparison | Internal consistency |
| Best for | Quick estimates, small ANPs | Large ANPs, spatial analysis |
| Limitations | Misses internal variation | Edge pixel approximation |

---

## Implementation Plan

### Phase 1: Validation (10 ANPs)
1. Select 10 diverse ANPs (varying size, terrain, location)
2. Extract centroid data from climateinformation.org (scraping)
3. Extract centroid data from GEE (CMIP6)
4. Compare and document any discrepancies
5. Determine if GEE-only extraction is sufficient

### Phase 2: Full Extraction
1. If validation passes: Extract centroid data for all 232 ANPs via GEE
2. Extract pixel-grid data for all ANPs via GEE
3. Store both datasets in ANP JSON files

### Phase 3: Dashboard Integration
1. Display centroid-based summary statistics
2. Provide spatial heatmap visualization (pixel data)
3. Show both methods with clear labeling

---

## Data Sources

### NASA GDDP-CMIP6
- **GEE Dataset ID**: `NASA/GDDP-CMIP6`
- **Resolution**: 0.25 degrees (~27 km)
- **Models**: Multiple (we use ACCESS-CM2)
- **Scenarios**: SSP1-2.6, SSP2-4.5, SSP3-7.0, SSP5-8.5
- **Variables**: tas (temperature), pr (precipitation), others
- **Time range**: 1950-2100 (daily)

### climateinformation.org
- **Provider**: Copernicus Climate Change Service
- **Interface**: Web-based point query
- **Use case**: Validation of GEE extractions

---

## Scientific Notes

### What Interpolation Does NOT Do
- It does not add information that isn't in the source data
- It does not know about local elevation, land cover, or microclimates
- It assumes smooth spatial variation (valid for temperature, less so for precipitation extremes)

### What Interpolation DOES Do
- Provides location-specific estimates within native grid cells
- Leverages spatial autocorrelation (nearby values inform estimates)
- Gives more accurate partial-coverage values than raw pixel averages

### When to Use Higher-Resolution Products
For applications requiring true high-resolution climate data (not interpolated), consider:
- NASA NEX-DCP30 (30 arc-second, ~1 km, statistically downscaled)
- CHELSA (30 arc-second, bias-corrected)

These products apply elevation-aware downscaling but have their own assumptions and limitations.

---

## Files

| File | Purpose |
|------|---------|
| `extract_climate_timeseries.py` | Pixel-grid extraction for visualization |
| `add_climate_projections.py` | Summary statistics extraction |
| `climate_heatmap.html` | Spatial visualization dashboard |
| `anp_data/*_climate_timeseries.json` | Pixel-grid data per ANP |

---

## Contact

Questions about this methodology: [Add contact info]

Last updated: January 2025
