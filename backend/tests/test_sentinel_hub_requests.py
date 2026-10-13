"""Catalog scene selection and the Process / Statistical API request bodies."""

import json
from datetime import UTC, date, datetime

import httpx
import pytest
from shapely.geometry import box, shape

from app.core.config import Settings
from app.processing.water_quality.indices import INDICES, IndexKey
from app.services.copernicus import catalog, process, statistics
from app.services.copernicus.catalog import Scene, select_least_cloudy
from app.services.copernicus.client import CopernicusClient

ROI = box(85.30, 19.60, 85.40, 19.80)  # lon/lat test polygon
CATALOG_URL = "https://sh.example/catalog"


def _client(handler) -> CopernicusClient:
    config = Settings(
        COPERNICUS_CLIENT_ID="id",
        COPERNICUS_CLIENT_SECRET="secret",
        COPERNICUS_TOKEN_URL="https://identity.example/token",
        COPERNICUS_CATALOG_URL=CATALOG_URL,
    )

    def route(request: httpx.Request) -> httpx.Response:
        if request.url.host == "identity.example":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        return handler(request)

    return CopernicusClient(config, transport=httpx.MockTransport(route))


def _item(item_id, when, cloud, footprint=None):
    return {
        "id": item_id,
        "geometry": json.loads(json.dumps((footprint or box(85, 19, 86, 20)).__geo_interface__)),
        "properties": {"datetime": when, "eo:cloud_cover": cloud, "platform": "sentinel-2b"},
    }


def _scene(item_id, day, cloud):
    return Scene(item_id, datetime(2023, 1, day, 5, tzinfo=UTC), cloud, None, None, None, 1.0)


# --- scene selection (GEE .filter(lt(CLOUDY, 100)).sort(CLOUDY).first()) ---


def test_least_cloudy_is_selected():
    scenes = [_scene("a", 1, 12.0), _scene("b", 2, 0.5), _scene("c", 3, 40.0)]
    assert select_least_cloudy(scenes, 100).id == "b"


def test_threshold_is_strict_and_missing_cloud_excluded():
    scenes = [_scene("full", 1, 100.0), _scene("none", 2, None)]
    assert select_least_cloudy(scenes, 100) is None
    assert select_least_cloudy([_scene("x", 1, 30.0)], 30) is None


def test_ties_resolved_by_earliest_acquisition():
    scenes = [_scene("later", 9, 0.0), _scene("earlier", 2, 0.0)]
    assert select_least_cloudy(scenes, 100).id == "earlier"


def test_catalog_search_paginates_filters_dates_and_footprints():
    tile = "S2B_MSIL2A_20231105T045939_N0509_R119_T45QUD_20231105T074020.SAFE"
    pages = [
        {
            "features": [
                _item(tile, "2023-11-05T05:05:00Z", 3.2),
                # footprint in the bbox query but not touching the ROI
                _item("far", "2023-11-06T05:05:00Z", 0.0, box(86.0, 21.0, 87.0, 22.0)),
            ],
            "context": {"next": 100},
        },
        # acquired on the (exclusive) end date -> dropped, like GEE filterDate
        {"features": [_item("end-day", "2026-05-30T05:05:00Z", 0.0)], "context": {}},
    ]
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=pages[len(requests) - 1])

    scenes = catalog.search_scenes(_client(handler), ROI, date(2022, 11, 1), date(2026, 5, 30))
    assert [s.id for s in scenes] == [tile]
    assert scenes[0].tile_id == "45QUD"
    assert scenes[0].roi_coverage == 1.0
    assert requests[0]["collections"] == ["sentinel-2-l2a"]
    assert requests[0]["datetime"] == "2022-11-01T00:00:00Z/2026-05-30T00:00:00Z"
    assert requests[0]["bbox"] == list(ROI.bounds)
    assert "next" not in requests[0] and requests[1]["next"] == 100


# --- Statistical API (GEE ui.Chart.image.series, mean, scale 1000) ---


def test_statistics_request_reproduces_gee_chart_settings():
    body = statistics.build_statistics_request(
        INDICES[IndexKey.NDWI], ROI, date(2022, 11, 1), date(2023, 1, 1), 100.0
    )
    bounds = body["input"]["bounds"]
    assert bounds["properties"]["crs"] == "http://www.opengis.net/def/crs/EPSG/0/32645"
    # Geometry is sent in UTM metres (so resx=1000 means 1000 m), not degrees.
    assert shape(bounds["geometry"]).bounds[0] > 100_000
    data = body["input"]["data"][0]
    assert data["type"] == "sentinel-2-l2a"
    assert data["processing"] == {"harmonizeValues": True, "downsampling": "BILINEAR"}
    assert data["dataFilter"] == {"maxCloudCoverage": 100.0}
    aggregation = body["aggregation"]
    assert aggregation["timeRange"] == {
        "from": "2022-11-01T00:00:00Z",
        "to": "2023-01-01T00:00:00Z",
    }
    assert aggregation["aggregationInterval"] == {"of": "P1D"}
    assert (aggregation["resx"], aggregation["resy"]) == (1000.0, 1000.0)
    assert "SCL" not in aggregation["evalscript"]  # charts are unmasked, as in GEE


