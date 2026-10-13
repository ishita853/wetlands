# Phase J — Live Copernicus + GEE Scientific Validation Report

**Status: BLOCKED. Live validation has not been performed.** This report records what was validated offline, what could not be validated and why, and the tooling prepared so the blocked steps can be run as soon as the inputs exist. No live or GEE result in this document is simulated or estimated.

---

## A. Environment

| Item | Value |
|---|---|
| Copernicus live validation | **NO**. `COPERNICUS_CLIENT_ID` and `COPERNICUS_CLIENT_SECRET` are empty in `backend/.env` and unset in the process environment |
| GEE reference validation | **NO**. No Earth Engine access in this environment (`earthengine-api` not installed, no credentials), and no GEE exports were provided |
| ROI polygons | **NONE**. `backend/data/roi/` contains only `README.md` |
| Validation date | 2026-09-24 |
| GEE source | `Wetland App GEE Code (1).txt` and `Wetland App GEE Code.txt` in Downloads are byte-identical (MD5 `f76f2bbea555d9edeed6412e531346a6`), so there is one script version |

Required message (section 2 of the brief):

```text
LIVE VALIDATION BLOCKED:
Copernicus credentials are not configured.
```

`python -m app.tools.live_validation` prints exactly this and exits with code 2 without writing anything. A test covers this behaviour.

### Credential handling (verified statically)

| Check | Result | Evidence |
|---|---|---|
| Credentials never returned by an API response | Pass | No route reads `COPERNICUS_*` settings. Error bodies are built from exception messages that never include the secret. `test_invalid_credentials` asserts the secret is absent from the 502 body |
| Credentials never logged | Pass | No logging or `print` calls in `services/copernicus`, `services/water_quality` or `services/wetlands` |
| Credentials never in frontend code | Pass | The only "Copernicus" text in `frontend/` is descriptive copy on the About page |
| Credentials never committed | Pass | `backend/.env` is git-ignored (`.gitignore:15`, verified with `git check-ignore`). The repository has no commits yet |
| Secret sent only to the identity service | Pass | `test_client_credentials_grant_and_bearer_header` asserts the secret is absent from Sentinel Hub request bodies and headers |
| OAuth token cached | Pass | `test_token_is_cached_between_requests`, `test_token_refreshed_after_expiry` |

---

## B. ROI validation

| Count | Value |
|---|---|
| Expected (manifest) | 74 |
| Valid | **0** |
| Missing (not yet exported) | **74** |
| Invalid | 0 |
| Manually matched: confirmed | **15** (mapping identity only; geometry unverified) |
| Manually matched: uncertain | **6** |
| Manually matched: incorrect | **0** |

`python -m app.tools.validate_rois` reports `{'missing': 74}` today. Once the polygons are in `backend/data/roi/`, the same command checks every file for:

- geometry type, CRS and axis order (rejects polygons outside India);
- validity;
- polygon area against the RSIS area;
- whether the RSIS point lies inside the polygon.

Nothing is repaired automatically.

### B.1 Evidence standard for the 21 manual mappings

The GEE application contains its own description for each wetland (`wetlandsList`), keyed by the **same asset name** as the dropdown and the ROI (`printinfo(dropdown value)`). That text is the GEE authors' own statement of which Ramsar site the asset denotes. It was parsed from the script (98 entries) and compared with the RSIS record (`frontend/data/ramsar-sites.json`).

- **CONFIRMED**: the GEE description for the asset cites the Ramsar site number, **or** cites a name, state and area that equal exactly one RSIS record.
- **UNCERTAIN**: only name and state agree. No number or area is given, so the evidence does not meet the standard.
- **INCORRECT**: the evidence contradicts the mapping.

"Confirmed" here means the **mapping identity** is confirmed. Whether the polygon is the Ramsar boundary is a separate question that needs the polygon (area ratio and RSIS point test).

