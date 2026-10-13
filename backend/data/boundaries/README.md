# Wetland boundaries

Three geometry sources are kept separately for every Ramsar site:

| Geometry | Where | Provenance |
|---|---|---|
| **Provided ROI** (primary water-quality analysis ROI) | `../India Ramsar Sites September 2026.geojson` and `../Indian Ramsar Sites.shp`; provenance record in `../provided-roi.meta.json` | Supplied by the project team on 2026-09-25. 114 features for 75 sites. The content is RSIS-derived: it has the same `v_idris` values and the geometry is within 8 mm |
| **Official boundary** | `raw/rsis/*.geojson` (unmodified WFS response) | Ramsar Sites Information Service, layer `ramsar_sdi:features_published` |
| **GEE ROI** | `../roi/<geeAssetName>.geojson` (see `../gee-roi-manifest.json`) | Existing GEE water-quality application. **Not** an official Ramsar boundary. Not exported yet |
| **Imported ROI** (`imported_roi`) | `../imported-roi/<ramsar id>.geojson`; per-file origin, SHA-256 and site mapping in `../imported-roi/manifest.json` | 29 zipped shapefiles supplied by the project team on 2026-09-30 (`../Ramsar Wetland Shapefiles/`), converted unchanged with `python -m app.tools.import_roi_shapefiles`. **Not** GEE ROIs: some archives are named after GEE assets, but GEE origin is not established. Origins: `supplied_shapefile` (25), `rsis_feature` (2), `rsis_feature_repaired_by_supplier` (2: Beas 2408, Saman 2413, where the supplier's copy is valid and the published RSIS geometry is not; the repair was not made here) |

Water-quality analysis (`roi=auto`) uses the provided ROI when it is valid. Otherwise it uses an imported ROI, then a GEE ROI, each only with a verified mapping. Otherwise it refuses, with a reason.

No geometry is ever derived from site coordinates (no buffers, hulls or approximations). Source geometries are never repaired, simplified or reprojected. Invalid geometry is reported, not fixed.

## Files

| File | What it is |
|---|---|
| `raw/rsis/*.geojson` | Raw RSIS response. **Never edit** |
| `raw/rsis/*.meta.json` | Retrieval time, query, layer, CRS, SHA-256 and feature count |
| `boundary-manifest.json` | One record per site: `official_boundary`, `gee_roi`, `gee_vs_official`, `analysis_boundary` |
| `missing-authoritative-boundaries.json` | Sites with no published official boundary, to request from MoEFCC (Wetlands Division) |
| `coverage-report.json` | All 101 sites: which analysis polygon is used, its provenance, or exactly why none is available (generated) |
| `candidate-sources.json` | Research record (hand-curated, 2026-09-25): possible boundaries for the 26 missing and 3 invalid sites (unpublished RSIS versions, WDPA), with provenance, licence and evidence. **None is imported or used** |
| `validation/boundary-validation-report.md` | Counts, invalid or review-required boundaries, and comparisons |

Rebuild the processed files from the raw sources. The output is deterministic.

```bash
cd backend
python -m app.tools.build_boundaries
```

## Status values

- `official_boundary.status`:
  - `verified`: every check passed;
  - `review_required`: valid geometry, but the site coordinate is outside the polygon or the area differs from `area_off` by more than 5 %;
  - `invalid`: the geometry is invalid; it is kept as published and not served;
  - `missing_authoritative_boundary`: no published polygon.
- `gee_roi.status`: `available`, `missing_export`, `invalid` or `not_in_gee_app`.
- `analysis_boundary`:
  - `gee_comparison` (water-quality reproduction) uses only a GEE ROI whose mapping is verified;
  - `official_explorer` uses only a `verified` official boundary.

The 5 % area tolerance and the IoU thresholds are **application validation thresholds**, not an official standard.
