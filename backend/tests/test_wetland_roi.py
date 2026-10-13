"""GEE ROI manifest and polygon validation."""

import json
from pathlib import Path

import pytest

from app.core.config import BACKEND_DIR
from app.services.wetlands.roi import RoiInvalid, load_manifest, lookup_roi, parse_roi_geojson

REAL_SITES = BACKEND_DIR.parent / "frontend" / "data" / "ramsar-sites.json"
SQUARE = [[85.3, 19.6], [85.4, 19.6], [85.4, 19.8], [85.3, 19.8], [85.3, 19.6]]


def test_manifest_has_74_distinct_gee_rois_on_real_ramsar_sites():
    manifest = load_manifest()
    assert len(manifest) == 74
    assert sorted(e.gee_table_index for e in manifest.values()) == list(range(1, 75))
    site_ids = {s["id"] for s in json.loads(REAL_SITES.read_text(encoding="utf-8"))["sites"]}
    assert set(manifest) <= site_ids
    assert all(
        e.gee_asset_id == f"projects/ee-ramsarwetlands5/assets/{e.gee_asset_name}"
        for e in manifest.values()
    )
    assert manifest[229].gee_asset_name == "chilka"
    assert manifest[229].mapping == "manual_confirmed"


def test_feature_collection_is_dissolved_like_gee_roi_geometry():
    other = [[85.5, 19.6], [85.6, 19.6], [85.6, 19.7], [85.5, 19.6]]
    data = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [SQUARE]}},
            {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [other]}},
        ],
    }
    geometry, count = parse_roi_geojson(data)
    assert count == 2
    assert geometry.geom_type == "MultiPolygon"


def test_swapped_axes_rejected():
    swapped = [[lat, lon] for lon, lat in SQUARE]
    with pytest.raises(RoiInvalid, match="swapped"):
        parse_roi_geojson({"type": "Polygon", "coordinates": [swapped]})


def test_projected_crs_rejected():
    data = {
        "type": "Polygon",
        "coordinates": [SQUARE],
        "crs": {"type": "name", "properties": {"name": "EPSG:32645"}},
    }
    with pytest.raises(RoiInvalid, match="Unsupported CRS"):
        parse_roi_geojson(data)


def test_point_is_not_accepted_as_roi():
    with pytest.raises(RoiInvalid, match="polygonal"):
        parse_roi_geojson({"type": "Point", "coordinates": [85.35, 19.7]})


def test_invalid_polygon_rejected_not_repaired():
    bowtie = [[85.3, 19.6], [85.4, 19.8], [85.4, 19.6], [85.3, 19.8], [85.3, 19.6]]
    with pytest.raises(RoiInvalid, match="Invalid polygon"):
        parse_roi_geojson({"type": "Polygon", "coordinates": [bowtie]})


def test_lookup_statuses(tmp_path: Path):
    assert lookup_roi(2534, tmp_path).status == "no_gee_roi"  # Aghanashini: no GEE ROI
    missing = lookup_roi(229, tmp_path)
    assert missing.status == "missing"
    assert missing.reason is not None
    assert "projects/ee-ramsarwetlands5/assets/chilka" in missing.reason

    (tmp_path / "chilka.geojson").write_text("{not json", encoding="utf-8")
    assert lookup_roi(229, tmp_path).status == "invalid"

    (tmp_path / "chilka.geojson").write_text(
        json.dumps({"type": "Polygon", "coordinates": [SQUARE]}), encoding="utf-8"
    )
    found = lookup_roi(229, tmp_path)
    assert found.status == "available" and found.roi is not None
    assert len(found.roi.version) == 16
    assert found.roi.area_ha == pytest.approx(10.5 * 22.1 * 100, rel=0.03)