| # | GEE asset | → Ramsar # | Site (RSIS) | Evidence in the GEE app's description | Result |
|---|---|---|---|---|---|
| 3 | `asthamudi` | 1204 | Ashtamudi Wetland | "Ramsar site no. 1204". Note: the text says 61,400 ha, RSIS says 6,140 ha (10× discrepancy in the GEE text; check against polygon area) | **MATCH CONFIRMED** |
| 7 | `Bhitarkanika_Wildlife_Sanctuary_and_National_Park` | 1205 | Bhitarkanika Mangroves | "site no. 1205", 65,000 ha = RSIS | **MATCH CONFIRMED** |
| 9 | `chilka` | 229 | Chilika Lake | "site no. 229", 116,500 ha = RSIS | **MATCH CONFIRMED** |
| 15 | `Harike_Lake_Bird_Sanctuary` | 462 | Harike Lake | "Ramsar site no. 462", 4,100 ha = RSIS | **MATCH CONFIRMED** |
| 17 | `hokera` | 1570 | Hokera Wetland | "site no. 1570", 1,375 ha = RSIS | **MATCH CONFIRMED** |
| 21 | `Kanjli_Lake` | 1160 | Kanjli | "site no. 1160", 183 ha = RSIS | **MATCH CONFIRMED** |
| 42 | `renuka` | 1571 | Renuka Wetland | "site no. 1571" | **MATCH CONFIRMED** |
| 43 | `Ropar_Lake` | 1161 | Ropar | "site no. 1161", 1,365 ha = RSIS | **MATCH CONFIRMED** |
| 59 | `Surinsar_Mansar` | 1573 | Surinsar-Mansar Lakes | "site no. 1573", 350 ha = RSIS | **MATCH CONFIRMED** |
| 70 | `Vembanad_Lake` | 1214 | Vembanad-Kol Wetland | "site no. 1214", 151,250 ha = RSIS | **MATCH CONFIRMED** |
| 40 | `Pong_Dam_Lake_Wildlife_Sanctuary` | 1211 | Pong Dam Lake | "Pong Dam Lake … Himachal Pradesh … 15,662 hectares" = RSIS | **MATCH CONFIRMED** |
| 45 | `Sakya_sagar` | 2483 | Sakhya Sagar | "Shivpuri District, Madhya Pradesh … 248 hectares" = RSIS | **MATCH CONFIRMED** |
| 51 | `Sasthamkotta` | 1212 | Sasthamkotta Lake | "Kerala … 373 hectares" = RSIS | **MATCH CONFIRMED** |
| 64 | `Tsomoriri_Lake_and_adjacent_marshes` | 1213 | Tsomoriri | "12,000 hectares" = RSIS | **MATCH CONFIRMED** |
| 73 | `Wular_Lake_and_associated_marshes` | 461 | Wular Lake | "Jammu & Kashmir … 18,900 hectares" = RSIS | **MATCH CONFIRMED** |
| 11 | `Deepor_Beel_Bird_Sanctuary` | 1207 | Deepor Beel | Short text (Assam, Guwahati) with no number or area. The asset is named after the *Bird Sanctuary*, whose boundary may differ from the Ramsar site (RSIS 4,000 ha) | **MATCH UNCERTAIN** |
| 12 | `east_kolkata` | 1208 | East Calcutta Wetlands | Short text (West Bengal, wastewater resource recovery) with no number or area | **MATCH UNCERTAIN** |
| 23 | `Keoladeo_National_Park_and_Ajan_Bande` | 230 | Keoladeo National Park | Text is the RSIS summary of site 230 (Rajasthan, Montreux Record 1990) with no number or area. The asset name adds "Ajan Bande", so the polygon may cover more than the RSIS 2,873 ha | **MATCH UNCERTAIN** |
| 26 | `Kolleru_Lake_Wildlife_Sanctuary` | 1209 | Kolleru Lake | RSIS text (Andhra Pradesh, Godavari/Krishna) with no number or area. The asset is named after the *Wildlife Sanctuary*, whose boundary may differ from the Ramsar site (RSIS 90,100 ha) | **MATCH UNCERTAIN** |
| 30 | `Nalsarovar_Wildlife_Sanctuary` | 2078 | Nalsarovar | RSIS text (Gujarat, Thar Desert) with no number or area. Named after the *Wildlife Sanctuary* | **MATCH UNCERTAIN** |
| 39 | `Point_Calimere_Wildlife_Sanctuary` | 1210 | Point Calimere Wildlife and Bird Sanctuary | RSIS text (257 bird species) with no number or area. The asset says "Wildlife Sanctuary" while the Ramsar site is the "Wildlife *and Bird* Sanctuary" (RSIS 38,500 ha) | **MATCH UNCERTAIN** |

