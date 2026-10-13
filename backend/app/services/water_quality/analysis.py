"""Water-quality analysis: the GEE map and chart workflows on Sentinel Hub.

wetland -> GEE ROI polygon -> Catalog (scene selection) -> Process API (map)
                           -> Statistical API (time series)

Every response carries a traceability block: wetland, ROI version, index and
formula, reference collection, Sentinel Hub data type, date range, cloud rule,
selected scene, spatial resolution/aggregation, known processing differences
and warnings. Nothing here returns values that did not come from Sentinel Hub.
"""

import base64
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal

from rasterio.errors import RasterioError

from app.core.config import settings
from app.processing.water_quality import methodology
from app.processing.water_quality.indices import IndexDefinition
from app.processing.water_quality.methodology import (
    CHART_DOWNSAMPLING,
    CHART_REDUCER,
    CHART_SCALE_M,
    HARMONIZE_VALUES,
    INPUT_UNITS,
    MAP_CLOUD_MASK_SCL_CLASSES,
    REFERENCE_COLLECTION,
    SENTINEL_HUB_DATA_TYPE,
    differences_for,
)
from app.processing.water_quality.raster import colorize, encode_png, read_index_geotiff
from app.schemas.water_quality import (
    CloudFilter,
    DateRange,
    IndexDefinitionRead,
    IndexTrace,
    LegendEntryRead,
    LonLatBounds,
    MapImage,
    MapResponse,
    PixelCounts,
    ProcessingDifferenceRead,
    RoiTrace,
    SceneRead,
    ScenesResponse,
    SpatialTrace,
    TimeSeriesPoint,
    TimeSeriesResponse,
    Traceability,
    ValueSummary,
    WetlandRef,
)
from app.services.copernicus import catalog, process, statistics
from app.services.copernicus.client import CopernicusClient
from app.services.copernicus.errors import CopernicusError, CopernicusInvalidResponse
from app.services.copernicus.evalscripts import map_evalscript, statistics_evalscript
from app.services.copernicus.geometry import WEB_MERCATOR_EPSG, epsg_uri, to_lonlat
from app.services.result_cache import cache_key, get_result_cache
from app.services.wetlands.boundaries import point_distance_m
from app.services.wetlands.resolver import (
    ResolvedRoi,
    RoiSource,
    RoiUnavailable,
    resolve_analysis_roi,
)
from app.services.wetlands.sites import RamsarSite, get_site

SELECTION_RULE = (
    "Least tile-level cloud cover (eo:cloud_cover < max_cloud_percent) among Sentinel-2 L2A "
    "tiles intersecting the ROI in [start, end_exclusive); ties go to the earliest acquisition. "
    "Reproduces GEE .sort('CLOUDY_PIXEL_PERCENTAGE', true).first()."
)
_SMALL_ROI_HA = 100.0  # one 1000 m x 1000 m pixel


class WetlandNotFound(Exception):
    pass


# Raised when no analysis polygon is available (re-exported for the routes).
GeometryUnavailable = RoiUnavailable


class NoScenes(Exception):
    pass


@dataclass(frozen=True)
class AnalysisRequest:
    site_id: int
    start: date
    end_exclusive: date
    max_cloud_percent: float
    roi_source: RoiSource = "auto"


@dataclass(frozen=True)
class MapResult:
    response: MapResponse
    geotiff: bytes


