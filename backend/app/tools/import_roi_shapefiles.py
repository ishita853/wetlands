"""Import the team-supplied ROI shapefiles as their own analysis source (imported_roi).

    python -m app.tools.import_roi_shapefiles [--src "data/Ramsar Wetland Shapefiles"]

Input: zipped shapefiles supplied by the project team on 2026-09-30, one per site.
Output (IMPORTED_ROI_DIR): <ramsar id>.geojson per site and manifest.json recording,
for each file, its archive, SHA-256, origin and how it was matched to a Ramsar site.

These are not GEE ROIs: nothing establishes that they were exported from the GEE
application, even where an archive is named after a GEE asset. Origins:
- rsis_feature: the layer carries RSIS attributes and matches the RSIS geometry;
- rsis_feature_repaired_by_supplier: as above, but the supplier's copy is valid where
  the published RSIS geometry is invalid (repaired before supply, not by this tool);
- supplied_shapefile: attributes Name/serial_num only; the archive is named after a
  GEE asset, and the site is identified through that asset's gee-roi-manifest mapping.

Geometry is written as supplied: no repair, simplification, buffering or dissolving.
Every supplied layer is WGS84 longitude/latitude; anything else is reprojected to
EPSG:4326. Validation happens when the service reads the file, not here.
"""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pyogrio
from shapely.geometry import MultiPolygon, Polygon, mapping, shape

from app.core.config import BACKEND_DIR, settings
from app.services.wetlands import boundaries as b
from app.services.wetlands.roi import load_manifest

DEFAULT_SRC = BACKEND_DIR / "data" / "Ramsar Wetland Shapefiles"
SUPPLIED = "2026-09-30"

# Archive names that differ from the GEE asset name they refer to.
ARCHIVE_ALIASES = {"Pong_Dam_Lake_Wildlife_Sanctuary_(2)": "Pong_Dam_Lake_Wildlife_Sanctuary"}
# Supplied layers with neither RSIS attributes nor a GEE manifest entry.
NAME_MATCHES = {
    "chandertal": (
        1569,
        "manual_confirmed",
        "Archive and layer name 'chandertal'; Chandertal Wetland is the only Ramsar site of "
        "that name, and the polygon lies 950 m from its RSIS site point (127 ha vs RSIS 49 ha).",
    ),
}


def _plain(value: Any) -> Any:
    if hasattr(value, "item"):  # numpy scalar
        value = value.item()
    return None if value != value else value  # NaN -> null


def _read(archive: Path) -> tuple[str, list[dict[str, Any]]]:
    layers = [n for n in zipfile.ZipFile(archive).namelist() if n.lower().endswith(".shp")]
    if len(layers) != 1:
        raise ValueError(f"{archive.name}: expected one .shp, found {len(layers)}.")
    frame = pyogrio.read_dataframe(f"/vsizip/{archive.as_posix()}/{layers[0]}")
    if frame.crs is not None and frame.crs.to_epsg() != 4326:
        frame = frame.to_crs(4326)
    features = [
        {
            "type": "Feature",
            "properties": {k: _plain(v) for k, v in row.items() if k != "geometry"},
            "geometry": mapping(row.geometry),
        }
        for _, row in frame.iterrows()
    ]
    return layers[0], features


def _vs_rsis(features: list[dict[str, Any]], rsis: list[dict[str, Any]]) -> dict[str, Any]:
    """Measurements only; buffer(0) is used for the overlap arithmetic, never stored."""
    supplied_parts = [shape(f["geometry"]) for f in features]
    published_parts = [shape(f["geometry"]) for f in rsis]
    supplied, published = b.assemble_parts(supplied_parts), b.assemble_parts(published_parts)
    a, p = supplied.buffer(0), published.buffer(0)
    return {
        # Per-part validity, the rule the analysis services apply (validate_parts).
        "rsis_valid": all(part.is_valid for part in published_parts),
        "supplied_valid": all(part.is_valid for part in supplied_parts),
        "area_ratio": round(b.geodesic_area_ha(a) / b.geodesic_area_ha(p), 6),
        "symmetric_difference_fraction": round(a.symmetric_difference(p).area / p.area, 6),
        "hausdorff_deg": round(a.hausdorff_distance(p), 6),
        "vertices": {
            "supplied": sum(len(s.exterior.coords) for s in _polygons(supplied)),
            "rsis": sum(len(s.exterior.coords) for s in _polygons(published)),
        },
    }