The six UNCERTAIN mappings each have exactly one RSIS site with that name and state, so a different identity is unlikely. What is not established is whether the **polygon** is the Ramsar boundary or a sanctuary boundary. `validate_rois` answers this from the polygon's area ratio and the RSIS point test once the files exist. **No mapping was changed.**

### B.2 The 53 "exact" mappings

The same evidence check found **no contradiction**. Three cite a matching site number (Bhoj 1206, Rudrasagar 1572, Upper Ganga 1574), 22 give a matching area, and the rest match by name. Two automatic flags were false positives: Hirakud's "436,000 ha" is irrigated area, and Hygam's "site no. 461" refers to its neighbour Wular Lake. `Kanjirankulam_Bird_Sanctuary` has no GEE description because of the `nmae` typo.

---

## C. Catalog validation

**NOT PERFORMED (blocked: credentials, ROI polygons).**

Prepared: `live_validation` records the following per site:

- item count, first and last acquisition, tile IDs;
- cloud range, items missing cloud metadata, items at 100 %;
- minimum ROI footprint coverage, processing baselines;
- the number of ties at the minimum cloud cover;
- the selected scene and the 10 least-cloudy candidates.

Representative sites (from the GEE export script):

| Role | Asset | Ramsar # | RSIS area |
|---|---|---|---|
| Small (< 1 km pixel) | `renuka` | 1571 | 20 ha |
| Small–medium | `Sirpur_wetland` | 2478 | 161 ha |
| Large | `chilka` | 229 | 116,500 ha |
| Likely multi-tile | `sundarban_wetland` | 2370 | 423,000 ha |

### C.1 CRS and axis order (section 6): NOT VERIFIED LIVE

What is prepared:

| API | Evidence the harness will record |
|---|---|
| Catalog | Axis probe: the same January 2024 search with the lon/lat bbox and with the axes swapped. Only the correct order should return footprints that touch the ROI |
| Process | Returned raster bounds, converted back to lon/lat, must contain the ROI bbox and the RSIS point |
| Statistical | `sampleCount` compared with the number of 1 km pixels expected from the ROI area. The request is in the ROI's UTM zone, built with pyproj `always_xy=True` |

What is already verified offline (tests):
- GeoJSON is always `[lon, lat]`.
- The Statistical API geometry is sent in UTM metres.
- The Process API geometry is sent in EPSG:3857.
- The returned image corners map back to the ROI's lon/lat.

### C.2 Cloud-cover semantics (section 7): UNKNOWN

| | Field | Scope |
|---|---|---|
| GEE | `CLOUDY_PIXEL_PERCENTAGE` (granule metadata; `CLOUD_COVERAGE_ASSESSMENT` also present) | One MGRS tile (granule) |
| Sentinel Hub | Catalog `eo:cloud_cover`; `dataFilter.maxCloudCoverage` | "per tile", per CDSE documentation |

Which ESA metadata field `eo:cloud_cover` is populated from is **not documented** in the pages consulted. Classification: **unknown**. The harness compares both fields per (date, tile) once GEE `scenes_*.csv` and live Catalog results exist.