def _method_fingerprint(kind: Literal["map", "timeseries"], index: IndexDefinition) -> str:
    """Hash of everything in the processing method that affects a result."""
    constants = {
        name: getattr(methodology, name)
        for name in dir(methodology)
        if name.isupper() and not name.startswith("_")
    }
    script = map_evalscript(index) if kind == "map" else statistics_evalscript(index)
    payload = json.dumps({"constants": constants, "evalscript": script}, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _result_key(
    kind: Literal["map", "timeseries"],
    index: IndexDefinition,
    request: AnalysisRequest,
    roi: ResolvedRoi,
) -> str:
    return cache_key(
        kind,
        {
            "site": request.site_id,
            "index": index.key.value,
            "start": request.start.isoformat(),
            "end_exclusive": request.end_exclusive.isoformat(),
            "max_cloud_percent": request.max_cloud_percent,
            "roi_source": roi.source,
            "roi_version": roi.version,
            "roi_geometry_sha256": roi.geometry_sha256 or roi.version,
            "method": _method_fingerprint(kind, index),
        },
    )


def _cache_status(status: Literal["hit", "miss"]) -> dict[str, str]:
    return {"status": status, "backend": get_result_cache().backend}


def index_read(index: IndexDefinition) -> IndexDefinitionRead:
    return IndexDefinitionRead(
        key=index.key.value,
        name=index.name,
        formula=index.formula,
        band_a=index.band_a,
        band_b=index.band_b,
        gee_expression=index.gee_expression,
        vis_min=index.vis_min,
        vis_max=index.vis_max,
        palette=list(index.palette),
        gee_palette=list(index.gee_palette),
        legend=[LegendEntryRead(label=e.label, color=e.color) for e in index.legend],
    )


def _resolve(site_id: int, roi_source: RoiSource = "auto") -> tuple[RamsarSite, ResolvedRoi]:
    """The site and its analysis polygon (app.services.wetlands.resolver policy).

    Never a geometry derived from coordinates; raises RoiUnavailable instead.
    """
    site = get_site(site_id)
    if site is None:
        raise WetlandNotFound(f"No Ramsar site with number {site_id}.")
    return site, resolve_analysis_roi(site_id, roi_source)


def _scene_read(scene: catalog.Scene) -> SceneRead:
    return SceneRead(
        id=scene.id,
        acquired_at=scene.acquired_at,
        cloud_cover=scene.cloud_cover,
        tile_id=scene.tile_id,
        platform=scene.platform,
        processing_baseline=scene.processing_baseline,
        roi_coverage=scene.roi_coverage,
    )


def _geometry_warnings(site: RamsarSite, roi: ResolvedRoi) -> list[str]:
    warnings: list[str] = []
    if site.latitude is not None and site.longitude is not None:
        distance = point_distance_m(roi.geometry, site.latitude, site.longitude)
        if distance > 0:
            warnings.append(
                f"The RSIS site coordinate lies {distance:,.0f} m outside the ROI polygon."
            )
    return warnings


def _traceability(
    kind: Literal["map", "timeseries"],
    site: RamsarSite,
    roi: ResolvedRoi,
    index: IndexDefinition,
    request: AnalysisRequest,
    spatial: SpatialTrace,
    warnings: list[str],
    selected: catalog.Scene | None = None,
) -> Traceability:
    if kind == "map":
        api = "Catalog API (scene selection) + Process API"
        cloud_filter = CloudFilter(
            property="eo:cloud_cover (tile level)",
            rule=f"< {request.max_cloud_percent:g} (strict, as GEE)",
            applied_by="Catalog API scene selection",
        )
        cloud_handling = (
            f"Sentinel-2 SCL classes {', '.join(map(str, MAP_CLOUD_MASK_SCL_CLASSES))} masked "
            "(cloud medium probability, cloud high probability, thin cirrus). Migration "
            "substitute for the GEE QA60 bits 10/11 mask; not identical to QA60."
        )
    else:
        api = "Statistical API (+ Catalog API for scene metadata)"
        cloud_filter = CloudFilter(
            property="tile cloud cover (maxCloudCoverage)",
            rule=f"<= {request.max_cloud_percent:g} (Sentinel Hub filter is inclusive)",
            applied_by="Statistical API dataFilter",
        )
        cloud_handling = "No cloud mask, as in the GEE charts."
    return Traceability(
        wetland=WetlandRef(ramsar_site_id=site.id, name=site.name),
        roi=RoiTrace(
            source=roi.source,
            provenance=roi.provenance,
            source_ids=roi.source_ids,
            gee_asset_id=roi.gee_entry.gee_asset_id if roi.gee_entry else None,
            gee_table_index=roi.gee_entry.gee_table_index if roi.gee_entry else None,
            mapping_status=roi.mapping,
            file=roi.file,
            version=roi.version,
            geometry_sha256=roi.geometry_sha256,
            area_ha=roi.area_ha,
            feature_count=roi.feature_count,
            crs="EPSG:4326 (WGS84 longitude/latitude); reprojected only inside requests",
        ),
        index=IndexTrace(
            key=index.key.value,
            formula=index.formula,
            band_a=index.band_a,
            band_b=index.band_b,
            gee_expression=index.gee_expression,
        ),
        reference_collection=REFERENCE_COLLECTION,
        sentinel_hub_data_type=SENTINEL_HUB_DATA_TYPE,
        sentinel_hub_api=api,
        input_processing={"harmonize_values": HARMONIZE_VALUES, "units": INPUT_UNITS},
        date_range=DateRange(start=request.start, end_exclusive=request.end_exclusive),
        cloud_filter=cloud_filter,
        cloud_handling=cloud_handling,
        selected_scene=_scene_read(selected) if selected else None,
        spatial=spatial,
        processing_differences=[
            ProcessingDifferenceRead(code=d.code, summary=d.summary) for d in differences_for(kind)
        ],
        warnings=warnings,
        generated_at=datetime.now(UTC),
    )


def list_scenes(client: CopernicusClient, request: AnalysisRequest) -> ScenesResponse:
    site, roi = _resolve(request.site_id, request.roi_source)
    scenes = catalog.search_scenes(client, roi.geometry, request.start, request.end_exclusive)
    selected = catalog.select_least_cloudy(scenes, request.max_cloud_percent)
    return ScenesResponse(
        wetland=WetlandRef(ramsar_site_id=site.id, name=site.name),
        date_range=DateRange(start=request.start, end_exclusive=request.end_exclusive),
        max_cloud_percent=request.max_cloud_percent,
        selection_rule=SELECTION_RULE,
        scenes=[_scene_read(s) for s in scenes],
        selected_scene=_scene_read(selected) if selected else None,
    )


def build_map(
    client: CopernicusClient, index: IndexDefinition, request: AnalysisRequest
) -> MapResult:
    site, roi = _resolve(request.site_id, request.roi_source)
    cache = get_result_cache()
    key = _result_key("map", index, request, roi)
    cached_json, cached_tif = cache.get(key + ":json"), cache.get(key + ":tif")
    if cached_json is not None and cached_tif is not None:
        cached = MapResponse.model_validate_json(cached_json)
        cached.traceability.result_cache = _cache_status("hit")
        return MapResult(response=cached, geotiff=cached_tif)

    scenes = catalog.search_scenes(client, roi.geometry, request.start, request.end_exclusive)
    selected = catalog.select_least_cloudy(scenes, request.max_cloud_percent)
    if selected is None:
        raise NoScenes(
            f"No Sentinel-2 L2A scene with cloud cover < {request.max_cloud_percent:g}% "
            f"intersects the ROI between {request.start} and {request.end_exclusive} (exclusive)."
        )

    grid = process.raster_grid(roi.geometry)
    geotiff = process.fetch_index_geotiff(
        client, process.build_map_request(index, roi.geometry, selected.acquired_at, grid)
    )
    try:
        raster = read_index_geotiff(geotiff)
    except (RasterioError, ValueError) as exc:
        raise CopernicusInvalidResponse(
            "The Process API response is not the expected 2-band GeoTIFF."
        ) from exc
    counts = raster.pixel_counts()

    warnings = _geometry_warnings(site, roi)
    warnings.append(
        "GEE reference behaviour for scenes dated 2022-01-25 to 2024-02-28 (QA60 masked in "
        "COPERNICUS/S2_SR_HARMONIZED) is still being validated; this map applies the SCL "
        "substitute for every date."
    )
    if selected.roi_coverage < 0.999:
        warnings.append(
            f"The selected tile covers {selected.roi_coverage:.0%} of the ROI. GEE would show "
            "only that tile; Sentinel Hub also fills in other tiles of the same acquisition."
        )
    if counts["valid"] == 0:
        warnings.append("No valid index pixels in the ROI for the selected acquisition.")

    raster_epsg = raster.epsg or WEB_MERCATOR_EPSG
    west, south, east, north = raster.bounds
    top_left = to_lonlat(west, north, raster_epsg)
    top_right = to_lonlat(east, north, raster_epsg)
    bottom_right = to_lonlat(east, south, raster_epsg)
    bottom_left = to_lonlat(west, south, raster_epsg)
    png = encode_png(colorize(raster.values, index))
    height, width = raster.values.shape

    response = MapResponse(
        wetland=WetlandRef(ramsar_site_id=site.id, name=site.name),
        index=index_read(index),
        image=MapImage(
            media_type="image/png",
            data_uri="data:image/png;base64," + base64.b64encode(png).decode("ascii"),
            width=width,
            height=height,
            raster_crs=epsg_uri(raster_epsg),
            bounds=LonLatBounds(
                west=bottom_left[0], south=bottom_left[1], east=top_right[0], north=top_right[1]
            ),
            coordinates=[list(top_left), list(top_right), list(bottom_right), list(bottom_left)],
        ),
        pixel_counts=PixelCounts(
            valid=counts["valid"],
            cloud_masked=counts["cloudMasked"],
            undefined_index=counts["undefinedIndex"],
            no_data_or_outside_roi=counts["noDataOrOutsideRoi"],
        ),
        value_summary=ValueSummary(**raster.value_summary()),
        traceability=_traceability(
            "map",
            site,
            roi,
            index,
            request,
            SpatialTrace(
                request_crs=epsg_uri(raster_epsg),
                resolution_m=grid.ground_resolution_m,
                aggregation="none (per-pixel index of the selected acquisition)",
            ),
            warnings,
            selected,
        ),
    )
    ttl = settings.RESULT_CACHE_TTL_MAP_SECONDS
    cache.set(key + ":tif", geotiff, ttl)
    cache.set(key + ":json", response.model_dump_json().encode("utf-8"), ttl)
    response.traceability.result_cache = _cache_status("miss")
    return MapResult(response=response, geotiff=geotiff)


def build_time_series(
    client: CopernicusClient, index: IndexDefinition, request: AnalysisRequest
) -> TimeSeriesResponse:
    site, roi = _resolve(request.site_id, request.roi_source)
    cache = get_result_cache()
    key = _result_key("timeseries", index, request, roi)
    cached_json = cache.get(key)
    if cached_json is not None:
        cached = TimeSeriesResponse.model_validate_json(cached_json)
        cached.traceability.result_cache = _cache_status("hit")
        return cached

    # Statistics and scene metadata are independent requests: run them together.
    with ThreadPoolExecutor(max_workers=2) as pool:
        series_future = pool.submit(
            statistics.fetch_time_series,
            client,
            index,
            roi.geometry,
            request.start,
            request.end_exclusive,
            request.max_cloud_percent,
        )
        scenes_future = pool.submit(
            catalog.search_scenes, client, roi.geometry, request.start, request.end_exclusive
        )
        series = series_future.result()
        scene_error: str | None = None
        try:
            scenes = scenes_future.result()
        except CopernicusError as exc:
            scenes, scene_error = [], str(exc)
    # Tiles the statistics could include: Sentinel Hub maxCloudCoverage is inclusive.
    by_day: dict[date, list[SceneRead]] = {}
    for scene in scenes:
        if scene.cloud_cover is None or scene.cloud_cover <= request.max_cloud_percent:
            by_day.setdefault(scene.acquired_at.date(), []).append(_scene_read(scene))
    warnings = _geometry_warnings(site, roi)
    if scene_error:
        warnings.append(
            f"Scene metadata could not be retrieved from the Catalog API: {scene_error}"
        )
    else:
        unmatched = sum(1 for o in series.observations if o.date not in by_day)
        if unmatched:
            warnings.append(
                f"{unmatched} observation day(s) have no matching Catalog scene record."
            )
    if roi.area_ha < _SMALL_ROI_HA:
        warnings.append(
            f"The ROI ({roi.area_ha:g} ha) is smaller than one 1000 m pixel; the 1000 m mean "
            "is dominated by surroundings and may differ strongly from GEE (difference X3)."
        )
    warnings.extend(f"Sentinel Hub interval error — {e}" for e in series.interval_errors)
    if not series.observations:
        warnings.append("Sentinel Hub returned no valid observations for this ROI and period.")

    response = TimeSeriesResponse(
        wetland=WetlandRef(ramsar_site_id=site.id, name=site.name),
        index=index_read(index),
        points=[
            TimeSeriesPoint(
                date=o.date,
                mean=o.mean,
                min=o.min,
                max=o.max,
                st_dev=o.st_dev,
                valid_pixels=o.valid_pixels,
                sample_count=o.sample_count,
                scenes=by_day.get(o.date, []),
            )
            for o in series.observations
        ],
        days_without_valid_pixels=series.days_without_valid_pixels,
        traceability=_traceability(
            "timeseries",
            site,
            roi,
            index,
            request,
            SpatialTrace(
                request_crs=epsg_uri(series.crs_epsg),
                resolution_m=CHART_SCALE_M,
                aggregation=(
                    f"{CHART_REDUCER} of valid pixels in the ROI per day; "
                    f"{CHART_DOWNSAMPLING} downsampling to {CHART_SCALE_M:g} m"
                ),
            ),
            warnings,
        ),
    )
    cache.set(
        key,
        response.model_dump_json().encode("utf-8"),
        settings.RESULT_CACHE_TTL_TIMESERIES_SECONDS,
    )
    response.traceability.result_cache = _cache_status("miss")
    return response
