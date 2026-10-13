"""Phase J §18: API error handling with Copernicus mocked at the HTTP layer."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.services.copernicus.client import CopernicusClient, get_copernicus_client
from tests.conftest import ROI_DIR

SECRET = "super-secret-value-123"
RING = [[85.345, 19.695], [85.355, 19.695], [85.355, 19.705], [85.345, 19.705], [85.345, 19.695]]
FOOTPRINT = {"type": "Polygon", "coordinates": [[[85, 19], [86, 19], [86, 20], [85, 20], [85, 19]]]}
ONE_SCENE = {
    "features": [
        {
            "id": "S2A_MSIL2A_20240310T044701_N0510_R076_T45QTE_20240310T082513.SAFE",
            "geometry": FOOTPRINT,
            "properties": {"datetime": "2024-03-10T04:55:21Z", "eo:cloud_cover": 1.0},
        }
    ],
    "context": {},
}


@pytest.fixture
def roi_file():
    path = ROI_DIR / "chilka.geojson"
    path.write_text(json.dumps({"type": "Polygon", "coordinates": [RING]}), encoding="utf-8")
    yield path
    path.unlink(missing_ok=True)


def _use(handler, sleeps: list[float] | None = None) -> None:
    config = Settings(
        COPERNICUS_CLIENT_ID="client-id",
        COPERNICUS_CLIENT_SECRET=SECRET,
        COPERNICUS_TOKEN_URL="https://identity.example/token",
        COPERNICUS_CATALOG_URL="https://sh.example/catalog/v1/search",
        COPERNICUS_PROCESS_URL="https://sh.example/process/v1",
        COPERNICUS_STATISTICS_URL="https://sh.example/statistics/v1",
    )

    def route(request: httpx.Request) -> httpx.Response:
        if request.url.host == "identity.example":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        return handler(request)

    app.dependency_overrides[get_copernicus_client] = lambda: CopernicusClient(
        config,
        transport=httpx.MockTransport(route),
        sleep=(sleeps.append if sleeps is not None else lambda s: None),
    )


@pytest.fixture
def api():
    # Unhandled server errors must come back as a response, not a raised exception,
    # so the test can check that nothing internal leaks.
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(get_copernicus_client, None)


def _assert_clean(response: httpx.Response) -> None:
    text = response.text
    assert SECRET not in text
    assert "Traceback" not in text and 'File "' not in text


def test_invalid_credentials(api, roi_file):
    def handler(request):  # never reached
        raise AssertionError

    config = Settings(
        COPERNICUS_CLIENT_ID="client-id",
        COPERNICUS_CLIENT_SECRET=SECRET,
        COPERNICUS_TOKEN_URL="https://identity.example/token",
    )
    app.dependency_overrides[get_copernicus_client] = lambda: CopernicusClient(
        config,
        transport=httpx.MockTransport(
            lambda r: httpx.Response(401, json={"error": "unauthorized_client"})
        ),
    )
    response = api.get("/api/v1/water-quality/229/NDWI/timeseries")
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "copernicus_auth_failed"
    _assert_clean(response)


def test_invalid_roi_rejected_with_reason(api):
    path = ROI_DIR / "chilka.geojson"
    swapped = [[lat, lon] for lon, lat in RING]
    path.write_text(json.dumps({"type": "Polygon", "coordinates": [swapped]}), encoding="utf-8")
    try:
        _use(lambda r: httpx.Response(500))
        response = api.get("/api/v1/water-quality/229/NDWI/map")
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["code"] == "roi_invalid"
        assert "swapped" in detail["message"]
    finally:
        path.unlink()


def test_unknown_wetland(api):
    _use(lambda r: httpx.Response(500))
    response = api.get("/api/v1/water-quality/999999/NDWI/map")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "wetland_not_found"


def test_empty_catalog_response(api, roi_file):
    _use(lambda r: httpx.Response(200, json={"features": [], "context": {}}))
    response = api.get("/api/v1/water-quality/229/NDCI/map")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "no_scenes"


def _catalog_then(process_response: httpx.Response):
    def handler(request: httpx.Request) -> httpx.Response:
        if "catalog" in request.url.path:
            return httpx.Response(200, json=ONE_SCENE)
        return process_response

    return handler


@pytest.mark.parametrize(
    "process_response",
    [
        httpx.Response(200, content=b"", headers={"Content-Type": "image/tiff"}),
        httpx.Response(200, content=b"<html>not a tiff</html>"),
    ],
    ids=["empty-body", "not-a-geotiff"],
)
def test_empty_or_garbled_process_response(api, roi_file, process_response):
    _use(_catalog_then(process_response))
    response = api.get("/api/v1/water-quality/229/NDTI/map")
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "sentinel_hub_invalid_response"
    _assert_clean(response)


def test_empty_statistical_response(api, roi_file):
    _use(lambda r: httpx.Response(200, json={"data": [], "status": "OK"}))
    response = api.get("/api/v1/water-quality/229/NDMI/timeseries?start=2024-01-01&end=2024-02-01")
    assert response.status_code == 200
    body = response.json()
    assert body["points"] == []
    assert any("no valid observations" in w for w in body["traceability"]["warnings"])


def test_non_json_statistical_response(api, roi_file):
    _use(lambda r: httpx.Response(200, content=b"<html>gateway</html>"))
    response = api.get("/api/v1/water-quality/229/NDMI/timeseries?start=2024-01-01&end=2024-02-01")
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "sentinel_hub_invalid_response"
    _assert_clean(response)


def test_copernicus_4xx(api, roi_file):
    _use(lambda r: httpx.Response(400, json={"error": {"message": "Invalid geometry"}}))
    response = api.get("/api/v1/water-quality/229/NDWI/timeseries")
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail == {
        "code": "sentinel_hub_error",
        "message": "Invalid geometry",
        "upstream_status": 400,
    }


def test_copernicus_500(api, roi_file):
    _use(lambda r: httpx.Response(500, text="internal"))
    response = api.get("/api/v1/water-quality/229/NDWI/timeseries")
    assert response.status_code == 502
    assert response.json()["detail"]["upstream_status"] == 500
    _assert_clean(response)


def test_copernicus_503_is_unavailable_not_rate_limit_and_bounded(api, roi_file):
    calls: list[httpx.Request] = []
    sleeps: list[float] = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503, text="maintenance")

    _use(handler, sleeps)
    response = api.get("/api/v1/water-quality/229/NDWI/timeseries?start=2024-01-01&end=2024-02-01")
    assert response.status_code == 504
    assert response.json()["detail"]["code"] == "copernicus_unavailable"
    # Statistical and Catalog (scene metadata) requests run together; each retries
    # at most twice (3 calls, 2 waits), so retries stay bounded per request.
    stats_calls = [c for c in calls if "statistics" in c.url.path]
    catalog_calls = [c for c in calls if "catalog" in c.url.path]
    assert len(stats_calls) == 3 and len(catalog_calls) == 3 and len(sleeps) == 4


def test_rate_limited_bounded_with_retry_after(api, roi_file):
    calls: list[httpx.Request] = []
    sleeps: list[float] = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "7"})

    _use(handler, sleeps)
    response = api.get("/api/v1/water-quality/229/NDWI/timeseries?start=2024-01-01&end=2024-02-01")
    assert response.status_code == 503
    assert response.headers["retry-after"] == "7"
    assert response.json()["detail"]["code"] == "copernicus_rate_limited"
    stats_calls = [c for c in calls if "statistics" in c.url.path]
    assert len(stats_calls) == 3 and len(calls) == 6 and sleeps == [7.0] * 4


def test_network_failure(api, roi_file):
    def handler(request):
        raise httpx.ConnectTimeout("timed out", request=request)

    _use(handler)
    response = api.get("/api/v1/water-quality/229/NDWI/timeseries")
    assert response.status_code == 504
    assert response.json()["detail"]["code"] == "copernicus_unavailable"
