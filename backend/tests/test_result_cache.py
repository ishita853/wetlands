"""Result cache: keys, expiry/size bounds, time-series reuse and GeoTIFF reuse."""

import json
from datetime import date

import httpx
import pytest

from app.core.config import Settings, settings
from app.main import app
from app.processing.water_quality.indices import IndexKey, get_index
from app.services import result_cache as rc
from app.services.copernicus.client import CopernicusClient, get_copernicus_client
from app.services.water_quality import analysis
from app.services.wetlands.resolver import resolve_analysis_roi
from tests.conftest import ROI_DIR
from tests.test_water_quality_api import FakeSentinelHub

RING = [[85.345, 19.695], [85.355, 19.695], [85.355, 19.705], [85.345, 19.705], [85.345, 19.695]]


# --- cache primitives -------------------------------------------------------------


def test_memory_cache_expires_entries():
    now = [0.0]
    cache = rc.MemoryCache(max_bytes=1000, clock=lambda: now[0])
    cache.set("k", b"value", ttl_seconds=10)
    assert cache.get("k") == b"value"
    now[0] = 10.0
    assert cache.get("k") is None


def test_memory_cache_is_bounded_lru():
    cache = rc.MemoryCache(max_bytes=10)
    cache.set("a", b"12345", 60)
    cache.set("b", b"12345", 60)
    assert cache.get("a") == b"12345"  # a is now most recently used
    cache.set("c", b"12345", 60)  # evicts b (least recently used)
    assert cache.get("b") is None and cache.get("a") and cache.get("c")
    cache.set("huge", b"x" * 11, 60)  # larger than the whole cache: not stored
    assert cache.get("huge") is None and cache.get("a")


def test_unreachable_redis_falls_back_to_memory(monkeypatch):
    monkeypatch.setattr(settings, "RESULT_CACHE_BACKEND", "auto")
    monkeypatch.setattr(settings, "REDIS_URL", "redis://127.0.0.1:1/0")
    rc.get_result_cache.cache_clear()
    try:
        assert rc.get_result_cache().backend == "memory"
        monkeypatch.setattr(settings, "RESULT_CACHE_BACKEND", "off")
        rc.get_result_cache.cache_clear()
        assert rc.get_result_cache().backend == "off"
    finally:
        monkeypatch.setattr(settings, "RESULT_CACHE_BACKEND", "memory")
        rc.get_result_cache.cache_clear()


@pytest.fixture
def chilika_roi():
    path = ROI_DIR / "chilka.geojson"
    path.write_text(json.dumps({"type": "Polygon", "coordinates": [RING]}), encoding="utf-8")
    yield path
    path.unlink()


def test_cache_key_changes_with_every_parameter(chilika_roi):
    roi = resolve_analysis_roi(229)
    base = analysis.AnalysisRequest(229, date(2023, 1, 1), date(2024, 1, 1), 100.0)
    ndwi = get_index(IndexKey.NDWI)
    key = analysis._result_key("timeseries", ndwi, base, roi)
    variants = [
        analysis._result_key("map", ndwi, base, roi),
        analysis._result_key("timeseries", get_index(IndexKey.NDTI), base, roi),
        analysis._result_key(
            "timeseries",
            ndwi,
            analysis.AnalysisRequest(229, date(2023, 1, 2), date(2024, 1, 1), 100.0),
            roi,
        ),
        analysis._result_key(
            "timeseries",
            ndwi,
            analysis.AnalysisRequest(229, date(2023, 1, 1), date(2024, 1, 2), 100.0),
            roi,
        ),
        analysis._result_key(
            "timeseries",
            ndwi,
            analysis.AnalysisRequest(229, date(2023, 1, 1), date(2024, 1, 1), 50.0),
            roi,
        ),
        analysis._result_key(
            "timeseries",
            ndwi,
            analysis.AnalysisRequest(2441, date(2023, 1, 1), date(2024, 1, 1), 100.0),
            roi,
        ),
    ]
    assert key == analysis._result_key("timeseries", ndwi, base, roi)  # deterministic
    assert len({key, *variants}) == 1 + len(variants)
    assert key.startswith("wq-result:") and len(key) == len("wq-result:") + 64


# --- API behaviour -----------------------------------------------------------------


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


def test_identical_time_series_request_is_served_from_cache(client, chilika_roi, sentinel_hub):
    url = "/api/v1/water-quality/229/NDCI/timeseries?start=2023-01-01&end=2025-01-01"
    first = client.get(url).json()
    calls_after_first = {k: len(v) for k, v in sentinel_hub.requests.items()}
    second = client.get(url).json()
    assert {k: len(v) for k, v in sentinel_hub.requests.items()} == calls_after_first
    assert first["traceability"]["result_cache"]["status"] == "miss"
    assert second["traceability"]["result_cache"] == {"status": "hit", "backend": "memory"}
    assert second["points"] == first["points"]
    assert second["traceability"]["generated_at"] == first["traceability"]["generated_at"]

    # Any parameter change is a different analysis: computed again.
    client.get(url.replace("NDCI", "NDTI"))
    client.get(url + "&max_cloud=50")
    assert len(sentinel_hub.requests["statistics"]) == calls_after_first["statistics"] + 4


def test_geotiff_download_reuses_the_map_raster(client, chilika_roi, sentinel_hub):
    query = "?start=2022-11-01&end=2026-05-30&max_cloud=100"
    shown = client.get(f"/api/v1/water-quality/229/NDMI/map{query}")
    assert shown.json()["traceability"]["result_cache"]["status"] == "miss"
    download = client.get(f"/api/v1/water-quality/229/NDMI/map.tif{query}")
    assert download.status_code == 200
    assert download.headers["x-result-cache"] == "hit"
    assert len(sentinel_hub.requests["process"]) == 1  # no second Sentinel Hub processing
    assert download.content[:4] in (b"II*\x00", b"MM\x00*")  # the GeoTIFF bytes themselves


def test_scene_metadata_respects_cloud_threshold(client, chilika_roi, sentinel_hub):
    # Catalog: tile at 0.4 % on 2024-03-10, another at 7 % on 2023-01-02 (FakeSentinelHub).
    body = client.get(
        "/api/v1/water-quality/229/NDWI/timeseries?start=2023-01-01&end=2025-01-01&max_cloud=0.5"
    ).json()
    by_date = {p["date"]: p for p in body["points"]}
    assert [s["cloud_cover"] for s in by_date["2024-03-10"]["scenes"]] == [0.4]
    assert body["traceability"]["sentinel_hub_api"].startswith("Statistical API")
