"""Wetland and water-quality endpoints with Copernicus Data Space mocked at the HTTP layer.

The mocked Sentinel Hub responses exist only to exercise request/response
handling; they are never served outside the tests.
"""

import base64
import json

import httpx
import numpy as np
import pytest
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from shapely.geometry import shape

from app.core.config import Settings
from app.main import app
from app.services.copernicus.client import CopernicusClient, get_copernicus_client
from tests.conftest import ROI_DIR

# A small test polygon at Chilika's RSIS point (lon/lat).
ROI_RING = [
    [85.345, 19.695],
    [85.355, 19.695],
    [85.355, 19.705],
    [85.345, 19.705],
    [85.345, 19.695],
]
TILE = "S2A_MSIL2A_20240310T044701_N0510_R076_T45QTE_20240310T082513.SAFE"


@pytest.fixture
def chilika_roi():
    path = ROI_DIR / "chilka.geojson"
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {"type": "Polygon", "coordinates": [ROI_RING]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    yield path
    path.unlink()


def _geotiff(request_body: dict) -> bytes:
    width = request_body["output"]["width"]
    height = request_body["output"]["height"]
    minx, miny, maxx, maxy = shape(request_body["input"]["bounds"]["geometry"]).bounds
    values = np.full((height, width), 0.3, dtype=np.float32)
    status = np.ones((height, width), dtype=np.float32)
    values[:, width // 2 :] = np.nan
    status[:, width // 2 :] = 2  # cloud-masked half
    with MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff",
            width=width,
            height=height,
            count=2,
            dtype="float32",
            crs="EPSG:3857",
            transform=from_bounds(minx, miny, maxx, maxy, width, height),
        ) as ds:
            ds.write(values, 1)
            ds.write(status, 2)
        return memfile.read()


class FakeSentinelHub:
    def __init__(self):
        self.requests: dict[str, list[dict]] = {"catalog": [], "process": [], "statistics": []}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "identity.example":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        body = json.loads(request.content)
        kind = request.url.path.strip("/").split("/")[0]
        self.requests[kind].append(body)
        if kind == "catalog":
            footprint = {
                "type": "Polygon",
                "coordinates": [[[85, 19], [86, 19], [86, 20], [85, 20], [85, 19]]],
            }
            return httpx.Response(
                200,
                json={
                    "features": [
                        {
                            "id": TILE,
                            "geometry": footprint,
                            "properties": {
                                "datetime": "2024-03-10T04:55:21Z",
                                "eo:cloud_cover": 0.4,
                            },
                        },
                        {
                            "id": "cloudier",
                            "geometry": footprint,
                            "properties": {
                                "datetime": "2023-01-02T04:55:21Z",
                                "eo:cloud_cover": 7.0,
                            },
                        },
                    ],
                    "context": {},
                },
            )
        if kind == "process":
            return httpx.Response(
                200, content=_geotiff(body), headers={"Content-Type": "image/tiff"}
            )
        year = body["aggregation"]["timeRange"]["from"][:4]
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "interval": {
                            "from": f"{year}-03-10T00:00:00Z",
                            "to": f"{year}-03-11T00:00:00Z",
                        },
                        "outputs": {
                            "index": {
                                "bands": {
                                    "B0": {
                                        "stats": {
                                            "min": 0.1,
                                            "max": 0.5,
                                            "mean": 0.25,
                                            "stDev": 0.1,
                                            "sampleCount": 4,
                                            "noDataCount": 1,
                                        }
                                    }
                                }
                            }
                        },
                    }
                ],
                "status": "OK",
            },
        )


@pytest.fixture
def sentinel_hub():
    fake = FakeSentinelHub()
    config = Settings(
        COPERNICUS_CLIENT_ID="id",
        COPERNICUS_CLIENT_SECRET="secret",
        COPERNICUS_TOKEN_URL="https://identity.example/token",
        COPERNICUS_CATALOG_URL="https://sh.example/catalog/v1/search",
        COPERNICUS_PROCESS_URL="https://sh.example/process/v1",
        COPERNICUS_STATISTICS_URL="https://sh.example/statistics/v1",
    )
    app.dependency_overrides[get_copernicus_client] = lambda: CopernicusClient(
        config, transport=httpx.MockTransport(fake), sleep=lambda s: None
    )
    yield fake
    app.dependency_overrides.pop(get_copernicus_client, None)


def trace_cache(body):
    return body["traceability"]["result_cache"]["status"]


def test_wetland_list_reports_analysis_geometry_status(client):
    body = client.get("/api/v1/wetlands").json()
    by_id = {w["ramsar_site_id"]: w for w in body}
    assert by_id[229]["analysis_geometry"]["status"] == "missing"
    assert by_id[229]["analysis_geometry"]["gee_asset_id"].endswith("/chilka")
    assert by_id[2534]["analysis_geometry"]["status"] == "no_gee_roi"
    assert by_id[229]["latitude"] == 19.7 and by_id[229]["longitude"] == 85.35


def test_wetland_detail_and_unknown_site(client):
    assert client.get("/api/v1/wetlands/229").json()["name"] == "Chilika Lake"
    assert client.get("/api/v1/wetlands/1").status_code == 404


