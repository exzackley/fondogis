# FondoGIS Validation Report

**Generated:** 2026-02-15 19:30:03 UTC
**Database:** fondogis on 172.232.163.60
**JSON Directory:** anp_data/

---
## Executive Summary

- **ANPs in DB:** 227
- **ANPs in JSON:** 227
- **ANPs in both:** 227
- **In DB only:** 0
- **In JSON only:** 0
- **ANPs with dataset coverage mismatches:** 0
- **Dataset rows with errors:** 190
- **Dataset rows with data_available=false:** 78
- **Empty dataset blobs:** 0
- **Full-coverage dataset types (227/227):** 11
- **Area discrepancies >10%:** 18
- **Marine-dominated ANPs (>95%):** 21
- **Marine ANPs with terrestrial data:** 57
- **Implausible pop density >500/km²:** 14

---
## 1. DB ↔ JSON Parity Check

### ✅ All DB ANPs have corresponding JSON files

### ✅ All JSON ANPs exist in DB


### Dataset Coverage Mismatches (0 ANPs)

✅ All ANPs have matching dataset coverage between DB and JSON.


### Deep Comparison (Sample of 7 ANPs)


#### `bajos_de_coyula` — ✅ Perfect match


#### `c.a.d.n.r._001_pabellon` — ✅ Perfect match


#### `bonampak` — ✅ Perfect match


#### `arrecife_alacranes` — ✅ Perfect match


#### `alto_golfo_de_california_y_delta_del_rio_colorado` — ✅ Perfect match


#### `barra_de_la_cruz_playa_grande` — ✅ Perfect match


#### `calakmul` — ✅ Perfect match


---
## 2. Missing Data Audit

**Total ANPs:** 227

**Full coverage (all 227 ANPs):** biodiversity, climate, climate_projections, elevation, fire, forest, human_modification, night_lights, population, vegetation, water_stress


### land_cover — 223/227 (4 missing)

**Pattern:** By category: {'Reserva de la Biosfera': 2, 'Área de Protección de Flora y Fauna': 1, 'Parque Nacional': 1}; Marine-dominated: 3/4; Small (<10 km²): 0/4

| ANP ID | Name | Designation | Area km² | Marine % |
|--------|------|-------------|----------|----------|
| `caribe_mexicano` | Caribe Mexicano | Reserva de la Biosfera | 57540.6 | 100% |
| `islas_del_golfo_de_california` | Islas del Golfo de California | Área de Protección de Flora y Fauna | 3147.4 | 0% |
| `pacifico_mexicano_profundo` | Pacífico Mexicano Profundo | Reserva de la Biosfera | 436141.2 | 100% |
| `revillagigedo` | Revillagigedo | Parque Nacional | 148087.8 | 100% |

### inegi_census — 213/227 (14 missing)

**Pattern:** By category: {'Área de Protección de Recursos Naturales': 9, 'Área de Protección de Flora y Fauna': 2, 'Reserva de la Biosfera': 1, 'Santuario': 2}; Marine-dominated: 0/14; Small (<10 km²): 4/14

| ANP ID | Name | Designation | Area km² | Marine % |
|--------|------|-------------|----------|----------|
| `c.a.d.n.r._001_pabellon` | C.A.D.N.R. 001 Pabellón | Área de Protección de Recursos Naturales | 977.0 | 0% |
| `c.a.d.n.r._004_don_martin` | C.A.D.N.R. 004 Don Martín | Área de Protección de Recursos Naturales | 15193.9 | 0% |
| `c.a.d.n.r._026_bajo_rio_san_juan` | C.A.D.N.R. 026 Bajo Río San Juan | Área de Protección de Recursos Naturales | 1971.6 | 0% |
| `c.a.d.n.r._043_estado_de_nayarit` | C.A.D.N.R. 043 Estado de Nayarit | Área de Protección de Recursos Naturales | 23290.3 | 0% |
| `cenote_aerolito` | Cenote Aerolito | Área de Protección de Flora y Fauna | 0.1 | 0% |
| `jacinto_pat` | Jacinto Pat | Área de Protección de Flora y Fauna | 0.2 | 0% |
| `lacan-tun` | Lacan-Tun | Reserva de la Biosfera | 618.7 | 0% |
| `lago_tlahuac-xico` | Lago Tláhuac-Xico | Área de Protección de Recursos Naturales | 35.5 | 0% |
| `las_huertas` | Las Huertas | Área de Protección de Recursos Naturales | 1.7 | 0% |
| `playa_huizache_caimanero` | Playa Huizache Caimanero | Santuario | 482.8 | 0% |
| `playa_teopa` | Playa Teopa | Santuario | 0.3 | 0% |
| `z.p.f._en_los_terrenos_que_se_encuentran_en_los_mpios._de_la_concordia,_angel_albino_corzo,_villa_flores_y_jiquipilas` | Z.P.F. en los terrenos que se encuentran en los mpios. de La Concordia, Ángel Albino Corzo, Villa Flores y Jiquipilas | Área de Protección de Recursos Naturales | 1775.5 | 0% |
| `z.p.f.t.c.c._de_los_rios_valle_de_bravo,_malacatepec,_tilostoc_y_temascaltepec` | Z.P.F.T.C.C. de los ríos Valle de Bravo, Malacatepec, Tilostoc y Temascaltepec | Área de Protección de Recursos Naturales | 1402.3 | 0% |
| `z.p.f.v._la_cuenca_hidrografica_del_rio_necaxa` | Z.P.F.V. la Cuenca Hidrográfica del Río Necaxa | Área de Protección de Recursos Naturales | 421.3 | 0% |

### inaturalist — 209/227 (18 missing)

**Pattern:** By category: {'Área de Protección de Recursos Naturales': 13, 'Reserva de la Biosfera': 1, 'Santuario': 4}; Marine-dominated: 0/18; Small (<10 km²): 4/18

| ANP ID | Name | Designation | Area km² | Marine % |
|--------|------|-------------|----------|----------|
| `c.a.d.n.r._001_pabellon` | C.A.D.N.R. 001 Pabellón | Área de Protección de Recursos Naturales | 977.0 | 0% |
| `c.a.d.n.r._004_don_martin` | C.A.D.N.R. 004 Don Martín | Área de Protección de Recursos Naturales | 15193.9 | 0% |
| `c.a.d.n.r._026_bajo_rio_san_juan` | C.A.D.N.R. 026 Bajo Río San Juan | Área de Protección de Recursos Naturales | 1971.6 | 0% |
| `c.a.d.n.r._043_estado_de_nayarit` | C.A.D.N.R. 043 Estado de Nayarit | Área de Protección de Recursos Naturales | 23290.3 | 0% |
| `lacan-tun` | Lacan-Tun | Reserva de la Biosfera | 618.7 | 0% |
| `lago_de_texcoco` | Lago de Texcoco | Área de Protección de Recursos Naturales | 100.8 | 0% |
| `lago_tlahuac-xico` | Lago Tláhuac-Xico | Área de Protección de Recursos Naturales | 35.5 | 0% |
| `las_huertas` | Las Huertas | Área de Protección de Recursos Naturales | 1.7 | 0% |
| `pena_colorada` | Peña Colorada | Área de Protección de Recursos Naturales | 48.4 | 0% |
| `playa_cahuitan` | Playa Cahuitán | Santuario | 2.6 | 0% |
| `playa_ceuta` | Playa Ceuta | Santuario | 1.4 | 0% |
| `playa_huizache_caimanero` | Playa Huizache Caimanero | Santuario | 482.8 | 0% |
| `playa_lechuguillas` | Playa Lechuguillas | Santuario | 1.5 | 0% |
| `rios_y_montanas_de_la_comarca_lagunera` | Ríos y Montañas de la Comarca Lagunera | Área de Protección de Recursos Naturales | 1729.2 | 0% |
| `tlachinoltepetl` | Tlachinoltepetl | Área de Protección de Recursos Naturales | 11.9 | 0% |
| `z.p.f._en_los_terrenos_que_se_encuentran_en_los_mpios._de_la_concordia,_angel_albino_corzo,_villa_flores_y_jiquipilas` | Z.P.F. en los terrenos que se encuentran en los mpios. de La Concordia, Ángel Albino Corzo, Villa Flores y Jiquipilas | Área de Protección de Recursos Naturales | 1775.5 | 0% |
| `z.p.f.t.c.c._de_los_rios_valle_de_bravo,_malacatepec,_tilostoc_y_temascaltepec` | Z.P.F.T.C.C. de los ríos Valle de Bravo, Malacatepec, Tilostoc y Temascaltepec | Área de Protección de Recursos Naturales | 1402.3 | 0% |
| `z.p.f.v._la_cuenca_hidrografica_del_rio_necaxa` | Z.P.F.V. la Cuenca Hidrográfica del Río Necaxa | Área de Protección de Recursos Naturales | 421.3 | 0% |

### gedi_biomass — 209/227 (18 missing)

**Pattern:** By category: {'Área de Protección de Recursos Naturales': 13, 'Reserva de la Biosfera': 1, 'Santuario': 4}; Marine-dominated: 0/18; Small (<10 km²): 4/18

