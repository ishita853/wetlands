"""Provided ROI dataset ('India Ramsar Sites September 2026') and water-quality ROI resolution.

Uses the real supplied GeoJSON and the real 101-site master list. Temporary
datasets are written only to pytest's tmp_path to exercise error handling.
"""

import json
import shutil

import httpx
import pytest
from shapely.geometry import box, mapping, shape

from app.core.config import BACKEND_DIR, Settings, settings
from app.main import app
from app.services.copernicus.client import CopernicusClient, get_copernicus_client
from app.services.wetlands import boundaries as b
from app.services.wetlands import provided as p
from app.services.wetlands.resolver import RoiUnavailable, resolve_analysis_roi
from app.tools import build_boundaries
from tests.conftest import ROI_DIR
from tests.test_water_quality_api import _geotiff

PROVIDED = BACKEND_DIR / "data" / "India Ramsar Sites September 2026.geojson"
MASTER = BACKEND_DIR.parent / "frontend" / "data" / "ramsar-sites.json"
MISSING_26 = {
    229,
    230,
    461,
    462,
    463,
    464,
    1160,
    1161,
    1204,
    1205,
    1206,
    1207,
    1208,
    1209,
    1210,
    1211,
    1212,
    1213,
    1214,
    1569,
    1570,
    1571,
    1572,
    1573,
    1574,
    2078,
}
INVALID_3 = {2408, 2413, 2548}
SCENE_ID = "S2B_MSIL2A_20240115T052119_N0510_R062_T43QFA_20240115T074012.SAFE"


def _master_sites():
    from app.services.wetlands.sites import load_sites

    return load_sites(MASTER)


# --- 101-site matching --------------------------------------------------------


def test_matching_against_the_101_site_master_list():
    report = build_boundaries.matching_report(_master_sites())
    assert report["dataset"] == PROVIDED.name
    assert report["master_sites"] == 101
    assert report["polygon_features"] == 114
    assert report["features_without_ramsar_id"] == 0
    assert report["distinct_ramsar_ids"] == 75
    assert report["matched_master_sites"] == 75
    assert set(report["unmatched_master_sites"]) == MISSING_26
    assert report["unmatched_polygon_ids"] == []
    assert report["exact_duplicate_geometries"] == []
    assert report["duplicate_names_across_ids"] == {}
    assert report["ambiguous_matches"] == []
    assert report["name_mismatches_by_id"] == []
    assert report["multipart_sites"]["2547"] == 20


def test_provided_features_carry_rsis_identifiers():
    manifest = json.loads(
        (BACKEND_DIR / "data/boundaries/boundary-manifest.json").read_text(encoding="utf-8")
    )
    compared = [
        s["provided_roi"]["vs_rsis"] for s in manifest["sites"] if s["provided_roi"].get("vs_rsis")
    ]
    assert len(compared) == 75
    assert all(c["same_v_idris"] for c in compared)
    assert all(abs(c["area_ratio"] - 1) < 1e-5 for c in compared)


# --- duplicates, missing sites, CRS, validity ---------------------------------


def _use_dataset(monkeypatch, path):
    monkeypatch.setattr(settings, "PROVIDED_ROI_FILE", path)


def test_duplicate_unknown_and_unidentified_features_detected(tmp_path, monkeypatch):
    data = json.loads(PROVIDED.read_text(encoding="utf-8"))
    lonar = next(f for f in data["features"] if f["properties"]["ramsarid"] == 2441)
    unknown = json.loads(json.dumps(lonar))
    unknown["properties"]["ramsarid"] = 999999
    unidentified = json.loads(json.dumps(lonar))
    unidentified["properties"].pop("ramsarid")
    data["features"] += [json.loads(json.dumps(lonar)), unknown, unidentified]
    path = tmp_path / "duplicates.geojson"
    path.write_text(json.dumps(data), encoding="utf-8")
    _use_dataset(monkeypatch, path)
    report = build_boundaries.matching_report(_master_sites())
    assert report["features_without_ramsar_id"] == 1
    assert report["unmatched_polygon_ids"] == [999999]
    assert any(sorted(ids) == [2441, 2441, 999999] for ids in report["exact_duplicate_geometries"])


def test_missing_sites_have_no_geometry():
    for site_id in MISSING_26:
        roi = p.lookup_provided(site_id)
        assert roi.status == "missing" and roi.geometry is None


def test_crs84_accepted_projected_crs_rejected(tmp_path, monkeypatch):
    assert p.load_dataset().crs_name == "urn:ogc:def:crs:OGC:1.3:CRS84"
    assert p.lookup_provided(2441).status == "available"
    data = json.loads(PROVIDED.read_text(encoding="utf-8"))
    data["crs"]["properties"]["name"] = "urn:ogc:def:crs:EPSG::32643"
    path = tmp_path / "projected.geojson"
    path.write_text(json.dumps(data), encoding="utf-8")
    _use_dataset(monkeypatch, path)
    roi = p.lookup_provided(2441)
    assert roi.status == "invalid" and "CRS" in (roi.reason or "")


def test_invalid_geometries_rejected_not_repaired():
    raw = json.loads(PROVIDED.read_text(encoding="utf-8"))
    for site_id in INVALID_3:
        roi = p.lookup_provided(site_id)
        assert roi.status == "invalid" and "Self-intersection" in (roi.reason or "")
        parts = [
            shape(f["geometry"]) for f in raw["features"] if f["properties"]["ramsarid"] == site_id
        ]
        assert roi.geometry_sha256 == b.geometry_sha256(b.assemble_parts(parts))
    with pytest.raises(RoiUnavailable) as exc_info:
        resolve_analysis_roi(2413)
    assert exc_info.value.code == "roi_invalid"


