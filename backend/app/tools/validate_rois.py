"""Validate the 74 GEE ROI polygons against the manifest and the RSIS site records.

    python -m app.tools.validate_rois [--json out.json]

For every manifest entry it reports whether the exported polygon exists and
passes the loader's checks (polygonal, WGS84 lon/lat, valid, inside India), and
adds two geometric plausibility checks against the Ramsar Sites Information
Service record: polygon area vs RSIS area, and whether the RSIS point lies
inside the polygon. It only reads files; nothing is repaired or rewritten.
"""

import argparse
import json
import sys
from typing import Any

from app.core.config import settings
from app.services.wetlands.roi import distance_to_site_point_m, load_manifest, lookup_roi
from app.services.wetlands.sites import load_sites


def validate() -> list[dict[str, Any]]:
    sites = load_sites()
    rows: list[dict[str, Any]] = []
    for entry in sorted(load_manifest().values(), key=lambda e: e.gee_table_index):
        site = sites.get(entry.ramsar_site_id)
        lookup = lookup_roi(entry.ramsar_site_id)
        row: dict[str, Any] = {
            "gee_table_index": entry.gee_table_index,
            "gee_asset": entry.gee_asset_name,
            "ramsar_site_id": entry.ramsar_site_id,
            "ramsar_site_name": site.name if site else None,
            "geometry_file": f"{entry.gee_asset_name}.geojson",
            "mapping_source": entry.mapping,
            "status": lookup.status,
            "reason": lookup.reason,
        }
        roi = lookup.roi
        if roi is not None:
            row.update(
                geometry_type=roi.geometry.geom_type,
                feature_count=roi.feature_count,
                bounds_lonlat=[round(v, 5) for v in roi.geometry.bounds],
                polygon_area_ha=roi.area_ha,
                rsis_area_ha=site.area_ha if site else None,
                area_ratio=(
                    round(roi.area_ha / site.area_ha, 3) if site and site.area_ha else None
                ),
                version=roi.version,
            )
            if site and site.latitude is not None and site.longitude is not None:
                row["rsis_point_distance_m"] = round(
                    distance_to_site_point_m(roi, site.latitude, site.longitude), 1
                )
        rows.append(row)
    return rows


def to_markdown(rows: list[dict[str, Any]]) -> str:
    header = (
        "| # | GEE asset | Ramsar # | Site | File | Mapping | Status | Type | Area ha "
        "(polygon / RSIS) | RSIS point |\n|---|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for r in rows:
        area = (
            f"{r['polygon_area_ha']:g} / {r['rsis_area_ha']:g}"
            if r.get("polygon_area_ha") is not None and r.get("rsis_area_ha")
            else ""
        )
        point = r.get("rsis_point_distance_m")
        point_text = "" if point is None else ("inside" if point == 0 else f"{point / 1000:.1f} km")
        status = r["status"] if r["status"] == "available" else f"{r['status']}: {r['reason']}"
        lines.append(
            f"| {r['gee_table_index']} | `{r['gee_asset']}` | {r['ramsar_site_id']} | "
            f"{r['ramsar_site_name']} | {r['geometry_file']} | {r['mapping_source']} | "
            f"{status} | {r.get('geometry_type', '')} | {area} | {point_text} |"
        )
    return header + "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", help="write the rows as JSON to this file")
    args = parser.parse_args()
    rows = validate()
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"ROI directory: {settings.WETLAND_ROI_DIR}")
    print(f"{len(rows)} manifest entries: {counts}\n")
    print(to_markdown(rows))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