def test_year_chunks_cover_range_without_overlap():
    chunks = statistics.year_chunks(date(2022, 11, 1), date(2026, 5, 30))
    assert chunks[0] == (date(2022, 11, 1), date(2023, 1, 1))
    assert chunks[-1] == (date(2026, 1, 1), date(2026, 5, 30))
    assert all(a[1] == b[0] for a, b in zip(chunks, chunks[1:], strict=False))


def _interval(day, stats=None, error=None):
    entry = {"interval": {"from": f"{day}T00:00:00Z", "to": f"{day}T23:59:59Z"}}
    if error:
        entry["error"] = {"type": "EXECUTION_ERROR", "message": error}
    else:
        entry["outputs"] = {"index": {"bands": {"B0": {"stats": stats}}}}
    return entry


def test_parse_interval_valid_empty_and_error():
    valid = statistics.parse_interval(
        _interval(
            "2023-02-03",
            {
                "min": -0.2,
                "max": 0.4,
                "mean": 0.1,
                "stDev": 0.05,
                "sampleCount": 20,
                "noDataCount": 5,
            },
        )
    )
    assert valid.date == date(2023, 2, 3) and valid.mean == 0.1 and valid.valid_pixels == 15
    empty = _interval("2023-02-08", {"mean": "NaN", "sampleCount": 20, "noDataCount": 20})
    assert statistics.parse_interval(empty) is None
    assert statistics.parse_interval(_interval("2023-02-13", error="boom")) == "2023-02-13: boom"


def test_fetch_time_series_merges_chunks():
    bodies = [
        {
            "data": [
                _interval("2022-12-01", {"mean": 0.2, "sampleCount": 4, "noDataCount": 0}),
                _interval("2022-12-06", {"mean": "NaN", "sampleCount": 4, "noDataCount": 4}),
            ]
        },
        {"data": [_interval("2023-01-05", {"mean": -0.1, "sampleCount": 4, "noDataCount": 1})]},
    ]
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=bodies[len(calls) - 1])

    series = statistics.fetch_time_series(
        _client(handler), INDICES[IndexKey.NDCI], ROI, date(2022, 11, 1), date(2023, 2, 1), 100
    )
    assert len(calls) == 2
    assert [(o.date, o.mean) for o in series.observations] == [
        (date(2022, 12, 1), 0.2),
        (date(2023, 1, 5), -0.1),
    ]
    assert series.days_without_valid_pixels == 1


# --- Process API (GEE makemap*: selected image, clipped to ROI) ---


def test_map_request_targets_selected_acquisition_and_masks_clouds():
    grid = process.raster_grid(ROI)
    acquired = datetime(2024, 3, 10, 4, 55, 21, tzinfo=UTC)
    body = process.build_map_request(INDICES[IndexKey.NDMI], ROI, acquired, grid)
    bounds = body["input"]["bounds"]
    assert bounds["properties"]["crs"] == "http://www.opengis.net/def/crs/EPSG/0/3857"
    data = body["input"]["data"][0]
    assert data["dataFilter"]["timeRange"] == {
        "from": "2024-03-10T04:25:21Z",
        "to": "2024-03-10T05:25:21Z",
    }
    assert data["processing"] == {"harmonizeValues": True}
    assert body["output"]["responses"][0]["format"]["type"] == "image/tiff"
    script = body["evalscript"]
    assert '"B08", "B11", "SCL", "dataMask"' in script
    assert "[8, 9, 10]" in script


def test_raster_grid_native_resolution_and_size_cap():
    small = process.raster_grid(ROI)  # ~10.5 km x 22 km
    assert small.ground_resolution_m == pytest.approx(10.0)
    assert max(small.width, small.height) <= 2500
    large = process.raster_grid(box(88.0, 21.5, 89.2, 22.6))  # Sundarbans-sized
    assert max(large.width, large.height) == 2500
    assert large.ground_resolution_m > 10.0


def test_catalog_requests_geojson_media_type():
    # Live CDSE Catalog answers HTTP 406 to Accept: application/json (found 2026-09-25).
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["Accept"])
        return httpx.Response(200, json={"features": [], "context": {}})

    catalog.search_scenes(_client(handler), ROI, date(2024, 1, 1), date(2024, 2, 1))
    assert seen == ["application/geo+json"]
