"""Official Ramsar boundaries (RSIS) and their comparison with the GEE ROIs.

Two geometries are kept separate for every site:

- official boundary: the polygon published by the Ramsar Sites Information
  Service (layer ramsar_sdi:features_published), stored as the unmodified WFS
  response under data/boundaries/raw/rsis/;
- GEE ROI: the polygon used by the existing GEE application (data/roi/, see
  app.services.wetlands.roi).

Nothing here repairs, simplifies, buffers or reprojects a source geometry. A
site's RSIS features are combined into one MultiPolygon by collecting their
polygons unchanged (no dissolve); every check is reported, not fixed.
"""

import hashlib
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pyproj import Geod
from shapely import Geometry
from shapely.geometry import MultiPolygon, Point, Polygon, mapping, shape
from shapely.ops import unary_union
from shapely.validation import explain_validity, make_valid

from app.core.config import settings
from app.services.copernicus.geometry import reproject, utm_epsg_for

_GEOD = Geod(ellps="WGS84")
_EPSG_4326_NAMES = {
    "urn:ogc:def:crs:EPSG::4326",
    "EPSG:4326",
    "http://www.opengis.net/def/crs/EPSG/0/4326",
    "urn:ogc:def:crs:OGC:1.3:CRS84",
    "urn:ogc:def:crs:OGC::CRS84",
    "http://www.opengis.net/def/crs/OGC/1.3/CRS84",
}
# Generous India extent: a polygon outside it almost always means swapped axes.
INDIA_LON = (66.0, 99.0)
INDIA_LAT = (5.0, 38.0)

# Application validation thresholds (not an official standard).
AREA_RATIO_TOLERANCE = 0.05  # polygon area vs RSIS official area (area_off)
IOU_MATCH = 0.95
AREA_DIFF_MATCH = 0.05
IOU_MINOR = 0.80

OfficialStatus = Literal["verified", "review_required", "invalid", "missing_authoritative_boundary"]
ComparisonStatus = Literal["MATCH", "MINOR_DIFFERENCE", "SIGNIFICANT_DIFFERENCE", "REVIEW_REQUIRED"]


def geodesic_area_ha(geometry: Geometry) -> float:
    """Area on the WGS84 ellipsoid in hectares (sum over polygon parts)."""
    area, _ = _GEOD.geometry_area_perimeter(geometry)
    return abs(area) / 10_000.0


