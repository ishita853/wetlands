from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from shapely.geometry import mapping

from app.schemas.wetland import (
    AnalysisGeometryStatus,
    AnalysisModeStatus,
    BoundarySummary,
    GeeRoiStatus,
    ImportedRoiStatus,
    OfficialBoundaryStatus,
    ProvidedRoiStatus,
    WetlandDetail,
    WetlandRead,
)
from app.services.wetlands.boundaries import load_boundary_manifest, official_boundary
from app.services.wetlands.imported import lookup_imported
from app.services.wetlands.provided import lookup_provided
from app.services.wetlands.resolver import ResolvedRoi, RoiUnavailable, resolve_analysis_roi
from app.services.wetlands.roi import RoiLookup, lookup_roi
from app.services.wetlands.sites import RamsarSite, get_site, load_sites

router = APIRouter(prefix="/wetlands", tags=["wetlands"])

_GEE_STATUS = {
    "available": "available",
    "missing": "missing_export",
    "invalid": "invalid",
    "no_gee_roi": "not_in_gee_app",
}


def _geometry_status(lookup: RoiLookup) -> AnalysisGeometryStatus:
    entry = lookup.entry
    return AnalysisGeometryStatus(
        status=lookup.status,
        gee_asset_id=entry.gee_asset_id if entry else None,
        gee_table_index=entry.gee_table_index if entry else None,
        mapping=entry.mapping if entry else None,
        version=lookup.roi.version if lookup.roi else None,
        reason=lookup.reason,
    )


def _mapping_status(lookup: RoiLookup) -> str | None:
    if lookup.entry is None:
        return None
    return "uncertain" if lookup.entry.mapping == "manual_uncertain" else "verified"


def _boundaries(site_id: int, lookup: RoiLookup) -> BoundarySummary:
    record = (load_boundary_manifest().get(site_id) or {}).get("official_boundary") or {}
    official = OfficialBoundaryStatus(
        status=record.get("status", "missing_authoritative_boundary"),
        source=record.get("source"),
        version=record.get("version"),
        reasons=record.get("reasons") or ([record["reason"]] if record.get("reason") else []),
    )
    mapping_status = _mapping_status(lookup)
    if lookup.roi is not None and mapping_status == "verified":
        gee_mode = AnalysisModeStatus(status="available", source="gee_roi")
    elif lookup.roi is not None:
        gee_mode = AnalysisModeStatus(
            status="unavailable", reason="GEE ROI present but its Ramsar mapping is uncertain."
        )
    else:
        gee_mode = AnalysisModeStatus(status="unavailable", reason=lookup.reason)
    if official.status == "verified":
        official_mode = AnalysisModeStatus(status="available", source="official_boundary")
    else:
        official_mode = AnalysisModeStatus(
            status="unavailable", reason=f"Official boundary status: {official.status}."
        )
    provided = lookup_provided(site_id)
    imported = lookup_imported(site_id)
    try:
        resolved = resolve_analysis_roi(site_id)
        water_quality = AnalysisModeStatus(status="available", source=resolved.source)
    except RoiUnavailable as exc:
        water_quality = AnalysisModeStatus(status="unavailable", reason=exc.message)
    return BoundarySummary(
        official_boundary=official,
        provided_roi=ProvidedRoiStatus(
            status=provided.status, version=provided.version, reason=provided.reason
        ),
        imported_roi=ImportedRoiStatus(
            status=imported.status,
            source_archive=imported.entry.source_archive if imported.entry else None,
            origin=imported.entry.origin if imported.entry else None,
            mapping_status=(
                ("uncertain" if imported.entry.mapping == "manual_uncertain" else "verified")
                if imported.entry
                else None
            ),
            version=imported.version,
            reason=imported.reason,
        ),
        water_quality_analysis=water_quality,
        gee_roi=GeeRoiStatus(
            status=_GEE_STATUS[lookup.status],
            asset_reference=lookup.entry.gee_asset_id if lookup.entry else None,
            mapping_status=mapping_status,
        ),
        gee_comparison=gee_mode,
        official_explorer=official_mode,
    )


def _read(site: RamsarSite) -> dict[str, Any]:
    lookup = lookup_roi(site.id)
    return {
        "ramsar_site_id": site.id,
        "name": site.name,
        "state": site.state,
        "district": site.district,
        "latitude": site.latitude,
        "longitude": site.longitude,
        "designation_year": site.designation_year,
        "area_ha": site.area_ha,
        "analysis_geometry": _geometry_status(lookup),
        "boundaries": _boundaries(site.id, lookup),
    }


def _site_or_404(site_id: int) -> RamsarSite:
    site = get_site(site_id)
    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "wetland_not_found", "message": f"No Ramsar site {site_id}."},
        )
    return site


