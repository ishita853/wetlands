# GEE Water-Quality App — Functional Specification and Sentinel Hub Migration Analysis

**Status:** Draft for review. Nothing in this document has been implemented yet.
**Source analysed:** `Wetland App GEE Code (1).txt` (the Earth Engine script for "Indian Ramsar Wetlands Water Quality Monitoring", HYDRO-CARES Lab, IIT Indore), read in full. The file is not yet in the repository.
**Cross-referenced with:** `frontend/data/ramsar-sites.json` (101 sites) and the existing FastAPI backend in `backend/app/`.

How to read this document:

- **[CODE]** means the statement comes straight from the GEE source.
- **[INFERRED]** means it follows from Earth Engine semantics but wasn't observed in a running app.
- **[VERIFY]** means it has to be confirmed before implementation. Section 25 collects all of these.

---

## Contents

1. [Feature inventory](#1-feature-inventory)
2. [Data source inventory](#2-data-source-inventory) (incl. §2.2 `S2_SR_HARMONIZED` ↔ `sentinel-2-l2a` correspondence)
3. [Sentinel-2 bands used](#3-sentinel-2-bands-used)
4. [Index inventory and formulas](#4-index-inventory-and-formulas)
5. [ROI / wetland mapping mechanism](#5-roi--wetland-mapping-mechanism)
6. [Map functions](#6-map-functions)
7. [Visualization ranges and palettes](#7-visualization-ranges-and-palettes)
8. [Legends](#8-legends)
9. [Charts](#9-charts)
10. [Reducers](#10-reducers)
11. [Scales](#11-scales)
12. [Date ranges](#12-date-ranges)
13. [Cloud filtering](#13-cloud-filtering)
14. [Cloud masking](#14-cloud-masking)
15. [Image selection logic](#15-image-selection-logic)
16. [UI controls](#16-ui-controls)
17. [Wetland selection workflow](#17-wetland-selection-workflow)
18. [GEE → Sentinel Hub migration mapping](#18-gee--sentinel-hub-migration-mapping)
19. [Process API vs Statistical API](#19-process-api-vs-statistical-api)
20. [WGS84 / GeoJSON coordinate strategy](#20-wgs84--geojson-coordinate-strategy)
21. [Missing data requirements](#21-missing-data-requirements)
22. [Scientific equivalence issues](#22-scientific-equivalence-issues)
23. [Recommended backend architecture](#23-recommended-backend-architecture)
24. [Recommended frontend workflow](#24-recommended-frontend-workflow)
25. [Items to verify before implementation](#25-items-to-verify-before-implementation)
26. [Implementation status — backend phase 1](#26-implementation-status--backend-phase-1-2026-09-24)
27. [Phase J validation status](#27-phase-j-validation-status-2026-09-24)
- [Appendix A — GEE asset → Ramsar site mapping](#appendix-a--gee-asset--ramsar-site-mapping-proposed)
- [Appendix B — Ramsar sites with no GEE ROI](#appendix-b--ramsar-sites-with-no-gee-roi)
- [Appendix C — Existing vs new portal functionality](#appendix-c--existing-gee-functionality-vs-new-portal-functionality)

---

## 1. Feature inventory

The GEE application does one thing. **For one selected Ramsar wetland and one of four spectral indices, it shows:**

1. a map of that index for a **single Sentinel-2 image**, clipped to the wetland polygon, with a colour legend;
2. a **time-series line chart** of the ROI-mean index value for every Sentinel-2 image from 2022-11-01 to 2026-05-30;
3. a **text description** of the wetland plus an attribution notice.

Complete list of functions and top-level blocks in the file:

| # | Function / block | What it does | Used? |
|---|---|---|---|
| 1 | `customMapStylea` + `mapaa` | Initial Google base map with a custom style (labels, roads and POIs hidden; land `#e0e0e0`, natural `#b0d4a3`, water `#a2daf2`), centred at lon 78.9629, lat 20.5937, zoom 5 | Yes, on the start screen only |
| 2 | `image = ee.Image('CGIAR/SRTM90_V4')` | Loads SRTM elevation | **No.** `addLayer` is commented out, so this is dead code |
| 3 | `infopanel` (25 % width) | Right-hand panel for wetland name, description and attribution | Yes, after submit |
| 4 | `printinfo(name)` | Clears `infopanel`, then shows the name and the matching `wetlandsList[].information` | Yes (bug, §5.5) |
| 5 | `panel` (30 % width) + `panelcreate()` | Left-hand control panel with the title "Indian Ramsar Wetlands Water Quality Monitoring" and an empty second label | Yes |
| 6 | `referencecreate()` | Adds the attribution text (9 px) to `infopanel` | Yes, after every submit |
| 7 | `referencecreatedup()` | Same attribution with a mailto link | **No.** Its call is commented out |
| 8 | `datasetlabel`, `paramlabel` | Labels "Select the Desired Ramsar Wetland Site:" and "Select the Desired Water Quality Parameter:" | Yes |
| 9 | `inspector` panel | Created but never added | **No** |
| 10 | `wetlandsList` (98 entries) | Name → description text | Yes, by `printinfo` |
| 11 | `table1`–`table74` | 74 `ee.FeatureCollection` assets under `projects/ee-ramsarwetlands5/assets/` | Yes |
| 12 | `rois` (74 entries) | `{roi: tableN, userId: 'N'}` | Yes, by the charts |
| 13 | `selectedROIs` | Selection flags (§5.3) | Yes |
| 14 | `nameToKeyMapping` | Dropdown name → `"tableN"` string | Yes |
| 15 | `nameToVarMapping` | Dropdown name → `tableN` FeatureCollection | Yes |
| 16 | `generateChartForROINDCI/NDTI/NDWI/NDMI` | Build the time-series chart for one index | Yes |
| 17 | `onSubmitaNDCI/NDTI/NDWI/NDMI` | Build the map, rebuild the root layout, set selection flags | Yes |
| 18 | `dropdown` (`ui.Select`) | 74 items, `Object.keys(nameToKeyMapping)` | Yes |
| 19 | `onClickSubmitButtonaNDCI/NDTI/NDWI/NDMI` | `onSubmit…()` → `makecheckchart…()` → `referencecreate()` | Yes |
| 20 | `buttonPanel` with 4 buttons (NDCI, NDTI, NDWI, NDMI) | Each button chooses the index **and** submits | Yes |
| 21 | `makecheckchartNDCI/NDTI/NDWI/NDMI` | Replace the chart panel (500×300 px) in `panel` | Yes |
| 22 | `makemapNDWI/NDCI/NDTI/NDMI` | Build a new `ui.Map` with the ROI layer, index layer and legend | Yes |

**Not in the GEE application:** climate analysis (drought, precipitation extremes, heat waves, cold waves), dot-density or national overview maps, wetland comparison, date pickers, cloud-threshold controls, statistics beyond the mean, data export. See Appendix C.

The four chart functions are identical except for the index. The same is true of the four map functions (apart from palette and legend), the four submit handlers and the four chart-panel functions. Everything can be generalized to one parameterized pipeline driven by an index definition table.

---

## 2. Data source inventory

| Item | Value | Where |
|---|---|---|
| Satellite collection | `COPERNICUS/S2_SR_HARMONIZED` (Sentinel-2 MSI Level-2A surface reflectance, harmonized) | All 8 chart and map functions [CODE] |
| Wetland ROIs | 74 `ee.FeatureCollection` table assets: `projects/ee-ramsarwetlands5/assets/<name>` | `table1`…`table74` [CODE] |
| Wetland descriptions | Hard-coded strings in `wetlandsList` | [CODE] |
| Elevation | `CGIAR/SRTM90_V4`, loaded but never displayed | Dead code [CODE] |
| Base map | Google Maps via `ui.Map` (custom style on the start map, default style after submit) | [CODE] |

### 2.1 Collection preprocessing, by code path

**The two code paths preprocess differently.** This is a documented inconsistency and must not be "fixed" silently.

| Step | Chart path (`generateChartForROI*`) | Map path (`makemap*`) |
|---|---|---|
| Collection | `COPERNICUS/S2_SR_HARMONIZED` | `COPERNICUS/S2_SR_HARMONIZED` |
| Spatial filter | `.filterBounds(roi)` | `.filterBounds(ROI)` |
| Date filter | `.filterDate('2022-11-01', '2026-05-30')` | `.filterDate('2022-11-01', '2026-05-30')` |
| Cloud filter | `.filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 100)` | `.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 100))`. Same semantics, different syntax |
| Sort | `.sort('CLOUDY_PIXEL_PERCENTAGE', true)` (ascending) | `.sort('CLOUDY_PIXEL_PERCENTAGE', true)` (ascending) |
| Cloud mask | **None** | **QA60 bits 10 and 11** (`maskS2clouds`) |
| Reflectance scaling | **None** (raw DN, 0–10000 scale) | **`.divide(10000)`** inside `maskS2clouds` |
| Index | `normalizedDifference([a, b])` | `normalizedDifference([a, b])` |

Notes:

- **Scaling:** a normalized difference `(a−b)/(a+b)` is unchanged by multiplying both bands by the same factor. So the `/10000` difference between paths does **not** change index values [INFERRED]. It is still recorded because it would matter for any non-ratio index added later.
- **Sort in the chart path:** `ui.Chart.image.series` plots against `system:time_start`, so the cloud-percentage sort has no visible effect on the chart [INFERRED].
- **Cloud mask in the chart path:** there is none. Cloudy pixels contribute to the chart's ROI mean. The chart and the map therefore apply different masking to the same scenes.
- **Harmonization:** `S2_SR_HARMONIZED` removes the `BOA_ADD_OFFSET` (−1000 DN) introduced by ESA processing baseline 04.00 (25 Jan 2022), so DN values are comparable across baselines [GEE catalog]. This **does** matter for normalized differences, because an additive offset is not cancelled by the ratio (§22.1).

### 2.2 Dataset correspondence: `COPERNICUS/S2_SR_HARMONIZED` ↔ Sentinel Hub `sentinel-2-l2a`

**`COPERNICUS/S2_SR_HARMONIZED` is the scientific reference.** The migration target is the CDSE Sentinel Hub collection `sentinel-2-l2a`. This section records how closely the two correspond. It does **not** assume they are identical.

Sources (read 2026-09-24):
- GEE catalog: `developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED` ("GEE catalog" below).
- CDSE docs: `documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html` and `…/Data/SentinelMissions/Sentinel2.html` ("CDSE docs" below).

**Common origin.** The GEE catalog states: *"The Sentinel-2 L2 data are downloaded from CDSE. They were computed by running sen2cor."* The CDSE docs state that L2A is produced by ESA's Sen2Cor, *"in most cases … by ESA itself."* So both collections are built from **the same upstream ESA L2A products (same Sen2Cor surface reflectance)**. They are two distributions of the same product, not two different products. The differences below come from each platform's ingestion, value conventions and access model, not from different atmospheric correction.

#### 2.2.1 Correspondence table

Status key:
- ✅ equivalent;
- ≈ equivalent in the values that matter for the four indices, with a documented caveat;
- ⚠ differs, needs verification or a decision;
- ❌ no equivalent exists.

| Aspect | `COPERNICUS/S2_SR_HARMONIZED` (GEE) | `sentinel-2-l2a` (Sentinel Hub, CDSE) | Status |
|---|---|---|---|
| **Product level** | Sentinel-2 MSI Level-2A, bottom-of-atmosphere surface reflectance | Sentinel-2 MSI Level-2A, BOA surface reflectance | ✅ |
| **Surface reflectance processing** | Sen2Cor; products downloaded from CDSE | Sen2Cor; processed by ESA | ✅ same upstream products |
| **Reprocessing / baselines** | Keeps the `PROCESSING_BASELINE` of each ingested granule. Whether Collection-1 reprocessed granules (baseline 05.xx, covering data up to 13 Dec 2023) replaced, were added alongside, or were not ingested is **not stated** | CDSE is moving all historical L2A (up to 13 Dec 2023) to baseline ≥ 05.00 (Collection-1). Which version Sentinel Hub serves for a given date isn't stated | ⚠ Our window 2022-11-01 → 2023-12-13 lies inside the Collection-1 range, so the same acquisition **could exist at different baselines** in the two archives. Needs a per-scene baseline comparison |
| **Harmonization** | For `PROCESSING_BASELINE ≥ 04.00` (after 2022-01-25) the DN range is *"shifted by 1000"* so newer scenes match older ones: harmonized DN ≈ DN − 1000 | `harmonizeValues: true` (default): DN are *"harmonized so they are comparable with data from previous baselines"*; negatives are **clamped to 0** | ≈ Same intent and same offset. Behaviour at the low end (whether GEE also floors at 0 or masks) must be checked. This matters for **water pixels**, where B8 and B11 are near 0 (§2.2.2) |
| **Value encoding / scaling** | UINT16 DN, scale 0.0001 (SR × 10000) | `units: "DN"` (SR × 10000) or `"REFLECTANCE"` (default, DN/10000) | ✅ Scale cancels in all four normalized differences. Use `DN` for a literal match |
| **Spectral bands used** | B3, B4, B5, B8, B11 (Sentinel-2A/B centre wavelengths per band table) | B03, B04, B05, B08, B11: same MSI bands | ✅ Band names differ by zero-padding only |
| **Native resolution** | B3, B4, B8: 10 m; B5, B11: 20 m | Same | ✅ |
| **Resampling** | Computed in the requested output projection. Downsampling reads GEE's image pyramid (mean-aggregated); upsampling is nearest by default [VERIFY] | `upsampling` and `downsampling` default to **NEAREST**; BILINEAR and BICUBIC available. No mean/area aggregation | ⚠ Matters for the charts at 1000 m (§22.5) and for mixing 10 m and 20 m bands (NDCI, NDMI) |
| **Other bands** | B1, B2, B6, B7, B8A, B9, B12, AOT, WVP, SCL, TCI_R/G/B, MSK_CLDPRB, MSK_SNWPRB, **QA60**, **MSK_CLASSI_OPAQUE / _CIRRUS / _SNOW_ICE** | B01, B02, B06, B07, B8A, B09, B12, AOT, SCL, SNW, CLD, angle bands, `dataMask`. **No QA60, no MSK_CLASSI_*, no TCI** | ❌ for QA60 (the only auxiliary band the GEE app uses) |
| **Cloud / QA information** | QA60 bits 10 (opaque) and 11 (cirrus). **QA60 is "masked out between 2022-01-25 to 2024-02-28 inclusive"**. From 2024-02-28 it is *"constructed from the MSK_CLASSI cloud classification bands"* | SCL (Sen2Cor classes 0–11), CLD (cloud probability), SNW. No equivalent of ESA's MSK_CLASSI-derived QA60 | ❌ No one-to-one equivalent (§14) |
| **Scene metadata: cloud %** | `CLOUDY_PIXEL_PERCENTAGE` per granule (the app filters and sorts on it). `CLOUD_COVERAGE_ASSESSMENT` also present | `dataFilter.maxCloudCoverage` works on per-tile cloud cover. The Catalog exposes `eo:cloud_cover`. **Which ESA field it's populated from is not stated** | ⚠ Verify that `eo:cloud_cover` == `CLOUDY_PIXEL_PERCENTAGE` for the same granule |
| **Scene metadata: other** | `MGRS_TILE`, `PROCESSING_BASELINE`, `SENSING_ORBIT_NUMBER`, `SPACECRAFT_NAME`, `DATATAKE_IDENTIFIER`, per-band incidence angles, `system:time_start`, `system:index` (`<datatake>_<generation>_T<tile>`) | Catalog (STAC) items with tile id, datetime, cloud cover, and (expected) platform and processing-baseline properties; `scenes` metadata in evalscripts with ORBIT/TILE mosaicking | ≈ Enough to identify the same granule [VERIFY property names] |
| **Unit of data** | **One image per granule** (one MGRS tile, one datatake). The app's filters, sorting, `.first()` and charts all operate per granule | **Tiles are mosaicked** over the requested area and time range (`mosaicking: SIMPLE` default; ORBIT/TILE give access to individual scenes inside an evalscript). Tile selection filters (a specific MGRS tile id) in `dataFilter`: **not documented** | ⚠ Largest structural difference (§2.2.3) |
| **Mosaicking order** | Not applicable: the app picks one granule with `.sort(CLOUDY…).first()` | `mosaickingOrder`: `mostRecent` (default), `leastRecent`, `leastCC` | ⚠ `leastCC` mixes scenes pixel-by-pixel; it is **not** "one least-cloudy granule" |
| **Acquisition dates** | `system:time_start` = granule sensing time (UTC) | Scene/tile `datetime` (UTC), same datatake | ✅ Same acquisitions. Duplicate granules (same tile and date, different generation or baseline) may be handled differently [VERIFY] |
| **Temporal availability** | 2017-03-28 → present (*"2017-2018 L2 coverage … not yet global"*); ingestion lags CDSE | Global L2A archive (CDSE docs: *"from 2015 onwards"* via reprocessing); near-real-time | ✅ for the app window 2022-11-01 → 2026-05-30: both archives are complete and global in this period. Recent days may appear earlier in CDSE than in GEE |
| **Spatial coverage** | Global land and coastal | Global land and coastal | ✅ |
| **Licence** | Copernicus Sentinel Data Terms and Conditions | Same | ✅ |

#### 2.2.2 What this means for the four index formulas

| Index | Formula (unchanged) | GEE bands → SH bands | Correspondence |
|---|---|---|---|
| NDCI | (B5 − B4) / (B5 + B4) | B5, B4 → B05, B04 | Same bands and formula. B5 is 20 m and B4 is 10 m; resampling differs (see table) |
| NDTI | (B3 − B4) / (B3 + B4) | B3, B4 → B03, B04 | Same bands and formula, both 10 m |
| NDWI | (B3 − B8) / (B3 + B8) | B3, B8 → B03, B08 | Same bands and formula, both 10 m. **Sensitive to the low-end harmonization caveat:** over open water B8 is near 0, so clamping or masking at 0 changes the result |
| NDMI | (B8 − B11) / (B8 + B11) | B8, B11 → B08, B11 | Same bands and formula. B11 is 20 m. **Sensitive to the low-end caveat:** over water both bands are near 0, so small absolute differences cause large index changes |

The formulas map exactly. The **input values** should be identical wherever the two archives hold the same granule at the same processing baseline, both apply the −1000 harmonization, and no pixel is at or below the offset floor. Each of these conditions is on the verification list (§25).

#### 2.2.3 Granule vs mosaic

GEE treats every granule as a separate image. Sentinel Hub returns a mosaic over the requested geometry and time range. In practice:

- **Map (one "least-cloudy" granule):** Sentinel Hub cannot be told "use only MGRS tile T43QHU" (not documented). What we can do is find the granule in the Catalog, then request the Process API for **that acquisition's time window only**. Adjacent tiles from the same datatake will then also fill the ROI. That shows **more** of the wetland than GEE did, from the same acquisition. Using `mosaickingOrder: "leastCC"` over the whole period would mix dates, and is **not** acceptable as a reproduction.
- **Time series (one point per granule):** the Statistical API gives **one value per interval** (P1D), computed over the mosaic. For wetlands inside a single tile, this matches GEE's per-granule series. For wetlands crossing tile boundaries or orbit overlaps, GEE plots several partial-ROI points per date and Sentinel Hub plots one whole-ROI point. Whether a per-tile breakdown is possible (ORBIT/TILE mosaicking inside a Statistical API evalscript) must be tested.

#### 2.2.4 Result: exact one-to-one mapping is **not** possible

Items where `sentinel-2-l2a` **cannot** exactly reproduce `COPERNICUS/S2_SR_HARMONIZED`, as used by this app:

| # | Difference | Affects | Why it can't be exact |
|---|---|---|---|
| X1 | **QA60 cloud mask unavailable** (and, in GEE, QA60 is masked for 2022-01-25 → 2024-02-28) | Maps | Band doesn't exist in Sentinel Hub L2A; MSK_CLASSI isn't exposed either. See §14 |
| X2 | **Granule-level image vs mosaic** | Map scene coverage, chart points for multi-tile wetlands | Sentinel Hub has no documented per-tile filter |
| X3 | **Resampling** (GEE pyramid mean vs Sentinel Hub nearest/bilinear/bicubic) | Charts at 1000 m; 20 m bands | Sentinel Hub offers no mean/area downsampling |
| X4 | **Possible baseline/reprocessing mismatch** for 2022-11-01 → 2023-12-13 | Pixel values | Depends on what each archive ingested. Can only be checked per scene |
| X5 | **Low-end harmonization behaviour** (clamp vs mask at 0) | NDWI and NDMI over water | Depends on GEE's exact implementation; needs a pixel test |

X4 and X5 might turn out to be zero differences after testing. X1–X3 are real platform differences. **Per the instruction, no methodology change will be made for any of them without your approval.** The decisions needed are listed in §25, items 18–20.

---

## 3. Sentinel-2 bands used

Only bands that actually occur in the code:

| GEE band | Sentinel-2 meaning | Native res. | Used by | Sentinel Hub L2A name |
|---|---|---|---|---|
| B3 | Green (~560 nm) | 10 m | NDTI, NDWI | `B03` |
| B4 | Red (~665 nm) | 10 m | NDCI, NDTI | `B04` |
| B5 | Red edge 1 (~705 nm) | 20 m | NDCI | `B05` |
| B8 | NIR, broad (~842 nm) | 10 m | NDWI, NDMI | `B08` |
| B11 | SWIR 1 (~1610 nm) | 20 m | NDMI | `B11` |
| QA60 | Cloud mask bitmask (bit 10 opaque, bit 11 cirrus) | 60 m | Map-path cloud mask | **Not available** in Sentinel Hub `sentinel-2-l2a` (§14) |

**Not used anywhere:** B1, B2, B6, B7, B8A, B9, B12, SCL, AOT, WVP, MSK_CLDPRB, MSK_SNWPRB, MSK_CLASSI_*. The example table in the brief listed B2 and B12, but neither appears in the code.

Image properties used: `CLOUDY_PIXEL_PERCENTAGE` (filter and sort) and `system:time_start` (implicitly, as the chart x-axis).

Sentinel Hub L2A auxiliary bands that exist and may serve as substitutes (from CDSE documentation): `SCL` (20 m), `CLD` cloud probability (20 m), `SNW` snow probability (20 m), `dataMask`.

---

## 4. Index inventory and formulas

**There are exactly four indices.** No other index, band ratio, expression or classification occurs anywhere in the file.

GEE's `normalizedDifference([a, b])` computes `(a − b) / (a + b)`.

### 4.1 NDCI — Normalized Difference Chlorophyll Index

| Field | Value |
|---|---|
| Formula | `(B5 − B4) / (B5 + B4)` |
| GEE bands | `B5`, `B4` |
| Sentinel Hub bands | `B05`, `B04` |
| Theoretical range | −1 … +1 |
| Map vis range | min −1, max 1 |
| Palette | `['lightblue', '7CFC00', '808000', '006400']` |
| Legend title | `NDCI` |
| Legend labels (top → bottom) | High Chlorophyll Content (`006400`), Moderate Chlorophyll Content (`808000`), Low Chlorophyll Content (`7CFC00`), Clear Water (`lightblue`) |
| Chart title | `NDCI Time Series - Ramsar ID: <N>` |
| Chart axes | h: `Date`, v: `NDCI Value` |
| Map usage | `makemapNDCI` |
| Time-series usage | `generateChartForROINDCI` |

### 4.2 NDTI — Normalized Difference Turbidity Index

| Field | Value |
|---|---|
| Formula | `(B3 − B4) / (B3 + B4)` |
| GEE bands | `B3`, `B4` |
| Sentinel Hub bands | `B03`, `B04` |
| Theoretical range | −1 … +1 |
| Map vis range | min −1, max 1 |
| Palette | `['red', 'A6CAE0', '00008B']` |
| Legend title | `NDTI` |
| Legend labels | High Turbidity (`red`), Moderate Turbidity (`A6CAE0`), Clear Water (`00008B`) |
| Chart title / axes | `NDTI Time Series - Ramsar ID: <N>`; `Date` / `NDTI Value` |
| Map usage | `makemapNDTI` |
| Time-series usage | `generateChartForROINDTI` |

### 4.3 NDWI — Normalized Difference Water Index (McFeeters form: Green/NIR)

| Field | Value |
|---|---|
| Formula | `(B3 − B8) / (B3 + B8)` |
| GEE bands | `B3`, `B8` |
| Sentinel Hub bands | `B03`, `B08` |
| Theoretical range | −1 … +1 |
| Map vis range | min −1, max 1 |
| Palette | `['32CD32', 'yellow', 'blue']` |
| Legend title | `NDWI` |
| Legend labels | Low Water Content (`32CD32`), Moderate Water Content (`yellow`), High Water Content (`blue`) |
| Code comment (not rendered) | `//-1 to 0 "Low Water Content"; 0 to 0.5 "Moderate Water Content"; 0.5 to 1 "High Water Content"` |
| Chart title / axes | `NDWI Time Series - Ramsar ID: <N>`; `Date` / `NDWI Value` |
| Map usage | `makemapNDWI` |
| Time-series usage | `generateChartForROINDWI` |

### 4.4 NDMI — Normalized Difference Moisture Index

| Field | Value |
|---|---|
| Formula | `(B8 − B11) / (B8 + B11)` |
| GEE bands | `B8`, `B11` |
| Sentinel Hub bands | `B08`, `B11` |
| Theoretical range | −1 … +1 |
| Map vis range | min −1, max 1 |
| Palette | `['#00008B', '#800080', 'lightgreen', 'darkgreen']` |
| Legend title | `NDMI` |
| Legend labels | Negligible Vegetation (`#00008B`), Low Moisture Vegetation (`#800080`), Moderate Moisture Vegetation (`lightgreen`), `High Moisture Vegetation ` (trailing space in source) (`darkgreen`) |
| Chart title / axes | `NDMI Time Series - Ramsar ID: <N>`; `Date` / `NDMI Value` |
| Map usage | `makemapNDMI` |
| Time-series usage | `generateChartForROINDMI` |

### 4.5 Edge-case semantics to reproduce

- **Negative inputs:** GEE `normalizedDifference` masks the output pixel when either input is negative [VERIFY against current GEE docs]. Harmonized L2A DN values should be ≥ 0, and Sentinel Hub `harmonizeValues: true` clamps negatives to 0. The two may behave differently at the rare negative pixel.
- **Zero sum (`a + b = 0`):** GEE output for this case must be confirmed [VERIFY]. In the evalscript it must be handled explicitly (proposed: treat as no-data, `dataMask = 0`).
- **No-data:** GEE masks L2A no-data pixels automatically. Sentinel Hub needs `dataMask` in the evalscript.

---

## 5. ROI / wetland mapping mechanism

### 5.1 Identifiers

The GEE app has **no Ramsar site numbers** anywhere. A wetland is identified by:

1. an **asset name string** such as `"east_kolkata"`, `"chilka"` or `"Pong_Dam_Lake_Wildlife_Sanctuary"`. Casing and spelling are inconsistent and sometimes not the official name;
2. a **table index** `N` from 1 to 74 (`tableN`), assigned alphabetically-ish.

### 5.2 Name → geometry chain (map path)

```
dropdown value (asset name)
   → nameToVarMapping[name]               → tableN (ee.FeatureCollection)
   → makemap<INDEX>(tableN)
```

### 5.3 Name → geometry chain (chart path)

This path is indirect:

```
dropdown value (asset name)
   → nameToKeyMapping[name]                → "tableN" (string)
   → selectedROIs["tableN"] = true          (every other "tableK" key is reset to false first)
   → makecheckchart<INDEX>() loops i = 0..73, builds key "table"+(i+1),
     and picks the first rois[i] whose key is true
   → generateChartForROI<INDEX>(rois[i])    → rois[i].roi = tableN, rois[i].userId = "N"
```

- This only works because `rois[i]` is in the same order as `table(i+1)`. It is.
- `selectedROIs` is first declared with asset-name keys that are never read. The "Populate selectedROIs" loop then adds `table1`…`table74` keys, which are the ones actually used. The asset-name keys are dead state.

### 5.4 The chart's "Ramsar ID" is not a Ramsar ID

The chart title is `'… Time Series - Ramsar ID: ' + userId`, and `userId` is the **table index 1–74**, not the Ramsar site number. For example, Chilika Lake (Ramsar site 229) is titled "Ramsar ID: 9". **This label must not be carried into the new application.** The new app should use the real Ramsar site number (`id` in `ramsar-sites.json`).

### 5.5 Description lookup (`printinfo`) and its bugs

`printinfo(name)` does a linear search of `wetlandsList` for `wetlandsList[i].name == name`, then reads `wetlandsList[i].information`. It indexes with the loop variable `i`, not with `index`. From static reading:

- **98 entries** in `wetlandsList`. **Six names are duplicated:** Chitrangudi_Bird_Sanctuary, Vedanthangal_Bird_Sanctuary, Vellode_Bird_Sanctuary, Vembannur_Wetland_Complex, Wadhvana_Wetland and Yashwant_Sagar. The first match wins, so Vedanthangal, Vellode, Vembannur, Wadhvana and Yashwant show the short version and Chitrangudi shows the long version.
- **One entry has a typo key `nmae:`** (Kanjirankulam_Bird_Sanctuary), so its `name` is `undefined`. Selecting **Kanjirankulam** in the dropdown finds no match, the loop ends with `i = 98`, and `wetlandsList[98].information` throws a TypeError. That aborts `onSubmit…` **before the map is built**, so no map, chart or description appears for that site [INFERRED; VERIFY in the live app].
- **19 entries can never be displayed** because their name matches no dropdown key. Examples are `Deepor_Beel`, `East_Calcutta_Wetlands`, `Chilika_Lake`, `Wular_Lake`, `Kolleru_Lake`, `Nalsarovar`, `Pong_Dam_Lake`, `"Gulf of Mannar Marine Biosphere Reserve"` (spaces), plus 5 sites that have no ROI at all: Aghanashini Estuary, Ankasamudra, Chandertal, Longwood Shola and Magadi Kere.
- The texts are paraphrased from Ramsar Information Sheets. Several contain PDF-extraction damage: dropped "fi"/"fl" ligatures, as in "ows" for "flows", "sh" for "fish" and "oods" for "floods".

**Recommendation:** the new app should **not** reuse `wetlandsList`. `ramsar-sites.json` already holds a `summary` field from the Ramsar Sites Information Service for all 101 sites, which is the more authoritative source. Whether any GEE text must be kept is a decision for the reviewer.

### 5.6 Geometry source

- Each ROI is an **`ee.FeatureCollection` table asset** (uploaded shapefile). The script contains no geometry at all. The file header says the assets are "official shapefiles" from Ramsar.
- **Chart path:** `roi.geometry()` dissolves all features of the collection into one geometry, which is the reduction region.
- **Map path:** the FeatureCollection itself is used for `filterBounds`, `clip`, `centerObject` and the red outline layer.
- Whether each asset is a polygon, multipolygon, or has several features (e.g., Surinsar-Mansar is two lakes, Keoladeo "and Ajan Bande") is unknown [VERIFY].

### 5.7 Polygon or point?

**The calculations need a polygon.** Every operation uses the ROI as an area:

- `clip(ROI)` for the map;
- `reduceRegion`-style mean over `roi.geometry()` for the chart;
- `filterBounds` for scene selection, where point and polygon give different results for large sites.

A latitude/longitude point **cannot reproduce** the GEE results. A reduction over a point returns a single pixel value, not an ROI mean. Any buffer radius would be an arbitrary substitute, so per the brief none is proposed. **The 74 wetland polygons are a required input (§21).**

### 5.8 Coverage against the portal's 101 sites

All 74 asset names can be matched to 74 **distinct** sites in `ramsar-sites.json`. 53 are exact after normalising case and underscores, and 21 were matched manually (Appendix A). **27 of the 101 sites have no GEE ROI** (Appendix B), mostly sites designated in 2023–2026. For these, the analysis cannot be reproduced until polygons are obtained.

---

## 6. Map functions

There are five maps: the start map and one per index.

### 6.1 Start map (`mapaa`)

- `ui.Map()` with custom style `Custom` (§1, row 1). Centre `setCenter(78.9629, 20.5937, 5)` (lon, lat, zoom).
- No layers. It shows no wetland points or boundaries.
- It is discarded after the first submit (`ui.root.clear()`) and never comes back.

### 6.2 Index maps (`makemapNDWI`, `makemapNDCI`, `makemapNDTI`, `makemapNDMI`)

All four are identical except for the index, palette and legend:

| Aspect | Behaviour [CODE] |
|---|---|
| Map object | A **new** `ui.Map()` on each submit, with the **default** Google base map (the custom style is not re-applied) |
| Layer 1 | `map.addLayer(ROI, {color: 'red'}, 'Wetland Site')`: FeatureCollection drawn with a red outline and semi-transparent red fill (GEE default FC rendering) |
| Zoom / centre | `map.centerObject(ROI, 14)`. **Fixed zoom 14** for every site, whatever its size. For large sites (Sundarbans, Gulf of Mannar, Chilika, Vembanad-Kol) only part of the ROI is visible at first |
| Image collection | §2.1, map path (QA60 mask, `/10000`) |
| Selected image | `ee.Image(collection.first())`: the single lowest-`CLOUDY_PIXEL_PERCENTAGE` image (§15) |
| Layer 2 | `firstImage.select('<INDEX>').clip(ROI)`, vis `{min: -1, max: 1, palette: …}`, name `'NDWI'` / `'NDCI'` / `'NDTI'` / `'NDMI'` |
| Layer order | The index layer is drawn **above** the red ROI layer, so red shows only where the index is masked (clouds, outside the scene footprint) |
| Legend | `ui.Panel` at `position: 'bottom-left'`, padding `8px 15px`; bold 18 px title; one row per palette colour with a 25 px swatch and label |
| Other layers | None. No true-colour image, no acquisition date shown, no scale bar |
| Pixel resolution | Computed on the fly at the map's zoom level (GEE tiles). Not fixed |

---

## 7. Visualization ranges and palettes

All four index layers use `min: -1, max: 1`. GEE spreads the palette colours at equal intervals over `[min, max]` and interpolates linearly between them. Values outside the range are clamped.

| Index | Stops (value → colour) |
|---|---|
| NDCI | −1 → `lightblue` (#ADD8E6), −⅓ → `7CFC00`, +⅓ → `808000`, +1 → `006400` |
| NDTI | −1 → `red` (#FF0000), 0 → `A6CAE0`, +1 → `00008B` |
| NDWI | −1 → `32CD32`, 0 → `yellow` (#FFFF00), +1 → `blue` (#0000FF) |
| NDMI | −1 → `#00008B`, −⅓ → `#800080`, +⅓ → `lightgreen` (#90EE90), +1 → `darkgreen` (#006400) |

CSS colour names are resolved to hex as shown. The new app must use the hex values so rendering is identical.

---

## 8. Legends

- The legends are **categorical swatches for a continuous gradient**. They show the palette stop colours with descriptive labels but **no numeric ranges or thresholds**.
- The only numeric breaks in the file are in the **NDWI comment** (−1–0, 0–0.5, 0.5–1). They are **not** consistent with the rendered gradient, where yellow is at exactly 0 and blue at 1. They also aren't shown to users. The new app should reproduce the legend as rendered, not the comment.
- Legend row order: NDWI and NDTI follow palette order (−1 first). NDCI is reversed (high chlorophyll first). NDMI follows palette order.
- The legend labels are the original authors' interpretation (e.g., NDTI red = "High Turbidity"). This spec does not change them.

**Proposed for the new app (to be approved):** a continuous colour bar with the −1 … +1 scale and the original labels placed at their stop positions. This keeps the original meaning and adds the numeric scale the GEE legend lacks.

---

## 9. Charts

There are four charts, one per index, all built the same way:

| Aspect | Value [CODE] |
|---|---|
| Builder | `ui.Chart.image.series({imageCollection, region, reducer, scale})` |
| Image collection | `S2_SR_HARMONIZED` → filterBounds → 2022-11-01…2026-05-30 → `CLOUDY_PIXEL_PERCENTAGE < 100` → sorted → index band only. **No cloud mask, no scaling** |
| Region | `roi.geometry()`: the dissolved FeatureCollection geometry |
| Reducer | `ee.Reducer.mean()` |
| Scale | `1000` (metres) |
| X axis | Image acquisition time (`system:time_start`, the chart default); title `Date` |
| Y axis | `<INDEX> Value` |
| Series | One series (the index band) |
| Points | **One per image**, i.e. per Sentinel-2 **granule (MGRS tile)** intersecting the ROI [INFERRED]. A wetland spanning two tiles or an orbit overlap gets several points per acquisition date, each a mean over only the part of the ROI that granule covers |
| Chart type | `LineChart` |
| Title | `<INDEX> Time Series - Ramsar ID: <table index>` (not a real Ramsar ID, §5.4) |
| Container | `ui.Panel` 500×300 px, added to the left `panel` under the buttons, replacing any previous chart |
| Null handling | Images where the ROI mean is null (fully masked) are omitted by GEE [INFERRED] |
| Interactivity | Standard GEE/Google Charts hover tooltip; pop-out for CSV/PNG download via the GEE chart menu |

Because the chart path has **no cloud mask**, cloudy acquisitions add cloud-contaminated values to the series. That is the GEE behaviour to reproduce, or to change only by explicit decision (§22.4).

---

## 10. Reducers

| Where | Reducer | Notes |
|---|---|---|
| All 4 charts | `ee.Reducer.mean()` | In region reductions, GEE's mean is **weighted by each pixel's fractional overlap** with the region [INFERRED/VERIFY] |
| Maps | none | Visualization only |

No other reducers (median, percentile, count, min/max, temporal composites) are used anywhere.

---

## 11. Scales

| Where | Scale |
|---|---|
| Charts | `scale: 1000` m. The index is evaluated at 1 km nominal pixels in the image's default projection. GEE reads bands from its image pyramid (mean-downsampled for S2) and computes the ratio **from 1 km-averaged reflectances**, not as the mean of 10 m index values [INFERRED/VERIFY] |
| Maps | Map zoom level (dynamic) |

**Consequence:** for small wetlands (e.g., Vembannur 19.7 ha, Vedanthangal 40 ha, Sirpur 161 ha) a 1 km pixel is larger than the whole ROI. The chart value is then a weighted mean of one or a few 1 km pixels that are mostly **outside** the wetland (§22.5).

---

## 12. Date ranges

| Where | Start | End | Notes |
|---|---|---|---|
| All 4 charts and all 4 maps | `2022-11-01` | `2026-05-30` | Hard-coded identically in 8 places. `filterDate` end is **exclusive**, so the last included day is 2026-05-29 |

- The window starts after the processing-baseline 04.00 change (2022-01-25), so every scene has the new DN offset convention. The collection is harmonized, so values are comparable anyway.
- As of this document (2026-09-24) the end date is in the past. Data acquired after 2026-05-29 are excluded.
- **New app:** the default range will be exactly `2022-11-01` → `2026-05-30` (end exclusive, or `2026-05-29T23:59:59Z` inclusive). Users can change it. Changing the default is the reviewer's decision.

---

## 13. Cloud filtering

- Both paths filter on `CLOUDY_PIXEL_PERCENTAGE < 100` (strictly less than). This drops only granules reported as 100 % cloudy and, because of how GEE metadata filters work, granules missing the property [INFERRED]. **In practice this is almost no filtering.**
- `CLOUDY_PIXEL_PERCENTAGE` is a **granule-level (whole 110×110 km tile)** figure, not the cloud cover over the wetland.
- **Sentinel Hub equivalent:** `dataFilter.maxCloudCoverage`, which works on tile-level cloud cover (inclusive upper bound, "at most N %"). To reproduce `< 100` exactly we'd need to exclude tiles at exactly 100 %, e.g. with a Catalog API query on `eo:cloud_cover < 100` [VERIFY how CDSE fills `eo:cloud_cover` for L2A: `CLOUDY_PIXEL_PERCENTAGE` or `CLOUD_COVERAGE_ASSESSMENT`].

---

## 14. Cloud masking

### 14.1 Exact GEE implementation (map path only)

```javascript
function maskS2clouds(image) {
  var qa = image.select('QA60');
  var cloudBitMask = 1 << 10;   // 1024 — opaque clouds
  var cirrusBitMask = 1 << 11;  // 2048 — cirrus
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
    .and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  return image.updateMask(mask).divide(10000);
}
```

It keeps a pixel only if QA60 bit 10 (opaque cloud) **and** bit 11 (cirrus) are both 0. It does **not** mask cloud shadows, snow or saturated pixels. QA60 is a 60 m raster, so the mask is blocky at 10–20 m.

### 14.2 QA60 in this date range (confirmed in the GEE catalog)

The GEE catalog for `COPERNICUS/S2_SR_HARMONIZED` states that QA60 is **"masked out between 2022-01-25 to 2024-02-28 inclusive"**. From 2024-02-28, *"legacy-consistent QA60 bands are constructed from the MSK_CLASSI cloud classification bands"*. The app window 2022-11-01 → 2026-05-30 therefore splits into two regimes:

| Scene date | QA60 state | Effect of `maskS2clouds` [INFERRED from Earth Engine masking semantics; VERIFY] |
|---|---|---|
| 2022-11-01 → 2024-02-28 | **Masked (no data)** | `qa.bitwiseAnd(...).eq(0)` is masked, so `updateMask(mask)` masks **every pixel**. The index layer is **empty**, and only the red ROI layer is visible |
| 2024-02-28 → 2026-05-29 | Populated from MSK_CLASSI | Mask works as written: opaque clouds and cirrus removed, at 60 m |

Because the map uses the **single** lowest-`CLOUDY_PIXEL_PERCENTAGE` granule from the whole window, the GEE map shows index pixels only if that granule is dated 2024-02-28 or later. Otherwise it shows a blank index layer over the red ROI. Which case applies is site-specific and must be checked in GEE (§25, item 5). If confirmed, this is a **defect of the reference app**, not intended methodology. Reproducing it faithfully would mean deliberately showing empty maps for some wetlands.

The chart path is unaffected because it applies no cloud mask.

### 14.3 Sentinel Hub options (no exact one-to-one equivalent)

Sentinel Hub `sentinel-2-l2a` does **not** provide `QA60` (CDSE band list: B01–B12, B8A, AOT, SCL, SNW, CLD, angles, dataMask). There is **no exact equivalent**.

| Option | Pixels masked | Closeness to GEE intent (opaque + cirrus, no shadows) |
|---|---|---|
| **A. SCL ∈ {8, 9, 10}** (cloud medium prob., cloud high prob., cirrus) | Clouds and cirrus from Sen2Cor scene classification, 20 m | **Closest in intent**: same two categories, no shadow masking. Different algorithm and resolution than QA60 |
| B. SCL ∈ {3, 8, 9, 10} | Adds cloud shadows | Stricter than GEE (masks shadows, which GEE doesn't) |
| C. `CLD` > threshold | Sen2Cor cloud probability | Needs a threshold, so it introduces a new parameter |
| D. No mask | Nothing | Matches GEE exactly **if** §14.2 shows QA60 is empty for these scenes |

None of A–D reproduces GEE exactly:
- **Scenes before 2024-02-28:** GEE masks *everything* (§14.2). Nothing sensible reproduces that.
- **Scenes from 2024-02-28:** GEE masks with ESA's MSK_CLASSI opaque and cirrus classes, which Sentinel Hub doesn't expose.

Option A (SCL 8/9/10) is the closest in intent: same two cloud categories, no shadow masking. It uses a different classifier (Sen2Cor SCL instead of ESA's MSK_CLASSI) at 20 m instead of 60 m.

**This is a methodology decision and is left for your approval** (§25, item 18). No option will be implemented before then.

The chart path uses no cloud mask in GEE, so the default time series should also be unmasked, unless the reviewer chooses otherwise (§22.4).

---

## 15. Image selection logic

**Map image:** `collection.sort('CLOUDY_PIXEL_PERCENTAGE', true).first()` returns the **single granule** with the lowest tile-level cloud percentage among **all** granules intersecting the ROI over the **entire** 3.5-year window. Implications [INFERRED]:

- The map shows one date, the "clearest tile" of the period. It is not the latest image, a user-chosen date or a composite.
- The acquisition date is **not shown** to the user.
- The choice is by **whole-tile** cloud percentage. A tile can be cloud-free overall yet cover only a sliver of the ROI (edge of swath, tile boundary), so the map may show the index for only part of the wetland, with the rest shown as the red ROI layer.
- Ties (several 0 % tiles, common in the dry season) are broken arbitrarily. The chosen image may not be stable over time.
- It is not a mosaic, so wetlands spanning several tiles are never fully covered.

**Chart images:** every granule passing the filters (§9).

---

## 16. UI controls

| Control | Type | Options | Behaviour |
|---|---|---|---|
| Wetland dropdown | `ui.Select` | 74 asset names (raw strings with underscores), placeholder "Select dataset" | No action on change |
| NDCI / NDTI / NDWI / NDMI | 4 × `ui.Button` | — | Each **submits** with the chosen index using the current dropdown value. There is no separate submit button |
| Map | `ui.Map` | Standard GEE pan/zoom, layer list with 'Wetland Site' and index layer toggles | — |
| Chart | `ui.Chart` | Hover tooltip, GEE pop-out (CSV/SVG/PNG export) | — |

There are no date, cloud-threshold, scale, statistic or comparison controls. If a button is clicked with no wetland selected, `printinfo(null)` throws and nothing happens [INFERRED].

Layout: at start the root holds `[mapaa, panel]` (map left, controls right). After submit it holds `[panel (30 %), new map, infopanel (25 %)]`.

---

## 17. Wetland selection workflow

```
Start: India map (custom style) + control panel
  │
  ├─ user picks a wetland name in the dropdown (no effect yet)
  │
  └─ user clicks an index button, e.g. NDWI
        │
        ├─ onSubmitaNDWI()
        │    ├─ printinfo(name)          → info panel: name + description   (throws for Kanjirankulam)
        │    ├─ lookup FeatureCollection (nameToVarMapping)
        │    ├─ makemapNDWI(fc)          → new map: red ROI + least-cloudy-tile NDWI clipped to ROI + legend, zoom 14
        │    ├─ ui.root = [panel, map, infopanel]
        │    ├─ reset selectedROIs; set selectedROIs["tableN"] = true
        │    └─ printinfo(name) again
        ├─ makecheckchartNDWI()          → replace chart panel in left panel with NDWI time series
        └─ referencecreate()             → attribution text appended to info panel
```

Switching index means clicking another button. Everything is rebuilt, including a new map object, so pan/zoom state is lost.

---

## 18. GEE → Sentinel Hub migration mapping

| GEE element | Sentinel Hub / new-app equivalent | Exactness |
|---|---|---|
| `COPERNICUS/S2_SR_HARMONIZED` | `input.data[].type = "sentinel-2-l2a"`, `dataFilter`, `processing.harmonizeValues = true` (default) | Same upstream ESA L2A products; not one-to-one (full comparison in §2.2) |
| DN scale (chart path), `/10000` (map path) | `units: "REFLECTANCE"` (default; DN/10000) or `"DN"` | Irrelevant for normalized differences |
| `.filterBounds(roi)` | `input.bounds.geometry` (the ROI polygon) | Equivalent in intent |
| `.filterDate(a, b)` | `dataFilter.timeRange` `{from, to}` (end exclusive to match GEE) | Exact if end handled as exclusive |
| `CLOUDY_PIXEL_PERCENTAGE < 100` | `dataFilter.maxCloudCoverage` (≤) and/or Catalog `eo:cloud_cover` filter | Near-exact (§13) |
| `.sort(CLOUDY…).first()` | Catalog API search → choose lowest `eo:cloud_cover` → Process API on that acquisition's time window (or `mosaickingOrder: "leastCC"`) | Not exact (§22.3) |
| `maskS2clouds` (QA60) | SCL-based mask or no mask (§14.3) | **No exact equivalent** |
| `normalizedDifference([a,b])` | evalscript `(a-b)/(a+b)` with `dataMask` handling | Exact formula; edge cases §4.5 |
| `.clip(ROI)` | Process API with `bounds.geometry`: pixels outside the geometry are returned as no-data | Equivalent |
| `map.addLayer(img, {min,max,palette})` | Process API raster → colourized with the same palette → MapLibre image overlay | Visual equivalent |
| `map.addLayer(ROI, {color:'red'})` | GeoJSON boundary layer in MapLibre | Equivalent |
| `centerObject(ROI, 14)` | Fit map to ROI bounds (proposed); fixed zoom 14 only if reviewer requires it | Deliberate UI improvement, flagged |
| `ui.Chart.image.series(mean, 1000)` | **Statistical API**, `aggregationInterval` P1D, `mean`, resolution ≈1000 m | Close, not exact (§22.5–22.6) |
| Legend panel | React legend component driven by the same palette definition | Equivalent |
| `wetlandsList` text | `ramsar-sites.json` `summary` (proposed) | Replacement, flagged |
| FeatureCollection assets | Exported GeoJSON polygons in `wetlands.boundary` (PostGIS MULTIPOLYGON, SRID 4326) | Exact if exported without simplification |

### 18.1 Evalscript strategy

One generator builds all four index evalscripts from a single definition table, so formulas are never duplicated:

```text
INDEX_DEFINITIONS = {
  NDCI: { a: "B05", b: "B04", vis: [-1, 1], palette: [...], legend: [...] },
  NDTI: { a: "B03", b: "B04", ... },
  NDWI: { a: "B03", b: "B08", ... },
  NDMI: { a: "B08", b: "B11", ... },
}
get_index_evalscript(index, purpose="raster"|"statistics", cloud_mask=None|"scl")
```

- **Raster (Process API):** returns `FLOAT32` index + `dataMask`. Colourization happens in the backend from the same palette table that drives the legend, so legend and raster can't drift apart. (Alternative: colourize inside the evalscript and return PNG. It's cheaper, but the numeric values are lost. Decision for review.)
- **Statistics (Statistical API):** outputs `index` (FLOAT32) and the mandatory `dataMask`. `dataMask = 0` where no-data, where `a + b = 0`, and where masked by the optional cloud mask.
- The same definition table is exposed to the frontend (via the API) for legend rendering.

---

## 19. Process API vs Statistical API

| GEE functionality | New API | Why |
|---|---|---|
| Index map (single-image raster clipped to ROI) | **Process API** + index evalscript | Needs a raster |
| Choosing the "least cloudy" scene for the map | **Catalog API** (STAC search, `sentinel-2-l2a`, ROI intersects, date range, sort/filter by `eo:cloud_cover`) | Needs scene metadata before requesting pixels; also gives the acquisition date to show users |
| ROI-mean time series (charts) | **Statistical API** (`aggregationInterval: P1D`, `mean` plus `sampleCount`/`noDataCount`) | Returns only the statistics, with no image downloads. This is what the API is designed for |
| Wetland boundary display | None: served from our DB as GeoJSON | — |
| Large historical / multi-site bulk runs | **Batch (Statistical) API: not needed now** | The GEE app works one wetland at a time. Revisit only if we precompute all 74 sites × 4 indices |

Endpoints (CDSE):

| Purpose | URL |
|---|---|
| OAuth2 token | `https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token` |
| Process API | `https://sh.dataspace.copernicus.eu/process/v1` (confirmed in CDSE Process API examples) |
| Statistical API | `https://sh.dataspace.copernicus.eu/statistics/v1` (confirmed in CDSE Statistical API examples) |
| Catalog API | `https://sh.dataspace.copernicus.eu/catalog/v1/search` (confirmed in CDSE Catalog docs) |

All four go in environment variables (`COPERNICUS_TOKEN_URL`, `COPERNICUS_PROCESS_URL`, `COPERNICUS_STATISTICS_URL`, `COPERNICUS_CATALOG_URL`), next to the existing `COPERNICUS_CLIENT_ID` / `COPERNICUS_CLIENT_SECRET` in `backend/app/core/config.py`.

---

## 20. WGS84 / GeoJSON coordinate strategy

| Layer | Rule |
|---|---|
| Storage | `wetlands.boundary` MULTIPOLYGON and `wetlands.centroid` POINT, **SRID 4326** (already defined in `backend/app/models/wetland.py`) |
| Point fields | `latitude` and `longitude` as separate named fields (as in `ramsar-sites.json`). Never an unnamed `[a, b]` pair |
| GeoJSON (API ↔ frontend) | RFC 7946: **`[longitude, latitude]`** order, WGS84, no `crs` member |
| Sentinel Hub `input.bounds` | Send the geometry with an **explicit** `properties.crs`. Proposed: `http://www.opengis.net/def/crs/OGC/1.3/CRS84`, which is unambiguously lon/lat, so the GeoJSON can be passed through unchanged. The CDSE docs warn that CRS84 and EPSG:4326 axis order differ, so **never** relabel a lon/lat geometry as EPSG:4326 without checking the axis convention [VERIFY with a test request on a known asymmetric site] |
| Statistical API resolution | `resx`/`resy` are in CRS units: **degrees** for CRS84/4326, **metres** for projected CRSs. To reproduce `scale: 1000` m, request in the site's **UTM zone** (EPSG:326xx for India, zones 42N–47N) with `resx = resy = 1000`, and transform the geometry server-side (pyproj/shapely) [VERIFY SH accepts UTM geometry + resolution in Statistical API] |
| Process API raster for the web map | Request output in **EPSG:3857** so the image aligns pixel-for-pixel with MapLibre's Web Mercator. Return the four corner coordinates **in lon/lat** for the MapLibre image source. (A 4326 raster stretched onto 3857 misaligns slightly on large sites.) |
| Transformations | Only in the backend, with pyproj `always_xy=True` so input and output stay lon/lat |

---

## 21. Missing data requirements

| # | Required data | Status | Needed for |
|---|---|---|---|
| D1 | **Polygon geometries of the 74 GEE ROIs** (`projects/ee-ramsarwetlands5/assets/*`), exported as GeoJSON/Shapefile in EPSG:4326, **unsimplified** | **Missing.** The script has asset paths only. Needs export by the asset owner (HYDRO-CARES Lab / `ee-ramsarwetlands5` project) or read access to run `Export.table.toDrive` | Every map and chart. **Blocking** |
| D2 | Confirmation of the asset → Ramsar site mapping (Appendix A; 21 manual matches) | Proposed, not verified | Linking GEE ROIs to portal sites |
| D3 | Polygons for the **27 sites without a GEE ROI** (Appendix B) | Missing | Extending analysis to all 101 sites (new functionality, not reproduction) |
| D4 | Provenance of the polygons: official Ramsar RSIS boundaries or digitized by the lab; date and version | Unknown | Metadata / reproducibility |
| D5 | Copernicus Data Space OAuth client (client ID + secret) and account quota (processing units) | Not provided | Any Sentinel Hub call |
| D6 | Point coordinates for 101 sites | **Available** in `ramsar-sites.json` (`latitude`, `longitude`) | Site list, dot map, map centring. **Not** sufficient for analysis |
| D7 | Wetland descriptions | Available in `ramsar-sites.json` (`summary`) | Info panel |
| D8 | Whether the deployed GEE app matches this file | Unknown | Validation baseline |
| D9 | Reference outputs from GEE: chart CSVs and the selected map image ID/date for a validation sample (e.g., 5 sites × 4 indices) | Not yet exported | Scientific validation of the migration |

---

## 22. Scientific equivalence issues

### 22.1 Source archive and harmonization
GEE `S2_SR_HARMONIZED` and CDSE `sentinel-2-l2a` both derive from ESA L2A products, but may differ in which products and reprocessing versions were ingested, and in duplicate handling. Harmonization matters because normalized differences cancel scale but not offsets. With `harmonizeValues: true` (default) and REFLECTANCE units, Sentinel Hub removes the baseline-04.00 offset and clamps negatives to 0 [VERIFY that this matches GEE's harmonization numerically on sample pixels].

### 22.2 Cloud mask
QA60 isn't available in Sentinel Hub. In GEE, QA60 is masked for 2022-01-25 → 2024-02-28 and derived from MSK_CLASSI after that (§14.2). **This is the largest known source of map difference** (§2.2.4, X1).

### 22.3 Scene selection and mosaicking for the map
GEE uses one **granule** (tile). Sentinel Hub's Process API returns a **mosaic** of all tiles matching the time window. Even when restricted to the chosen acquisition, adjacent tiles from the same pass fill in the ROI. That improves coverage but differs from GEE. `mosaickingOrder: "leastCC"` over the full window would instead mix dates pixel-by-pixel, which is further from GEE and **not recommended**. Proposal: Catalog → lowest cloud-cover acquisition → Process API over that acquisition's time window only. Show the acquisition date in the UI.

### 22.4 Chart has no cloud mask
The GEE series includes cloud-contaminated observations. Faithful reproduction means no mask by default. Offering a masked variant is new methodology, so it must be clearly labelled and approved before being added.

### 22.5 Scale and resampling at 1000 m
GEE computes the index from **mean-aggregated** 1 km reflectances (pyramid) and takes an **overlap-weighted** mean over the ROI. Sentinel Hub resamples bands to the requested resolution with a `downsampling` method (NEAREST by default; BILINEAR/BICUBIC available). There is no "area-average" option [VERIFY], and partial-pixel handling in the Statistical API is not documented as overlap-weighted [VERIFY]. Expect differences, largest for **small wetlands** where the ROI is smaller than one 1 km pixel. Options for the reviewer:
- (a) replicate 1000 m as closely as possible (UTM, 1000 m, BILINEAR), which gives the best fidelity to GEE;
- (b) compute at native 10/20 m, which is scientifically more representative of the wetland but a **methodology change**.

### 22.6 Temporal sampling
GEE gives **one point per granule**, so there can be several per day with partial-ROI means. The Statistical API with `P1D` gives **one point per day**, computed over the mosaic of that day's tiles. For single-tile wetlands these should coincide. For multi-tile wetlands the GEE series has duplicate/partial points that Sentinel Hub won't reproduce. The new series is arguably more correct, but it isn't identical.

### 22.7 Time zone / date assignment
Days are UTC in both systems. India's overpass is ≈05:00–06:00 UTC, so there is no day-boundary ambiguity [INFERRED].

### 22.8 Edge semantics
`normalizedDifference` masking of negative inputs and the zero-sum behaviour (§4.5).

### 22.9 Ramsar ID label
The GEE chart title "Ramsar ID: N" is wrong (§5.4). It will be corrected, and this is a deliberate change.

### 22.10 Validation plan (before release)
For a sample of sites covering small / large / multi-tile / coastal / high-altitude (e.g., Sirpur, Chilika, Sundarbans, Vembanad-Kol, Tso Kar):
1. export the GEE series (CSV) and the map image ID;
2. run the Sentinel Hub pipeline with the same dates;
3. compare per-date values (bias, RMSE, correlation) and document the tolerances.

---

## 23. Recommended backend architecture

This extends the **existing** FastAPI app (`backend/app`, API prefix `/api/v1`) and does not create a second backend. It reuses the existing folders:

```
backend/app/
  core/config.py                      + COPERNICUS_TOKEN_URL, _PROCESS_URL, _STATISTICS_URL, _CATALOG_URL
  services/copernicus/
    client.py        (exists)         → OAuth2 client-credentials, token cache until expiry, retry/backoff on 429
    process.py                        → Process API calls (raster)
    statistics.py                     → Statistical API calls (time series)
    catalog.py                        → Catalog (STAC) search for scene selection
    evalscripts.py                    → get_index_evalscript(index, purpose, cloud_mask)
  processing/water_quality/
    indices.py                        → INDEX_DEFINITIONS (bands, formula, vis range, palette, legend) — single source of truth
    colorize.py                       → FLOAT32 → RGBA PNG using the palette (matches GEE interpolation)
  services/wetlands/                  → wetland lookup + boundary GeoJSON (ramsar-sites.json + PostGIS boundary)
  services/water_quality/             → orchestration: wetland → geometry → catalog → process/statistics → response + metadata
  api/routes/
    wetlands.py      (exists, 501)    → list/detail/boundary
    water_quality.py (exists, 501)    → indices, image, timeseries
```

- `services/earth_engine/` stays untouched for now. Retiring it is a later decision.
- **Credentials:** the backend only. The frontend never sees `client_secret` or tokens.
- **Identifiers:** use the **Ramsar site number** (`ramsar-sites.json` `id`) as the public wetland ID. The existing `water_quality` route stubs use UUIDs, and this needs a decision.

### 23.1 Proposed API

| Method | Path (under `/api/v1`) | Returns |
|---|---|---|
| GET | `/wetlands` | Site list (id, name, state, lat, lon, `hasBoundary`) |
| GET | `/wetlands/{id}` | Site detail |
| GET | `/wetlands/{id}/boundary` | GeoJSON polygon (404/`null` if no ROI) |
| GET | `/water-quality/indices` | The index definition table (formula, bands, vis range, palette, legend) |
| GET | `/water-quality/{id}/{index}/scenes?start&end&maxCloud` | Catalog results (date, tile cloud %) |
| GET | `/water-quality/{id}/{index}/image?start&end&maxCloud&cloudMask&date` | PNG + bounds + metadata (or FLOAT32 GeoTIFF) |
| GET | `/water-quality/{id}/{index}/timeseries?start&end&maxCloud&cloudMask` | `[{date, mean, sampleCount, noDataCount}]` + metadata |

Every analysis response carries a `metadata` block: data source (Sentinel-2 L2A), collection `sentinel-2-l2a`, index + formula + bands, date range, cloud filter, cloud mask used, ROI (site id + boundary version), CRS, spatial aggregation (mean), resolution, harmonization, acquisition date (for images), processing service (Sentinel Hub / CDSE), request timestamp.

### 23.2 Caching (requirement, not built now)
Key: `(wetland_id, boundary_version, index, start, end, max_cloud, cloud_mask, resolution, output_crs, api_version)`. Redis is already configured (`REDIS_URL`) and suits this. Historical ranges are immutable once the archive is stable, so long TTLs are fine. Ranges touching "today" need short TTLs. Token caching is required from day one.

### 23.3 Performance
- Time series: Statistical API only, with no image downloads.
- Maps: size the raster to the ROI and display. Native 10 m for small sites, capped at a maximum output of about 1500–2500 px per side [VERIFY the Process API size limit], with coarser resolution for large ROIs.
- National overview: not part of the GEE app. If needed later, it would be low-resolution and precomputed.

---

## 24. Recommended frontend workflow

Uses the existing stack (Next.js, MapLibre GL, ECharts) and the portal's institutional design. It rebuilds the GEE interaction as a proper web workflow rather than copying the GEE UI:

1. **Select wetland:** searchable list of the 74 sites with an ROI. The other 27 are listed as "boundary not yet available" rather than hidden or approximated.
2. **Site context:** name, Ramsar number, state, coordinates (lat/lon), official summary, and a location map with the boundary polygon.
3. **Select index:** NDCI / NDTI / NDWI / NDMI. Selecting an index doesn't rebuild the page.
4. **Date range:** defaults to 2022-11-01 → 2026-05-30, editable. The cloud filter defaults to the GEE value (< 100 %).
5. **Map:** boundary outline + index raster overlay + continuous legend with original labels + **acquisition date and scene cloud %**. The map fits the ROI rather than using a fixed zoom of 14.
6. **Time series:** ECharts line chart with date on x and the ROI mean on y, hover values, range zoom, and CSV download. The title uses the real Ramsar number.
7. **Metadata panel:** the §23.1 metadata block, visible and exportable.
8. **States:** explicit loading, empty ("no scenes in range"), not-configured ("satellite service not connected") and error states. **No placeholder, sample or simulated values, ever.**
9. **Attribution:** the original GEE app credits HYDRO-CARES Lab, IIT Indore. How to acknowledge it in the portal needs the client's decision.

The existing `/water-quality` page is a placeholder. It won't be changed until this spec is approved.

---

## 25. Items to verify before implementation

**Data / access**
1. Get the 74 ROI polygons (D1) and confirm feature counts, geometry types and CRS of each asset.
2. Confirm the asset → Ramsar site mapping in Appendix A, especially the 21 manual matches and whether `Keoladeo_National_Park_and_Ajan_Bande` is the Ramsar boundary of site 230.
3. Confirm this file matches the deployed GEE app (D8).
4. Get the CDSE OAuth client and check the processing-unit quota (D5).

**GEE behaviour (run in the GEE Code Editor)**
5. Confirm the §14.2 inference in the Code Editor: for sample wetlands, does the map show a blank index layer when the selected granule is dated before 2024-02-28? Record which of the 74 sites are affected.
5a. For the same granules, compare GEE `PROCESSING_BASELINE` with the CDSE Catalog baseline (Collection-1 question, §2.2 X4).
5b. Pixel test: harmonized B8/B11 values ≤ 0 over water in GEE vs Sentinel Hub (clamp vs mask, §2.2 X5).
6. Does selecting Kanjirankulam throw in the live app? (§5.5)
7. `normalizedDifference` behaviour for negative inputs and `a + b = 0`.
8. Projection used by `ui.Chart.image.series` at `scale: 1000` without `crs`, and confirmation that pyramid mean-downsampling applies.
9. Whether the region mean is fractional-overlap weighted.
10. Export reference outputs (D9) for validation.

**Sentinel Hub (test requests once credentials exist)**
11. Exact CDSE endpoint URLs for Process, Statistical and Catalog (§19).
12. Axis order with `CRS84` vs `EPSG:4326` in `input.bounds`.
13. Statistical API with a UTM CRS geometry and `resx/resy = 1000`; partial-pixel inclusion rules; the `downsampling` options available.
14. How `eo:cloud_cover` in the CDSE catalog relates to GEE's `CLOUDY_PIXEL_PERCENTAGE`.
15. Numeric agreement of harmonized reflectance between GEE and CDSE on the same granule/pixels.
16. Process API maximum output size and processing-unit cost per typical wetland request.
17. How the Statistical API reports days with no valid pixels (so the chart shows gaps, not zeros).

**Decisions for the reviewer**
18. Cloud mask choice for maps (§14.3) and whether charts stay unmasked (§22.4).
19. 1000 m reproduction vs native resolution for time series (§22.5).
20. Map scene selection method (§22.3), and showing the acquisition date.
21. Replace `wetlandsList` text with RSIS `summary`? (§5.5)
22. Public wetland ID = Ramsar site number? (§23)
23. Raster delivery: FLOAT32 + backend colourization, or evalscript PNG? (§18.1)
24. Map framing: fit to ROI, or fixed zoom 14 as in GEE? (§6.2)
25. Default date range: keep the GEE window exactly, or extend to today?

---

## 26. Implementation status — backend phase 1 (2026-09-24)

Implemented according to the approved decisions. **Not yet run against live Copernicus Data Space** (no credentials) **and not yet validated against GEE** (no ROI polygons, no reference exports). All tests use HTTP-level mocks.

| Approved decision | Implementation |
|---|---|
| Map cloud mask = SCL 8/9/10 as QA60 substitute | `map_evalscript` masks SCL 8, 9, 10 only (not shadows). Traceability states "not identical to QA60" |
| Charts unmasked | `statistics_evalscript` reads no SCL; masks only no-data and a + b = 0 |
| Map scene = least cloudy | Catalog search (bbox + footprint ∩ ROI, end exclusive), strict `eo:cloud_cover < max`, ties → earliest. Process API window = selected acquisition ± 30 min. Scene id/date/tile/cloud returned |
| Charts at 1000 m | Statistical API, ROI in its UTM zone, `resx = resy = 1000`, `BILINEAR` downsampling (closest available; X3), `P1D`, split per calendar year |
| Four formulas unchanged | One table (`app/processing/water_quality/indices.py`) drives both evalscripts, colourization and the legend endpoint |
| No invented geometry | ROI = exported GEE polygon only (`backend/data/roi/<asset>.geojson`). Without it, analysis endpoints return 409 `roi_missing` / `roi_no_gee_roi`, and no Sentinel Hub request is made |
| QA60 historical behaviour | Not reproduced; every map carries a validation warning |
| X4 / X5 | No corrections. `harmonizeValues: true` (platform clamp of negatives to 0) documented as X5; no further clamping |
| Traceability | Every map and time series returns a `traceability` block (§23.1 fields plus `processing_differences` X1–X6 and `warnings`) |

Implementation difference added during this phase: **X6** — the Statistical API cloud filter `maxCloudCoverage` is inclusive (≤), while GEE's is strict (<). The map path keeps the strict rule because selection happens client-side on Catalog metadata.

---

## 27. Phase J validation status (2026-09-24)

Full report: [phase-j-validation-report.md](phase-j-validation-report.md). **Live Copernicus validation and GEE comparison have not been performed**: there are no credentials, no ROI polygons and no GEE exports. The earlier sections and decisions are unchanged. This section classifies each item.

| Item | GEE reference behaviour | Sentinel Hub implementation | Known unavoidable difference | Validated difference | Unresolved |
|---|---|---|---|---|---|
| Formulas (4 indices) | `normalizedDifference` | Same ratio in evalscripts | — | Offline: evalscripts executed on sample pixels | — |
| Cloud mask (maps) | QA60 bits 10/11 | SCL 8/9/10 substitute | X1 (QA60 not offered) | — | Live effect; QA60 2022-01-25 → 2024-02-28 blank-map inference (§14.2) |
| Scene selection | `.sort(CLOUDY_PIXEL_PERCENTAGE).first()`, arbitrary ties | Catalog, strict `<`, earliest-first ties | Tie-break rule; tile stitching X2 | — | `eo:cloud_cover` vs `CLOUDY_PIXEL_PERCENTAGE` (unknown) |
| Charts | Per-granule `reduceRegion(mean, 1000 m)`, unmasked | Statistical API P1D, 1000 m UTM, BILINEAR, unmasked | X2 (per day), X3 (resampling), X6 (≤ vs <) | — | Magnitude of X3; partial-pixel rule (UNRESOLVED) |
| Values | S2_SR_HARMONIZED | `sentinel-2-l2a`, `harmonizeValues` | — | — | X4, X5 |
| CRS / axis order | FeatureCollection geometry | CRS84 bbox, UTM statistics, EPSG:3857 maps | — | Offline: request geometry and return transforms | Live axis probe |
| ROI mapping (21 manual) | Asset names | Manifest | — | 15 identities confirmed from the GEE app's own descriptions (site no. or area) | 6 uncertain pending polygons |
| Error handling | — | Structured errors | — | Validated with mocked HTTP (3 defects fixed) | — |

Tooling to complete the validation: `python -m app.tools.validate_rois`, `python -m app.tools.live_validation --gee-dir …`, and `docs/validation/gee/phase-j-reference-export.js`.

---

## Appendix A — GEE asset → Ramsar site mapping (proposed)

`N` is the GEE `tableN` / `userId` (shown in GEE charts as "Ramsar ID"). "Ramsar #" is the real site number from `ramsar-sites.json`. **Manual** rows were matched by name and state knowledge and need confirmation.

| N | GEE asset name | Ramsar # | Portal site name | State | Match |
|---|---|---|---|---|---|
| 1 | Ansupa_Lake | 2487 | Ansupa Lake | Odisha | exact |
| 2 | Asan_Conservation_Reserve | 2437 | Asan Conservation Reserve | Uttarakhand | exact |
| 3 | asthamudi | 1204 | Ashtamudi Wetland | Kerala | manual |
| 4 | Bakhira_Wildlife_Sanctuary | 2465 | Bakhira Wildlife Sanctuary | Uttar Pradesh | exact |
| 5 | Beas_Conservation_reserve | 2408 | Beas Conservation Reserve | Punjab | exact |
| 6 | Bhindawas_Wildlife_Sanctuary | 2459 | Bhindawas Wildlife Sanctuary | Haryana | exact |
| 7 | Bhitarkanika_Wildlife_Sanctuary_and_National_Park | 1205 | Bhitarkanika Mangroves | Odisha | manual |
| 8 | Bhoj_wetland | 1206 | Bhoj Wetland | Madhya Pradesh | exact |
| 9 | chilka | 229 | Chilika Lake | Odisha | manual |
| 10 | Chitrangudi_Bird_Sanctuary | 2491 | Chitrangudi Bird Sanctuary | Tamil Nadu | exact |
| 11 | Deepor_Beel_Bird_Sanctuary | 1207 | Deepor Beel | Assam | manual |
| 12 | east_kolkata | 1208 | East Calcutta Wetlands | West Bengal | manual |
| 13 | Gulf_of_Mannar_Marine_Biosphere_Reserve | 2472 | Gulf of Mannar Marine Biosphere Reserve | Tamil Nadu | exact |
| 14 | Haiderpur_Wetland | 2463 | Haiderpur Wetland | Uttar Pradesh | exact |
| 15 | Harike_Lake_Bird_Sanctuary | 462 | Harike Lake | Punjab | manual |
| 16 | Hirakud_Reservoir | 2494 | Hirakud Reservoir | Odisha | exact |
| 17 | hokera | 1570 | Hokera Wetland | Jammu and Kashmir | manual |
| 18 | Hygam_Wetland_Conservation_Reserve | 2496 | Hygam Wetland Conservation Reserve | Jammu and Kashmir | exact |
| 19 | Kabartal_Wetland | 2436 | Kabartal Wetland | Bihar | exact |
| 20 | Kanjirankulam_Bird_Sanctuary | 2486 | Kanjirankulam Bird Sanctuary | Tamil Nadu | exact |
| 21 | Kanjli_Lake | 1160 | Kanjli | Punjab | manual |
| 22 | Karikili_Bird_Sanctuary | 2480 | Karikili Bird Sanctuary | Tamil Nadu | exact |
| 23 | Keoladeo_National_Park_and_Ajan_Bande | 230 | Keoladeo National Park | Rajasthan | manual |
| 24 | Keshopur-Miani_Community_Reserve | 2414 | Keshopur-Miani Community Reserve | Punjab | exact |
| 25 | Khijadia_Wildlife_Sanctuary | 2464 | Khijadia Wildlife Sanctuary | Gujarat | exact |
| 26 | Kolleru_Lake_Wildlife_Sanctuary | 1209 | Kolleru Lake | Andhra Pradesh | manual |
| 27 | Koonthankulam_Bird_Sanctuary | 2479 | Koonthankulam Bird Sanctuary | Tamil Nadu | exact |
| 28 | Loktak_Lake | 463 | Loktak Lake | Manipur | exact |
| 29 | Lonar_Lake | 2441 | Lonar Lake | Maharashtra | exact |
| 30 | Nalsarovar_Wildlife_Sanctuary | 2078 | Nalsarovar | Gujarat | manual |
| 31 | Nanda_Lake | 2471 | Nanda Lake | Goa | exact |
| 32 | Nandur_Madhameshwar | 2410 | Nandur Madhameshwar | Maharashtra | exact |
| 33 | Nangal_Wildlife_sanctuary | 2407 | Nangal Wildlife Sanctuary | Punjab | exact |
| 34 | Nawabganj_Bird_Sanctuary | 2412 | Nawabganj Bird Sanctuary | Uttar Pradesh | exact |
| 35 | Pala_Wetland | 2484 | Pala Wetland | Mizoram | exact |
| 36 | Pallikaranai_Marsh_Reserve_Forest | 2481 | Pallikaranai Marsh Reserve Forest | Tamil Nadu | exact |
| 37 | Parvati_Arga_Bird_Sanctuary | 2416 | Parvati Arga Bird Sanctuary | Uttar Pradesh | exact |
| 38 | Pichavaram_Mangrove | 2482 | Pichavaram Mangrove | Tamil Nadu | exact |
| 39 | Point_Calimere_Wildlife_Sanctuary | 1210 | Point Calimere Wildlife and Bird Sanctuary | Tamil Nadu | manual |
| 40 | Pong_Dam_Lake_Wildlife_Sanctuary | 1211 | Pong Dam Lake | Himachal Pradesh | manual |
| 41 | Ranganathittu_Bird_Sanctuary | 2473 | Ranganathittu Bird Sanctuary | Karnataka | exact |
| 42 | renuka | 1571 | Renuka Wetland | Himachal Pradesh | manual |
| 43 | Ropar_Lake | 1161 | Ropar | Punjab | manual |
| 44 | Rudrasagar_Lake | 1572 | Rudrasagar Lake | Tripura | exact |
| 45 | Sakya_sagar | 2483 | Sakhya Sagar | Madhya Pradesh | manual |
| 46 | Saman_Bird_Sanctuary | 2413 | Saman Bird Sanctuary | Uttar Pradesh | exact |
| 47 | Samaspur_Bird_Sanctuary | 2415 | Samaspur Bird Sanctuary | Uttar Pradesh | exact |
| 48 | Sambhar_Lake | 464 | Sambhar Lake | Rajasthan | exact |
| 49 | sandi_Bird_sanctuary | 2409 | Sandi Bird Sanctuary | Uttar Pradesh | exact |
| 50 | Sarsai_Nawar_Jheel | 2411 | Sarsai Nawar Jheel | Uttar Pradesh | exact |
| 51 | Sasthamkotta | 1212 | Sasthamkotta Lake | Kerala | manual |
| 52 | Satkosia_Gorge | 2470 | Satkosia Gorge | Odisha | exact |
| 53 | Shallbugh_Wetland_Conservation_Reserve | 2488 | Shallbugh Wetland Conservation Reserve | Jammu and Kashmir | exact |
| 54 | Sirpur_wetland | 2478 | Sirpur Wetland | Madhya Pradesh | exact |
| 55 | Suchindram_Theroor_Wetland_Complex | 2492 | Suchindram Theroor Wetland Complex | Tamil Nadu | exact |
| 56 | Sultanpur_National_Park | 2457 | Sultanpur National Park | Haryana | exact |
| 57 | sundarban_wetland | 2370 | Sundarban Wetland | West Bengal | exact |
| 58 | Sur_Sarovar | 2440 | Sur Sarovar | Uttar Pradesh | exact |
| 59 | Surinsar_Mansar | 1573 | Surinsar-Mansar Lakes | Jammu and Kashmir | manual |
| 60 | Tampara_Lake | 2489 | Tampara Lake | Odisha | exact |
| 61 | Thane_Creek | 2490 | Thane Creek | Maharashtra | exact |
| 62 | Thol_Lake_Wildlife_Sanctuary | 2458 | Thol Lake Wildlife Sanctuary | Gujarat | exact |
| 63 | Tso_Kar_Wetland_Complex | 2443 | Tso Kar Wetland Complex | Ladakh | exact |
| 64 | Tsomoriri_Lake_and_adjacent_marshes | 1213 | Tsomoriri | Ladakh | manual |
| 65 | Udhayamarthandapuram_Bird_Sanctuary | 2476 | Udhayamarthandapuram Bird Sanctuary | Tamil Nadu | exact |
| 66 | Upper_Ganga_River | 1574 | Upper Ganga River | Uttar Pradesh | exact |
| 67 | Vaduvur_Bird_Sanctuary | 2493 | Vaduvur Bird Sanctuary | Tamil Nadu | exact |
| 68 | Vedanthangal_Bird_Sanctuary | 2477 | Vedanthangal Bird Sanctuary | Tamil Nadu | exact |
| 69 | Vellode_Bird_Sanctuary | 2475 | Vellode Bird Sanctuary | Tamil Nadu | exact |
| 70 | Vembanad_Lake | 1214 | Vembanad-Kol Wetland | Kerala | manual |
| 71 | Vembannur_Wetland_Complex | 2474 | Vembannur Wetland Complex | Tamil Nadu | exact |
| 72 | Wadhvana_Wetland | 2454 | Wadhvana Wetland | Gujarat | exact |
| 73 | Wular_Lake_and_associated_marshes | 461 | Wular Lake | Jammu and Kashmir | manual |
| 74 | Yashwant_Sagar | 2495 | Yashwant Sagar | Madhya Pradesh | exact |

## Appendix B — Ramsar sites with no GEE ROI

27 sites. The GEE app can't analyse these, and polygons would be needed to extend coverage (D3).

| Ramsar # | Site | State | Designated |
|---|---|---|---|
| 2534 | Aghanashini Estuary | Karnataka | 2023 |
| 2535 | Ankasamudra Bird Conservation Reserve | Karnataka | 2023 |
| 1569 | Chandertal Wetland | Himachal Pradesh | 2005 |
| 2588 | Chhari Dhand | Gujarat | 2025 |
| 2597 | Glaw Lake | Arunachal Pradesh | 2026 |
| 2579 | Gogabil Lake | Bihar | 2025 |
| 2576 | Gokul Jalashay | Bihar | 2025 |
| 2595 | Jai Prakash Narayan Bird Sanctuary | Uttar Pradesh | 2026 |
| 2537 | Karaivetti Bird Sanctuary | Tamil Nadu | 2023 |
| 2548 | Kazhuveli Bird Sanctuary | Tamil Nadu | 2024 |
| 2560 | Khachoedpalri wetland | Sikkim | 2024 |
| 2568 | Khichan wetland | Rajasthan | 2025 |
| 2583 | Kopra Jalashay | Chhattisgarh | 2025 |
| 2538 | Longwood Shola Reserve Forest | Tamil Nadu | 2023 |
| 2536 | Magadi Kere Conservation Reserve | Karnataka | 2023 |
| 2567 | Menar Wetland Complex | Rajasthan | 2025 |
| 2545 | Nagi Bird Sanctuary | Bihar | 2023 |
| 2546 | Nakti Bird Sanctuary | Bihar | 2023 |
| 2549 | Nanjarayan Bird Sanctuary | Tamil Nadu | 2024 |
| 2589 | Patna Bird Sanctuary | Uttar Pradesh | 2025 |
| 2561 | Sakkarakottai Bird Sanctuary | Tamil Nadu | 2024 |
| 2594 | Sheikha Jheel Bird Sanctuary | Uttar Pradesh | 2026 |
| 2581 | Siliserh lake | Rajasthan | 2025 |
| 2547 | Tawa Reservoir | Madhya Pradesh | 2024 |
| 2562 | Therthangal Bird Sanctuary | Tamil Nadu | 2024 |
| 2577 | Udaipur Jheel | Bihar | 2025 |
| 2559 | Udhwa Lake Bird Sanctuary | Jharkhand | 2024 |

## Appendix C — Existing GEE functionality vs new portal functionality

| Capability | In GEE code? | Portal requirement |
|---|---|---|
| NDCI / NDTI / NDWI / NDMI maps (single scene) | **Yes** | Reproduce |
| NDCI / NDTI / NDWI / NDMI ROI-mean time series | **Yes** | Reproduce |
| Wetland description panel | **Yes** (with bugs) | Reproduce with RSIS data |
| Configurable date range / cloud threshold | No (hard-coded) | New (defaults = GEE values) |
| Scene date display, metadata block | No | New |
| Wetland drought | **No** | New (separate climate module; already built in the portal, awaiting data) |
| Precipitation extremes | **No** | New (as above) |
| Heat waves / cold waves | **No** | New (as above) |
| Dot-density map of the 101 sites | **No** (start map has no points) | New (portal already has one from `ramsar-sites.json` coordinates) |
| Wetland comparison, selected-date analysis, trend statistics | **No** | New (to be specified separately, with no invented methodology) |
| SRTM elevation | Loaded, unused | Not required |

---

## 28. Analysis ROI source — provided dataset (2026-09-25)

**Decision (approved 2026-09-25):** water-quality analysis uses the **provided ROI dataset**, `backend/data/India Ramsar Sites September 2026.geojson`, wherever it has a valid polygon.

**What the file contains.**
- It has **114 features for 75 Ramsar sites**, not 101.
- Every feature's `v_idris`, `ramsarid`, name and `area_off` equal the RSIS layer `ramsar_sdi:features_published`.
- Per site, the geometry agrees with RSIS within 7.8 mm (coordinates rounded to 7 decimals).
- So the dataset is **RSIS-derived**. It is **not** a GEE ROI export and is labelled `provided_roi`.

**Coverage.**
- 72 sites are valid and used.
- 3 sites (2408, 2413, 2548) have invalid geometry (self-intersections, as in RSIS) and are rejected, not repaired.
- The same 26 sites as RSIS have no polygon. They remain unavailable, and no geometry is derived from coordinates.

**Resolution policy (`roi` query parameter).**
- `auto` (default): provided ROI, else a GEE ROI with a verified mapping, else HTTP 409 with each source's reason.
- `provided` or `gee`: that source only.

**Consequence for GEE reproduction.** Analysis now runs over the RSIS-derived boundary rather than the GEE app's own ROI, which has not been exported. Where the two differ, results will differ from the GEE app. The comparison (`gee_vs_official`) becomes possible once GEE ROIs are exported.

**First live results (Lonar Lake, 2441, provided ROI).**
- Map: the Catalog selected `S2B_MSIL2A_20221102…_N0510_…_T43QFC_20240803…` (0 % cloud). The raster is 245×274 at 10 m, with 43,827 valid pixels.
- NDWI time series: 278 observations from 2022-11-02 to 2026-05-25 (gaps 2–10 days, median 5), with 6 × 1 km pixels per day.
- The product generation date (2024-08-03, baseline N0510) shows that CDSE serves Collection-1 reprocessed data for 2022. This is live evidence for **X4**.
- Six 1 km pixels over a 428 ha polygon suggests that partly covered pixels are included. This is not yet conclusive for §22.5 / E.2.

**Fix found live.** The CDSE Catalog returns HTTP 406 for `Accept: application/json`. Catalog requests now send `Accept: application/geo+json`.
