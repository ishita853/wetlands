from pydantic import BaseModel


class AnalysisGeometryStatus(BaseModel):
    # available | missing | invalid | no_gee_roi
    status: str
    gee_asset_id: str | None = None
    gee_table_index: int | None = None
    mapping: str | None = None
    version: str | None = None
    reason: str | None = None


class OfficialBoundaryStatus(BaseModel):
    # verified | review_required | invalid | missing_authoritative_boundary
    status: str
    source: str | None = None
    version: str | None = None
    reasons: list[str] = []


class GeeRoiStatus(BaseModel):
    # available | missing_export | invalid | not_in_gee_app
    status: str
    asset_reference: str | None = None
    # verified | uncertain
    mapping_status: str | None = None


class ProvidedRoiStatus(BaseModel):
    # available | invalid | missing
    status: str
    version: str | None = None
    reason: str | None = None


class ImportedRoiStatus(BaseModel):
    # available | invalid | missing
    status: str
    source_archive: str | None = None
    # rsis_feature | rsis_feature_repaired_by_supplier | supplied_shapefile
    origin: str | None = None
    # verified | uncertain
    mapping_status: str | None = None
    version: str | None = None
    reason: str | None = None


class AnalysisModeStatus(BaseModel):
    # available | unavailable
    status: str
    source: str | None = None
    reason: str | None = None


class BoundarySummary(BaseModel):
    official_boundary: OfficialBoundaryStatus
    provided_roi: ProvidedRoiStatus
    imported_roi: ImportedRoiStatus
    gee_roi: GeeRoiStatus
    # The polygon water-quality analysis uses (resolver policy, roi=auto).
    water_quality_analysis: AnalysisModeStatus
    # Water-quality reproduction of the GEE app (GEE ROI with a verified mapping only).
    gee_comparison: AnalysisModeStatus
    # Official spatial explorer (RSIS boundary with status "verified" only).
    official_explorer: AnalysisModeStatus


class WetlandRead(BaseModel):
    ramsar_site_id: int
    name: str
    state: str | None = None
    district: str | None = None
    # WGS84 point locating the site (not analysis geometry).
    latitude: float | None = None
    longitude: float | None = None
    designation_year: int | None = None
    area_ha: float | None = None
    analysis_geometry: AnalysisGeometryStatus
    boundaries: BoundarySummary


class WetlandDetail(WetlandRead):
    summary: str | None = None
