"""Coordinate handling for Sentinel Hub requests.

Wetland geometry is stored and served as WGS84 longitude/latitude (GeoJSON
order). Every Sentinel Hub request states its CRS explicitly:
- CRS84 (lon/lat axis order) for Catalog searches,
- the wetland's UTM zone for 1000 m statistics (resolution in metres),
- Web Mercator for map rasters, so they align with the web map.
All transforms use pyproj with always_xy=True so axis order stays x=lon, y=lat.
"""

import math
from functools import lru_cache

from pyproj import Transformer
from shapely import Geometry
from shapely.ops import transform

CRS84_URI = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
WEB_MERCATOR_EPSG = 3857


def epsg_uri(epsg: int) -> str:
    return f"http://www.opengis.net/def/crs/EPSG/0/{epsg}"


def utm_epsg_for(geometry_lonlat: Geometry) -> int:
    """Northern/southern-hemisphere WGS84 UTM zone of the geometry's centroid."""
    centroid = geometry_lonlat.centroid
    zone = min(int((centroid.x + 180.0) // 6.0) + 1, 60)
    return (32600 if centroid.y >= 0 else 32700) + zone


@lru_cache(maxsize=64)
def _transformer(src_epsg: int, dst_epsg: int) -> Transformer:
    return Transformer.from_crs(src_epsg, dst_epsg, always_xy=True)


def reproject(geometry: Geometry, src_epsg: int, dst_epsg: int) -> Geometry:
    return transform(_transformer(src_epsg, dst_epsg).transform, geometry)


def to_lonlat(x: float, y: float, src_epsg: int) -> tuple[float, float]:
    lon, lat = _transformer(src_epsg, 4326).transform(x, y)
    return lon, lat


def area_hectares(geometry_lonlat: Geometry) -> float:
    return reproject(geometry_lonlat, 4326, utm_epsg_for(geometry_lonlat)).area / 10_000.0


def mercator_scale(latitude: float) -> float:
    """Web Mercator units per ground metre at the given latitude."""
    return 1.0 / math.cos(math.radians(latitude))
