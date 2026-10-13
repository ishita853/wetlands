"""Build the per-site boundary manifest from the raw sources.

    python -m app.tools.build_boundaries [--raw data/boundaries/raw/rsis/<file>.geojson]

Inputs (never modified):
- the 101-site master list (RAMSAR_SITES_FILE, from the RSIS India export);
- the GEE ROI manifest (GEE_ROI_MANIFEST_FILE) and exported GEE ROIs (WETLAND_ROI_DIR);
- the imported ROIs and their manifest (IMPORTED_ROI_DIR);
- the raw RSIS WFS response (newest file in BOUNDARIES_DIR/raw/rsis unless --raw).

Outputs (fully reproducible from the inputs; no timestamps of their own):
- BOUNDARIES_DIR/boundary-manifest.json         one record per Ramsar site
- BOUNDARIES_DIR/missing-authoritative-boundaries.json
- BOUNDARIES_DIR/coverage-report.json               all 101 sites: which ROI, or why none
- BOUNDARIES_DIR/validation/boundary-validation-report.md
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from shapely.geometry import shape

from app.core.config import settings
from app.services.wetlands import boundaries as b
from app.services.wetlands import imported as im
from app.services.wetlands import provided as p
from app.services.wetlands.resolver import (
    GEE_PROVENANCE,
    IMPORTED_PROVENANCE,
    PROVIDED_PROVENANCE,
    RoiUnavailable,
    resolve_analysis_roi,
)
from app.services.wetlands.roi import lookup_roi
from app.services.wetlands.sites import load_sites

TOOL_VERSION = "3"


def newest_raw(raw_dir: Path) -> Path:
    files = sorted(raw_dir.glob("*.geojson"))
    if not files:
        raise FileNotFoundError(f"No raw RSIS response in {raw_dir}.")
    return files[-1]


def _official(site, source: b.RsisSource, raw_rel: str) -> dict[str, Any]:
    features = source.features_by_site.get(site.id, [])
    if not features:
        return {
            "source": None,
            "status": "missing_authoritative_boundary",
            "reason": "RSIS publishes no boundary polygon for this site (centroid only).",
        }
    parts = [shape(f["geometry"]) for f in features]
    validation = b.validate_parts(parts, source.crs_name)
    geometry = b.assemble_parts(parts)
    props = [f["properties"] for f in features]
    area_off = props[0].get("area_off")
    reasons: list[str] = list(validation.errors)
    area_ratio = (
        round(validation.area_ha / area_off, 4) if validation.area_ha and area_off else None
    )
    if area_ratio is not None and abs(area_ratio - 1) > b.AREA_RATIO_TOLERANCE:
        reasons.append(
            f"Polygon area differs from the RSIS official area by {abs(area_ratio - 1):.1%} "
            f"(application tolerance {b.AREA_RATIO_TOLERANCE:.0%})."
        )
    point_distance = None
    if site.latitude is not None and site.longitude is not None:
        point_distance = round(b.point_distance_m(geometry, site.latitude, site.longitude), 1)
        if point_distance > 0:
            reasons.append(
                f"The RSIS/Excel site coordinate lies {point_distance:.0f} m outside the polygon."
            )
    if validation.errors:
        status = "invalid"
    elif reasons:
        status = "review_required"
    else:
        status = "verified"
    return {
        "source": "RSIS",
        "status": status,
        "reasons": reasons,
        "source_layer": source.meta.get("layer", "ramsar_sdi:features_published"),
        "source_ids": {"ramsarid": site.id, "v_idris": [p.get("v_idris") for p in props]},
        "official_name": props[0].get("officialname"),
        "area_off_ha": area_off,
        "raw_file": raw_rel,
        "raw_sha256": source.meta["sha256"],
        "retrieved_at": source.meta.get("retrieved_at"),
        "crs": "EPSG:4326",
        "geometry_sha256": b.geometry_sha256(geometry),
        "version": "rsis-{}-{}".format(
            source.meta.get("retrieved_at", "unknown"), source.meta["sha256"][:12]
        ),
        "assembly": "RSIS features collected into one MultiPolygon without dissolving or repair",
        "area_ratio_to_area_off": area_ratio,
        "site_point_distance_m": point_distance,
        "validation": validation.as_dict(),
    }


def _gee(site_id: int) -> tuple[dict[str, Any], Any]:
    lookup = lookup_roi(site_id)
    entry = lookup.entry
    if entry is None:
        return {"source": None, "status": "not_in_gee_app"}, None
    record: dict[str, Any] = {
        "source": "existing GEE application ROI (not an official Ramsar boundary)",
        "asset_reference": entry.gee_asset_id,
        "gee_table_index": entry.gee_table_index,
        "mapping": entry.mapping,
        "mapping_status": "uncertain" if entry.mapping == "manual_uncertain" else "verified",
        "mapping_evidence": entry.mapping_evidence,
        "file": f"{entry.gee_asset_name}.geojson",
        "crs": "EPSG:4326",
        "status": {"missing": "missing_export", "invalid": "invalid", "available": "available"}[
            lookup.status
        ],
    }
    if lookup.reason:
        record["reason"] = lookup.reason
    if lookup.roi is not None:
        record.update(
            sha256_prefix=lookup.roi.version,
            area_ha=round(b.geodesic_area_ha(lookup.roi.geometry), 4),
            feature_count=lookup.roi.feature_count,
        )
    return record, lookup.roi


def _provided(site_id: int, rsis: b.RsisSource) -> dict[str, Any]:
    roi = p.lookup_provided(site_id)
    record: dict[str, Any] = {
        "source": (
            "provided ROI dataset (India Ramsar Sites September 2026; RSIS-derived)"
            if roi.status != "missing"
            else None
        ),
        "status": roi.status,
        "reason": roi.reason,
    }
    if roi.geometry is None:
        return record
    record.update(
        source_ids=roi.source_ids,
        feature_count=roi.feature_count,
        crs="EPSG:4326 (declared CRS84)",
        version=roi.version,
        geometry_sha256=roi.geometry_sha256,
        area_ha=roi.area_ha,
        validation=roi.validation.as_dict() if roi.validation else None,
    )
    rsis_features = rsis.features_by_site.get(site_id)
    if rsis_features:
        rsis_geometry = b.assemble_parts([shape(f["geometry"]) for f in rsis_features])
        record["vs_rsis"] = {
            # One-off check (2026-09-25, see provided-roi.meta.json): max Hausdorff 7.8 mm.
            "area_ratio": round(
                b.geodesic_area_ha(roi.geometry) / b.geodesic_area_ha(rsis_geometry), 6
            ),
            "same_v_idris": sorted(roi.source_ids.get("v_idris", []))
            == sorted(f["properties"].get("v_idris") for f in rsis_features),
        }
    return record


def _imported(site_id: int) -> dict[str, Any]:
    roi = im.lookup_imported(site_id)
    entry = roi.entry
    if entry is None:
        return {"source": None, "status": "missing", "reason": roi.reason}
    record: dict[str, Any] = {
        "source": "imported ROI (team-supplied shapefile; not a GEE ROI)",
        "status": roi.status,
        "reason": roi.reason,
        "file": entry.file,
        "source_archive": entry.source_archive,
        "origin": entry.origin,
        "origin_evidence": entry.origin_evidence,
        "mapping": entry.mapping,
        "mapping_status": "uncertain" if entry.mapping == "manual_uncertain" else "verified",
        "mapping_evidence": entry.mapping_evidence,
    }
    if roi.geometry is not None:
        record.update(
            crs="EPSG:4326 (declared CRS84)",
            version=roi.version,
            geometry_sha256=roi.geometry_sha256,
            area_ha=roi.area_ha,
            feature_count=roi.feature_count,
        )
    return record


def _water_quality(site_id: int) -> dict[str, Any]:
    try:
        roi = resolve_analysis_roi(site_id)
    except RoiUnavailable as exc:
        return {"source": None, "status": "unavailable", "reason": exc.message}
    return {"source": roi.source, "status": "available", "reason": None}


def _norm(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum())


def matching_report(sites: dict[int, Any]) -> dict[str, Any]:
    """Provided dataset vs the 101-site master list (Ramsar number first, then name)."""
    dataset = p.load_dataset()
    if dataset is None:
        return {"dataset": None}
    features = [f for fs in dataset.features_by_site.values() for f in fs]
    ids = set(dataset.features_by_site)
    names_by_id = {
        i: {(f["properties"].get("officialna") or "") for f in fs}
        for i, fs in dataset.features_by_site.items()
    }
    name_mismatches = [
        {"ramsar_number": i, "names": sorted(names), "master_name": sites[i].name}
        for i, names in names_by_id.items()
        if i in sites and any(_norm(n) != _norm(sites[i].name) for n in names)
    ]
    by_name: dict[str, set[int]] = {}
    for site_id, names in names_by_id.items():
        for n in names:
            by_name.setdefault(n, set()).add(site_id)
    geometry_hashes: dict[str, list[int]] = {}
    for f in features:
        key = b.geometry_sha256(shape(f["geometry"]))
        geometry_hashes.setdefault(key, []).append(f["properties"].get("ramsarid"))
    return {
        "dataset": dataset.path.name,
        "dataset_sha256": dataset.sha256,
        "crs": dataset.crs_name,
        "master_sites": len(sites),
        "polygon_features": len(features),
        "features_without_ramsar_id": dataset.features_without_id,
        "distinct_ramsar_ids": len(ids),
        "match_method": "ramsarid (Ramsar site number); names used only as a cross-check",
        "matched_master_sites": len(ids & set(sites)),
        "unmatched_master_sites": sorted(set(sites) - ids),
        "unmatched_polygon_ids": sorted(ids - set(sites)),
        "multipart_sites": {
            str(i): len(fs) for i, fs in sorted(dataset.features_by_site.items()) if len(fs) > 1
        },
        "exact_duplicate_geometries": [v for v in geometry_hashes.values() if len(v) > 1],
        "duplicate_names_across_ids": {n: sorted(v) for n, v in by_name.items() if len(v) > 1},
        "ambiguous_matches": [],
        "name_mismatches_by_id": name_mismatches,
    }


def _analysis(gee: dict[str, Any], official: dict[str, Any]) -> dict[str, Any]:
    if gee["status"] == "available" and gee["mapping_status"] == "verified":
        gee_mode = {"source": "gee_roi", "status": "available", "reason": None}
    elif gee["status"] == "available":
        gee_mode = {
            "source": None,
            "status": "unavailable",
            "reason": "GEE ROI present but its Ramsar mapping is uncertain.",
        }
    elif gee["status"] == "not_in_gee_app":
        gee_mode = {"source": None, "status": "unavailable", "reason": "No GEE ROI for this site."}
    else:
        gee_mode = {"source": None, "status": "unavailable", "reason": gee.get("reason")}
    if official["status"] == "verified":
        official_mode = {"source": "official_boundary", "status": "available", "reason": None}
    else:
        official_mode = {
            "source": None,
            "status": "unavailable",
            "reason": f"Official boundary status: {official['status']}.",
        }
    return {
        "policy": (
            "water_quality (roi=auto): the provided ROI if valid, else an imported ROI, else a "
            "GEE ROI (each with a verified mapping). gee_comparison: only a GEE ROI with a "
            "verified mapping. official_explorer: only an RSIS boundary with status "
            "'verified'. No geometry is ever derived from coordinates."
        ),
        "gee_comparison": gee_mode,
        "official_explorer": official_mode,
    }


def build(raw_path: Path) -> dict[str, Any]:
    sites = load_sites()
    boundaries_dir = Path(settings.BOUNDARIES_DIR)
    source = b.load_rsis_raw(raw_path)
    raw_rel = raw_path.resolve().relative_to(boundaries_dir.resolve()).as_posix()
    unknown_rsis = sorted(set(source.features_by_site) - set(sites))
    records = []
    for site in sorted(sites.values(), key=lambda s: s.id):
        official = _official(site, source, raw_rel)
        gee, gee_roi = _gee(site.id)
        comparison = None
        if gee_roi is not None and official["source"] == "RSIS":
            parts = [shape(f["geometry"]) for f in source.features_by_site[site.id]]
            rsis_geometry = b.assemble_parts(parts)
            comparison = b.compare_geometries(
                gee_roi.geometry, True, rsis_geometry, official["validation"]["valid"]
            )
            comparison["gee_contains_site_point"] = gee_roi.geometry.contains(
                shape({"type": "Point", "coordinates": [site.longitude, site.latitude]})
            )
            comparison["rsis_contains_site_point"] = official["site_point_distance_m"] == 0
        records.append(
            {
                "ramsar_number": site.id,
                "name": site.name,
                "state": site.state,
                "latitude": site.latitude,
                "longitude": site.longitude,
                "official_boundary": official,
                "provided_roi": _provided(site.id, source),
                "imported_roi": _imported(site.id),
                "gee_roi": gee,
                "gee_vs_official": comparison,
                "analysis_boundary": {
                    **_analysis(gee, official),
                    "water_quality": _water_quality(site.id),
                },
            }
        )
    return {
        "tool_version": TOOL_VERSION,
        "sources": {
            "master_sites": Path(settings.RAMSAR_SITES_FILE).name,
            "gee_roi_manifest": Path(settings.GEE_ROI_MANIFEST_FILE).name,
            "provided_roi": Path(settings.PROVIDED_ROI_FILE).name,
            "imported_roi_manifest": "imported-roi/manifest.json",
            "rsis_raw": {
                k: source.meta.get(k)
                for k in ("raw_file", "retrieved_at", "query", "layer", "sha256", "feature_count")
            },
            "rsis_sites_not_in_master_list": unknown_rsis,
        },
        "thresholds": {
            "type": "application validation thresholds (not an official standard)",
            "official_area_ratio_tolerance": b.AREA_RATIO_TOLERANCE,
            "comparison": {
                "IOU_MATCH": b.IOU_MATCH,
                "AREA_DIFF_MATCH": b.AREA_DIFF_MATCH,
                "IOU_MINOR": b.IOU_MINOR,
            },
        },
        "provided_roi_matching": matching_report(sites),
        "sites": records,
    }


def summarize(manifest: dict[str, Any]) -> dict[str, Any]:
    sites = manifest["sites"]

    def count(predicate) -> int:
        return sum(1 for s in sites if predicate(s))

    gee_usable = {
        s["ramsar_number"]
        for s in sites
        if s["analysis_boundary"]["gee_comparison"]["status"] == "available"
    }
    official_usable = {
        s["ramsar_number"] for s in sites if s["official_boundary"]["status"] == "verified"
    }
    provided_usable = {
        s["ramsar_number"] for s in sites if s["provided_roi"]["status"] == "available"
    }
    imported_usable = {
        s["ramsar_number"]
        for s in sites
        if s["imported_roi"]["status"] == "available"
        and s["imported_roi"]["mapping_status"] == "verified"
    }
    usable = gee_usable | official_usable | provided_usable | imported_usable
    wq = [s["analysis_boundary"]["water_quality"] for s in sites]
    return {
        "total_sites": len(sites),
        "gee": {
            "in_manifest": count(lambda s: s["gee_roi"]["status"] != "not_in_gee_app"),
            "present": count(lambda s: s["gee_roi"]["status"] in ("available", "invalid")),
            "valid": count(lambda s: s["gee_roi"]["status"] == "available"),
            "mapping_verified": count(lambda s: s["gee_roi"].get("mapping_status") == "verified"),
            "mapping_uncertain": count(lambda s: s["gee_roi"].get("mapping_status") == "uncertain"),
            "missing_export": count(lambda s: s["gee_roi"]["status"] == "missing_export"),
        },
        "rsis": {
            "available": count(lambda s: s["official_boundary"]["source"] == "RSIS"),
            "verified": count(lambda s: s["official_boundary"]["status"] == "verified"),
            "review_required": count(
                lambda s: s["official_boundary"]["status"] == "review_required"
            ),
            "invalid": count(lambda s: s["official_boundary"]["status"] == "invalid"),
            "missing": count(
                lambda s: s["official_boundary"]["status"] == "missing_authoritative_boundary"
            ),
        },
        "imported": {
            "present": count(lambda s: s["imported_roi"]["status"] != "missing"),
            "valid": count(lambda s: s["imported_roi"]["status"] == "available"),
            "mapping_uncertain": count(
                lambda s: s["imported_roi"].get("mapping_status") == "uncertain"
            ),
            "by_origin": {
                origin: count(lambda s, o=origin: s["imported_roi"].get("origin") == o)
                for origin in (
                    "rsis_feature",
                    "rsis_feature_repaired_by_supplier",
                    "supplied_shapefile",
                )
            },
        },
        "provided": {
            "available": len(provided_usable),
            "invalid": count(lambda s: s["provided_roi"]["status"] == "invalid"),
            "missing": count(lambda s: s["provided_roi"]["status"] == "missing"),
        },
        "water_quality_analysis": {
            "provided_roi": sum(1 for w in wq if w["source"] == "provided_roi"),
            "imported_roi": sum(1 for w in wq if w["source"] == "imported_roi"),
            "gee_roi": sum(1 for w in wq if w["source"] == "gee_roi"),
            "unavailable": sum(1 for w in wq if w["status"] == "unavailable"),
        },
        "combined": {
            "at_least_one_usable": len(usable),
            "none": len(sites) - len(usable),
            "gee_verified_usable": len(gee_usable),
            "official_verified": len(official_usable),
            "provided_valid": len(provided_usable),
            "imported_verified_usable": len(imported_usable),
        },
    }


def report_markdown(manifest: dict[str, Any], summary: dict[str, Any]) -> str:
    sites = manifest["sites"]
    raw = manifest["sources"]["rsis_raw"]
    lines = [
        "# Boundary validation report",
        "",
        "Generated by `python -m app.tools.build_boundaries` from:",
        f"- RSIS raw `{raw['raw_file']}` (retrieved {raw['retrieved_at']}, "
        f"SHA-256 `{raw['sha256']}`, {raw['feature_count']} features)",
        f"- master list `{manifest['sources']['master_sites']}`, GEE manifest "
        f"`{manifest['sources']['gee_roi_manifest']}`",
        "",
        "Thresholds are application validation thresholds, not an official standard.",
        "",
        "## Counts",
        "",
        "```json",
        json.dumps(summary, indent=2),
        "```",
        "",
        "## Official boundaries needing attention",
        "",
        "| Ramsar # | Site | Status | Reasons |",
        "|---|---|---|---|",
    ]
    for s in sites:
        o = s["official_boundary"]
        if o["status"] in ("invalid", "review_required"):
            lines.append(
                f"| {s['ramsar_number']} | {s['name']} | {o['status']} | "
                f"{'; '.join(o['reasons'])} |"
            )
    lines += [
        "",
        "## Sites without a published official boundary",
        "",
        "| Ramsar # | Site | State | GEE ROI asset |",
        "|---|---|---|---|",
    ]
    for s in sites:
        if s["official_boundary"]["status"] == "missing_authoritative_boundary":
            lines.append(
                f"| {s['ramsar_number']} | {s['name']} | {s['state']} | "
                f"{s['gee_roi'].get('asset_reference') or '—'} |"
            )
    lines += ["", "## GEE ROI vs official boundary", ""]
    compared = [s for s in sites if s["gee_vs_official"]]
    if not compared:
        lines.append("No comparisons: no GEE ROI polygon has been exported yet.")
    else:
        lines += [
            "| Ramsar # | Site | GEE ha | RSIS ha | Diff % | IoU | Status |",
            "|---|---|---|---|---|---|---|",
        ]
        for s in compared:
            c = s["gee_vs_official"]
            lines.append(
                f"| {s['ramsar_number']} | {s['name']} | {c['gee_area_ha']:g} | "
                f"{c['rsis_area_ha']:g} | {c['area_difference_percent']} | "
                f"{c['iou']} | {c['status']} |"
            )
    matching = manifest.get("provided_roi_matching") or {}
    lines += [
        "",
        "## Provided ROI dataset vs the 101-site master list",
        "",
        "```json",
        json.dumps(matching, indent=2),
        "```",
        "",
        "## Sites without a water-quality analysis polygon",
        "",
        "| Ramsar # | Site | Reason |",
        "|---|---|---|",
    ]
    for s in sites:
        wq = s["analysis_boundary"]["water_quality"]
        if wq["status"] == "unavailable":
            lines.append(f"| {s['ramsar_number']} | {s['name']} | {wq['reason']} |")
    lines += [
        "",
        "## Imported ROIs (team-supplied shapefiles)",
        "",
        "| Ramsar # | Site | Archive | Origin | Mapping | Status |",
        "|---|---|---|---|---|---|",
    ]
    for s in sites:
        i = s["imported_roi"]
        if i["status"] != "missing" or i.get("file"):
            lines.append(
                f"| {s['ramsar_number']} | {s['name']} | `{i['source_archive']}` | "
                f"{i['origin']} | {i['mapping_status']} | {i['status']} |"
            )
    lines += ["", "## Uncertain GEE mappings", ""]
    for s in sites:
        if s["gee_roi"].get("mapping_status") == "uncertain":
            lines.append(
                f"- {s['ramsar_number']} {s['name']} ← `{s['gee_roi']['asset_reference']}`: "
                f"{s['gee_roi']['mapping_evidence']}"
            )
    return "\n".join(lines) + "\n"


def coverage_report(manifest: dict[str, Any]) -> dict[str, Any]:
    """One row per Ramsar site: which analysis polygon is used, or exactly why none is."""
    candidates_path = Path(settings.BOUNDARIES_DIR) / "candidate-sources.json"
    candidates = (
        {c["ramsar_number"]: c for c in json.loads(candidates_path.read_text("utf-8"))["sites"]}
        if candidates_path.is_file()
        else {}
    )
    provenance = {
        "provided_roi": PROVIDED_PROVENANCE,
        "imported_roi": IMPORTED_PROVENANCE,
        "gee_roi": GEE_PROVENANCE,
    }
    rows = []
    for s in manifest["sites"]:
        provided, gee, official = s["provided_roi"], s["gee_roi"], s["official_boundary"]
        imported = s["imported_roi"]
        wq = s["analysis_boundary"]["water_quality"]
        candidate = candidates.get(s["ramsar_number"])
        rows.append(
            {
                "ramsar_id": s["ramsar_number"],
                "name": s["name"],
                "state": s["state"],
                "latitude": s["latitude"],
                "longitude": s["longitude"],
                "provided_roi": provided["status"] != "missing",
                "provided_roi_valid": provided["status"] == "available",
                "imported_roi": imported["status"] != "missing",
                "imported_roi_valid": imported["status"] == "available",
                "imported_roi_origin": imported.get("origin"),
                "imported_mapping_status": imported.get("mapping_status"),
                "gee_roi_in_app": gee["status"] != "not_in_gee_app",
                "gee_roi": gee["status"] in ("available", "invalid"),
                "gee_roi_verified": gee["status"] == "available"
                and gee.get("mapping_status") == "verified",
                "gee_mapping_status": gee.get("mapping_status"),
                "official_roi": official["source"] == "RSIS",
                "official_roi_status": official["status"],
                "analysis_available": wq["status"] == "available",
                "selected_analysis_source": wq["source"],
                "provenance": provenance.get(wq["source"] or ""),
                "reason_unavailable": wq["reason"],
                "candidate_sources_not_imported": len(candidate["candidates"]) if candidate else 0,
            }
        )
    available = [r for r in rows if r["analysis_available"]]
    return {
        "description": (
            "Water-quality analysis ROI coverage for every Ramsar site. Generated by "
            "`python -m app.tools.build_boundaries`. No geometry is derived from coordinates; "
            "candidate sources in candidate-sources.json are documented but not used."
        ),
        "policy": "roi=auto: provided ROI if valid, else an imported ROI, else a GEE ROI (each "
        "with a verified mapping), else unavailable (HTTP 409 with the reason).",
        "totals": {
            "sites": len(rows),
            "analysis_available": len(available),
            "analysis_unavailable": len(rows) - len(available),
            "by_source": {
                source: sum(1 for r in available if r["selected_analysis_source"] == source)
                for source in ("provided_roi", "imported_roi", "gee_roi")
            },
        },
        "sites": rows,
    }


def write_outputs(manifest: dict[str, Any]) -> dict[str, Any]:
    out_dir = Path(settings.BOUNDARIES_DIR)
    summary = summarize(manifest)
    (out_dir / "validation").mkdir(parents=True, exist_ok=True)
    (out_dir / "boundary-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    missing = [
        {
            "ramsar_number": s["ramsar_number"],
            "name": s["name"],
            "state": s["state"],
            "latitude": s["latitude"],
            "longitude": s["longitude"],
            "gee_roi_asset": s["gee_roi"].get("asset_reference"),
            "request": "Official Ramsar site boundary polygon (vector, with CRS)",
            "request_to": "MoEFCC Wetlands Division (India's Ramsar Administrative Authority)",
        }
        for s in manifest["sites"]
        if s["official_boundary"]["status"] == "missing_authoritative_boundary"
    ]
    (out_dir / "missing-authoritative-boundaries.json").write_text(
        json.dumps({"count": len(missing), "sites": missing}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "coverage-report.json").write_text(
        json.dumps(coverage_report(manifest), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "validation" / "boundary-validation-report.md").write_text(
        report_markdown(manifest, summary), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, help="raw RSIS GeoJSON (default: newest)")
    args = parser.parse_args()
    raw = args.raw or newest_raw(Path(settings.BOUNDARIES_DIR) / "raw" / "rsis")
    summary = write_outputs(build(raw))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
