# GEE ROI polygons (analysis geometry)

Water-quality maps and time series are computed over the wetland ROI polygons
used by the GEE application. **This folder is empty until those polygons are
exported.** Until then the API reports the analysis geometry as `missing` and
returns no satellite results for the site. No buffer around the point
coordinates is used as a substitute.

## Expected files

One GeoJSON file per GEE asset, named after the asset:

```
backend/data/roi/<geeAssetName>.geojson      e.g. chilka.geojson, east_kolkata.geojson
```

The asset names and their Ramsar site numbers are listed in
`backend/data/gee-roi-manifest.json` (74 assets).

Each file must be:

- a GeoJSON `FeatureCollection`, `Feature`, `Polygon` or `MultiPolygon`;
- in WGS84 longitude/latitude, `[lon, lat]` order (RFC 7946). A `crs` member, if present, must be CRS84 or EPSG:4326;
- a valid geometry, exported **without simplification**.

All features of a file are dissolved into one geometry, the same as GEE's
`roi.geometry()`.

## Exporting from Earth Engine (asset owner / project `ee-ramsarwetlands5`)

```javascript
var name = 'chilka';  // repeat for each asset in gee-roi-manifest.json
Export.table.toDrive({
  collection: ee.FeatureCollection('projects/ee-ramsarwetlands5/assets/' + name),
  description: name,
  fileFormat: 'GeoJSON'
});
```

The backend records a SHA-256 of each file as the geometry version, which
every analysis response reports.