@router.get("", response_model=list[WetlandRead])
def list_wetlands() -> list[WetlandRead]:
    sites = sorted(load_sites().values(), key=lambda s: s.name.lower())
    return [WetlandRead(**_read(site)) for site in sites]


@router.get("/{site_id}", response_model=WetlandDetail)
def get_wetland(site_id: int) -> WetlandDetail:
    site = _site_or_404(site_id)
    return WetlandDetail(**_read(site), summary=site.summary)


def _gee_roi_feature(site_id: int) -> dict[str, Any]:
    lookup = lookup_roi(site_id)
    if lookup.roi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": f"roi_{lookup.status}",
                "message": lookup.reason,
                "analysis_geometry": _geometry_status(lookup).model_dump(),
            },
        )
    roi = lookup.roi
    mapping_status = _mapping_status(lookup)
    return {
        "type": "Feature",
        "geometry": mapping(roi.geometry),
        "properties": {
            "ramsar_site_id": site_id,
            "source": "gee_roi",
            "provenance": "existing GEE application ROI (not an official Ramsar boundary)",
            "is_official": False,
            "gee_asset_id": roi.entry.gee_asset_id,
            "gee_table_index": roi.entry.gee_table_index,
            "mapping": roi.entry.mapping,
            "mapping_status": mapping_status,
            "crs": "EPSG:4326",
            "version": roi.version,
            "boundary_status": "available",
            "area_ha": roi.area_ha,
            "usable_for_water_quality_analysis": mapping_status == "verified",
            "usable_for_official_explorer": False,
        },
    }


def _official_feature(site_id: int) -> dict[str, Any]:
    boundary = official_boundary(site_id)
    record = boundary.record
    if boundary.geometry is None or boundary.status == "invalid":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": f"official_boundary_{boundary.status}",
                "message": (
                    "The published official boundary failed validation and is not served."
                    if boundary.status == "invalid"
                    else "No official Ramsar boundary is published for this site; "
                    "it must be requested from MoEFCC (Wetlands Division)."
                ),
                "reasons": record.get("reasons") or [],
            },
        )
    return {
        "type": "Feature",
        "geometry": mapping(boundary.geometry),
        "properties": {
            "ramsar_site_id": site_id,
            "source": "official_boundary",
            "provenance": "Ramsar Sites Information Service (RSIS), ramsar_sdi:features_published",
            "is_official": True,
            "official_name": record.get("official_name"),
            "source_ids": record.get("source_ids"),
            "area_off_ha": record.get("area_off_ha"),
            "crs": "EPSG:4326",
            "version": record.get("version"),
            "geometry_sha256": record.get("geometry_sha256"),
            "raw_sha256": record.get("raw_sha256"),
            "retrieved_at": record.get("retrieved_at"),
            "boundary_status": boundary.status,
            "reasons": record.get("reasons") or [],
            "usable_for_water_quality_analysis": False,
            "usable_for_official_explorer": boundary.status == "verified",
        },
    }


def _resolved_feature(roi: ResolvedRoi, boundary_status: str) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": mapping(roi.geometry),
        "properties": {
            "ramsar_site_id": roi.site_id,
            "source": roi.source,
            "provenance": roi.provenance,
            "is_official": False,
            "source_ids": roi.source_ids,
            "gee_asset_id": roi.gee_entry.gee_asset_id if roi.gee_entry else None,
            "gee_table_index": roi.gee_entry.gee_table_index if roi.gee_entry else None,
            "mapping": roi.mapping,
            "crs": "EPSG:4326",
            "version": roi.version,
            "geometry_sha256": roi.geometry_sha256,
            "boundary_status": boundary_status,
            "area_ha": roi.area_ha,
            "usable_for_water_quality_analysis": True,
            "usable_for_official_explorer": False,
        },
    }


def _analysis_feature(
    site_id: int, source: Literal["auto", "provided", "imported"]
) -> dict[str, Any]:
    try:
        roi = resolve_analysis_roi(site_id, source)
    except RoiUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message, "roi_sources": exc.sources},
        ) from exc
    return _resolved_feature(roi, "available")


@router.get("/{site_id}/roi")
def get_wetland_roi(
    site_id: int,
    source: Annotated[
        Literal["analysis", "provided", "imported", "gee", "official"],
        Query(
            description=(
                "analysis (default): the polygon water-quality analysis uses; provided: the "
                "provided ROI dataset; imported: the team-supplied ROI shapefile; gee: the GEE "
                "application ROI; official: the RSIS Ramsar boundary."
            )
        ),
    ] = "analysis",
) -> dict[str, Any]:
    """A boundary as a GeoJSON Feature ([lon, lat], EPSG:4326) with its provenance."""
    _site_or_404(site_id)
    if source == "analysis":
        return _analysis_feature(site_id, "auto")
    if source in ("provided", "imported"):
        return _analysis_feature(site_id, source)
    return _gee_roi_feature(site_id) if source == "gee" else _official_feature(site_id)
