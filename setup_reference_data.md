# Reference Data Setup

Some large reference data files are not included in the git repository to keep it lightweight. The dashboard works without these files, but they're required if you want to regenerate census or poverty data.

## Quick Start

**Dashboard only?** No action needed - `anp_data/` contains all pre-extracted data.

**Re-running extraction scripts?** Follow the instructions below.

---

## INEGI Census Data (ITER 2020)

**Size:** ~138 MB (32 CSV files, one per state)  
**Used by:** `update_census_data.py`, `extract_external_data.py`, `add_coneval_poverty.py`

### Download Steps

1. Go to: https://www.inegi.org.mx/programas/ccpv/2020/
2. Click "Microdatos" tab
3. Download "Integración Territorial (ITER)" for each state
4. Extract CSVs to `reference_data/`

Files should be named: `ITER_01CSV20.csv` through `ITER_32CSV20.csv`

### State Codes Reference

| Code | State | Code | State |
|------|-------|------|-------|
| 01 | Aguascalientes | 17 | Morelos |
| 02 | Baja California | 18 | Nayarit |
| 03 | Baja California Sur | 19 | Nuevo León |
| 04 | Campeche | 20 | Oaxaca |
| 05 | Coahuila | 21 | Puebla |
| 06 | Colima | 22 | Querétaro |
| 07 | Chiapas | 23 | Quintana Roo |
| 08 | Chihuahua | 24 | San Luis Potosí |
| 09 | Ciudad de México | 25 | Sinaloa |
| 10 | Durango | 26 | Sonora |
| 11 | Guanajuato | 27 | Tabasco |
| 12 | Guerrero | 28 | Tamaulipas |
| 13 | Hidalgo | 29 | Tlaxcala |
| 14 | Jalisco | 30 | Veracruz |
| 15 | Estado de México | 31 | Yucatán |
| 16 | Michoacán | 32 | Zacatecas |

### Verify Installation

```bash
ls reference_data/ITER_*CSV20.csv | wc -l
# Should output: 32
```

---

## CONEVAL Social Lag Index (Optional)

**Size:** ~2.5 MB  
**Used by:** `add_coneval_poverty.py`

### Download Steps

1. Go to: https://www.coneval.org.mx/Medicion/IRS/Paginas/Indice_Rezago_Social_2020.aspx
2. Download "Índice de Rezago Social 2020" ZIP file
3. Save to `reference_data/coneval_rezago_social_2020.zip`

Note: The extracted Excel files in `reference_data/coneval_irs/` are already included in the repository.

---

## Files Already Included

These reference files ARE tracked in git (small enough to include):

- `reference_data/official_anp_list.json` - Authoritative ANP list
- `reference_data/simec_*.xlsx` - SIMEC NOM-059 species data
- `reference_data/simec_anp_list.json` - SIMEC ANP name mappings
- `reference_data/coneval_irs/*.xlsx` - CONEVAL IRS Excel files
- `reference_data/manifest.json` - Data source documentation
- `reference_data/iter_descriptor.csv` - ITER field descriptions

---

## Troubleshooting

### Scripts fail with "file not found"

The extraction scripts handle missing ITER files gracefully - they'll skip census data extraction and continue with other data sources. Check script output for specific warnings.

### Need specific state data only

You don't need all 32 ITER files. Download only the states that overlap with ANPs you're updating. Check which states an ANP spans using its bounding box coordinates.
