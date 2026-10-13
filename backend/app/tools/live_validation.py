"""Phase J live validation against Copernicus Data Space (and GEE exports, if given).

    python -m app.tools.live_validation [--sites 2441 2478 ...] [--gee-dir DIR]
                                        [--out docs/validation/live]

Requires COPERNICUS_CLIENT_ID / COPERNICUS_CLIENT_SECRET in the backend
environment and exported ROI polygons in WETLAND_ROI_DIR. Without them it
stops and says so; it never substitutes synthetic data.

Records, per site: Catalog results and scene selection, an axis-order probe,
the four index maps (dimensions, bounds, pixel counts, response sizes) and the
four time series (point counts, sample counts). With --gee-dir pointing at the
CSVs from docs/validation/gee/phase-j-reference-export.js it also compares
cloud metadata, selected scenes and chart values.
"""

import argparse
import csv
import json
import statistics as stats
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from shapely.geometry import Point, box, shape

from app.processing.water_quality.indices import INDICES
from app.processing.water_quality.methodology import (
    DEFAULT_END_EXCLUSIVE,
    DEFAULT_MAX_CLOUD_PERCENT,
    DEFAULT_START,
)
from app.services.copernicus import catalog
from app.services.copernicus.catalog import CATALOG_MEDIA_TYPE
from app.services.copernicus.client import get_copernicus_client
from app.services.copernicus.errors import CopernicusError
from app.services.water_quality import analysis
from app.services.wetlands.resolver import RoiUnavailable, resolve_analysis_roi
from app.services.wetlands.roi import load_manifest
from app.services.wetlands.sites import get_site

# Ramsar numbers: small crater lake, small reservoir, large delta, multi-part reservoir.
DEFAULT_SITES = [2441, 2478, 2370, 2494]


def _axis_probe(client, roi) -> dict[str, Any]:
    """Catalog with the correct lon/lat bbox vs the same bbox with axes swapped."""
    minx, miny, maxx, maxy = roi.bounds
    body: dict[str, Any] = {
        "collections": ["sentinel-2-l2a"],
        "datetime": "2024-01-01T00:00:00Z/2024-01-31T23:59:59Z",
        "limit": 100,
    }
    results: dict[str, Any] = {}
    for label, bbox in (
        ("lonlat", [minx, miny, maxx, maxy]),
        ("swapped", [miny, minx, maxy, maxx]),
    ):
        try:
            page = client.post_json(
                client.config.COPERNICUS_CATALOG_URL,
                {**body, "bbox": bbox},
                accept=CATALOG_MEDIA_TYPE,
            )
        except CopernicusError as exc:
            results[label] = {"error": str(exc)}
            continue
        feats = page.get("features", [])
        results[label] = {
            "items": len(feats),
            "items_touching_roi": sum(1 for f in feats if shape(f["geometry"]).intersects(roi)),
        }
    return results


