"""Phase J tools, exercised with mocked HTTP. These fixtures are test inputs only."""

import csv
import json

import pytest

from app.tools import live_validation, validate_rois
from tests.conftest import ROI_DIR
from tests.test_water_quality_api import TILE, FakeSentinelHub

RING = [[85.345, 19.695], [85.355, 19.695], [85.355, 19.705], [85.345, 19.705], [85.345, 19.695]]


@pytest.fixture
def chilika_roi():
    path = ROI_DIR / "chilka.geojson"
    path.write_text(json.dumps({"type": "Polygon", "coordinates": [RING]}), encoding="utf-8")
    yield path
    path.unlink()


def test_validate_rois_reports_every_manifest_entry(chilika_roi):
    rows = validate_rois.validate()
    assert len(rows) == 74
    chilika = next(r for r in rows if r["gee_asset"] == "chilka")
    assert chilika["status"] == "available"
    assert chilika["rsis_point_distance_m"] == 0.0  # RSIS point (85.35, 19.70) is inside
    assert chilika["area_ratio"] < 0.01  # the test square is far smaller than RSIS 116,500 ha
    assert sum(r["status"] == "missing" for r in rows) == 73
    assert "| 9 | `chilka` | 229 | Chilika Lake |" in validate_rois.to_markdown(rows)


def test_live_validation_blocked_without_credentials(capsys, monkeypatch, tmp_path):
    monkeypatch.setattr("sys.argv", ["live_validation", "--out", str(tmp_path)])
    assert live_validation.main() == 2
    assert "LIVE VALIDATION BLOCKED" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []  # nothing written


def test_live_validation_run_and_gee_comparison(chilika_roi, tmp_path, monkeypatch):
    import httpx

    from app.core.config import Settings
    from app.services.copernicus.client import CopernicusClient

    fake = FakeSentinelHub()
    config = Settings(
        COPERNICUS_CLIENT_ID="id",
        COPERNICUS_CLIENT_SECRET="secret",
        COPERNICUS_TOKEN_URL="https://identity.example/token",
        COPERNICUS_CATALOG_URL="https://sh.example/catalog/v1/search",
        COPERNICUS_PROCESS_URL="https://sh.example/process/v1",
        COPERNICUS_STATISTICS_URL="https://sh.example/statistics/v1",
    )
    client = CopernicusClient(config, transport=httpx.MockTransport(fake), sleep=lambda s: None)
    monkeypatch.setattr(live_validation, "get_copernicus_client", lambda: client)

    def write(name, rows):
        with (tmp_path / name).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    write(
        "scenes_chilka.csv",
        [
            {
                "image_id": "x",
                "time_start": "2024-03-10T04:55:21Z",
                "mgrs_tile": "45QTE",
                "cloudy_pixel_percentage": "0.4",
            }
        ],
    )
    write(
        "map_selection_chilka.csv",
        [
            {
                "index": "NDWI",
                "image_id": "x",
                "time_start": "2024-03-10T04:55:21Z",
                "mgrs_tile": "45QTE",
                "qa60_unmasked_pixels_in_roi": "12",
                "index_valid_pixels_in_roi_20m": "300",
            }
        ],
    )
    write(
        "series_chilka_NDWI.csv",
        [
            {"time_start": "2024-03-10T04:55:21Z", "mean": "0.2"},
            {"time_start": "2025-03-10T04:55:21Z", "mean": "0.3"},
            {"time_start": "2025-03-10T04:55:30Z", "mean": "0.31"},  # second granule same day
        ],
    )

    report = live_validation.run([229, 1571], tmp_path)
    chilika = report["sites"]["chilka"]
    assert report["sites"]["renuka"]["roi"] == "roi_missing"
    assert chilika["roi"] == "gee_roi"  # Chilika has no provided polygon; GEE fixture used
    assert chilika["catalog"]["selected"]["id"] == TILE
    assert chilika["axis_probe"]["lonlat"]["items"] == 2
    ndwi_map = chilika["maps"]["NDWI"]
    assert ndwi_map["raster_contains_roi_bbox"] and ndwi_map["raster_contains_rsis_point"]
    assert ndwi_map["json_response_bytes"] > ndwi_map["png_data_uri_chars"]
    assert "_points" not in chilika["timeseries"]["NDWI"]

    comparison = chilika["gee_comparison"]
    assert comparison["cloud_cover"]["identical_count"] == 1
    assert comparison["map_selection"]["gee_tile"] == "45QTE"
    series = comparison["series"]["NDWI"]
    assert series["gee_multi_granule_days"] == 1
    assert series["comparable_single_granule_days"] == 1
    assert series["max_abs_diff"] == pytest.approx(0.05)  # |0.25 (mock) - 0.2|