### C.3 Scene selection (section 8): NOT PERFORMED

The algorithm is unchanged:
- strict `< threshold`;
- items without cloud metadata excluded;
- ties go to the earliest acquisition, then the item ID. This differs from GEE, which breaks ties arbitrarily, and is documented.

---

## D. Process validation

**NOT PERFORMED for NDCI, NDTI, NDWI and NDMI (blocked).**

Verified offline:
- Each generated evalscript is executed in Node on sample pixels. It returns `(a − b)/(a + b)`.
- SCL 8/9/10 is masked, and SCL 3 (shadow) is *not*, which matches the approved QA60 substitute.
- `a + b = 0` and no-data return NaN, each with its own status code.
- The palette interpolation matches GEE's evenly spaced stops.

### D.1 Cloud mask (section 10)

| | Mask |
|---|---|
| GEE | QA60 bits 10 (opaque) and 11 (cirrus), 60 m |
| Sentinel Hub | SCL classes 8, 9, 10, 20 m (**migration substitute, not identical**) |

Live behaviour: **not observed.**

### D.2 Response size (section 19): NOT MEASURED

No polygons and no live rasters, so no size was measured. Two design facts are known without measuring:

- The Process request is capped at **2500 × 2500 px**. The two-band FLOAT32 GeoTIFF Sentinel Hub returns is therefore up to **~50 MB uncompressed** (2500 × 2500 × 2 bands × 4 bytes) per map request, and `map.tif` repeats the full request.
- The PNG in the JSON is base64 (+33 %). Its size depends on the data and cannot be predicted honestly.

The harness records `geotiff_bytes`, `png_data_uri_chars` and `json_response_bytes` per site and index. Whether **FRONTEND/API OPTIMIZATION REQUIRED** applies has to be decided from those measurements.

---

## E. Statistical validation

**NOT PERFORMED (blocked).**

Verified offline:
- The request structure: UTM CRS, `resx = resy = 1000`, `P1D`, BILINEAR, `harmonizeValues: true`, no SCL, one request per calendar year.
- Parsing, including days without valid pixels, `"NaN"` means, per-interval errors, and the exclusive end date.

### E.1 The 1000 m methodology (section 12)

| | GEE | Sentinel Hub |
|---|---|---|
| Method | `reduceRegion(mean, roi, scale=1000)`, pyramid (mean-aggregated) inputs | Statistical API mean over valid pixels |
| Resolution | 1000 m | 1000 m (UTM) |
| Resampling | Mean pyramids | BILINEAR (closest available; no area average) |
| Observed difference | Not measured | Not measured |

Renuka (RSIS 20 ha) and Sirpur (161 ha): a 1 km pixel is 100 ha, so **Renuka's ROI is smaller than one output pixel**. For Sirpur this depends on the polygon.

### E.2 Partially covered pixels (section 13): **UNRESOLVED**

```text
Observed Sentinel Hub behaviour: not observed. The CDSE Statistical API page says pixels
  partially intersecting the geometry are "typically included based on overlap"; the exact
  rule (pixel centre vs any overlap, weighting) is not documented.
Expected GEE behaviour: ee.Reducer.mean() in reduceRegion weights each pixel by the fraction
  of its area inside the region (not verified in this environment).
Difference: UNRESOLVED.
```

---

## F. GEE comparison

**NOT PERFORMED.** There are no GEE reference exports and no live results.

| Site | Index | GEE scene | SH scene | GEE date | SH date | GEE map | SH map | GEE points | SH points | MAD | Max AD | Classification |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| renuka / Sirpur / chilka / sundarban | NDCI, NDTI, NDWI, NDMI | — | — | — | — | — | — | — | — | — | — | **UNRESOLVED (no data)** |

Prepared: [`docs/validation/gee/phase-j-reference-export.js`](validation/gee/phase-j-reference-export.js) (Earth Engine Code Editor) exports:

- the **74 ROI polygons** as `<asset>.geojson`;
- the candidate scenes with `CLOUDY_PIXEL_PERCENTAGE`, `CLOUD_COVERAGE_ASSESSMENT` and `PROCESSING_BASELINE`;
- the map `.first()` selection, with QA60 and index pixel counts inside the ROI;
- the per-image chart series. This is the same `reduceRegion(mean, scale 1000)` that `ui.Chart.image.series` computes, exported to CSV rather than copied by hand.

`live_validation --gee-dir` produces the comparison, restricted to days where GEE has a single granule so the values are comparable, and reports GEE multi-granule days separately.

### F.1 QA60 2022–2024 (section 17): NOT VERIFIED

The GEE catalog statement that QA60 is masked from 2022-01-25 to 2024-02-28 is documentary. The inference that the GEE map is blank when the selected image falls in that window is **unverified**. The export script measures it directly (`qa60_unmasked_pixels_in_roi`, `index_valid_pixels_in_roi_20m` for the `.first()` image). The warning stays on every map response, and the behaviour is not reproduced.

---

## G. X1–X6

| Difference | Status | Evidence |
|---|---|---|
| X1 (QA60 vs SCL) | **CONFIRMED DIFFERENCE (documentation)**; effect NOT TESTABLE | QA60 is absent from the CDSE `sentinel-2-l2a` band list; GEE uses QA60. No live comparison |
| X2 (single tile vs stitched) | **CONFIRMED DIFFERENCE (documentation)**; effect NOT TESTABLE | CDSE documents mosaicking with no tile filter; GEE images are per granule |
| X3 (1000 m aggregation) | **CONFIRMED DIFFERENCE (documentation)**; magnitude NOT TESTABLE | Sentinel Hub downsampling is NEAREST, BILINEAR or BICUBIC only |
| X4 (processing baseline) | **NOT TESTABLE** | Needs per-scene baselines from both archives (both tools record them) |
| X5 (low values / zero denominator) | **NOT TESTABLE** | Needs a pixel-level comparison. Zero-denominator handling verified offline in the evalscripts |
| X6 (cloud filter ≤ vs <) | **CONFIRMED DIFFERENCE (documentation)**; effect NOT TESTABLE | CDSE: `maxCloudCoverage` = "at most". GEE uses `lt`. Whether any tile sits exactly at 100 % will be counted from live Catalog results (`items_at_100_percent`) |

No X item is removed.

---

## Error handling (section 18): VALIDATED (mocked HTTP)

| Case | Result | Test |
|---|---|---|
| Missing Copernicus credentials | 503 `copernicus_not_configured`, no outbound call | `test_not_configured_is_explicit`, `test_client_not_configured_raises_and_sends_nothing` |
| Invalid credentials | 502 `copernicus_auth_failed`, secret absent | `test_invalid_credentials` |
| Invalid ROI | 409 `roi_invalid` with reason (e.g. swapped axes) | `test_invalid_roi_rejected_with_reason` |
| Missing ROI | 409 `roi_missing`, **no** Sentinel Hub request | `test_no_analysis_without_roi_polygon` |
| Unknown wetland | 404 `wetland_not_found` | `test_unknown_wetland` |
| Unknown index | 422 | `test_parameter_validation` |
| Invalid date range | 422 `invalid_date_range` | `test_parameter_validation` |
| Empty Catalog | 404 `no_scenes` | `test_empty_catalog_response` |
| Empty / non-GeoTIFF Process response | 502 `sentinel_hub_invalid_response` | `test_empty_or_garbled_process_response` (**was an unhandled 500; fixed**) |
| Empty Statistical response | 200 with no points and an explicit warning | `test_empty_statistical_response` |
| Non-JSON Statistical/Catalog response | 502 `sentinel_hub_invalid_response` | `test_non_json_statistical_response` (**was an unhandled 500; fixed**) |
| Copernicus 4xx | 502 `sentinel_hub_error` with upstream message and status | `test_copernicus_4xx` |
| Copernicus 500 | 502 `sentinel_hub_error`, `upstream_status: 500` | `test_copernicus_500` |
| Copernicus 503 | Bounded retries (3 calls, 2 waits), then 504 `copernicus_unavailable` | `test_copernicus_503_…` (**was reported as "rate limited"; fixed**) |
| 429 with Retry-After | Bounded retries (3 calls), then 503 with `Retry-After` forwarded | `test_rate_limited_bounded_with_retry_after` |
| Network failure | 504 `copernicus_unavailable` | `test_network_failure` |