| ANP ID | Name | Designation | Area km² | Marine % |
|--------|------|-------------|----------|----------|
| `c.a.d.n.r._001_pabellon` | C.A.D.N.R. 001 Pabellón | Área de Protección de Recursos Naturales | 977.0 | 0% |
| `c.a.d.n.r._004_don_martin` | C.A.D.N.R. 004 Don Martín | Área de Protección de Recursos Naturales | 15193.9 | 0% |
| `c.a.d.n.r._026_bajo_rio_san_juan` | C.A.D.N.R. 026 Bajo Río San Juan | Área de Protección de Recursos Naturales | 1971.6 | 0% |
| `c.a.d.n.r._043_estado_de_nayarit` | C.A.D.N.R. 043 Estado de Nayarit | Área de Protección de Recursos Naturales | 23290.3 | 0% |
| `lacan-tun` | Lacan-Tun | Reserva de la Biosfera | 618.7 | 0% |
| `lago_de_texcoco` | Lago de Texcoco | Área de Protección de Recursos Naturales | 100.8 | 0% |
| `lago_tlahuac-xico` | Lago Tláhuac-Xico | Área de Protección de Recursos Naturales | 35.5 | 0% |
| `las_huertas` | Las Huertas | Área de Protección de Recursos Naturales | 1.7 | 0% |
| `pena_colorada` | Peña Colorada | Área de Protección de Recursos Naturales | 48.4 | 0% |
| `playa_cahuitan` | Playa Cahuitán | Santuario | 2.6 | 0% |
| `playa_ceuta` | Playa Ceuta | Santuario | 1.4 | 0% |
| `playa_huizache_caimanero` | Playa Huizache Caimanero | Santuario | 482.8 | 0% |
| `playa_lechuguillas` | Playa Lechuguillas | Santuario | 1.5 | 0% |
| `rios_y_montanas_de_la_comarca_lagunera` | Ríos y Montañas de la Comarca Lagunera | Área de Protección de Recursos Naturales | 1729.2 | 0% |
| `tlachinoltepetl` | Tlachinoltepetl | Área de Protección de Recursos Naturales | 11.9 | 0% |
| `z.p.f._en_los_terrenos_que_se_encuentran_en_los_mpios._de_la_concordia,_angel_albino_corzo,_villa_flores_y_jiquipilas` | Z.P.F. en los terrenos que se encuentran en los mpios. de La Concordia, Ángel Albino Corzo, Villa Flores y Jiquipilas | Área de Protección de Recursos Naturales | 1775.5 | 0% |
| `z.p.f.t.c.c._de_los_rios_valle_de_bravo,_malacatepec,_tilostoc_y_temascaltepec` | Z.P.F.T.C.C. de los ríos Valle de Bravo, Malacatepec, Tilostoc y Temascaltepec | Área de Protección de Recursos Naturales | 1402.3 | 0% |
| `z.p.f.v._la_cuenca_hidrografica_del_rio_necaxa` | Z.P.F.V. la Cuenca Hidrográfica del Río Necaxa | Área de Protección de Recursos Naturales | 421.3 | 0% |

### coneval_irs — 205/227 (22 missing)

**Pattern:** By category: {'Área de Protección de Recursos Naturales': 13, 'Reserva de la Biosfera': 3, 'Santuario': 5, 'Parque Nacional': 1}; Marine-dominated: 1/22; Small (<10 km²): 4/22

| ANP ID | Name | Designation | Area km² | Marine % |
|--------|------|-------------|----------|----------|
| `c.a.d.n.r._001_pabellon` | C.A.D.N.R. 001 Pabellón | Área de Protección de Recursos Naturales | 977.0 | 0% |
| `c.a.d.n.r._004_don_martin` | C.A.D.N.R. 004 Don Martín | Área de Protección de Recursos Naturales | 15193.9 | 0% |
| `c.a.d.n.r._026_bajo_rio_san_juan` | C.A.D.N.R. 026 Bajo Río San Juan | Área de Protección de Recursos Naturales | 1971.6 | 0% |
| `c.a.d.n.r._043_estado_de_nayarit` | C.A.D.N.R. 043 Estado de Nayarit | Área de Protección de Recursos Naturales | 23290.3 | 0% |
| `lacan-tun` | Lacan-Tun | Reserva de la Biosfera | 618.7 | 0% |
| `lago_de_texcoco` | Lago de Texcoco | Área de Protección de Recursos Naturales | 100.8 | 0% |
| `lago_tlahuac-xico` | Lago Tláhuac-Xico | Área de Protección de Recursos Naturales | 35.5 | 0% |
| `las_huertas` | Las Huertas | Área de Protección de Recursos Naturales | 1.7 | 0% |
| `pena_colorada` | Peña Colorada | Área de Protección de Recursos Naturales | 48.4 | 0% |
| `playa_cahuitan` | Playa Cahuitán | Santuario | 2.6 | 0% |
| `playa_ceuta` | Playa Ceuta | Santuario | 1.4 | 0% |
| `playa_huizache_caimanero` | Playa Huizache Caimanero | Santuario | 482.8 | 0% |
| `playa_lechuguillas` | Playa Lechuguillas | Santuario | 1.5 | 0% |
| `rios_y_montanas_de_la_comarca_lagunera` | Ríos y Montañas de la Comarca Lagunera | Área de Protección de Recursos Naturales | 1729.2 | 0% |
| `tlachinoltepetl` | Tlachinoltepetl | Área de Protección de Recursos Naturales | 11.9 | 0% |
| `ventilas_hidrotermales_de_la_cuenca_de_guaymas_y_de_la_dorsal_del_pacifico_orien` | Ventilas Hidrotermales de la Cuenca de Guaymas y de la Dorsal del Pacífico Oriental | Santuario | 1455.6 | 100% |
| `volcan_nevado_de_colima` | Volcán Nevado de Colima | Parque Nacional | 65.5 | 0% |
| `volcan_tacana` | Volcán Tacaná | Reserva de la Biosfera | 63.8 | 0% |
| `wanha` | Wanha' | Reserva de la Biosfera | 382.6 | 0% |
| `z.p.f._en_los_terrenos_que_se_encuentran_en_los_mpios._de_la_concordia,_angel_albino_corzo,_villa_flores_y_jiquipilas` | Z.P.F. en los terrenos que se encuentran en los mpios. de La Concordia, Ángel Albino Corzo, Villa Flores y Jiquipilas | Área de Protección de Recursos Naturales | 1775.5 | 0% |
| `z.p.f.t.c.c._de_los_rios_valle_de_bravo,_malacatepec,_tilostoc_y_temascaltepec` | Z.P.F.T.C.C. de los ríos Valle de Bravo, Malacatepec, Tilostoc y Temascaltepec | Área de Protección de Recursos Naturales | 1402.3 | 0% |
| `z.p.f.v._la_cuenca_hidrografica_del_rio_necaxa` | Z.P.F.V. la Cuenca Hidrográfica del Río Necaxa | Área de Protección de Recursos Naturales | 421.3 | 0% |

### gbif_species — 199/227 (28 missing)

**Pattern:** By category: {'Área de Protección de Recursos Naturales': 13, 'Área de Protección de Flora y Fauna': 4, 'Parque Nacional': 2, 'Reserva de la Biosfera': 3, 'Santuario': 6}; Marine-dominated: 1/28; Small (<10 km²): 9/28

| ANP ID | Name | Designation | Area km² | Marine % |
|--------|------|-------------|----------|----------|
| `c.a.d.n.r._001_pabellon` | C.A.D.N.R. 001 Pabellón | Área de Protección de Recursos Naturales | 977.0 | 0% |
| `c.a.d.n.r._004_don_martin` | C.A.D.N.R. 004 Don Martín | Área de Protección de Recursos Naturales | 15193.9 | 0% |
| `c.a.d.n.r._026_bajo_rio_san_juan` | C.A.D.N.R. 026 Bajo Río San Juan | Área de Protección de Recursos Naturales | 1971.6 | 0% |
| `c.a.d.n.r._043_estado_de_nayarit` | C.A.D.N.R. 043 Estado de Nayarit | Área de Protección de Recursos Naturales | 23290.3 | 0% |
| `cenote_aerolito` | Cenote Aerolito | Área de Protección de Flora y Fauna | 0.1 | 0% |
| `costa_occ_de_i_mujeres_pta_cancun_y_pta_nizuc` | Costa Occ. de I. Mujeres, Pta. Cancún y Pta. Nizuc | Parque Nacional | 86.7 | 100% |
| `islas_del_golfo_de_california` | Islas del Golfo de California | Área de Protección de Flora y Fauna | 3147.4 | 0% |
| `jacinto_pat` | Jacinto Pat | Área de Protección de Flora y Fauna | 0.2 | 0% |
| `janos` | Janos | Reserva de la Biosfera | 5264.8 | 0% |
| `lacan-tun` | Lacan-Tun | Reserva de la Biosfera | 618.7 | 0% |
| `lago_de_texcoco` | Lago de Texcoco | Área de Protección de Recursos Naturales | 100.8 | 0% |
| `lago_tlahuac-xico` | Lago Tláhuac-Xico | Área de Protección de Recursos Naturales | 35.5 | 0% |
| `las_huertas` | Las Huertas | Área de Protección de Recursos Naturales | 1.7 | 0% |
| `pena_colorada` | Peña Colorada | Área de Protección de Recursos Naturales | 48.4 | 0% |
| `playa_cahuitan` | Playa Cahuitán | Santuario | 2.6 | 0% |
| `playa_ceuta` | Playa Ceuta | Santuario | 1.4 | 0% |
| `playa_huizache_caimanero` | Playa Huizache Caimanero | Santuario | 482.8 | 0% |
| `playa_lechuguillas` | Playa Lechuguillas | Santuario | 1.5 | 0% |
| `playa_teopa` | Playa Teopa | Santuario | 0.3 | 0% |
| `playa_tierra_colorada` | Playa Tierra Colorada | Santuario | 1.4 | 0% |
| `rios_y_montanas_de_la_comarca_lagunera` | Ríos y Montañas de la Comarca Lagunera | Área de Protección de Recursos Naturales | 1729.2 | 0% |
| `tlachinoltepetl` | Tlachinoltepetl | Área de Protección de Recursos Naturales | 11.9 | 0% |
| `valle_de_los_cirios` | Valle de los Cirios | Área de Protección de Flora y Fauna | 25219.9 | 0% |
| `vicente_guerrero` | Vicente Guerrero | Parque Nacional | 7.2 | 0% |
| `wanha` | Wanha' | Reserva de la Biosfera | 382.6 | 0% |
| `z.p.f._en_los_terrenos_que_se_encuentran_en_los_mpios._de_la_concordia,_angel_albino_corzo,_villa_flores_y_jiquipilas` | Z.P.F. en los terrenos que se encuentran en los mpios. de La Concordia, Ángel Albino Corzo, Villa Flores y Jiquipilas | Área de Protección de Recursos Naturales | 1775.5 | 0% |
| `z.p.f.t.c.c._de_los_rios_valle_de_bravo,_malacatepec,_tilostoc_y_temascaltepec` | Z.P.F.T.C.C. de los ríos Valle de Bravo, Malacatepec, Tilostoc y Temascaltepec | Área de Protección de Recursos Naturales | 1402.3 | 0% |
| `z.p.f.v._la_cuenca_hidrografica_del_rio_necaxa` | Z.P.F.V. la Cuenca Hidrográfica del Río Necaxa | Área de Protección de Recursos Naturales | 421.3 | 0% |

