"""Imported ROIs (team-supplied shapefiles, 2026-09-30): provenance, geometry, availability."""

import json
import zipfile

import pyogrio
import pytest
from shapely.geometry import shape

from app.core.config import BACKEND_DIR, settings
from app.services.wetlands import boundaries as b
from app.services.wetlands import imported as im
from app.services.wetlands.resolver import RoiUnavailable, resolve_analysis_roi

IMPORTED = BACKEND_DIR / "data" / "imported-roi"
ARCHIVES = BACKEND_DIR / "data" / "Ramsar Wetland Shapefiles"
MANIFEST = json.loads((IMPORTED / "manifest.json").read_text(encoding="utf-8"))["imports"]
UNCERTAIN_6 = {230, 1207, 1208, 1209, 1210, 2078}


@pytest.fixture
def real_imported(monkeypatch):
    monkeypatch.setattr(settings, "IMPORTED_ROI_DIR", IMPORTED)


def test_manifest_records_actual_origin_never_gee():
    assert len(MANIFEST) == 29
    origins = {e["ramsarSiteId"]: e["origin"] for e in MANIFEST}
    assert set(origins.values()) == {
        "rsis_feature",
        "rsis_feature_repaired_by_supplier",
        "supplied_shapefile",
    }
    # Repaired copies of the invalid published RSIS geometry: documented, not repaired here.
    assert {i for i, o in origins.items() if o == "rsis_feature_repaired_by_supplier"} == {
        2408,
        2413,
    }
    assert {i for i, o in origins.items() if o == "rsis_feature"} == {2464, 2548}
    for e in MANIFEST:
        assert "gee" not in e["origin"]
        if e["origin"] == "supplied_shapefile":
            assert "not established" in e["originEvidence"] or "not a GEE" in e["originEvidence"]
    mapping = {e["ramsarSiteId"]: e["mapping"] for e in MANIFEST}
    assert {i for i, m in mapping.items() if m == "manual_uncertain"} == UNCERTAIN_6


@pytest.mark.parametrize("entry", MANIFEST, ids=lambda e: e["sourceArchive"])
def test_geometry_is_exactly_as_supplied(entry):
    archive = ARCHIVES / entry["sourceArchive"]
    layer = entry["sourceLayer"]
    assert layer in zipfile.ZipFile(archive).namelist()
    frame = pyogrio.read_dataframe(f"/vsizip/{archive.as_posix()}/{layer}")
    stored = json.loads((IMPORTED / entry["file"]).read_text(encoding="utf-8"))["features"]
    assert b.geometry_sha256(b.assemble_parts(list(frame.geometry))) == b.geometry_sha256(
        b.assemble_parts([shape(f["geometry"]) for f in stored])
    )


def test_uncertain_sites_stay_unavailable(real_imported):
    for site_id in UNCERTAIN_6:
        assert im.lookup_imported(site_id).status == "available"  # polygon present and valid
        with pytest.raises(RoiUnavailable) as exc_info:
            resolve_analysis_roi(site_id)
        assert exc_info.value.code == "roi_mapping_uncertain"


def test_repaired_rsis_copy_is_used_with_its_provenance(real_imported):
    with pytest.raises(RoiUnavailable) as exc_info:
        resolve_analysis_roi(2408, "provided")
    assert exc_info.value.code == "roi_invalid"
    roi = resolve_analysis_roi(2408)
    assert roi.source == "imported_roi"
    assert roi.source_ids["origin"] == "rsis_feature_repaired_by_supplier"
    assert "repaired by the supplier" in roi.provenance
    # Kazhuveli: the supplied copy is the same invalid RSIS geometry, so nothing is usable.
    assert im.lookup_imported(2548).status == "invalid"
    with pytest.raises(RoiUnavailable):
        resolve_analysis_roi(2548)


def test_valid_provided_roi_still_takes_precedence(real_imported):
    assert im.lookup_imported(2464).status == "available"
    assert resolve_analysis_roi(2464).source == "provided_roi"
    assert resolve_analysis_roi(2464, "imported").source == "imported_roi"


def test_api_exposes_imported_source(client, real_imported):
    feature = client.get("/api/v1/wetlands/229/roi").json()
    props = feature["properties"]
    assert props["source"] == "imported_roi"
    assert "not a GEE ROI" in props["provenance"]
    assert props["gee_asset_id"] is None
    assert props["source_ids"] == {"source_archive": "chilka.zip", "origin": "supplied_shapefile"}
    # The GEE ROI itself is still not exported.
    assert client.get("/api/v1/wetlands/229/roi?source=gee").status_code == 404

    boundaries = client.get("/api/v1/wetlands/229").json()["boundaries"]
    assert boundaries["water_quality_analysis"] == {
        "status": "available",
        "source": "imported_roi",
        "reason": None,
    }
    assert boundaries["imported_roi"]["origin"] == "supplied_shapefile"
    assert boundaries["gee_roi"]["status"] == "missing_export"

    uncertain = client.get("/api/v1/wetlands/1207/roi")  # Deepor Beel (in the test site list)
    assert uncertain.status_code == 404
    assert uncertain.json()["detail"]["code"] == "roi_mapping_uncertain"
