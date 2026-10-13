/**
 * Response shapes of the FastAPI water-quality and wetland endpoints
 * (backend/app/schemas/water_quality.py, backend/app/schemas/wetland.py).
 * The backend is the source of truth for formulas, palettes and legends.
 */

export type IndexKey = "NDCI" | "NDTI" | "NDWI" | "NDMI";

export interface LegendEntry {
  label: string;
  color: string;
}

export interface IndexDefinition {
  key: IndexKey;
  name: string;
  formula: string;
  band_a: string;
  band_b: string;
  gee_expression: string;
  vis_min: number;
  vis_max: number;
  palette: string[];
  gee_palette: string[];
  legend: LegendEntry[];
}

export interface SceneInfo {
  id: string;
  acquired_at: string;
  cloud_cover: number | null;
  tile_id: string | null;
  platform: string | null;
  processing_baseline: string | null;
  roi_coverage: number;
}

export interface Traceability {
  wetland: { ramsar_site_id: number; name: string };
  roi: {
    source: string;
    provenance: string;
    source_ids: Record<string, unknown>;
    gee_asset_id: string | null;
    file: string;
    version: string;
    geometry_sha256: string | null;
    area_ha: number;
    feature_count: number;
    crs: string;
  };
  index: { key: string; formula: string; band_a: string; band_b: string; gee_expression: string };
  reference_collection: string;
  sentinel_hub_data_type: string;
  sentinel_hub_api: string;
  input_processing: Record<string, string | boolean>;
  date_range: { start: string; end_exclusive: string };
  cloud_filter: { property: string; rule: string; applied_by: string };
  cloud_handling: string;
  selected_scene: SceneInfo | null;
  spatial: { request_crs: string; resolution_m: number; aggregation: string };
  processing_differences: { code: string; summary: string }[];
  warnings: string[];
  generated_at: string;
  /** Whether this result was computed now ("miss") or reused from the result cache ("hit"). */
  result_cache: { status: "hit" | "miss"; backend: string } | null;
}

export interface MapResponse {
  wetland: { ramsar_site_id: number; name: string };
  index: IndexDefinition;
  image: {
    media_type: string;
    data_uri: string;
    width: number;
    height: number;
    raster_crs: string;
    bounds: { west: number; south: number; east: number; north: number };
    /** [lon, lat] corners: top-left, top-right, bottom-right, bottom-left. */
    coordinates: [number, number][];
  };
  pixel_counts: {
    valid: number;
    cloud_masked: number;
    undefined_index: number;
    no_data_or_outside_roi: number;
  };
  value_summary: { min: number | null; max: number | null; mean: number | null };
  traceability: Traceability;
}

export interface TimeSeriesPoint {
  date: string;
  mean: number;
  min: number | null;
  max: number | null;
  st_dev: number | null;
  valid_pixels: number;
  sample_count: number;
  /** Catalog records of the Sentinel-2 tiles acquired that UTC day. */
  scenes: SceneInfo[];
}

export interface TimeSeriesResponse {
  wetland: { ramsar_site_id: number; name: string };
  index: IndexDefinition;
  points: TimeSeriesPoint[];
  days_without_valid_pixels: number;
  traceability: Traceability;
}

/** Backend `boundaries` summary on /wetlands (analysis availability and why). */
export interface BoundarySummary {
  official_boundary: {
    status: string;
    source: string | null;
    version: string | null;
    reasons: string[];
  };
  provided_roi: { status: string; version: string | null; reason: string | null };
  gee_roi: { status: string; asset_reference: string | null; mapping_status: string | null };
  water_quality_analysis: { status: string; source: string | null; reason: string | null };
  gee_comparison: { status: string; source: string | null; reason: string | null };
  official_explorer: { status: string; source: string | null; reason: string | null };
}

export interface BackendWetland {
  ramsar_site_id: number;
  name: string;
  state: string | null;
  latitude: number | null;
  longitude: number | null;
  designation_year: number | null;
  area_ha: number | null;
  boundaries: BoundarySummary;
}

export type AvailabilityStatus =
  "available" | "boundary_unavailable" | "geometry_invalid" | "unknown";

/** One Ramsar site as shown in the Water Quality module (master list + backend status). */
export interface WaterQualitySite {
  id: number;
  name: string;
  state: string;
  district: string;
  designationYear: number;
  areaHa: number;
  latitude: number;
  longitude: number;
  availability: AvailabilityStatus;
  /** Backend label of the polygon used for analysis, e.g. "provided_roi". */
  analysisSource: string | null;
  /** Backend explanation when analysis is unavailable (technical detail). */
  reason: string | null;
  officialBoundaryStatus: string | null;
}

export interface RoiFeature {
  type: "Feature";
  geometry: GeoJSON.Geometry;
  properties: {
    source: string;
    provenance: string;
    version: string;
    crs: string;
    area_ha: number;
    boundary_status: string;
  };
}