### simec_nom059 — 201/227 (26 missing)

**Pattern:** By category: {'Área de Protección de Recursos Naturales': 13, 'Área de Protección de Flora y Fauna': 3, 'Reserva de la Biosfera': 3, 'Santuario': 6, 'Parque Nacional': 1}; Marine-dominated: 0/26; Small (<10 km²): 9/26

| ANP ID | Name | Designation | Area km² | Marine % |
|--------|------|-------------|----------|----------|
| `c.a.d.n.r._001_pabellon` | C.A.D.N.R. 001 Pabellón | Área de Protección de Recursos Naturales | 977.0 | 0% |
| `c.a.d.n.r._004_don_martin` | C.A.D.N.R. 004 Don Martín | Área de Protección de Recursos Naturales | 15193.9 | 0% |
| `c.a.d.n.r._026_bajo_rio_san_juan` | C.A.D.N.R. 026 Bajo Río San Juan | Área de Protección de Recursos Naturales | 1971.6 | 0% |
| `c.a.d.n.r._043_estado_de_nayarit` | C.A.D.N.R. 043 Estado de Nayarit | Área de Protección de Recursos Naturales | 23290.3 | 0% |
| `cenote_aerolito` | Cenote Aerolito | Área de Protección de Flora y Fauna | 0.1 | 0% |
| `jacinto_pat` | Jacinto Pat | Área de Protección de Flora y Fauna | 0.2 | 0% |
| `janos` | Janos | Reserva de la Biosfera | 5264.8 | 0% |
| `lacan-tun` | Lacan-Tun | Reserva de la Biosfera | 618.7 | 0% |
| `lago_de_texcoco` | Lago de Texcoco | Área de Protección de Recursos Naturales | 100.8 | 0% |
| `lago_tlahuac-xico` | Lago Tláhuac-Xico | Área de Protección de Recursos Naturales | 35.5 | 0% |
| `las_huertas` | Las Huertas | Área de Protección de Recursos Naturales | 1.7 | 0% |
| `pena_colorada` | Peña Colorada | Área de Protección de Recursos Naturales | 48.4 | 0% |
| `playa_cahuitan` | Playa Cahuitán | Santuario | 2.6 | 0% |
| `playa_ceuta` | Playa Ceuta | Santuario | 1.4 | 0% |
| `playa_huizache_caimanero` | Playa Huizache Caimanero | Santuario | 482.8 | 0% |
| `playa_lechuguillas` | Playa Lechuguillas | Santuario | 1.5 | 0% |
| `playa_teopa` | Playa Teopa | Santuario | 0.3 | 0% |
| `playa_tierra_colorada` | Playa Tierra Colorada | Santuario | 1.4 | 0% |
| `rios_y_montanas_de_la_comarca_lagunera` | Ríos y Montañas de la Comarca Lagunera | Área de Protección de Recursos Naturales | 1729.2 | 0% |
| `tlachinoltepetl` | Tlachinoltepetl | Área de Protección de Recursos Naturales | 11.9 | 0% |
| `valle_de_los_cirios` | Valle de los Cirios | Área de Protección de Flora y Fauna | 25219.9 | 0% |
| `vicente_guerrero` | Vicente Guerrero | Parque Nacional | 7.2 | 0% |
| `wanha` | Wanha' | Reserva de la Biosfera | 382.6 | 0% |
| `z.p.f._en_los_terrenos_que_se_encuentran_en_los_mpios._de_la_concordia,_angel_albino_corzo,_villa_flores_y_jiquipilas` | Z.P.F. en los terrenos que se encuentran en los mpios. de La Concordia, Ángel Albino Corzo, Villa Flores y Jiquipilas | Área de Protección de Recursos Naturales | 1775.5 | 0% |
| `z.p.f.t.c.c._de_los_rios_valle_de_bravo,_malacatepec,_tilostoc_y_temascaltepec` | Z.P.F.T.C.C. de los ríos Valle de Bravo, Malacatepec, Tilostoc y Temascaltepec | Área de Protección de Recursos Naturales | 1402.3 | 0% |
| `z.p.f.v._la_cuenca_hidrografica_del_rio_necaxa` | Z.P.F.V. la Cuenca Hidrográfica del Río Necaxa | Área de Protección de Recursos Naturales | 421.3 | 0% |

### iucn_threatened — 199/227 (28 missing)

**Pattern:** By category: {'Área de Protección de Recursos Naturales': 13, 'Área de Protección de Flora y Fauna': 4, 'Parque Nacional': 2, 'Reserva de la Biosfera': 3, 'Santuario': 6}; Marine-dominated: 1/28; Small (<10 km²): 9/28

| ANP ID | Name | Designation | Area km² | Marine % |
|--------|------|-------------|----------|----------|
| `c.a.d.n.r._001_pabellon` | C.A.D.N.R. 001 Pabellón | Área de Protección de Recursos Naturales | 977.0 | 0% |
| `c.a.d.n.r._004_don_martin` | C.A.D.N.R. 004 Don Martín | Área de Protección de Recursos Naturales | 15193.9 | 0% |
| `c.a.d.n.r._026_bajo_rio_san_juan` | C.A.D.N.R. 026 Bajo Río San Juan | Área de Protección de Recursos Naturales | 1971.6 | 0% |
| `c.a.d.n.r._043_estado_de_nayarit` | C.A.D.N.R. 043 Estado de Nayarit | Área de Protección de Recursos Naturales | 23290.3 | 0% |
| `cenote_aerolito` | Cenote Aerolito | Área de Protección de Flora y Fauna | 0.1 | 0% |
| `costa_occ_de_i_mujeres_pta_cancun_y_pta_nizuc` | Costa Occ. de I. Mujeres, Pta. Cancún y Pta. Nizuc | Parque Nacional | 86.7 | 100% |
| `islas_del_golfo_de_california` | Islas del Golfo de California | Área de Protección de Flora y Fauna | 3147.4 | 0% |
| `jacinto_pat` | Jacinto Pat | Área de Protección de Flora y Fauna | 0.2 | 0% |
| `janos` | Janos | Reserva de la Biosfera | 5264.8 | 0% |
| `lacan-tun` | Lacan-Tun | Reserva de la Biosfera | 618.7 | 0% |
| `lago_de_texcoco` | Lago de Texcoco | Área de Protección de Recursos Naturales | 100.8 | 0% |
| `lago_tlahuac-xico` | Lago Tláhuac-Xico | Área de Protección de Recursos Naturales | 35.5 | 0% |
| `las_huertas` | Las Huertas | Área de Protección de Recursos Naturales | 1.7 | 0% |
| `pena_colorada` | Peña Colorada | Área de Protección de Recursos Naturales | 48.4 | 0% |
| `playa_cahuitan` | Playa Cahuitán | Santuario | 2.6 | 0% |
| `playa_ceuta` | Playa Ceuta | Santuario | 1.4 | 0% |
| `playa_huizache_caimanero` | Playa Huizache Caimanero | Santuario | 482.8 | 0% |
| `playa_lechuguillas` | Playa Lechuguillas | Santuario | 1.5 | 0% |
| `playa_teopa` | Playa Teopa | Santuario | 0.3 | 0% |
| `playa_tierra_colorada` | Playa Tierra Colorada | Santuario | 1.4 | 0% |
| `rios_y_montanas_de_la_comarca_lagunera` | Ríos y Montañas de la Comarca Lagunera | Área de Protección de Recursos Naturales | 1729.2 | 0% |
| `tlachinoltepetl` | Tlachinoltepetl | Área de Protección de Recursos Naturales | 11.9 | 0% |
| `valle_de_los_cirios` | Valle de los Cirios | Área de Protección de Flora y Fauna | 25219.9 | 0% |
| `vicente_guerrero` | Vicente Guerrero | Parque Nacional | 7.2 | 0% |
| `wanha` | Wanha' | Reserva de la Biosfera | 382.6 | 0% |
| `z.p.f._en_los_terrenos_que_se_encuentran_en_los_mpios._de_la_concordia,_angel_albino_corzo,_villa_flores_y_jiquipilas` | Z.P.F. en los terrenos que se encuentran en los mpios. de La Concordia, Ángel Albino Corzo, Villa Flores y Jiquipilas | Área de Protección de Recursos Naturales | 1775.5 | 0% |
| `z.p.f.t.c.c._de_los_rios_valle_de_bravo,_malacatepec,_tilostoc_y_temascaltepec` | Z.P.F.T.C.C. de los ríos Valle de Bravo, Malacatepec, Tilostoc y Temascaltepec | Área de Protección de Recursos Naturales | 1402.3 | 0% |
| `z.p.f.v._la_cuenca_hidrografica_del_rio_necaxa` | Z.P.F.V. la Cuenca Hidrográfica del Río Necaxa | Área de Protección de Recursos Naturales | 421.3 | 0% |

