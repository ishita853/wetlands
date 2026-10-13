"""Catalog API: Sentinel-2 L2A scene search and GEE-style scene selection.

Reproduces the GEE map's image choice:
    collection.filterBounds(ROI).filterDate(start, end)
              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max))
              .sort('CLOUDY_PIXEL_PERCENTAGE', true).first()
Each Catalog item is one Sentinel-2 L2A tile, like a GEE granule. Cloud cover
is the item's tile-level `eo:cloud_cover` (whether it equals GEE's
CLOUDY_PIXEL_PERCENTAGE is a validation item).
"""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any

from shapely import Geometry
from shapely.geometry import shape

from app.processing.water_quality.methodology import SENTINEL_HUB_DATA_TYPE
from app.services.copernicus.client import CopernicusClient

_PAGE_LIMIT = 100
CATALOG_MEDIA_TYPE = "application/geo+json"
_MAX_PAGES = 100
_TILE_ID = re.compile(r"_T(\d{2}[A-Z]{3})_")


@dataclass(frozen=True)
class Scene:
    id: str
    acquired_at: datetime
    cloud_cover: float | None
    tile_id: str | None
    platform: str | None
    processing_baseline: str | None
    # Fraction (0-1) of the ROI area inside this tile's footprint.
    roi_coverage: float


def day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def iso_z(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def search_scenes(
    client: CopernicusClient, roi_lonlat: Geometry, start: date, end_exclusive: date
) -> list[Scene]:
    """All L2A tiles intersecting the ROI with start <= acquisition < end_exclusive."""
    start_dt, end_dt = day_start(start), day_start(end_exclusive)
    body: dict[str, Any] = {
        "collections": [SENTINEL_HUB_DATA_TYPE],
        "datetime": f"{iso_z(start_dt)}/{iso_z(end_dt)}",
        "bbox": list(roi_lonlat.bounds),
        "limit": _PAGE_LIMIT,
    }
    scenes: list[Scene] = []
    for _ in range(_MAX_PAGES):
        # STAC search responds with GeoJSON; Accept: application/json gets HTTP 406.
        page = client.post_json(
            client.config.COPERNICUS_CATALOG_URL, body, accept=CATALOG_MEDIA_TYPE
        )
        for feature in page.get("features", []):
            scene = _to_scene(feature, roi_lonlat)
            # GEE filterDate end is exclusive; STAC datetime intervals are inclusive.
            if scene is not None and start_dt <= scene.acquired_at < end_dt:
                scenes.append(scene)
        next_token = (page.get("context") or {}).get("next")
        if next_token is None:
            break
        body["next"] = next_token
    return sorted(scenes, key=lambda s: (s.acquired_at, s.id))


def select_least_cloudy(scenes: list[Scene], max_cloud_percent: float) -> Scene | None:
    """GEE `.filter(lt(CLOUDY_PIXEL_PERCENTAGE, max)).sort(..., true).first()`.

    Tiles without cloud metadata are excluded, as GEE metadata filters exclude
    images missing the property. GEE breaks ties arbitrarily; here ties go to
    the earliest acquisition, then the item id, so the choice is reproducible.
    """
    eligible = [
        s for s in scenes if s.cloud_cover is not None and s.cloud_cover < max_cloud_percent
    ]
    if not eligible:
        return None
    return min(eligible, key=lambda s: (s.cloud_cover, s.acquired_at, s.id))


def _to_scene(feature: dict[str, Any], roi_lonlat: Geometry) -> Scene | None:
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry")
    raw_datetime = properties.get("datetime")
    if not geometry or not raw_datetime:
        return None
    footprint = shape(geometry)
    if not footprint.intersects(roi_lonlat):
        return None  # bbox match only; GEE filterBounds uses the ROI geometry
    cloud = properties.get("eo:cloud_cover")
    item_id = str(feature.get("id", ""))
    tile = _TILE_ID.search(item_id)
    return Scene(
        id=item_id,
        acquired_at=datetime.fromisoformat(raw_datetime.replace("Z", "+00:00")),
        cloud_cover=float(cloud) if cloud is not None else None,
        tile_id=tile.group(1) if tile else None,
        platform=properties.get("platform"),
        processing_baseline=_processing_baseline(properties),
        roi_coverage=round(footprint.intersection(roi_lonlat).area / roi_lonlat.area, 4)
        if roi_lonlat.area > 0
        else 0.0,
    )


def _processing_baseline(properties: dict[str, Any]) -> str | None:
    for key, value in properties.items():
        if "processing_baseline" in key.lower() and value is not None:
            return str(value)
    return None
