from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class LegendEntryRead(BaseModel):
    label: str
    color: str


class IndexDefinitionRead(BaseModel):
    key: str
    name: str
    formula: str
    band_a: str
    band_b: str
    gee_expression: str
    vis_min: float
    vis_max: float
    palette: list[str]
    gee_palette: list[str]
    legend: list[LegendEntryRead]


class SceneRead(BaseModel):
    id: str
    acquired_at: datetime
    cloud_cover: float | None
    tile_id: str | None
    platform: str | None
    processing_baseline: str | None
    roi_coverage: float


class ProcessingDifferenceRead(BaseModel):
    code: str
    summary: str


class WetlandRef(BaseModel):
    ramsar_site_id: int
    name: str


class RoiTrace(BaseModel):
    # provided_roi | imported_roi | gee_roi
    source: str
    provenance: str
    source_ids: dict[str, Any] = {}
    gee_asset_id: str | None = None
    gee_table_index: int | None = None
    mapping_status: str | None = None
    file: str
    version: str
    geometry_sha256: str | None = None
    area_ha: float
    feature_count: int
    crs: str


class IndexTrace(BaseModel):
    key: str
    formula: str
    band_a: str
    band_b: str
    gee_expression: str


class DateRange(BaseModel):
    start: date
    end_exclusive: date


class CloudFilter(BaseModel):
    property: str
    rule: str
    applied_by: str


class SpatialTrace(BaseModel):
    request_crs: str
    resolution_m: float
    aggregation: str


class Traceability(BaseModel):
    wetland: WetlandRef
    roi: RoiTrace
    index: IndexTrace
    reference_collection: str
    sentinel_hub_data_type: str
    sentinel_hub_api: str
    input_processing: dict[str, str | bool]
    date_range: DateRange
    cloud_filter: CloudFilter
    cloud_handling: str
    selected_scene: SceneRead | None = None
    spatial: SpatialTrace
    processing_differences: list[ProcessingDifferenceRead]
    warnings: list[str]
    generated_at: datetime
    # {"status": "hit" | "miss", "backend": "redis" | "memory" | "off"}
    result_cache: dict[str, str] | None = None


class LonLatBounds(BaseModel):
    west: float
    south: float
    east: float
    north: float


class MapImage(BaseModel):
    media_type: str
    data_uri: str
    width: int
    height: int
    raster_crs: str
    bounds: LonLatBounds
    # Corners as [lon, lat]: top-left, top-right, bottom-right, bottom-left
    # (the order a MapLibre image source expects).
    coordinates: list[list[float]]


class PixelCounts(BaseModel):
    valid: int
    cloud_masked: int
    undefined_index: int
    no_data_or_outside_roi: int


class ValueSummary(BaseModel):
    min: float | None
    max: float | None
    mean: float | None


class ScenesResponse(BaseModel):
    wetland: WetlandRef
    date_range: DateRange
    max_cloud_percent: float
    selection_rule: str
    scenes: list[SceneRead]
    selected_scene: SceneRead | None


class MapResponse(BaseModel):
    wetland: WetlandRef
    index: IndexDefinitionRead
    image: MapImage
    pixel_counts: PixelCounts
    value_summary: ValueSummary
    traceability: Traceability


class TimeSeriesPoint(BaseModel):
    date: date
    mean: float
    min: float | None
    max: float | None
    st_dev: float | None
    valid_pixels: int
    sample_count: int
    # Catalog records of the Sentinel-2 tiles acquired that day (same UTC date).
    scenes: list[SceneRead] = []


class TimeSeriesResponse(BaseModel):
    wetland: WetlandRef
    index: IndexDefinitionRead
    points: list[TimeSeriesPoint]
    days_without_valid_pixels: int
    traceability: Traceability