### nom059_enciclovida — 199/227 (28 missing)

**Pattern:** By category: {'Área de Protección de Recursos Naturales': 13, 'Área de Protección de Flora y Fauna': 4, 'Parque Nacional': 2, 'Reserva de la Biosfera': 3, 'Santuario': 6}; Marine-dominated: 1/28; Small (<10 km²): 9/28

| ANP ID | Name | Designation | Area km² | Marine % |
|--------|------|-------------|----------|----------|
| `c.a.d.n.r._001_pabellon` | C.A.D.N.R. 001 Pabellón | Área de Protección de Recursos Naturales | 977.0 | 0% |
| `c.a.d.n.r._004_don_martin` | C.A.D.N.R. 004 Don Martín | Área de Protección de Recursos Naturales | 15193.9 | 0% |
| `c.a.d.n.r._026_bajo_rio_san_juan` | C.A.D.N.R. 026 Bajo Río San Juan | Área de Protección de Recursos Naturales | 1971.6 | 0% |
| `c.a.d.n.r._043_estado_de_nayarit` | C.A.D.N.R. 043 Estado de Nayarit | Área de Protección de Recursos Naturales | 23290.3 | 0% |
| `cenote_aerolito` | Cenote Aerolito | Área de Protección de Flora y Fauna | 0.1 | 0% |
| `costa_occ_de_i_mujeres_pta_cancun_y_pta_nizuc` | Costa Occ. de I. Mujeres, Pta. Cancún y Pta. Nizuc | Parque Nacional | 86.7 | 100% |
| `islas_del_golfo_de_california` | Islas del Golfo de California | Área de Protección de Flora y Fauna | 3147.4 | 0% |
| `jacinto_pat` | Jacinto Pat | Área de Protección de Flora y Fauna | 0.2 | 0% |
| `janos` | Janos | Reserva de la Biosfera | 5264.8 | 0% |
| `lacan-tun` | Lacan-Tun | Reserva de la Biosfera | 618.7 | 0% |
| `lago_de_texcoco` | Lago de Texcoco | Área de Protección de Recursos Naturales | 100.8 | 0% |
| `lago_tlahuac-xico` | Lago Tláhuac-Xico | Área de Protección de Recursos Naturales | 35.5 | 0% |
| `las_huertas` | Las Huertas | Área de Protección de Recursos Naturales | 1.7 | 0% |
| `pena_colorada` | Peña Colorada | Área de Protección de Recursos Naturales | 48.4 | 0% |
| `playa_cahuitan` | Playa Cahuitán | Santuario | 2.6 | 0% |
| `playa_ceuta` | Playa Ceuta | Santuario | 1.4 | 0% |
| `playa_huizache_caimanero` | Playa Huizache Caimanero | Santuario | 482.8 | 0% |
| `playa_lechuguillas` | Playa Lechuguillas | Santuario | 1.5 | 0% |
| `playa_teopa` | Playa Teopa | Santuario | 0.3 | 0% |
| `playa_tierra_colorada` | Playa Tierra Colorada | Santuario | 1.4 | 0% |
| `rios_y_montanas_de_la_comarca_lagunera` | Ríos y Montañas de la Comarca Lagunera | Área de Protección de Recursos Naturales | 1729.2 | 0% |
| `tlachinoltepetl` | Tlachinoltepetl | Área de Protección de Recursos Naturales | 11.9 | 0% |
| `valle_de_los_cirios` | Valle de los Cirios | Área de Protección de Flora y Fauna | 25219.9 | 0% |
| `vicente_guerrero` | Vicente Guerrero | Parque Nacional | 7.2 | 0% |
| `wanha` | Wanha' | Reserva de la Biosfera | 382.6 | 0% |
| `z.p.f._en_los_terrenos_que_se_encuentran_en_los_mpios._de_la_concordia,_angel_albino_corzo,_villa_flores_y_jiquipilas` | Z.P.F. en los terrenos que se encuentran en los mpios. de La Concordia, Ángel Albino Corzo, Villa Flores y Jiquipilas | Área de Protección de Recursos Naturales | 1775.5 | 0% |
| `z.p.f.t.c.c._de_los_rios_valle_de_bravo,_malacatepec,_tilostoc_y_temascaltepec` | Z.P.F.T.C.C. de los ríos Valle de Bravo, Malacatepec, Tilostoc y Temascaltepec | Área de Protección de Recursos Naturales | 1402.3 | 0% |
| `z.p.f.v._la_cuenca_hidrografica_del_rio_necaxa` | Z.P.F.V. la Cuenca Hidrográfica del Río Necaxa | Área de Protección de Recursos Naturales | 421.3 | 0% |

### extracted_at — 199/227 (28 missing)

**Pattern:** By category: {'Área de Protección de Recursos Naturales': 13, 'Área de Protección de Flora y Fauna': 4, 'Parque Nacional': 2, 'Reserva de la Biosfera': 3, 'Santuario': 6}; Marine-dominated: 1/28; Small (<10 km²): 9/28

| ANP ID | Name | Designation | Area km² | Marine % |
|--------|------|-------------|----------|----------|
| `c.a.d.n.r._001_pabellon` | C.A.D.N.R. 001 Pabellón | Área de Protección de Recursos Naturales | 977.0 | 0% |
| `c.a.d.n.r._004_don_martin` | C.A.D.N.R. 004 Don Martín | Área de Protección de Recursos Naturales | 15193.9 | 0% |
| `c.a.d.n.r._026_bajo_rio_san_juan` | C.A.D.N.R. 026 Bajo Río San Juan | Área de Protección de Recursos Naturales | 1971.6 | 0% |
| `c.a.d.n.r._043_estado_de_nayarit` | C.A.D.N.R. 043 Estado de Nayarit | Área de Protección de Recursos Naturales | 23290.3 | 0% |
| `cenote_aerolito` | Cenote Aerolito | Área de Protección de Flora y Fauna | 0.1 | 0% |
| `costa_occ_de_i_mujeres_pta_cancun_y_pta_nizuc` | Costa Occ. de I. Mujeres, Pta. Cancún y Pta. Nizuc | Parque Nacional | 86.7 | 100% |
| `islas_del_golfo_de_california` | Islas del Golfo de California | Área de Protección de Flora y Fauna | 3147.4 | 0% |
| `jacinto_pat` | Jacinto Pat | Área de Protección de Flora y Fauna | 0.2 | 0% |
| `janos` | Janos | Reserva de la Biosfera | 5264.8 | 0% |
| `lacan-tun` | Lacan-Tun | Reserva de la Biosfera | 618.7 | 0% |
| `lago_de_texcoco` | Lago de Texcoco | Área de Protección de Recursos Naturales | 100.8 | 0% |
| `lago_tlahuac-xico` | Lago Tláhuac-Xico | Área de Protección de Recursos Naturales | 35.5 | 0% |
| `las_huertas` | Las Huertas | Área de Protección de Recursos Naturales | 1.7 | 0% |
| `pena_colorada` | Peña Colorada | Área de Protección de Recursos Naturales | 48.4 | 0% |
| `playa_cahuitan` | Playa Cahuitán | Santuario | 2.6 | 0% |
| `playa_ceuta` | Playa Ceuta | Santuario | 1.4 | 0% |
| `playa_huizache_caimanero` | Playa Huizache Caimanero | Santuario | 482.8 | 0% |
| `playa_lechuguillas` | Playa Lechuguillas | Santuario | 1.5 | 0% |
| `playa_teopa` | Playa Teopa | Santuario | 0.3 | 0% |
| `playa_tierra_colorada` | Playa Tierra Colorada | Santuario | 1.4 | 0% |
| `rios_y_montanas_de_la_comarca_lagunera` | Ríos y Montañas de la Comarca Lagunera | Área de Protección de Recursos Naturales | 1729.2 | 0% |
| `tlachinoltepetl` | Tlachinoltepetl | Área de Protección de Recursos Naturales | 11.9 | 0% |
| `valle_de_los_cirios` | Valle de los Cirios | Área de Protección de Flora y Fauna | 25219.9 | 0% |
| `vicente_guerrero` | Vicente Guerrero | Parque Nacional | 7.2 | 0% |
| `wanha` | Wanha' | Reserva de la Biosfera | 382.6 | 0% |
| `z.p.f._en_los_terrenos_que_se_encuentran_en_los_mpios._de_la_concordia,_angel_albino_corzo,_villa_flores_y_jiquipilas` | Z.P.F. en los terrenos que se encuentran en los mpios. de La Concordia, Ángel Albino Corzo, Villa Flores y Jiquipilas | Área de Protección de Recursos Naturales | 1775.5 | 0% |
| `z.p.f.t.c.c._de_los_rios_valle_de_bravo,_malacatepec,_tilostoc_y_temascaltepec` | Z.P.F.T.C.C. de los ríos Valle de Bravo, Malacatepec, Tilostoc y Temascaltepec | Área de Protección de Recursos Naturales | 1402.3 | 0% |
| `z.p.f.v._la_cuenca_hidrografica_del_rio_necaxa` | Z.P.F.V. la Cuenca Hidrográfica del Río Necaxa | Área de Protección de Recursos Naturales | 421.3 | 0% |