def _series_summary(points) -> dict[str, Any]:
    if not points:
        return {"points": 0}
    samples = [p.sample_count for p in points]
    return {
        "points": len(points),
        "first": points[0].date.isoformat(),
        "last": points[-1].date.isoformat(),
        "mean_min": min(p.mean for p in points),
        "mean_max": max(p.mean for p in points),
        "sample_count_median": stats.median(samples),
        "sample_count_min": min(samples),
        "valid_pixels_min": min(p.valid_pixels for p in points),
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _gee_date(row: dict[str, str]) -> date:
    return datetime.fromisoformat(row["time_start"].replace("Z", "+00:00")).date()


def _compare(asset: str, gee_dir: Path, scenes, selected, results) -> dict[str, Any]:
    out: dict[str, Any] = {}
    gee_scenes = _read_csv(gee_dir / f"scenes_{asset}.csv")
    if gee_scenes:
        by_tile = {(s.acquired_at.date(), s.tile_id): s for s in scenes}
        diffs = []
        for row in gee_scenes:
            match = by_tile.get((_gee_date(row), (row.get("mgrs_tile") or "").lstrip("T")))
            if (
                match is not None
                and match.cloud_cover is not None
                and row["cloudy_pixel_percentage"]
            ):
                diffs.append(abs(match.cloud_cover - float(row["cloudy_pixel_percentage"])))
        out["cloud_cover"] = {
            "gee_images": len(gee_scenes),
            "sentinel_hub_items": len(scenes),
            "matched_by_date_and_tile": len(diffs),
            "abs_diff_max": max(diffs) if diffs else None,
            "abs_diff_mean": stats.fmean(diffs) if diffs else None,
            "identical_count": sum(1 for d in diffs if d < 1e-6),
        }
    gee_selection = _read_csv(gee_dir / f"map_selection_{asset}.csv")
    if gee_selection:
        row = gee_selection[0]
        out["map_selection"] = {
            "gee_image_id": row["image_id"],
            "gee_date": _gee_date(row).isoformat(),
            "gee_tile": row.get("mgrs_tile"),
            "gee_qa60_unmasked_pixels": {
                r["index"]: r["qa60_unmasked_pixels_in_roi"] for r in gee_selection
            },
            "gee_index_valid_pixels": {
                r["index"]: r["index_valid_pixels_in_roi_20m"] for r in gee_selection
            },
            "sentinel_hub_scene_id": selected.id if selected else None,
            "sentinel_hub_date": selected.acquired_at.date().isoformat() if selected else None,
            "sentinel_hub_tile": selected.tile_id if selected else None,
        }
    series_cmp = {}
    for index_key in INDICES:
        name = index_key.value
        rows = [r for r in _read_csv(gee_dir / f"series_{asset}_{name}.csv") if r.get("mean")]
        ts = results.get("timeseries", {}).get(name, {}).get("_points")
        if not rows or ts is None:
            continue
        by_day: dict[date, list[float]] = {}
        for r in rows:
            by_day.setdefault(_gee_date(r), []).append(float(r["mean"]))
        ours = {p.date: p.mean for p in ts}
        single = [abs(ours[d] - v[0]) for d, v in by_day.items() if len(v) == 1 and d in ours]
        series_cmp[name] = {
            "gee_points": len(rows),
            "gee_days": len(by_day),
            "gee_multi_granule_days": sum(1 for v in by_day.values() if len(v) > 1),
            "sentinel_hub_points": len(ts),
            "comparable_single_granule_days": len(single),
            "mean_abs_diff": stats.fmean(single) if single else None,
            "max_abs_diff": max(single) if single else None,
            "days_only_in_gee": len(set(by_day) - set(ours)),
            "days_only_in_sentinel_hub": len(set(ours) - set(by_day)),
        }
    if series_cmp:
        out["series"] = series_cmp
    return out


def run(site_ids: list[int], gee_dir: Path | None) -> dict[str, Any]:
    client = get_copernicus_client()
    manifest = {e.gee_asset_name: e for e in load_manifest().values()}
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "period": [DEFAULT_START.isoformat(), DEFAULT_END_EXCLUSIVE.isoformat()],
        "sites": {},
    }
    gee_asset = {e.ramsar_site_id: e.gee_asset_name for e in manifest.values()}
    for site_id in site_ids:
        site = get_site(site_id)
        asset = gee_asset.get(site_id, str(site_id))
        record: dict[str, Any] = {"ramsar_site_id": site_id}
        report["sites"][asset] = record
        try:
            resolved = resolve_analysis_roi(site_id)
        except RoiUnavailable as exc:
            record["roi"] = exc.code
            record["blocked"] = exc.message
            continue
        roi = resolved.geometry
        record["roi"] = resolved.source
        record["roi_version"] = resolved.version
        record["roi_bbox_lonlat"] = list(roi.bounds)
        record["roi_area_ha"] = resolved.area_ha
        record["axis_probe"] = _axis_probe(client, roi)

        request = analysis.AnalysisRequest(
            site_id, DEFAULT_START, DEFAULT_END_EXCLUSIVE, DEFAULT_MAX_CLOUD_PERCENT
        )
        scenes = catalog.search_scenes(client, roi, DEFAULT_START, DEFAULT_END_EXCLUSIVE)
        selected = catalog.select_least_cloudy(scenes, DEFAULT_MAX_CLOUD_PERCENT)
        clouds = [s.cloud_cover for s in scenes if s.cloud_cover is not None]
        record["catalog"] = {
            "items": len(scenes),
            "first": scenes[0].acquired_at.isoformat() if scenes else None,
            "last": scenes[-1].acquired_at.isoformat() if scenes else None,
            "tiles": sorted({s.tile_id or "?" for s in scenes}),
            "cloud_min": min(clouds) if clouds else None,
            "cloud_max": max(clouds) if clouds else None,
            "items_without_cloud_metadata": sum(1 for s in scenes if s.cloud_cover is None),
            "items_at_100_percent": sum(1 for c in clouds if c >= 100),
            "roi_coverage_min": min((s.roi_coverage for s in scenes), default=None),
            "processing_baselines": sorted({s.processing_baseline or "?" for s in scenes}),
            "ties_at_minimum": sum(1 for c in clouds if clouds and c == min(clouds)),
            "selected": None
            if selected is None
            else {
                "id": selected.id,
                "acquired_at": selected.acquired_at.isoformat(),
                "tile": selected.tile_id,
                "cloud_cover": selected.cloud_cover,
                "roi_coverage": selected.roi_coverage,
                "processing_baseline": selected.processing_baseline,
            },
            "lowest_10": [
                {
                    "id": s.id,
                    "date": s.acquired_at.date().isoformat(),
                    "tile": s.tile_id,
                    "cloud": s.cloud_cover,
                }
                for s in sorted(scenes, key=lambda s: (s.cloud_cover is None, s.cloud_cover))[:10]
            ],
        }

        record["maps"] = {}
        for index in INDICES.values():
            try:
                result = analysis.build_map(client, index, request)
            except (CopernicusError, analysis.NoScenes) as exc:
                record["maps"][index.key.value] = {"error": f"{type(exc).__name__}: {exc}"}
                continue
            response = result.response
            b = response.image.bounds
            raster_box = box(b.west, b.south, b.east, b.north)
            record["maps"][index.key.value] = {
                "width": response.image.width,
                "height": response.image.height,
                "resolution_m": response.traceability.spatial.resolution_m,
                "raster_bounds_lonlat": [b.west, b.south, b.east, b.north],
                "raster_contains_roi_bbox": raster_box.buffer(1e-4).contains(box(*roi.bounds)),
                "raster_contains_rsis_point": (
                    site is not None
                    and site.longitude is not None
                    and site.latitude is not None
                    and raster_box.contains(Point(site.longitude, site.latitude))
                ),
                "pixel_counts": response.pixel_counts.model_dump(),
                "value_summary": response.value_summary.model_dump(),
                "geotiff_bytes": len(result.geotiff),
                "png_data_uri_chars": len(response.image.data_uri),
                "json_response_bytes": len(response.model_dump_json()),
            }

        record["timeseries"] = {}
        for index in INDICES.values():
            try:
                ts = analysis.build_time_series(client, index, request)
            except CopernicusError as exc:
                record["timeseries"][index.key.value] = {"error": f"{type(exc).__name__}: {exc}"}
                continue
            summary = _series_summary(ts.points)
            summary["days_without_valid_pixels"] = ts.days_without_valid_pixels
            summary["expected_1km_pixels_from_area"] = round(resolved.area_ha / 100, 2)
            summary["request_crs"] = ts.traceability.spatial.request_crs
            summary["_points"] = ts.points
            record["timeseries"][index.key.value] = summary

        if gee_dir is not None:
            record["gee_comparison"] = _compare(asset, gee_dir, scenes, selected, record)
        for ts_record in record["timeseries"].values():
            ts_record.pop("_points", None)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", nargs="+", type=int, default=DEFAULT_SITES)
    parser.add_argument("--gee-dir", type=Path)
    parser.add_argument("--out", type=Path, default=Path("../docs/validation/live"))
    args = parser.parse_args()

    if not get_copernicus_client().is_configured():
        print("LIVE VALIDATION BLOCKED:\nCopernicus credentials are not configured.")
        return 2
    report = run(args.sites, args.gee_dir)
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"phase-j-live-{stamp}.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
