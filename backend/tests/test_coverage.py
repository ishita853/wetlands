"""Boundary coverage report (all 101 sites) and documented-but-unused candidate sources."""

import json

import pytest

from app.core.config import BACKEND_DIR, settings
from app.services.wetlands.resolver import RoiUnavailable, resolve_analysis_roi

DATA = BACKEND_DIR / "data" / "boundaries"
COVERAGE = json.loads((DATA / "coverage-report.json").read_text(encoding="utf-8"))
CANDIDATES = json.loads((DATA / "candidate-sources.json").read_text(encoding="utf-8"))
MASTER = json.loads(
    (BACKEND_DIR.parent / "frontend" / "data" / "ramsar-sites.json").read_text(encoding="utf-8")
)["sites"]
MISSING_26 = {
    229,
    230,
    461,
    462,
    463,
    464,
    1160,
    1161,
    *range(1204, 1215),
    *range(1569, 1575),
    2078,
}
INVALID_3 = {2408, 2413, 2548}
UNCERTAIN_6 = {230, 1207, 1208, 1209, 1210, 2078}
FIELDS = {
    "ramsar_id",
    "name",
    "latitude",
    "longitude",
    "provided_roi",
    "provided_roi_valid",
    "gee_roi",
    "gee_roi_verified",
    "official_roi",
    "analysis_available",
    "selected_analysis_source",
    "provenance",
    "reason_unavailable",
}


def test_coverage_report_lists_every_master_site_with_required_fields():
    rows = COVERAGE["sites"]
    assert len(rows) == 101
    assert {r["ramsar_id"] for r in rows} == {s["id"] for s in MASTER}
    assert all(set(r) >= FIELDS for r in rows)


def test_coverage_totals_and_unavailable_sites():
    totals = COVERAGE["totals"]
    assert totals["analysis_available"] == 93
    assert totals["by_source"] == {"provided_roi": 72, "imported_roi": 21, "gee_roi": 0}
    unavailable = {r["ramsar_id"] for r in COVERAGE["sites"] if not r["analysis_available"]}
    # Imported ROIs (supplied 2026-09-30) cover the rest; these remain: uncertain mapping (6),
    # Vembanad-Kol (nothing supplied) and Kazhuveli (invalid in every source).
    assert unavailable == UNCERTAIN_6 | {1214, 2548}
    for row in COVERAGE["sites"]:
        if row["analysis_available"]:
            assert row["selected_analysis_source"] and row["provenance"]
            assert row["reason_unavailable"] is None
        else:
            assert row["selected_analysis_source"] is None and row["reason_unavailable"]


def test_coverage_matches_live_resolver(monkeypatch):
    # The report is built from the real ROI files, not the tests' empty directories.
    monkeypatch.setattr(settings, "WETLAND_ROI_DIR", BACKEND_DIR / "data" / "roi")
    monkeypatch.setattr(settings, "IMPORTED_ROI_DIR", BACKEND_DIR / "data" / "imported-roi")
    for row in COVERAGE["sites"]:
        if row["analysis_available"]:
            assert resolve_analysis_roi(row["ramsar_id"]).source == row["selected_analysis_source"]
        else:
            with pytest.raises(RoiUnavailable):
                resolve_analysis_roi(row["ramsar_id"])


def test_candidates_are_documented_but_never_imported():
    sites = {s["ramsar_number"]: s for s in CANDIDATES["sites"]}
    assert set(sites) == MISSING_26 | INVALID_3
    for site in sites.values():
        for candidate in site["candidates"]:
            assert candidate["status"] == "not_imported"
            assert candidate["reason"] and candidate["source"] and candidate["licence"]
    # The Beas (2408) WDPA version is valid but a third-party repair: still rejected here.
    beas = sites[2408]["candidates"]
    assert any("third-party repair" in c.get("comparison_with_rsis", "") for c in beas)
    with pytest.raises(RoiUnavailable) as exc_info:
        resolve_analysis_roi(2408, "provided")
    assert exc_info.value.code == "roi_invalid"