---
## 3. Null/Empty/Error Audit

**Total dataset rows scanned:** 4657

### Summary by Dataset Type

| Dataset Type | Errors | Data Unavailable | Empty | Null Fields |
|-------------|--------|-----------------|-------|-------------|
| climate | 0 | 0 | 0 | 11 |
| coneval_irs | 0 | 46 | 0 | 0 |
| gedi_biomass | 3 | 2 | 0 | 2 |
| human_modification | 0 | 0 | 0 | 6 |
| inegi_census | 44 | 0 | 0 | 8 |
| mangroves | 6 | 28 | 0 | 0 |
| simec_nom059 | 137 | 0 | 0 | 0 |
| vegetation | 0 | 0 | 0 | 4 |
| water_stress | 0 | 2 | 0 | 209 |

### Detailed Findings


#### climate

**null_fields** (11):
- arrecife_alacranes (Arrecife Alacranes): ['mean_max_temp_c', 'mean_min_temp_c', 'annual_precipitation_mm']
- bajos_del_norte (Bajos del Norte): ['mean_max_temp_c', 'mean_min_temp_c', 'annual_precipitation_mm']
- barra_de_la_cruz_playa_grande (Barra de la Cruz-Playa Grande): ['mean_max_temp_c', 'mean_min_temp_c', 'annual_precipitation_mm']
- el_lago_de_camecuaro (El Lago de Camécuaro): ['mean_max_temp_c', 'mean_min_temp_c', 'annual_precipitation_mm']
- isla_isabel (Isla Isabel): ['mean_max_temp_c', 'mean_min_temp_c', 'annual_precipitation_mm']
- islas_marietas (Islas Marietas): ['mean_max_temp_c', 'mean_min_temp_c', 'annual_precipitation_mm']
- pacifico_mexicano_profundo (Pacífico Mexicano Profundo): ['mean_max_temp_c', 'mean_min_temp_c', 'annual_precipitation_mm']
- playa_delfines (Playa Delfines): ['mean_max_temp_c', 'mean_min_temp_c', 'annual_precipitation_mm']
- sistema_arrecifal_lobos_tuxpan (Sistema Arrecifal Lobos-Tuxpan): ['mean_max_temp_c', 'mean_min_temp_c', 'annual_precipitation_mm']
- ventilas_hidrotermales_de_la_cuenca_de_guaymas_y_de_la_dorsal_del_pacifico_orien (Ventilas Hidrotermales de la Cuenca de Guaymas y de la Dorsal del Pacífico Oriental): ['mean_max_temp_c', 'mean_min_temp_c', 'annual_precipitation_mm']
- zona_marina_de_la_isla_isabel (Zona Marina de la Isla Isabel): ['mean_max_temp_c', 'mean_min_temp_c', 'annual_precipitation_mm']

#### coneval_irs

**data_unavailable** (46):
- arrecife_alacranes (Arrecife Alacranes): No municipalities found within ANP bounds
- bajos_del_norte (Bajos del Norte): No municipalities found within ANP bounds
- banco_chinchorro (Banco Chinchorro): No municipalities found within ANP bounds
- bonampak (Bonampak): No municipalities found within ANP bounds
- cabo_san_lucas (Cabo San Lucas): No municipalities found within ANP bounds
- cenote_aerolito (Cenote Aerolito): No municipalities found within ANP bounds
- cerro_de_garnica (Cerro de Garnica): No municipalities found within ANP bounds
- cerro_de_la_estrella (Cerro de La Estrella): No municipalities found within ANP bounds
- cerro_de_las_campanas (Cerro de Las Campanas): No municipalities found within ANP bounds
- chan_kin (Chan-Kin): No municipalities found within ANP bounds
- cotorra_serrana_occidental (Cotorra Serrana Occidental): No municipalities found within ANP bounds
- cumbres_del_ajusco (Cumbres del Ajusco): No municipalities found within ANP bounds
- el_historico_coyoacan (El Histórico Coyoacán): No municipalities found within ANP bounds
- el_sabinal (El Sabinal): No municipalities found within ANP bounds
- el_tepeyac (El Tepeyac): No municipalities found within ANP bounds
- *... and 31 more*

#### gedi_biomass

**data_unavailable** (2):
- arrecife_alacranes (Arrecife Alacranes): unknown
- bajos_del_norte (Bajos del Norte): unknown
**error** (3):
- islas_del_golfo_de_california (Islas del Golfo de California): Image.reduceRegion: Too many pixels in the region. Found 3681681725, but maxPixels allows only 10000
- islas_del_pacifico_de_la_peninsula_de_baja_california (Islas del Pacífico de la Península de Baja California): Image.reduceRegion: Too many pixels in the region. Found 1913188334, but maxPixels allows only 10000
- pacifico_mexicano_profundo (Pacífico Mexicano Profundo): Image.reduceRegion: Too many pixels in the region. Found 9370818223, but maxPixels allows only 10000
**null_fields** (2):
- arrecife_alacranes (Arrecife Alacranes): ['anp_area_ha', 'agbd_max_mg_ha', 'agbd_std_mg_ha', 'agbd_mean_mg_ha', 'total_carbon_estimate_mt']
- bajos_del_norte (Bajos del Norte): ['anp_area_ha', 'agbd_max_mg_ha', 'agbd_std_mg_ha', 'agbd_mean_mg_ha', 'total_carbon_estimate_mt']

#### human_modification

**null_fields** (6):
- arrecife_alacranes (Arrecife Alacranes): ['gHM_max', 'gHM_mean']
- bajos_del_norte (Bajos del Norte): ['gHM_max', 'gHM_mean']
- pacifico_mexicano_profundo (Pacífico Mexicano Profundo): ['gHM_max', 'gHM_mean']
- revillagigedo (Revillagigedo): ['gHM_max', 'gHM_mean']
- sistema_arrecifal_lobos_tuxpan (Sistema Arrecifal Lobos-Tuxpan): ['gHM_max', 'gHM_mean']
- ventilas_hidrotermales_de_la_cuenca_de_guaymas_y_de_la_dorsal_del_pacifico_orien (Ventilas Hidrotermales de la Cuenca de Guaymas y de la Dorsal del Pacífico Oriental): ['gHM_max', 'gHM_mean']

#### inegi_census

**error** (44):
- arrecife_alacranes (Arrecife Alacranes): No ITER data files found or no localities in bbox
- bajos_del_norte (Bajos del Norte): No ITER data files found or no localities in bbox
- banco_chinchorro (Banco Chinchorro): No ITER data files found or no localities in bbox
- bonampak (Bonampak): No ITER data files found or no localities in bbox
- cabo_san_lucas (Cabo San Lucas): No ITER data files found or no localities in bbox
- cerro_de_garnica (Cerro de Garnica): No ITER data files found or no localities in bbox
- cerro_de_la_estrella (Cerro de La Estrella): No ITER data files found or no localities in bbox
- cerro_de_las_campanas (Cerro de Las Campanas): No ITER data files found or no localities in bbox
- chan_kin (Chan-Kin): No ITER data files found or no localities in bbox
- cotorra_serrana_occidental (Cotorra Serrana Occidental): No ITER data files found or no localities in bbox
- cumbres_del_ajusco (Cumbres del Ajusco): No ITER data files found or no localities in bbox
- el_historico_coyoacan (El Histórico Coyoacán): No ITER data files found or no localities in bbox
- el_sabinal (El Sabinal): No ITER data files found or no localities in bbox
- el_tepeyac (El Tepeyac): No ITER data files found or no localities in bbox
- fuentes_brotantes_de_tlalpan (Fuentes Brotantes de Tlalpan): No ITER data files found or no localities in bbox
- *... and 29 more*
**null_fields** (8):
- balandra (Balandra): ['avg_schooling_years']
- benito_juarez (Benito Juárez): ['avg_schooling_years']
- dzibilchantun (Dzibilchantún): ['avg_schooling_years']
- el_lago_de_camecuaro (El Lago de Camécuaro): ['avg_schooling_years']
- manglares_de_nichupte (Manglares de Nichupté): ['avg_schooling_years']
- playa_chenkan (Playa Chenkan): ['avg_schooling_years']
- playa_rancho_nuevo (Playa Rancho Nuevo): ['avg_schooling_years']
- tulum (Tulum): ['avg_schooling_years']

#### mangroves

