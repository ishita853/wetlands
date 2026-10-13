"""Phase 1 boundary foundation: master list, GEE manifest, RSIS boundaries, API provenance.

These tests read the real project data (101-site master list, raw RSIS WFS
response, generated boundary manifest). Small fixture polygons appear only in
tests that exercise the GEE-ROI code path and are written to the temporary
test ROI directory, never to the project data.
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from shapely.geometry import box, mapping, shape

from app.core.config import BACKEND_DIR, settings
from app.services.wetlands import boundaries as b
from app.services.wetlands.roi import load_manifest
from app.tools import build_boundaries
from tests.conftest import ROI_DIR

MASTER = BACKEND_DIR.parent / "frontend" / "data" / "ramsar-sites.json"
BOUNDARIES_DIR = BACKEND_DIR / "data" / "boundaries"
RAW = sorted((BOUNDARIES_DIR / "raw" / "rsis").glob("*.geojson"))[-1]
MANIFEST = json.loads((BOUNDARIES_DIR / "boundary-manifest.json").read_text(encoding="utf-8"))
BY_ID = {s["ramsar_number"]: s for s in MANIFEST["sites"]}

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
UNCERTAIN_6 = {1207, 1208, 230, 1209, 2078, 1210}


# 1-2. master dataset
def test_master_dataset_has_101_unique_sites_with_coordinates():
    sites = json.loads(MASTER.read_text(encoding="utf-8"))["sites"]
    ids = [s["id"] for s in sites]
    assert len(sites) == 101
    assert len(set(ids)) == 101
    assert all(s["latitude"] is not None and s["longitude"] is not None for s in sites)
    assert len(MANIFEST["sites"]) == 101
    assert {s["ramsar_number"] for s in MANIFEST["sites"]} == set(ids)


# 3. GEE manifest
def test_gee_manifest_consistency():
    master_ids = {s["id"] for s in json.loads(MASTER.read_text(encoding="utf-8"))["sites"]}
    manifest = load_manifest()
    assert len(manifest) == 74
    assert set(manifest) <= master_ids
    counts = {
        m: sum(1 for e in manifest.values() if e.mapping == m)
        for m in ("exact", "manual_confirmed", "manual_uncertain")
    }
    assert counts == {"exact": 53, "manual_confirmed": 15, "manual_uncertain": 6}
    assert {i for i, e in manifest.items() if e.mapping == "manual_uncertain"} == UNCERTAIN_6
    assert all(e.mapping_evidence for e in manifest.values())


# 4-5. RSIS source and matching by Ramsar number
def test_rsis_raw_is_preserved_and_matches_metadata():
    meta = json.loads(RAW.with_suffix(".meta.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == meta["sha256"]
    source = b.load_rsis_raw(RAW)
    assert source.crs_name == "urn:ogc:def:crs:EPSG::4326"
    assert sum(len(v) for v in source.features_by_site.values()) == meta["feature_count"] == 114
    assert len(source.features_by_site) == 75
    master = {s["id"]: s for s in json.loads(MASTER.read_text(encoding="utf-8"))["sites"]}
    for site_id, features in source.features_by_site.items():
        assert site_id in master  # matched by Ramsar number, not by name/coordinates
        area_off = features[0]["properties"]["area_off"]
        assert area_off == pytest.approx(master[site_id]["areaHa"], rel=0.01)


def test_crs_check_rejects_non_wgs84():
    parts = [box(76.5, 19.9, 76.6, 20.0)]
    assert b.validate_parts(parts, "urn:ogc:def:crs:EPSG::4326").crs_ok
    report = b.validate_parts(parts, "urn:ogc:def:crs:EPSG::32643")
    assert not report.crs_ok and report.errors


def test_swapped_axes_detected():
    report = b.validate_parts([box(19.9, 76.5, 20.0, 76.6)], "EPSG:4326")
    assert not report.lonlat_order_ok
    assert any("swapped" in e for e in report.errors)


# 6-8. validity, multipart, invalid detection
def test_official_statuses_and_counts():
    status = {i: s["official_boundary"]["status"] for i, s in BY_ID.items()}
    assert {i for i, v in status.items() if v == "invalid"} == INVALID_3
    assert {i for i, v in status.items() if v == "missing_authoritative_boundary"} == MISSING_26
    assert sum(v == "verified" for v in status.values()) == 58
    assert sum(v == "review_required" for v in status.values()) == 14
    for site_id in INVALID_3:
        validation = BY_ID[site_id]["official_boundary"]["validation"]
        assert validation["valid"] is False and validation["make_valid_possible"] is True


def test_multipart_sites_are_collected_not_dissolved():
    source = b.load_rsis_raw(RAW)
    parts = [shape(f["geometry"]) for f in source.features_by_site[2547]]  # Tawa Reservoir
    assert len(parts) == 20
    assembled = b.assemble_parts(parts)
    assert len(assembled.geoms) >= 20
    assert assembled.area == pytest.approx(sum(p.area for p in parts))
    assert BY_ID[2547]["official_boundary"]["validation"]["feature_count"] == 20


def test_invalid_geometry_is_reported_not_repaired():
    source = b.load_rsis_raw(RAW)
    raw_parts = [shape(f["geometry"]) for f in source.features_by_site[2413]]
    assert not raw_parts[0].is_valid
    boundary = b.official_boundary(2413)
    assert boundary.status == "invalid"
    # The retained geometry is the original, byte-for-byte equivalent to the raw source.
    assert b.geometry_sha256(boundary.geometry) == b.geometry_sha256(b.assemble_parts(raw_parts))
    assert not boundary.geometry.is_valid


# 9-10. missing boundaries and no-buffer behaviour
def test_missing_authoritative_boundaries_list():
    data = json.loads(
        (BOUNDARIES_DIR / "missing-authoritative-boundaries.json").read_text(encoding="utf-8")
    )
    assert data["count"] == 26
    assert {s["ramsar_number"] for s in data["sites"]} == MISSING_26
    chandertal = next(s for s in data["sites"] if s["ramsar_number"] == 1569)
    assert chandertal["gee_roi_asset"] is None
    for site_id in MISSING_26:
        record = BY_ID[site_id]["official_boundary"]
        assert record["source"] is None and "geometry_sha256" not in record


def test_no_geometry_is_ever_derived_from_coordinates(client):
    # Chilika: no RSIS boundary, GEE ROI not exported -> every geometry request fails.
    official = client.get("/api/v1/wetlands/229/roi?source=official")
    assert official.status_code == 404
    assert official.json()["detail"]["code"] == "official_boundary_missing_authoritative_boundary"
    assert client.get("/api/v1/wetlands/229/roi").json()["detail"]["code"] == "roi_missing"
    assert client.get("/api/v1/wetlands/229/roi?source=gee").json()["detail"]["code"] == (
        "roi_missing"
    )
    analysis = client.get("/api/v1/water-quality/229/NDWI/timeseries")
    assert analysis.status_code == 409
    assert b.official_boundary(229).geometry is None


# 11. API provenance
def test_official_boundary_api_provenance(client):
    response = client.get("/api/v1/wetlands/2441/roi?source=official")  # Lonar Lake
    assert response.status_code == 200
    feature = response.json()
    props = feature["properties"]
    record = BY_ID[2441]["official_boundary"]
    assert props["source"] == "official_boundary" and props["is_official"] is True
    assert props["crs"] == "EPSG:4326"
    assert props["boundary_status"] == "verified"
    assert props["usable_for_official_explorer"] is True
    assert props["usable_for_water_quality_analysis"] is False
    assert props["version"] == record["version"]
    assert props["geometry_sha256"] == record["geometry_sha256"]
    assert b.geometry_sha256(shape(feature["geometry"])) == record["geometry_sha256"]


def test_invalid_official_boundary_not_served(client):
    response = client.get("/api/v1/wetlands/2408/roi?source=official")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "official_boundary_invalid"
    assert any("Self-intersection" in r for r in detail["reasons"])


def test_wetland_summary_reports_both_boundaries(client):
    by_id = {w["ramsar_site_id"]: w for w in client.get("/api/v1/wetlands").json()}
    lonar = by_id[2441]["boundaries"]
    assert lonar["official_boundary"]["status"] == "verified"
    assert lonar["gee_roi"]["status"] == "missing_export"
    assert lonar["official_explorer"]["status"] == "available"
    assert lonar["gee_comparison"]["status"] == "unavailable"
    agh = by_id[2534]["boundaries"]
    assert agh["gee_roi"]["status"] == "not_in_gee_app"
    assert agh["official_boundary"]["status"] == "verified"


# 12. GEE ROI and RSIS boundary stay separate
@pytest.fixture
def lonar_gee_fixture():
    path = ROI_DIR / "Lonar_Lake.geojson"
    square = box(76.50, 19.97, 76.52, 19.99)  # test fixture, not project data
    path.write_text(
        json.dumps({"type": "Polygon", "coordinates": mapping(square)["coordinates"]}),
        encoding="utf-8",
    )
    yield square
    path.unlink()


def test_gee_roi_and_official_boundary_are_separate(client, lonar_gee_fixture):
    gee = client.get("/api/v1/wetlands/2441/roi?source=gee").json()
    official = client.get("/api/v1/wetlands/2441/roi?source=official").json()
    assert gee["properties"]["source"] == "gee_roi" and gee["properties"]["is_official"] is False
    assert official["properties"]["source"] == "official_boundary"
    assert shape(gee["geometry"]).equals(lonar_gee_fixture)
    assert not shape(official["geometry"]).equals(lonar_gee_fixture)
    summary = client.get("/api/v1/wetlands/2441").json()["boundaries"]
    assert summary["gee_comparison"]["status"] == "available"
    assert summary["official_explorer"]["status"] == "available"


def test_uncertain_mapping_blocks_gee_comparison_analysis(client):
    path = ROI_DIR / "Deepor_Beel_Bird_Sanctuary.geojson"
    path.write_text(
        json.dumps(
            {
                "type": "Polygon",
                "coordinates": mapping(box(91.60, 26.10, 91.70, 26.16))["coordinates"],
            }
        ),
        encoding="utf-8",
    )
    try:
        response = client.get("/api/v1/water-quality/1207/NDWI/timeseries")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "roi_mapping_uncertain"
        roi = client.get("/api/v1/wetlands/1207/roi?source=gee").json()
        assert roi["properties"]["usable_for_water_quality_analysis"] is False
    finally:
        path.unlink()


def test_comparison_statuses_on_real_geometry():
    source = b.load_rsis_raw(RAW)
    lonar = b.assemble_parts([shape(f["geometry"]) for f in source.features_by_site[2441]])
    same = b.compare_geometries(lonar, True, lonar, True)
    assert same["status"] == "MATCH" and same["iou"] == pytest.approx(1.0)
    far = b.compare_geometries(box(76.40, 19.90, 76.41, 19.91), True, lonar, True)
    assert far["status"] == "SIGNIFICANT_DIFFERENCE" and far["iou"] == 0
    invalid = b.compare_geometries(lonar, True, lonar, False)
    assert invalid["status"] == "REVIEW_REQUIRED" and invalid["iou"] is None
    assert "not an official standard" in same["thresholds"]["type"]


# 13. SHA-256 / version preserved and reproducible build
def test_build_is_reproducible_and_preserves_hashes(tmp_path, monkeypatch):
    work = tmp_path / "boundaries"
    shutil.copytree(BOUNDARIES_DIR / "raw", work / "raw")
    monkeypatch.setattr(settings, "BOUNDARIES_DIR", work)
    monkeypatch.setattr(settings, "RAMSAR_SITES_FILE", MASTER)
    raw = sorted((work / "raw" / "rsis").glob("*.geojson"))[-1]
    first = build_boundaries.build(raw)
    second = build_boundaries.build(raw)
    assert first == second
    committed = {s["ramsar_number"]: s["official_boundary"] for s in MANIFEST["sites"]}
    for site in first["sites"]:
        official = site["official_boundary"]
        assert official.get("geometry_sha256") == committed[site["ramsar_number"]].get(
            "geometry_sha256"
        )
        if official["source"] == "RSIS":
            assert official["raw_sha256"] == first["sources"]["rsis_raw"]["sha256"]


def test_tampered_raw_source_is_rejected(tmp_path):
    copy = tmp_path / RAW.name
    shutil.copy(RAW, copy)
    shutil.copy(RAW.with_suffix(".meta.json"), copy.with_suffix(".meta.json"))
    copy.write_bytes(copy.read_bytes().replace(b"Lonar", b"Lonxr", 1))
    with pytest.raises(ValueError, match="does not match"):
        b.load_rsis_raw(copy)


def test_raw_file_is_unchanged_by_build():
    before = hashlib.sha256(RAW.read_bytes()).hexdigest()
    b.load_rsis_raw(RAW)
    assert hashlib.sha256(Path(RAW).read_bytes()).hexdigest() == before