def _polygons(geometry: MultiPolygon | Polygon) -> list[Polygon]:
    return list(geometry.geoms) if isinstance(geometry, MultiPolygon) else [geometry]


def classify(asset: str, features: list[dict[str, Any]], rsis: b.RsisSource) -> dict[str, Any]:
    props = features[0]["properties"]
    by_v_idris = {
        f["properties"].get("v_idris"): site_id
        for site_id, fs in rsis.features_by_site.items()
        for f in fs
    }
    site_id = props.get("ramsarid") or by_v_idris.get(props.get("v_idris"))
    if site_id is not None:
        site_id = int(site_id)
        comparison = _vs_rsis(features, rsis.features_by_site[site_id])
        repaired = not comparison["rsis_valid"] and comparison["supplied_valid"]
        ids = sorted(f["properties"].get("v_idris") for f in features)
        return {
            "ramsarSiteId": site_id,
            "origin": "rsis_feature_repaired_by_supplier" if repaired else "rsis_feature",
            "originEvidence": (
                f"Layer carries RSIS v_idris {ids}"
                + (f" and ramsarid {site_id}" if props.get("ramsarid") else "")
                + "; geometry compared with the published RSIS feature in vs_rsis."
                + (
                    " The published RSIS geometry is invalid and this copy is valid: it was "
                    "repaired before supply (not by this application)."
                    if repaired
                    else ""
                )
            ),
            "mapping": "exact",
            "mappingEvidence": "RSIS identifier on the supplied features.",
            "vsRsis": comparison,
        }
    gee = {e.gee_asset_name: e for e in load_manifest().values()}.get(asset)
    if gee is not None:
        return {
            "ramsarSiteId": gee.ramsar_site_id,
            "origin": "supplied_shapefile",
            "originEvidence": (
                f"Attributes {sorted(props)} only (no Ramsar or RSIS identifier). The archive is "
                f"named after GEE asset {gee.gee_asset_id}, but GEE origin of the geometry is "
                "not established."
            ),
            "mapping": gee.mapping,
            "mappingEvidence": (
                f"Archive name equals GEE asset '{asset}'; that asset's mapping: "
                f"{gee.mapping_evidence}"
            ),
        }
    if asset in NAME_MATCHES:
        site_id, mapping_status, evidence = NAME_MATCHES[asset]
        return {
            "ramsarSiteId": site_id,
            "origin": "supplied_shapefile",
            "originEvidence": f"Attributes {sorted(props)} only; not a GEE application asset.",
            "mapping": mapping_status,
            "mappingEvidence": evidence,
        }
    raise ValueError(f"{asset}: cannot identify the Ramsar site.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    args = parser.parse_args(argv)

    raw_dir = Path(settings.BOUNDARIES_DIR) / "raw" / "rsis"
    rsis = b.load_rsis_raw(sorted(raw_dir.glob("*.geojson"))[-1])
    out_dir = Path(settings.IMPORTED_ROI_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for archive in sorted(args.src.glob("*.zip"), key=lambda p: p.name.lower()):
        asset = ARCHIVE_ALIASES.get(archive.stem, archive.stem)
        layer, features = _read(archive)
        entry = classify(asset, features, rsis)
        target = out_dir / f"{entry['ramsarSiteId']}.geojson"
        body = json.dumps(
            {
                "type": "FeatureCollection",
                "name": archive.stem,
                "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
                "features": features,
            },
            ensure_ascii=False,
        )
        target.write_text(body, encoding="utf-8")
        entries.append(
            {
                "ramsarSiteId": entry.pop("ramsarSiteId"),
                "file": target.name,
                "fileSha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                "sourceArchive": archive.name,
                "sourceArchiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "sourceLayer": layer,
                "featureCount": len(features),
                **entry,
            }
        )
        print(f"{archive.name} -> {target.name} ({entry['origin']}, mapping {entry['mapping']})")
    entries.sort(key=lambda e: e["ramsarSiteId"])
    manifest = {
        "description": (
            "ROI polygons supplied by the project team as zipped shapefiles in "
            f"'{args.src.name}' ({SUPPLIED}). Source 'imported_roi': not GEE ROIs and not "
            "official Ramsar boundaries. Generated by app.tools.import_roi_shapefiles; "
            "geometry is as supplied."
        ),
        "supplied": SUPPLIED,
        "imports": entries,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