**data_unavailable** (28):
- alto_golfo_de_california_y_delta_del_rio_colorado (Alto Golfo de California y Delta del Río Colorado): unknown
- arrecife_alacranes (Arrecife Alacranes): unknown
- caribe_mexicano (Caribe Mexicano): Image.reduceRegion: Too many pixels in the region. Found 1243789389, but maxPixels allows only 1000000000.
Ensure that you are not aggregating at a higher resolution than you intended; that is a frequent cause of this error. If not, then you may set the 'maxPixels' argument to a limit suitable for your computation; set 'bestEffort' to true to aggregate at whatever scale results in 'maxPixels' total pixels; or both.
- cenote_aerolito (Cenote Aerolito): unknown
- constitucion_de_1857 (Constitución de 1857): unknown
- el_pinacate_y_gran_desierto_de_altar (El Pinacate y Gran Desierto de Altar): unknown
- humedales_de_montana_la_kisst_y_maria_eugenia (Humedales de Montaña La Kisst y María Eugenia): unknown
- insurgente_jose_maria_morelos (Insurgente José María Morelos): unknown
- isla_guadalupe (Isla Guadalupe): unknown
- isla_isabel (Isla Isabel): unknown
- isla_san_pedro_martir (Isla San Pedro Mártir): unknown
- islas_del_golfo_de_california (Islas del Golfo de California): Image.reduceRegion: Too many pixels in the region. Found 11505265303, but maxPixels allows only 1000000000.
Ensure that you are not aggregating at a higher resolution than you intended; that is a frequent cause of this error. If not, then you may set the 'maxPixels' argument to a limit suitable for your computation; set 'bestEffort' to true to aggregate at whatever scale results in 'maxPixels' total pixels; or both.
- islas_del_pacifico_de_la_peninsula_de_baja_california (Islas del Pacífico de la Península de Baja California): Image.reduceRegion: Too many pixels in the region. Found 5978672971, but maxPixels allows only 1000000000.
Ensure that you are not aggregating at a higher resolution than you intended; that is a frequent cause of this error. If not, then you may set the 'maxPixels' argument to a limit suitable for your computation; set 'bestEffort' to true to aggregate at whatever scale results in 'maxPixels' total pixels; or both.
- islas_marias (Islas Marías): unknown
- islas_marietas (Islas Marietas): unknown
- *... and 13 more*
**error** (6):
- caribe_mexicano (Caribe Mexicano): Image.reduceRegion: Too many pixels in the region. Found 1243789389, but maxPixels allows only 10000
- islas_del_golfo_de_california (Islas del Golfo de California): Image.reduceRegion: Too many pixels in the region. Found 11505265303, but maxPixels allows only 1000
- islas_del_pacifico_de_la_peninsula_de_baja_california (Islas del Pacífico de la Península de Baja California): Image.reduceRegion: Too many pixels in the region. Found 5978672971, but maxPixels allows only 10000
- pacifico_mexicano_profundo (Pacífico Mexicano Profundo): Image.reduceRegion: Too many pixels in the region. Found 29283700778, but maxPixels allows only 1000
- revillagigedo (Revillagigedo): Image.reduceRegion: Too many pixels in the region. Found 1573797387, but maxPixels allows only 10000
- ventilas_hidrotermales_de_la_cuenca_de_guaymas_y_de_la_dorsal_del_pacifico_orien (Ventilas Hidrotermales de la Cuenca de Guaymas y de la Dorsal del Pacífico Oriental): Image.reduceRegion: Too many pixels in the region. Found 2080897999, but maxPixels allows only 10000

#### simec_nom059

**error** (137):
- bajos_de_coyula (Bajos de Coyula): ANP not found in SIMEC data
- bajos_del_norte (Bajos del Norte): ANP not found in SIMEC data
- balam_kin (Balam Kin): ANP not found in SIMEC data
- balam_ku (Balam Kú): ANP not found in SIMEC data
- balandra (Balandra): ANP not found in SIMEC data
- barra_de_la_cruz_playa_grande (Barra de la Cruz-Playa Grande): ANP not found in SIMEC data
- bavispe (Bavispe): ANP not found in SIMEC data
- benito_juarez (Benito Juárez): ANP not found in SIMEC data
- bonampak (Bonampak): ANP not found in SIMEC data
- boqueron_de_tonala (Boquerón de Tonalá): ANP not found in SIMEC data
- bosencheve (Bosencheve): ANP not found in SIMEC data
- cabo_san_lucas (Cabo San Lucas): ANP not found in SIMEC data
- campo_verde (Campo Verde): ANP not found in SIMEC data
- canoas (Canoas): ANP not found in SIMEC data
- canon_del_rio_blanco (Cañón del Río Blanco): ANP not found in SIMEC data
- *... and 122 more*

#### vegetation

**null_fields** (4):
- arrecife_alacranes (Arrecife Alacranes): ['NDVI_max', 'NDVI_min', 'NDVI_mean']
- bajos_del_norte (Bajos del Norte): ['NDVI_max', 'NDVI_min', 'NDVI_mean']
- pacifico_mexicano_profundo (Pacífico Mexicano Profundo): ['NDVI_max', 'NDVI_min', 'NDVI_mean']
- ventilas_hidrotermales_de_la_cuenca_de_guaymas_y_de_la_dorsal_del_pacifico_orien (Ventilas Hidrotermales de la Cuenca de Guaymas y de la Dorsal del Pacífico Oriental): ['NDVI_max', 'NDVI_min', 'NDVI_mean']

#### water_stress

