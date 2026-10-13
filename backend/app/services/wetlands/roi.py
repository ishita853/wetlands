"""Analysis geometry: the GEE ROI polygons.

GEE computes every map and chart over a FeatureCollection asset per wetland
(`projects/ee-ramsarwetlands5/assets/<name>`), dissolved with `roi.geometry()`.
Those polygons are required input; a point with an arbitrary buffer is never
substituted. A site's geometry status is one of:

- available  — a valid exported polygon is present;
- missing    — the site has a GEE ROI asset but its polygon hasn't been exported yet;
- invalid    — a file is present but failed validation (reason given);
- no_gee_roi — the GEE application has no ROI for this site;
- mapping_uncertain — (analysis policy) a polygon exists but its Ramsar mapping is
  uncertain, so it is not used for GEE-comparison analysis.
"""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from shapely import Geometry
from shapely.geometry import MultiPolygon, Point, Polygon, shape
from shapely.ops import unary_union
from shapely.validation import explain_validity

from app.core.config import settings
from app.services.copernicus.geometry import area_hectares, reproject, utm_epsg_for

RoiStatus = Literal["available", "missing", "invalid", "no_gee_roi", "mapping_uncertain"]
MappingStatus = Literal["exact", "manual_confirmed", "manual_uncertain"]

_ACCEPTED_CRS = {
    "urn:ogc:def:crs:OGC:1.3:CRS84",
    "urn:ogc:def:crs:OGC::CRS84",
    "http://www.opengis.net/def/crs/OGC/1.3/CRS84",
    "EPSG:4326",
    "urn:ogc:def:crs:EPSG::4326",
    "http://www.opengis.net/def/crs/EPSG/0/4326",
}
# Generous India extent; a polygon outside it almost always means lat/lon swapped.
_INDIA_LON = (66.0, 99.0)
_INDIA_LAT = (5.0, 38.0)
# Distance between the RSIS site point and the polygon above which we warn.
_POINT_DISTANCE_WARNING_M = 5_000.0


class RoiInvalid(Exception):
    pass


@dataclass(frozen=True)
class RoiManifestEntry:
    ramsar_site_id: int
    gee_table_index: int
    gee_asset_name: str
    gee_asset_id: str
    mapping: MappingStatus
    mapping_evidence: str | None = None


@dataclass(frozen=True)
class WetlandRoi:
    entry: RoiManifestEntry
    geometry: Geometry  # WGS84 lon/lat, Polygon or MultiPolygon
    version: str  # sha256 of the source file (first 16 hex chars)
    source_file: str
    area_ha: float
    feature_count: int


@dataclass(frozen=True)
class RoiLookup:
    status: RoiStatus
    entry: RoiManifestEntry | None = None
    roi: WetlandRoi | None = None
    reason: str | None = None


def load_manifest(path: Path | None = None) -> dict[int, RoiManifestEntry]:
    source = Path(path or settings.GEE_ROI_MANIFEST_FILE)
    return _load_manifest(source, source.stat().st_mtime_ns)


@lru_cache(maxsize=4)
def _load_manifest(source: Path, _mtime: int) -> dict[int, RoiManifestEntry]:
    data = json.loads(source.read_text(encoding="utf-8"))
    entries: dict[int, RoiManifestEntry] = {}
    for raw in data.get("rois", []):
        entry = RoiManifestEntry(
            ramsar_site_id=int(raw["ramsarSiteId"]),
            gee_table_index=int(raw["geeTableIndex"]),
            gee_asset_name=str(raw["geeAssetName"]),
            gee_asset_id=str(raw["geeAssetId"]),
            mapping=raw["mapping"],
            mapping_evidence=raw.get("mappingEvidence"),
        )
        entries[entry.ramsar_site_id] = entry
    return entries


def lookup_roi(site_id: int, roi_dir: Path | None = None) -> RoiLookup:
    entry = load_manifest().get(site_id)
    if entry is None:
        return RoiLookup("no_gee_roi", reason="The GEE application has no ROI for this site.")
    path = Path(roi_dir or settings.WETLAND_ROI_DIR) / f"{entry.gee_asset_name}.geojson"
    if not path.is_file():
        return RoiLookup(
            "missing",
            entry,
            reason=f"The polygon for GEE asset {entry.gee_asset_id} has not been exported yet.",
        )
    try:
        roi = _load_roi(path, path.stat().st_mtime_ns, entry)
    except RoiInvalid as exc:
        return RoiLookup("invalid", entry, reason=str(exc))
    return RoiLookup("available", entry, roi)


@lru_cache(maxsize=128)
def _load_roi(path: Path, _mtime: int, entry: RoiManifestEntry) -> WetlandRoi:
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoiInvalid(f"{path.name} is not valid JSON: {exc}") from exc
    geometry, feature_count = parse_roi_geojson(data)
    return WetlandRoi(
        entry=entry,
        geometry=geometry,
        version=hashlib.sha256(raw).hexdigest()[:16],
        source_file=path.name,
        area_ha=round(area_hectares(geometry), 2),
        feature_count=feature_count,
    )


def parse_roi_geojson(data: Any) -> tuple[Geometry, int]:
    """Dissolve all polygons of a GeoJSON object into one WGS84 geometry."""
    if not isinstance(data, dict):
        raise RoiInvalid("GeoJSON must be an object.")
    crs_name = ((data.get("crs") or {}).get("properties") or {}).get("name")
    if crs_name is not None and crs_name not in _ACCEPTED_CRS:
        raise RoiInvalid(f"Unsupported CRS {crs_name!r}; expected WGS84 longitude/latitude.")

    kind = data.get("type")
    if kind == "FeatureCollection":
        raw_geometries = [f.get("geometry") for f in data.get("features") or []]
    elif kind == "Feature":
        raw_geometries = [data.get("geometry")]
    else:
        raw_geometries = [data]

    parts: list[Geometry] = []
    for raw_geometry in raw_geometries:
        if not raw_geometry:
            continue
        try:
            geometry = shape(raw_geometry)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise RoiInvalid(f"Unreadable geometry: {exc}") from exc
        if not isinstance(geometry, Polygon | MultiPolygon):
            raise RoiInvalid(f"ROI geometry must be polygonal, found {geometry.geom_type}.")
        if not geometry.is_valid:
            raise RoiInvalid(f"Invalid polygon: {explain_validity(geometry)}.")
        parts.append(geometry)
    if not parts:
        raise RoiInvalid("No polygon found.")

    dissolved = unary_union(parts)
    minx, miny, maxx, maxy = dissolved.bounds
    if not (
        _INDIA_LON[0] <= minx
        and maxx <= _INDIA_LON[1]
        and _INDIA_LAT[0] <= miny
        and maxy <= _INDIA_LAT[1]
    ):
        raise RoiInvalid(
            f"Polygon bounds {tuple(round(v, 4) for v in dissolved.bounds)} are outside India; "
            "coordinates must be [longitude, latitude] (check for swapped axes)."
        )
    return dissolved, len(parts)


def distance_to_site_point_m(roi: WetlandRoi, latitude: float, longitude: float) -> float:
    """Distance (metres) from the RSIS site point to the ROI polygon, 0 if inside."""
    utm = utm_epsg_for(roi.geometry)
    return reproject(Point(longitude, latitude), 4326, utm).distance(
        reproject(roi.geometry, 4326, utm)
    )


def point_distance_exceeds_warning(distance_m: float) -> bool:
    return distance_m > _POINT_DISTANCE_WARNING_M