def test_roi_endpoint(client, chilika_roi):
    missing = client.get("/api/v1/wetlands/2441/roi?source=gee")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "roi_missing"
    feature = client.get("/api/v1/wetlands/229/roi?source=gee").json()
    assert feature["type"] == "Feature"
    assert feature["geometry"]["coordinates"][0][0][:2] in (
        [85.345, 19.695],
        [85.355, 19.695],
        [85.355, 19.705],
        [85.345, 19.705],
    )
    assert feature["properties"]["gee_asset_id"] == "projects/ee-ramsarwetlands5/assets/chilka"


def test_no_analysis_without_roi_polygon(client, sentinel_hub):
    response = client.get("/api/v1/water-quality/229/NDWI/timeseries")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "roi_missing"
    assert sentinel_hub.requests == {"catalog": [], "process": [], "statistics": []}
    # Aghanashini has a provided ROI but no GEE ROI: forcing roi=gee must not fall back.
    assert (
        client.get("/api/v1/water-quality/2534/NDWI/map?roi=gee").json()["detail"]["code"]
        == "roi_no_gee_roi"
    )
    assert sentinel_hub.requests == {"catalog": [], "process": [], "statistics": []}


def test_not_configured_is_explicit(client, chilika_roi):
    response = client.get("/api/v1/water-quality/229/NDCI/map")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "copernicus_not_configured"


def test_indices_endpoint(client):
    indices = client.get("/api/v1/water-quality/indices").json()
    assert [i["key"] for i in indices] == ["NDCI", "NDTI", "NDWI", "NDMI"]
    assert indices[2]["formula"] == "(B03 - B08) / (B03 + B08)"


def test_parameter_validation(client, chilika_roi):
    assert client.get("/api/v1/water-quality/229/NDVI/map").status_code == 422
    bad_range = client.get("/api/v1/water-quality/229/NDWI/map?start=2024-01-01&end=2024-01-01")
    assert bad_range.status_code == 422


def test_map_end_to_end(client, chilika_roi, sentinel_hub):
    response = client.get("/api/v1/water-quality/229/NDMI/map")
    assert response.status_code == 200, response.text
    body = response.json()

    catalog_request = sentinel_hub.requests["catalog"][0]
    assert catalog_request["datetime"] == "2022-11-01T00:00:00Z/2026-05-30T00:00:00Z"
    process_request = sentinel_hub.requests["process"][0]
    assert process_request["input"]["data"][0]["dataFilter"]["timeRange"]["from"] == (
        "2024-03-10T04:25:21Z"
    )

    image = body["image"]
    assert base64.b64decode(image["data_uri"].split(",", 1)[1])[:8] == b"\x89PNG\r\n\x1a\n"
    top_left, _, bottom_right, _ = image["coordinates"]
    assert top_left[0] == pytest.approx(85.345, abs=1e-4)
    assert top_left[1] == pytest.approx(19.705, abs=1e-4)
    assert bottom_right[0] == pytest.approx(85.355, abs=2e-4)
    counts = body["pixel_counts"]
    assert counts["valid"] > 0 and counts["cloud_masked"] > 0
    assert body["value_summary"]["mean"] == pytest.approx(0.3)

    trace = body["traceability"]
    assert trace["reference_collection"] == "COPERNICUS/S2_SR_HARMONIZED"
    assert trace["sentinel_hub_data_type"] == "sentinel-2-l2a"
    assert trace["selected_scene"]["id"] == TILE
    assert trace["selected_scene"]["tile_id"] == "45QTE"
    assert trace["index"]["formula"] == "(B08 - B11) / (B08 + B11)"
    assert trace["roi"]["gee_table_index"] == 9
    assert trace["roi"]["mapping_status"] == "manual_confirmed"
    assert "not identical to QA60" in trace["cloud_handling"]
    assert {d["code"] for d in trace["processing_differences"]} >= {"X1", "X2", "X4", "X5"}
    assert trace["spatial"]["resolution_m"] == pytest.approx(10.0)
    assert any("QA60" in w for w in trace["warnings"])


def test_geotiff_download(client, chilika_roi, sentinel_hub):
    response = client.get("/api/v1/water-quality/229/NDTI/map.tif")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/tiff"
    assert "ramsar229_NDTI_20240310.tif" in response.headers["content-disposition"]


def test_time_series_end_to_end(client, chilika_roi, sentinel_hub):
    response = client.get(
        "/api/v1/water-quality/229/NDCI/timeseries?start=2023-01-01&end=2025-01-01"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [p["date"] for p in body["points"]] == ["2023-03-10", "2024-03-10"]
    assert body["points"][0]["mean"] == 0.25 and body["points"][0]["valid_pixels"] == 3
    assert len(sentinel_hub.requests["statistics"]) == 2  # one per calendar year
    # One Catalog search supplies scene metadata; it does not select a scene.
    assert len(sentinel_hub.requests["catalog"]) == 1
    assert body["points"][0]["scenes"] == []  # no Catalog tile acquired on 2023-03-10
    assert [s["id"] for s in body["points"][1]["scenes"]] == [TILE]  # 2024-03-10
    assert body["points"][1]["scenes"][0]["cloud_cover"] == 0.4
    assert trace_cache(body) == "miss"

    trace = body["traceability"]
    assert trace["cloud_handling"] == "No cloud mask, as in the GEE charts."
    assert trace["spatial"]["resolution_m"] == 1000.0
    assert trace["spatial"]["request_crs"].endswith("/32645")
    assert trace["date_range"] == {"start": "2023-01-01", "end_exclusive": "2025-01-01"}
    assert {d["code"] for d in trace["processing_differences"]} >= {"X2", "X3", "X6"}
    assert "X1" not in {d["code"] for d in trace["processing_differences"]}