**data_unavailable** (2):
- arrecife_alacranes (Arrecife Alacranes): unknown
- bajos_del_norte (Bajos del Norte): unknown
**null_fields** (209):
- alto_golfo_de_california_y_delta_del_rio_colorado (Alto Golfo de California y Delta del Río Colorado): ['note']
- arrecife_alacranes (Arrecife Alacranes): ['drought_risk', 'baseline_water_stress', 'drought_risk_category', 'baseline_water_stress_category']
- arrecife_de_puerto_morelos (Arrecife de Puerto Morelos): ['note']
- arrecifes_de_cozumel (Arrecifes de Cozumel): ['note']
- arrecifes_de_sian_kaan (Arrecifes de Sian Ka'an): ['note']
- arrecifes_de_xcalak (Arrecifes de Xcalak): ['note']
- bahia_de_loreto (Bahía de Loreto): ['note']
- bajos_de_coyula (Bajos de Coyula): ['note']
- bajos_del_norte (Bajos del Norte): ['drought_risk', 'baseline_water_stress', 'drought_risk_category', 'baseline_water_stress_category']
- balaan_kaax (Bala'an K'aax): ['note']
- balam_kin (Balam Kin): ['note']
- balam_ku (Balam Kú): ['note']
- balandra (Balandra): ['note']
- banco_chinchorro (Banco Chinchorro): ['note']
- barra_de_la_cruz_playa_grande (Barra de la Cruz-Playa Grande): ['note']
- *... and 194 more*

---
## 4. Extraction Timestamp Audit

### Timestamps by Dataset Type

| Dataset Type | Total | Has Timestamp | Missing | Oldest | Newest |
|-------------|-------|---------------|---------|--------|--------|
| biodiversity | 227 | 0 | 227 | N/A | N/A |
| climate | 227 | 0 | 227 | N/A | N/A |
| elevation | 227 | 0 | 227 | N/A | N/A |
| fire | 227 | 0 | 227 | N/A | N/A |
| forest | 227 | 0 | 227 | N/A | N/A |
| human_modification | 227 | 0 | 227 | N/A | N/A |
| night_lights | 227 | 0 | 227 | N/A | N/A |
| population | 227 | 0 | 227 | N/A | N/A |
| vegetation | 227 | 0 | 227 | N/A | N/A |
| land_cover | 223 | 0 | 223 | N/A | N/A |
| soil | 22 | 0 | 22 | N/A | N/A |
| surface_water | 22 | 0 | 22 | N/A | N/A |
| water_stress | 227 | 209 | 18 | 2026-01-03 | 2026-01-03 |
| climate_portal | 1 | 1 | 0 | 2026-01-04 | 2026-01-04 |
| climate_projections | 227 | 227 | 0 | 2026-01-05 | 2026-01-08 |
| coneval_irs | 205 | 205 | 0 | 2026-01-15 | 2026-01-15 |
| extracted_at | 199 | 199 | 0 | 2026-01-15 | 2026-01-15 |
| gbif_species | 199 | 199 | 0 | 2026-01-15 | 2026-01-15 |
| gedi_biomass | 209 | 209 | 0 | 2026-01-03 | 2026-01-03 |
| inaturalist | 209 | 209 | 0 | 2026-01-15 | 2026-01-15 |
| inegi_census | 213 | 213 | 0 | 2026-01-15 | 2026-01-15 |
| iucn_threatened | 199 | 199 | 0 | 2026-01-15 | 2026-01-15 |
| mangroves | 58 | 58 | 0 | 2026-01-03 | 2026-01-03 |
| nom059 | 1 | 1 | 0 | 2026-01-15 | 2026-01-15 |
| nom059_enciclovida | 199 | 199 | 0 | 2026-01-15 | 2026-01-15 |
| simec_nom059 | 201 | 201 | 0 | 2026-01-15 | 2026-01-15 |

### ⚠️ 'extracted_at' stored as dataset_type

There are rows where `dataset_type = 'extracted_at'` — this appears to be a bug.
These should likely be timestamps on other datasets, not standalone entries.

Sample data:
- `alto_golfo_de_california_y_delta_del_rio_colorado`: `"2026-01-02T22:46:04.899839"`
- `arrecife_alacranes`: `"2026-01-02T22:47:11.133140"`
- `arrecife_de_puerto_morelos`: `"2026-01-02T22:48:21.076179"`

### JSON File Modification Dates (potential backfill source)

Total JSON files: 227

Sample dates:
- `alto_golfo_de_california_y_delta_del_rio_colorado`: 2026-01-11T17:30:11.107974
- `arrecife_alacranes`: 2026-01-11T17:30:11.107974
- `arrecife_de_puerto_morelos`: 2026-01-11T17:30:11.107974
- `arrecifes_de_cozumel`: 2026-01-11T17:30:11.127974
- `arrecifes_de_sian_kaan`: 2026-01-11T17:30:11.127974

---
## 5. Cross-Source Sanity Checks


### 5a. Area Discrepancies >10% (18 found)

| ANP | Name | WDPA km² | Comparison km² | Diff % | Source |
|-----|------|----------|---------------|--------|--------|
| `playa_huizache_caimanero` | Playa Huizache Caimanero | 482.83 | 4.51 | 10594.1% | WDPA vs superficie_total |
| `playa_maruata` | Playa Maruata | 2.2 | 0.12 | 1669.4% | WDPA vs superficie_total |
| `playa_rancho_nuevo` | Playa Rancho Nuevo | 0.91 | 18.44 | 95.1% | WDPA vs superficie_total |
| `playa_chacahua` | Playa Chacahua | 0.93 | 5.46 | 83.0% | WDPA vs superficie_total |
| `balandra` | Balandra | 4.49 | 25.13 | 82.1% | WDPA vs superficie_total |
| `bajos_del_norte` | Bajos del Norte | 3444.67 | 13041.15 | 73.6% | WDPA vs superficie_total |
| `playa_ceuta` | Playa Ceuta | 1.44 | 5.03 | 71.3% | WDPA vs superficie_total |
| `playa_puerto_arista` | Playa Puerto Arista | 2.12 | 7.26 | 70.8% | WDPA vs superficie_total |
| `balam_ku` | Balam Kú | 1839.64 | 4634.42 | 60.3% | WDPA vs superficie_total |
| `playa_tierra_colorada` | Playa Tierra Colorada | 1.39 | 2.64 | 47.5% | WDPA vs superficie_total |
| `playa_escobilla` | Playa Escobilla | 1.46 | 2.63 | 44.5% | WDPA vs superficie_total |
| `playa_el_tecuan` | Playa El Tecuán | 0.36 | 0.52 | 30.5% | WDPA vs superficie_total |
| `lago_de_texcoco` | Lago de Texcoco | 100.77 | 140.0 | 28.0% | WDPA vs superficie_total |
| `playa_ria_lagartos` | Playa Ría Lagartos | 6.06 | 8.27 | 26.7% | WDPA vs superficie_total |
| `playa_mexiquillo` | Playa Mexiquillo | 0.74 | 1.0 | 26.5% | WDPA vs superficie_total |
| `playa_mismaloya` | Playa Mismaloya | 6.28 | 8.11 | 22.5% | WDPA vs superficie_total |
| `el_lago_de_camecuaro` | El Lago de Camécuaro | 0.05 | 0.06 | 16.3% | WDPA vs superficie_total |
| `islas_del_golfo_de_california` | Islas del Golfo de California | 3147.36 | 3745.54 | 16.0% | WDPA vs superficie_total |

### 5b. Marine-Dominated ANPs (>95% marine): 21 total

| ANP | Name | Marine % | Terr. ha |
|-----|------|---------|----------|
| `arrecife_alacranes` | Arrecife Alacranes | 100.0% | 53.0 |
| `bajos_del_norte` | Bajos del Norte | 100.0% | 0.0 |
| `costa_occ_de_i_mujeres_pta_cancun_y_pta_nizuc` | Costa Occ. de I. Mujeres, Pta. Cancún y Pta. Nizuc | 100.0% | 0.61 |
| `pacifico_mexicano_profundo` | Pacífico Mexicano Profundo | 100.0% | 0.0 |
| `sistema_arrecifal_lobos_tuxpan` | Sistema Arrecifal Lobos-Tuxpan | 100.0% | 0.0 |
| `sistema_arrecifal_veracruzano` | Sistema Arrecifal Veracruzano | 100.0% | 12.24 |
| `tiburon_ballena` | Tiburón Ballena | 100.0% | 0.0 |
| `ventilas_hidrotermales_de_la_cuenca_de_guaymas_y_de_la_dorsal_del_pacifico_orien` | Ventilas Hidrotermales de la Cuenca de Guaymas y de la Dorsal del Pacífico Oriental | 100.0% | 0.0 |
| `zona_marina_de_la_isla_isabel` | Zona Marina de la Isla Isabel | 100.0% | 0.0 |
| `zona_marina_del_archipielago_de_espiritu_santo` | Zona marina del Archipiélago de Espíritu Santo | 100.0% | 0.0 |
| `zona_marina_del_archipielago_de_san_lorenzo` | Zona marina del Archipiélago de San Lorenzo | 100.0% | 0.0 |
| `revillagigedo` | Revillagigedo | 99.9% | 15518.22 |
| `zona_marina_bahia_de_los_angeles_canales_de_ballenas_y_de_salsipuedes` | Zona marina Bahía de los Ángeles, canales de Ballenas y de Salsipuedes | 99.9% | 483.2 |
| `banco_chinchorro` | Banco Chinchorro | 99.6% | 585.79 |
| `isla_san_pedro_martir` | Isla San Pedro Mártir | 99.6% | 126.99 |
| `cabo_pulmo` | Cabo Pulmo | 99.5% | 38.86 |
| `caribe_mexicano` | Caribe Mexicano | 99.5% | 28589.5 |
| `arrecifes_de_cozumel` | Arrecifes de Cozumel | 99.3% | 82.28 |
| `islas_marias` | Islas Marías | 96.2% | 24295.17 |
| `arrecifes_de_sian_kaan` | Arrecifes de Sian Ka'an | 96.1% | 1361.0 |
| `isla_contoy` | Isla Contoy | 95.5% | 230.0 |

**Marine ANPs with terrestrial-only data:** 57 found

| ANP | Marine % | Dataset | Note |
|-----|---------|---------|------|
| `arrecife_alacranes` (Arrecife Alacranes) | 100.0% | land_cover | terr_ha=53.0 |
| `arrecife_alacranes` (Arrecife Alacranes) | 100.0% | forest | terr_ha=53.0 |
| `arrecifes_de_cozumel` (Arrecifes de Cozumel) | 99.3% | land_cover | terr_ha=82.28 |
| `arrecifes_de_cozumel` (Arrecifes de Cozumel) | 99.3% | forest | terr_ha=82.28 |
| `arrecifes_de_cozumel` (Arrecifes de Cozumel) | 99.3% | gedi_biomass | terr_ha=82.28 |
| `arrecifes_de_sian_kaan` (Arrecifes de Sian Ka'an) | 96.1% | land_cover | terr_ha=1361.0 |
| `arrecifes_de_sian_kaan` (Arrecifes de Sian Ka'an) | 96.1% | forest | terr_ha=1361.0 |
| `arrecifes_de_sian_kaan` (Arrecifes de Sian Ka'an) | 96.1% | gedi_biomass | terr_ha=1361.0 |
| `bajos_del_norte` (Bajos del Norte) | 100.0% | land_cover | terr_ha=0.0 |
| `bajos_del_norte` (Bajos del Norte) | 100.0% | forest | terr_ha=0.0 |
| `banco_chinchorro` (Banco Chinchorro) | 99.6% | land_cover | terr_ha=585.79 |
| `banco_chinchorro` (Banco Chinchorro) | 99.6% | forest | terr_ha=585.79 |
| `banco_chinchorro` (Banco Chinchorro) | 99.6% | gedi_biomass | terr_ha=585.79 |
| `cabo_pulmo` (Cabo Pulmo) | 99.5% | land_cover | terr_ha=38.86 |
| `cabo_pulmo` (Cabo Pulmo) | 99.5% | forest | terr_ha=38.86 |
| `cabo_pulmo` (Cabo Pulmo) | 99.5% | gedi_biomass | terr_ha=38.86 |
| `caribe_mexicano` (Caribe Mexicano) | 99.5% | forest | terr_ha=28589.5 |
| `caribe_mexicano` (Caribe Mexicano) | 99.5% | gedi_biomass | terr_ha=28589.5 |
| `costa_occ_de_i_mujeres_pta_cancun_y_pta_nizuc` (Costa Occ. de I. Mujeres, Pta. Cancún y Pta. Nizuc) | 100.0% | land_cover | terr_ha=0.61 |
| `costa_occ_de_i_mujeres_pta_cancun_y_pta_nizuc` (Costa Occ. de I. Mujeres, Pta. Cancún y Pta. Nizuc) | 100.0% | forest | terr_ha=0.61 |
| `costa_occ_de_i_mujeres_pta_cancun_y_pta_nizuc` (Costa Occ. de I. Mujeres, Pta. Cancún y Pta. Nizuc) | 100.0% | gedi_biomass | terr_ha=0.61 |
| `isla_contoy` (Isla Contoy) | 95.5% | land_cover | terr_ha=230.0 |
| `isla_contoy` (Isla Contoy) | 95.5% | forest | terr_ha=230.0 |
| `isla_contoy` (Isla Contoy) | 95.5% | gedi_biomass | terr_ha=230.0 |
| `isla_san_pedro_martir` (Isla San Pedro Mártir) | 99.6% | land_cover | terr_ha=126.99 |
| `isla_san_pedro_martir` (Isla San Pedro Mártir) | 99.6% | forest | terr_ha=126.99 |
| `isla_san_pedro_martir` (Isla San Pedro Mártir) | 99.6% | gedi_biomass | terr_ha=126.99 |
| `islas_marias` (Islas Marías) | 96.2% | land_cover | terr_ha=24295.17 |
| `islas_marias` (Islas Marías) | 96.2% | forest | terr_ha=24295.17 |
| `islas_marias` (Islas Marías) | 96.2% | gedi_biomass | terr_ha=24295.17 |
| `pacifico_mexicano_profundo` (Pacífico Mexicano Profundo) | 100.0% | forest | terr_ha=0.0 |
| `revillagigedo` (Revillagigedo) | 99.9% | forest | terr_ha=15518.22 |
| `revillagigedo` (Revillagigedo) | 99.9% | gedi_biomass | terr_ha=15518.22 |
| `sistema_arrecifal_lobos_tuxpan` (Sistema Arrecifal Lobos-Tuxpan) | 100.0% | land_cover | terr_ha=0.0 |
| `sistema_arrecifal_lobos_tuxpan` (Sistema Arrecifal Lobos-Tuxpan) | 100.0% | forest | terr_ha=0.0 |
| `sistema_arrecifal_lobos_tuxpan` (Sistema Arrecifal Lobos-Tuxpan) | 100.0% | gedi_biomass | terr_ha=0.0 |
| `sistema_arrecifal_veracruzano` (Sistema Arrecifal Veracruzano) | 100.0% | land_cover | terr_ha=12.24 |
| `sistema_arrecifal_veracruzano` (Sistema Arrecifal Veracruzano) | 100.0% | forest | terr_ha=12.24 |
| `sistema_arrecifal_veracruzano` (Sistema Arrecifal Veracruzano) | 100.0% | gedi_biomass | terr_ha=12.24 |
| `tiburon_ballena` (Tiburón Ballena) | 100.0% | land_cover | terr_ha=0.0 |
| `tiburon_ballena` (Tiburón Ballena) | 100.0% | forest | terr_ha=0.0 |
| `tiburon_ballena` (Tiburón Ballena) | 100.0% | gedi_biomass | terr_ha=0.0 |
| `ventilas_hidrotermales_de_la_cuenca_de_guaymas_y_de_la_dorsal_del_pacifico_orien` (Ventilas Hidrotermales de la Cuenca de Guaymas y de la Dorsal del Pacífico Oriental) | 100.0% | land_cover | terr_ha=0.0 |
| `ventilas_hidrotermales_de_la_cuenca_de_guaymas_y_de_la_dorsal_del_pacifico_orien` (Ventilas Hidrotermales de la Cuenca de Guaymas y de la Dorsal del Pacífico Oriental) | 100.0% | forest | terr_ha=0.0 |
| `ventilas_hidrotermales_de_la_cuenca_de_guaymas_y_de_la_dorsal_del_pacifico_orien` (Ventilas Hidrotermales de la Cuenca de Guaymas y de la Dorsal del Pacífico Oriental) | 100.0% | gedi_biomass | terr_ha=0.0 |
| `zona_marina_bahia_de_los_angeles_canales_de_ballenas_y_de_salsipuedes` (Zona marina Bahía de los Ángeles, canales de Ballenas y de Salsipuedes) | 99.9% | gedi_biomass | terr_ha=483.2 |
| `zona_marina_bahia_de_los_angeles_canales_de_ballenas_y_de_salsipuedes` (Zona marina Bahía de los Ángeles, canales de Ballenas y de Salsipuedes) | 99.9% | land_cover | terr_ha=483.2 |
| `zona_marina_bahia_de_los_angeles_canales_de_ballenas_y_de_salsipuedes` (Zona marina Bahía de los Ángeles, canales de Ballenas y de Salsipuedes) | 99.9% | forest | terr_ha=483.2 |
| `zona_marina_de_la_isla_isabel` (Zona Marina de la Isla Isabel) | 100.0% | land_cover | terr_ha=0.0 |
| `zona_marina_de_la_isla_isabel` (Zona Marina de la Isla Isabel) | 100.0% | forest | terr_ha=0.0 |
| `zona_marina_de_la_isla_isabel` (Zona Marina de la Isla Isabel) | 100.0% | gedi_biomass | terr_ha=0.0 |
| `zona_marina_del_archipielago_de_espiritu_santo` (Zona marina del Archipiélago de Espíritu Santo) | 100.0% | land_cover | terr_ha=0.0 |
| `zona_marina_del_archipielago_de_espiritu_santo` (Zona marina del Archipiélago de Espíritu Santo) | 100.0% | forest | terr_ha=0.0 |
| `zona_marina_del_archipielago_de_espiritu_santo` (Zona marina del Archipiélago de Espíritu Santo) | 100.0% | gedi_biomass | terr_ha=0.0 |
| `zona_marina_del_archipielago_de_san_lorenzo` (Zona marina del Archipiélago de San Lorenzo) | 100.0% | land_cover | terr_ha=0.0 |
| `zona_marina_del_archipielago_de_san_lorenzo` (Zona marina del Archipiélago de San Lorenzo) | 100.0% | forest | terr_ha=0.0 |
| `zona_marina_del_archipielago_de_san_lorenzo` (Zona marina del Archipiélago de San Lorenzo) | 100.0% | gedi_biomass | terr_ha=0.0 |

### 5c. Implausible Population Density >500/km² (14 found)

| ANP | Population | Area km² | Density |
|-----|-----------|----------|---------|
| `lomas_de_padierna` (Lomas de Padierna) | 157,030 | 11.6 | 13523/km² |
| `cerro_de_la_estrella` (Cerro de La Estrella) | 138,206 | 11.8 | 11679/km² |
| `los_remedios` (Los Remedios) | 33,855 | 4.0 | 8460/km² |
| `cerro_de_las_campanas` (Cerro de Las Campanas) | 1,793 | 0.6 | 3064/km² |
| `xicotencatl` (Xicoténcatl) | 23,026 | 8.5 | 2705/km² |
| `humedales_de_montana_la_kisst_y_maria_eugenia` (Humedales de Montaña La Kisst y María Eugenia) | 4,283 | 2.2 | 1986/km² |
| `fuentes_brotantes_de_tlalpan` (Fuentes Brotantes de Tlalpan) | 1,925 | 1.3 | 1492/km² |
| `el_historico_coyoacan` (El Histórico Coyoacán) | 388 | 0.4 | 975/km² |
| `molino_de_flores_netzahualcoyotl` (Molino de Flores Netzahualcóyotl) | 420 | 0.5 | 920/km² |
| `sacromonte` (Sacromonte) | 387 | 0.4 | 886/km² |
| `el_tepeyac` (El Tepeyac) | 12,521 | 15.0 | 835/km² |
| `canon_del_sumidero` (Cañón del Sumidero) | 156,732 | 217.9 | 719/km² |
| `canon_del_rio_blanco` (Cañón del Río Blanco) | 293,777 | 488.0 | 602/km² |
| `el_veladero` (El Veladero) | 21,167 | 36.2 | 585/km² |

---
## Recommended Fixes (Prioritized by Impact)


### High Priority

1. **Fix `extracted_at` as dataset_type** — 199 rows have `dataset_type='extracted_at'` storing a timestamp string as JSONB data. This is a bug in the JSON→DB import script. These should be deleted from `anp_datasets` after backfilling real `extracted_at` columns.
   - `DELETE FROM anp_datasets WHERE dataset_type = 'extracted_at';`

2. **Fix SIMEC name matching** — 137/201 `simec_nom059` records contain "ANP not found in SIMEC data" errors. The SIMEC scraper's name-matching logic needs fixing — likely fuzzy matching or a manual name mapping table.

3. **Backfill missing `extracted_at` timestamps** — 13 dataset types (2328 total rows) have NULL `extracted_at`. The GEE-sourced datasets (population, forest, climate, etc.) were likely imported without timestamps. Use the `extracted_at` values stored (incorrectly) as datasets, or fall back to JSON file modification dates (~Jan 2-11, 2026).

4. **Fix CONEVAL/INEGI municipality matching** — 46 CONEVAL and 44 INEGI records show "No municipalities found within ANP bounds". Many are real ANPs (urban parks like Cumbres del Ajusco, Cerro de la Estrella) that clearly have nearby municipalities. The bounding-box intersection logic needs widening or the municipality dataset needs updating.

### Medium Priority

5. **Complete partial coverage datasets** — Priority order:
   - `land_cover`: 4 missing (Caribe Mexicano, Islas del Golfo, Pacífico Mexicano Profundo, Revillagigedo — all large/remote marine ANPs, may need `bestEffort=True` for GEE)
   - `inegi_census`: 14 missing (mix of new ANPs and Z.P.F. type areas)
   - `inaturalist`/`gedi_biomass`: 18 missing (same 18 ANPs for both)
   - `coneval_irs`: 22 missing
   - `gbif`/`simec`/`iucn`/`nom059`: 28 missing (same core set of 28)

6. **Fix GEE maxPixels errors** — 3 `gedi_biomass` and 6 `mangroves` records failed with "Too many pixels" errors for large-area ANPs (Islas del Golfo, Pacífico Mexicano Profundo, etc.). Fix by adding `bestEffort=True` or increasing `maxPixels` in the extraction scripts.

7. **Investigate area discrepancies** — 18 ANPs show >10% difference between WDPA area and `superficie_total_ha`. Top outliers:
   - Playa Huizache Caimanero: 10,594% diff (482 km² WDPA vs 4.5 km² superficie — likely WDPA includes surrounding lagoon)
   - Several "Playa" ANPs where WDPA geometry includes marine buffer not in the official area

### Low Priority

8. **Marine ANP terrestrial data cleanup** — 57 cases of marine-dominated ANPs (>95% marine) having forest/land_cover/GEDI data. Many are legitimate (e.g., Islas Marías has 24,295 terr. ha). Flag for dashboard: ANPs with 0 terrestrial hectares but non-null terrestrial data (Bajos del Norte, Tiburón Ballena, Pacífico Mexicano Profundo, etc.) should show N/A.

9. **Population density review** — 14 ANPs show >500/km² density. Most are urban parks (Lomas de Padierna at 13,523/km², Cerro de la Estrella at 11,679/km²). These are real but the dashboard should contextualize: GEE WorldPop captures surrounding urban population within the ANP boundary, not just people living inside the park.

10. **Clean up `nom059` singleton** — There's 1 row with `dataset_type='nom059'` (likely a predecessor of `nom059_enciclovida`). Verify and delete.

11. **Create `anp_expectations.json`** — Codify which datasets are expected/applicable per ANP type (marine, terrestrial, coastal, urban) to distinguish "missing data" from "not applicable".