Stack traces: the two unhandled-500 paths above would have returned a **traceback** because `DEBUG=true` is the default. Both paths are now handled. In addition, `app/main.py` disables FastAPI debug mode whenever `APP_ENV=production`. Development keeps tracebacks for unexpected errors.

---

## H. Blocking issues

1. **No Copernicus Data Space credentials.** Nothing live can run.
2. **No GEE ROI polygons.** All 74 are missing, so no analysis can run, even with credentials.
3. **No GEE reference outputs.** No comparison is possible.
4. **Six manual mappings are UNCERTAIN** until their polygons can be checked.
5. **Unresolved scientific items:** partial-pixel handling (E.2), cloud-cover field semantics (C.2), the QA60 blank-map inference (F.1), X4 and X5. None can be settled without the data above.

## I. Recommended next action

Provide Copernicus Data Space OAuth credentials in `backend/.env`. Run `docs/validation/gee/phase-j-reference-export.js` in Earth Engine with access to `projects/ee-ramsarwetlands5`. Place the 74 exported `<asset>.geojson` files in `backend/data/roi/` and the CSVs in a folder. Then run:

```bash
cd backend
python -m app.tools.validate_rois --json ../docs/validation/roi-validation.json
python -m app.tools.live_validation --gee-dir <folder with the GEE CSVs>
```

and complete sections C–G of this report from the outputs.

---

## Changes made in Phase J

| File | Change | Why |
|---|---|---|
| `app/services/copernicus/errors.py` | Added `CopernicusInvalidResponse` | Empty or garbled 2xx bodies previously caused unhandled 500s |
| `app/services/copernicus/client.py` | Added `post_json`; 503 after retries → `CopernicusUnavailable` | Non-JSON handling; 503 was mislabelled as a rate limit |
| `app/services/copernicus/catalog.py`, `statistics.py` | Use `post_json` | As above |
| `app/services/copernicus/process.py` | Empty body → `CopernicusInvalidResponse` | As above |
| `app/services/water_quality/analysis.py` | GeoTIFF read errors → `CopernicusInvalidResponse` | As above |
| `app/api/routes/water_quality.py` | Map the new error to 502 `sentinel_hub_invalid_response` | As above |
| `app/main.py` | Debug mode off when `APP_ENV=production`; typing cast | No tracebacks in production; `mypy .` |
| `app/services/datasets/climate.py` | Renamed a shadowed loop variable; `TypeGuard` | Type-only fixes so `mypy .` passes (no behaviour change) |
| `app/tools/validate_rois.py` | New: validates all 74 ROIs | Phase J §3–4 |
| `app/tools/live_validation.py` | New: live harness and GEE comparison; refuses to run without credentials | Phase J §5–17 |
| `docs/validation/gee/phase-j-reference-export.js` | New: GEE export script | Phase J §14 |
| `tests/test_water_quality_errors.py`, `tests/test_validation_tools.py` | New tests (16) | §18 and the tools |
| `tests/test_copernicus_client.py`, `tests/test_wetland_roi.py` | Type annotations only | `mypy .` |

**No scientific methodology was changed.** Formulas, cloud handling, scene selection, resolution and resampling are all as approved.
