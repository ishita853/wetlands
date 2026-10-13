"""Process API: index raster for one selected acquisition, clipped to the ROI.

The request covers only a short window around the selected scene, so every
pixel comes from that acquisition pass. Sentinel Hub mosaics the pass's tiles
inside the ROI (difference X2); there is no documented way to restrict a
request to one MGRS tile, so none is attempted.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from shapely import Geometry
from shapely.geometry import mapping

from app.processing.water_quality.indices import IndexDefinition
from app.processing.water_quality.methodology import (
    HARMONIZE_VALUES,
    MAP_MAX_SIDE_PX,
    MAP_SCENE_WINDOW_MINUTES,
    MAP_TARGET_RESOLUTION_M,
    SENTINEL_HUB_DATA_TYPE,
)
from app.services.copernicus.catalog import iso_z
from app.services.copernicus.client import CopernicusClient
from app.services.copernicus.errors import CopernicusInvalidResponse
from app.services.copernicus.evalscripts import map_evalscript
from app.services.copernicus.geometry import (
    WEB_MERCATOR_EPSG,
    epsg_uri,
    mercator_scale,
    reproject,
)


@dataclass(frozen=True)
class RasterGrid:
    width: int
    height: int
    # Ground resolution actually delivered (metres); coarser than the target
    # only when the ROI would exceed MAP_MAX_SIDE_PX.
    ground_resolution_m: float


def raster_grid(roi_lonlat: Geometry) -> RasterGrid:
    roi_3857 = reproject(roi_lonlat, 4326, WEB_MERCATOR_EPSG)
    minx, miny, maxx, maxy = roi_3857.bounds
    scale = mercator_scale(roi_lonlat.centroid.y)
    resolution = MAP_TARGET_RESOLUTION_M * scale  # Web Mercator units per pixel
    longest = max(maxx - minx, maxy - miny)
    if longest / resolution > MAP_MAX_SIDE_PX:
        resolution = longest / MAP_MAX_SIDE_PX
    width = max(1, math.ceil((maxx - minx) / resolution))
    height = max(1, math.ceil((maxy - miny) / resolution))
    return RasterGrid(width, height, round(resolution / scale, 2))


def build_map_request(
    index: IndexDefinition, roi_lonlat: Geometry, acquired_at: datetime, grid: RasterGrid
) -> dict[str, Any]:
    window = timedelta(minutes=MAP_SCENE_WINDOW_MINUTES)
    return {
        "input": {
            "bounds": {
                "geometry": mapping(reproject(roi_lonlat, 4326, WEB_MERCATOR_EPSG)),
                "properties": {"crs": epsg_uri(WEB_MERCATOR_EPSG)},
            },
            "data": [
                {
                    "type": SENTINEL_HUB_DATA_TYPE,
                    "dataFilter": {
                        "timeRange": {
                            "from": iso_z(acquired_at - window),
                            "to": iso_z(acquired_at + window),
                        },
                        "mosaickingOrder": "leastCC",
                    },
                    "processing": {"harmonizeValues": HARMONIZE_VALUES},
                }
            ],
        },
        "output": {
            "width": grid.width,
            "height": grid.height,
            "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}],
        },
        "evalscript": map_evalscript(index),
    }


def fetch_index_geotiff(client: CopernicusClient, request: dict[str, Any]) -> bytes:
    response = client.post(client.config.COPERNICUS_PROCESS_URL, request, accept="image/tiff")
    if not response.content:
        raise CopernicusInvalidResponse("Sentinel Hub returned an empty Process API response.")
    return response.content
