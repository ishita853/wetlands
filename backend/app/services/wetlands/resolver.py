"""Which polygon a water-quality analysis runs over.

Sources, kept separate:
- provided_roi : the provided dataset (India Ramsar Sites September 2026; RSIS-derived)
- imported_roi : team-supplied ROI shapefiles (2026-09-30; only with a verified mapping)
- gee_roi      : the existing GEE application's ROI (only with a verified mapping)

Policy (approved 2026-09-25; imported_roi added 2026-09-30):
- auto (default): the provided ROI if valid, else a verified imported ROI, else a
  verified GEE ROI, else unavailable;
- provided / imported / gee: that source only.
The official RSIS boundary is served for display (official explorer) and is not
an analysis source here. No geometry is ever derived from site coordinates.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from shapely import Geometry

from app.services.wetlands.imported import lookup_imported
from app.services.wetlands.provided import lookup_provided
from app.services.wetlands.roi import RoiManifestEntry, lookup_roi

RoiSource = Literal["auto", "provided", "imported", "gee"]

PROVIDED_PROVENANCE = (
    "Provided ROI dataset 'India Ramsar Sites September 2026' (RSIS-derived: matches "
    "ramsar_sdi:features_published within 8 mm); not a GEE ROI"
)
GEE_PROVENANCE = "Existing GEE application ROI (exported asset); not an official Ramsar boundary"
IMPORTED_PROVENANCE = (
    "Imported ROI: shapefile supplied by the project team (2026-09-30); not a GEE ROI and "
    "not an official Ramsar boundary"
)
_ORIGIN_NOTES = {
    "rsis_feature": "RSIS feature",
    "rsis_feature_repaired_by_supplier": (
        "RSIS feature, self-intersection repaired by the supplier before supply"
    ),
    "supplied_shapefile": "supplied shapefile; GEE origin not established",
}


@dataclass(frozen=True)
class ResolvedRoi:
    site_id: int
    source: Literal["provided_roi", "imported_roi", "gee_roi"]
    provenance: str
    geometry: Geometry
    version: str
    file: str
    area_ha: float
    feature_count: int
    geometry_sha256: str | None = None
    # Ramsar-site mapping of an imported or GEE ROI (exact | manual_confirmed).
    mapping: str | None = None
    gee_entry: RoiManifestEntry | None = None
    source_ids: dict[str, Any] = field(default_factory=dict)


class RoiUnavailable(Exception):
    def __init__(self, code: str, message: str, sources: dict[str, Any]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.sources = sources


def _provided(site_id: int) -> tuple[ResolvedRoi | None, dict[str, Any]]:
    roi = lookup_provided(site_id)
    status = {"status": roi.status, "reason": roi.reason}
    if roi.status != "available" or roi.geometry is None:
        return None, status
    return (
        ResolvedRoi(
            site_id=site_id,
            source="provided_roi",
            provenance=PROVIDED_PROVENANCE,
            geometry=roi.geometry,
            version=roi.version or "",
            file="India Ramsar Sites September 2026.geojson",
            area_ha=roi.area_ha or 0.0,
            feature_count=roi.feature_count,
            geometry_sha256=roi.geometry_sha256,
            source_ids=roi.source_ids,
        ),
        status,
    )


def _imported(site_id: int) -> tuple[ResolvedRoi | None, dict[str, Any]]:
    roi = lookup_imported(site_id)
    entry = roi.entry
    if roi.status != "available" or roi.geometry is None or entry is None:
        return None, {"status": roi.status, "reason": roi.reason}
    if entry.mapping == "manual_uncertain":
        return None, {
            "status": "mapping_uncertain",
            "reason": (
                f"The imported ROI {entry.source_archive} exists but its mapping to Ramsar "
                f"site {site_id} is uncertain: {entry.mapping_evidence}"
            ),
        }
    return (
        ResolvedRoi(
            site_id=site_id,
            source="imported_roi",
            provenance=f"{IMPORTED_PROVENANCE} ({_ORIGIN_NOTES[entry.origin]})",
            geometry=roi.geometry,
            version=roi.version or "",
            file=entry.file,
            area_ha=roi.area_ha or 0.0,
            feature_count=roi.feature_count,
            geometry_sha256=roi.geometry_sha256,
            mapping=entry.mapping,
            source_ids={"source_archive": entry.source_archive, "origin": entry.origin},
        ),
        {"status": "available", "reason": None},
    )


def _gee(site_id: int) -> tuple[ResolvedRoi | None, dict[str, Any]]:
    lookup = lookup_roi(site_id)
    if lookup.roi is None:
        return None, {"status": lookup.status, "reason": lookup.reason}
    entry = lookup.roi.entry
    if entry.mapping == "manual_uncertain":
        return None, {
            "status": "mapping_uncertain",
            "reason": (
                f"The GEE ROI '{entry.gee_asset_name}' exists but its mapping to Ramsar site "
                f"{site_id} is uncertain: {entry.mapping_evidence}"
            ),
        }
    return (
        ResolvedRoi(
            site_id=site_id,
            source="gee_roi",
            provenance=GEE_PROVENANCE,
            geometry=lookup.roi.geometry,
            version=lookup.roi.version,
            file=lookup.roi.source_file,
            area_ha=lookup.roi.area_ha,
            feature_count=lookup.roi.feature_count,
            mapping=entry.mapping,
            gee_entry=entry,
            source_ids={"gee_asset_id": entry.gee_asset_id},
        ),
        {"status": "available", "reason": None},
    )


_CODES = {
    "missing": "roi_missing",
    "no_gee_roi": "roi_no_gee_roi",
    "invalid": "roi_invalid",
    "mapping_uncertain": "roi_mapping_uncertain",
}


def resolve_analysis_roi(site_id: int, source: RoiSource = "auto") -> ResolvedRoi:
    statuses: dict[str, dict[str, Any]] = {}
    for name, lookup in (("provided", _provided), ("imported", _imported), ("gee", _gee)):
        if source not in ("auto", name):
            continue
        roi, statuses[name] = lookup(site_id)
        if roi is not None:
            return roi

    sources = {k: v for k, v in statuses.items() if v}
    if source != "auto":
        code = _CODES[statuses[source]["status"]]
    elif statuses["provided"]["status"] == "invalid":
        code = "roi_invalid"
    elif any(s["status"] in ("mapping_uncertain", "invalid") for s in statuses.values()):
        status = next(
            s["status"]
            for s in (statuses["imported"], statuses["gee"])
            if s["status"] in ("mapping_uncertain", "invalid")
        )
        code = _CODES[status]
    else:
        code = "roi_missing"
    message = (
        " ".join(
            f"{name}: {status['reason']}"
            for name, status in sources.items()
            if status.get("reason")
        )
        or "No analysis polygon is available for this site."
    )
    raise RoiUnavailable(code, message, sources)