def geometry_sha256(geometry: Geometry) -> str:
    """Hash of the GeoJSON geometry as served (coordinates unmodified)."""
    payload = json.dumps(mapping(geometry), separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assemble_parts(parts: list[Geometry]) -> MultiPolygon:
    """Collect polygon parts into one MultiPolygon without dissolving them."""
    polygons: list[Polygon] = []
    for part in parts:
        if isinstance(part, Polygon):
            polygons.append(part)
        elif isinstance(part, MultiPolygon):
            polygons.extend(part.geoms)
    return MultiPolygon(polygons)


@dataclass
class GeometryValidation:
    geometry_type: str | None = None
    feature_count: int = 0
    part_count: int = 0
    crs: str | None = None
    crs_ok: bool = False
    lonlat_order_ok: bool = False
    coordinates_possible: bool = False
    empty: bool = True
    valid: bool = False
    invalid_parts: list[str] = field(default_factory=list)
    assembled_valid: bool = False
    assembled_validity_reason: str | None = None
    parts_overlap: bool = False
    make_valid_possible: bool | None = None
    area_ha: float | None = None
    bbox: list[float] | None = None
    centroid: list[float] | None = None
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def validate_parts(parts: list[Geometry], crs_name: str | None) -> GeometryValidation:
    """All checks on a site's polygon parts; nothing is modified."""
    report = GeometryValidation(feature_count=len(parts), crs=crs_name)
    report.crs_ok = crs_name in _EPSG_4326_NAMES
    if not report.crs_ok:
        report.errors.append(f"CRS {crs_name!r} is not EPSG:4326/CRS84.")
    if not parts:
        report.errors.append("No geometry.")
        return report

    types = {p.geom_type for p in parts}
    report.geometry_type = types.pop() if len(types) == 1 else "mixed"
    if any(not isinstance(p, Polygon | MultiPolygon) for p in parts):
        report.errors.append(f"Non-polygonal geometry: {sorted(p.geom_type for p in parts)}.")
        return report

    assembled = assemble_parts(parts)
    report.part_count = len(assembled.geoms)
    report.empty = assembled.is_empty
    if report.empty:
        report.errors.append("Geometry is empty.")
        return report

    minx, miny, maxx, maxy = assembled.bounds
    report.bbox = [minx, miny, maxx, maxy]
    report.coordinates_possible = -180 <= minx <= maxx <= 180 and -90 <= miny <= maxy <= 90
    report.lonlat_order_ok = (
        INDIA_LON[0] <= minx
        and maxx <= INDIA_LON[1]
        and INDIA_LAT[0] <= miny
        and maxy <= INDIA_LAT[1]
    )
    if not report.coordinates_possible:
        report.errors.append("Coordinates outside the valid longitude/latitude range.")
    elif not report.lonlat_order_ok:
        report.errors.append("Bounds outside India; axes may be swapped (expected lon, lat).")

    for index, part in enumerate(parts):
        if not part.is_valid:
            report.invalid_parts.append(f"feature {index}: {explain_validity(part)}")
    report.valid = not report.invalid_parts
    report.assembled_valid = assembled.is_valid
    if not assembled.is_valid:
        report.assembled_validity_reason = explain_validity(assembled)
    if report.valid and len(parts) > 1:
        # Valid parts that nonetheless overlap each other.
        report.parts_overlap = unary_union(parts).area < sum(p.area for p in parts) * (1 - 1e-9)
    if not report.valid:
        try:
            repaired = make_valid(assembled)
            report.make_valid_possible = not repaired.is_empty
        except Exception:  # noqa: BLE001 - only recording whether a repair is possible
            report.make_valid_possible = False
        report.errors.append("Invalid geometry: " + "; ".join(report.invalid_parts))

    report.area_ha = round(geodesic_area_ha(assembled), 4)
    centroid = assembled.centroid
    report.centroid = [centroid.x, centroid.y]
    return report


def point_distance_m(geometry: Geometry, latitude: float, longitude: float) -> float:
    """Distance (metres) from a lon/lat point to the geometry; 0 if inside."""
    utm = utm_epsg_for(geometry)
    target = reproject(geometry, 4326, utm)
    if not target.is_valid:
        target = target.buffer(0)  # distance only; the stored geometry is untouched
    return float(reproject(Point(longitude, latitude), 4326, utm).distance(target))


def compare_geometries(
    gee: Geometry, gee_valid: bool, rsis: Geometry, rsis_valid: bool
) -> dict[str, Any]:
    """GEE ROI vs RSIS boundary. Thresholds are application validation thresholds."""
    result: dict[str, Any] = {
        "thresholds": {
            "type": "application validation thresholds (not an official standard)",
            "MATCH": f"IoU >= {IOU_MATCH} and |area difference| <= {AREA_DIFF_MATCH:.0%}",
            "MINOR_DIFFERENCE": f"IoU >= {IOU_MINOR}",
            "SIGNIFICANT_DIFFERENCE": f"IoU < {IOU_MINOR}",
            "REVIEW_REQUIRED": "either geometry invalid, so overlay results are unreliable",
        }
    }
    gee_area, rsis_area = geodesic_area_ha(gee), geodesic_area_ha(rsis)
    result.update(
        gee_area_ha=round(gee_area, 4),
        rsis_area_ha=round(rsis_area, 4),
        area_ratio_gee_to_rsis=round(gee_area / rsis_area, 4) if rsis_area else None,
        area_difference_percent=round((gee_area - rsis_area) / rsis_area * 100, 2)
        if rsis_area
        else None,
        gee_bbox=list(gee.bounds),
        rsis_bbox=list(rsis.bounds),
        centroid_distance_m=round(
            point_distance_m(rsis.centroid, gee.centroid.y, gee.centroid.x), 1
        ),
    )
    if not (gee_valid and rsis_valid):
        result.update(intersection_ha=None, union_ha=None, iou=None, status="REVIEW_REQUIRED")
        return result
    intersection = geodesic_area_ha(gee.intersection(rsis))
    union = geodesic_area_ha(gee.union(rsis))
    iou = intersection / union if union else 0.0
    area_diff = abs(gee_area - rsis_area) / rsis_area if rsis_area else 1.0
    status: ComparisonStatus
    if iou >= IOU_MATCH and area_diff <= AREA_DIFF_MATCH:
        status = "MATCH"
    elif iou >= IOU_MINOR:
        status = "MINOR_DIFFERENCE"
    else:
        status = "SIGNIFICANT_DIFFERENCE"
    result.update(
        intersection_ha=round(intersection, 4),
        union_ha=round(union, 4),
        iou=round(iou, 4),
        status=status,
    )
    return result


# --- raw RSIS source ------------------------------------------------------


@dataclass(frozen=True)
class RsisSource:
    raw_path: Path
    meta: dict[str, Any]
    crs_name: str | None
    features_by_site: dict[int, list[dict[str, Any]]]


def load_rsis_raw(raw_path: Path) -> RsisSource:
    raw_bytes = raw_path.read_bytes()
    meta_path = raw_path.with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    expected = meta.get("sha256")
    actual = hashlib.sha256(raw_bytes).hexdigest()
    if expected and expected != actual:
        raise ValueError(f"{raw_path.name}: SHA-256 {actual} does not match its metadata.")
    data = json.loads(raw_bytes.decode("utf-8"))
    crs_name = ((data.get("crs") or {}).get("properties") or {}).get("name")
    by_site: dict[int, list[dict[str, Any]]] = {}
    for feature in data.get("features", []):
        site_id = (feature.get("properties") or {}).get("ramsarid")
        if isinstance(site_id, int):
            by_site.setdefault(site_id, []).append(feature)
    return RsisSource(raw_path, {**meta, "sha256": actual}, crs_name, by_site)


# --- runtime lookup (API) -------------------------------------------------


@dataclass(frozen=True)
class OfficialBoundary:
    site_id: int
    status: OfficialStatus
    record: dict[str, Any]
    geometry: MultiPolygon | None


def load_boundary_manifest(path: Path | None = None) -> dict[int, dict[str, Any]]:
    source = Path(path or settings.BOUNDARY_MANIFEST_FILE)
    if not source.is_file():
        return {}
    return _load_boundary_manifest(source, source.stat().st_mtime_ns)


@lru_cache(maxsize=4)
def _load_boundary_manifest(source: Path, _mtime: int) -> dict[int, dict[str, Any]]:
    data = json.loads(source.read_text(encoding="utf-8"))
    return {int(site["ramsar_number"]): site for site in data.get("sites", [])}


@lru_cache(maxsize=4)
def _rsis_source(raw_path: Path, _mtime: int) -> RsisSource:
    return load_rsis_raw(raw_path)


def official_boundary(site_id: int) -> OfficialBoundary:
    site = load_boundary_manifest().get(site_id)
    record = (site or {}).get("official_boundary") or {}
    status: OfficialStatus = record.get("status", "missing_authoritative_boundary")
    if status == "missing_authoritative_boundary" or not record.get("raw_file"):
        return OfficialBoundary(site_id, "missing_authoritative_boundary", record, None)
    raw_path = Path(settings.BOUNDARIES_DIR) / record["raw_file"]
    source = _rsis_source(raw_path, raw_path.stat().st_mtime_ns)
    parts = [shape(f["geometry"]) for f in source.features_by_site.get(site_id, [])]
    geometry = assemble_parts(parts)
    if geometry_sha256(geometry) != record.get("geometry_sha256"):
        raise ValueError(
            f"Official boundary for site {site_id} does not match its manifest hash; "
            "rebuild with `python -m app.tools.build_boundaries`."
        )
    return OfficialBoundary(site_id, status, record, geometry)