def test_changed_provided_file_is_refused(tmp_path, monkeypatch):
    copy = tmp_path / PROVIDED.name  # same name -> checked against provided-roi.meta.json
    shutil.copy(PROVIDED, copy)
    copy.write_bytes(copy.read_bytes().replace(b"Lonar", b"Lonxr", 1))
    _use_dataset(monkeypatch, copy)
    with pytest.raises(ValueError, match="does not match"):
        p.lookup_provided(2441)


def test_supplied_geometry_is_used_unchanged():
    raw = json.loads(PROVIDED.read_text(encoding="utf-8"))
    parts = [shape(f["geometry"]) for f in raw["features"] if f["properties"]["ramsarid"] == 2547]
    roi = resolve_analysis_roi(2547)
    assert roi.source == "provided_roi"
    assert roi.geometry_sha256 == b.geometry_sha256(b.assemble_parts(parts))
    assert len(roi.geometry.geoms) >= 20  # parts collected, not dissolved


# --- ROI source selection -------------------------------------------------------


@pytest.fixture
def lonar_gee_fixture():
    path = ROI_DIR / "Lonar_Lake.geojson"
    square = box(76.50, 19.97, 76.52, 19.99)  # test fixture, not project data
    path.write_text(json.dumps(mapping(square)), encoding="utf-8")
    yield square
    path.unlink()


def test_source_selection_policy(lonar_gee_fixture):
    assert resolve_analysis_roi(2441).source == "provided_roi"  # provided is primary
    assert resolve_analysis_roi(2441, "provided").source == "provided_roi"
    gee = resolve_analysis_roi(2441, "gee")
    assert gee.source == "gee_roi" and gee.geometry.equals(lonar_gee_fixture)
    with pytest.raises(RoiUnavailable) as missing:
        resolve_analysis_roi(229)  # no provided or imported polygon, GEE ROI not exported
    assert missing.value.code == "roi_missing"
    assert set(missing.value.sources) == {"provided", "imported", "gee"}


def test_roi_endpoint_sources(client):
    analysis = client.get("/api/v1/wetlands/2441/roi").json()["properties"]
    assert analysis["source"] == "provided_roi" and analysis["is_official"] is False
    assert analysis["usable_for_water_quality_analysis"] is True
    assert analysis["crs"] == "EPSG:4326"
    assert "RSIS-derived" in analysis["provenance"]
    assert client.get("/api/v1/wetlands/2441/roi?source=provided").status_code == 200
    official = client.get("/api/v1/wetlands/2441/roi?source=official").json()["properties"]
    assert official["source"] == "official_boundary"
    invalid = client.get("/api/v1/wetlands/2413/roi?source=provided")
    assert invalid.status_code == 404
    summary = client.get("/api/v1/wetlands/2441").json()["boundaries"]
    assert summary["provided_roi"]["status"] == "available"
    assert summary["water_quality_analysis"] == {
        "status": "available",
        "source": "provided_roi",
        "reason": None,
    }


# --- water-quality ROI resolution (Sentinel Hub mocked) ------------------------


class IndiaWideFake:
    """Catalog footprint covering India; Process returns a GeoTIFF on the requested grid."""

    def __init__(self):
        self.process_bodies: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "identity.example":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        body = json.loads(request.content)
        if "catalog" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "features": [
                        {
                            "id": SCENE_ID,
                            "geometry": mapping(box(60, 0, 100, 40)),
                            "properties": {
                                "datetime": "2024-01-15T05:21:19Z",
                                "eo:cloud_cover": 0.2,
                            },
                        }
                    ],
                    "context": {},
                },
            )
        self.process_bodies.append(body)
        return httpx.Response(200, content=_geotiff(body), headers={"Content-Type": "image/tiff"})


def test_water_quality_map_uses_the_supplied_polygon(client):
    fake = IndiaWideFake()
    config = Settings(
        COPERNICUS_CLIENT_ID="id",
        COPERNICUS_CLIENT_SECRET="secret",
        COPERNICUS_TOKEN_URL="https://identity.example/token",
        COPERNICUS_CATALOG_URL="https://sh.example/catalog/v1/search",
        COPERNICUS_PROCESS_URL="https://sh.example/process/v1",
    )
    app.dependency_overrides[get_copernicus_client] = lambda: CopernicusClient(
        config, transport=httpx.MockTransport(fake), sleep=lambda s: None
    )
    try:
        response = client.get("/api/v1/water-quality/2441/NDWI/map")
    finally:
        app.dependency_overrides.pop(get_copernicus_client, None)
    assert response.status_code == 200, response.text
    trace = response.json()["traceability"]
    roi = resolve_analysis_roi(2441)
    assert trace["roi"]["source"] == "provided_roi"
    assert trace["roi"]["geometry_sha256"] == roi.geometry_sha256
    assert trace["roi"]["version"] == roi.version
    # The request geometry is the supplied polygon, reprojected only inside the request.
    from app.services.copernicus.geometry import reproject

    sent = shape(fake.process_bodies[0]["input"]["bounds"]["geometry"])
    expected = reproject(roi.geometry, 4326, 3857)
    assert sent.symmetric_difference(expected).area < 1e-6 * expected.area
