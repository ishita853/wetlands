"""Water-quality endpoints: the GEE application's index maps and time series,
computed from Copernicus Data Space Sentinel Hub (sentinel-2-l2a)."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.processing.water_quality.indices import INDICES, IndexKey, get_index
from app.processing.water_quality.methodology import (
    DEFAULT_END_EXCLUSIVE,
    DEFAULT_MAX_CLOUD_PERCENT,
    DEFAULT_START,
)
from app.schemas.water_quality import (
    IndexDefinitionRead,
    MapResponse,
    ScenesResponse,
    TimeSeriesResponse,
)
from app.services.copernicus.client import CopernicusClient, get_copernicus_client
from app.services.copernicus.errors import (
    CopernicusAuthError,
    CopernicusInvalidResponse,
    CopernicusNotConfigured,
    CopernicusRateLimited,
    CopernicusRequestError,
    CopernicusUnavailable,
)
from app.services.water_quality import analysis

router = APIRouter(prefix="/water-quality", tags=["water-quality"])

ClientDep = Annotated[CopernicusClient, Depends(get_copernicus_client)]


def analysis_request(
    site_id: int,
    start: Annotated[date, Query(description="First day included (UTC).")] = DEFAULT_START,
    end: Annotated[
        date, Query(description="End date, excluded (as GEE filterDate).")
    ] = DEFAULT_END_EXCLUSIVE,
    max_cloud: Annotated[
        float, Query(gt=0, le=100, description="Tile cloud cover threshold (percent).")
    ] = DEFAULT_MAX_CLOUD_PERCENT,
    roi: Annotated[
        Literal["auto", "provided", "imported", "gee"],
        Query(
            description=(
                "Analysis polygon. auto (default): provided ROI dataset if valid, else an "
                "imported ROI, else a GEE ROI (each with a verified mapping). "
                "provided / imported / gee: that source only."
            )
        ),
    ] = "auto",
) -> analysis.AnalysisRequest:
    if start >= end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_date_range", "message": "start must be before end."},
        )
    return analysis.AnalysisRequest(site_id, start, end, max_cloud, roi)


RequestDep = Annotated[analysis.AnalysisRequest, Depends(analysis_request)]


def _error(code: int, key: str, message: str, **extra: object) -> HTTPException:
    return HTTPException(status_code=code, detail={"code": key, "message": message, **extra})


@contextmanager
def _translate_errors() -> Iterator[None]:
    try:
        yield
    except analysis.WetlandNotFound as exc:
        raise _error(404, "wetland_not_found", str(exc)) from exc
    except analysis.GeometryUnavailable as exc:
        raise _error(409, exc.code, exc.message, roi_sources=exc.sources) from exc
    except analysis.NoScenes as exc:
        raise _error(404, "no_scenes", str(exc)) from exc
    except CopernicusNotConfigured as exc:
        raise _error(503, "copernicus_not_configured", str(exc)) from exc
    except CopernicusAuthError as exc:
        raise _error(502, "copernicus_auth_failed", str(exc)) from exc
    except CopernicusRateLimited as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "copernicus_rate_limited", "message": str(exc)},
            headers={"Retry-After": str(int(exc.retry_after or 30))},
        ) from exc
    except CopernicusRequestError as exc:
        raise _error(
            502, "sentinel_hub_error", exc.message, upstream_status=exc.status_code
        ) from exc
    except CopernicusInvalidResponse as exc:
        raise _error(502, "sentinel_hub_invalid_response", str(exc)) from exc
    except CopernicusUnavailable as exc:
        raise _error(504, "copernicus_unavailable", str(exc)) from exc


@router.get("/indices", response_model=list[IndexDefinitionRead])
def list_indices() -> list[IndexDefinitionRead]:
    return [analysis.index_read(index) for index in INDICES.values()]


@router.get("/{site_id}/scenes", response_model=ScenesResponse)
def list_scenes(client: ClientDep, request: RequestDep) -> ScenesResponse:
    with _translate_errors():
        return analysis.list_scenes(client, request)


@router.get("/{site_id}/{index}/map", response_model=MapResponse)
def get_index_map(index: IndexKey, client: ClientDep, request: RequestDep) -> MapResponse:
    with _translate_errors():
        return analysis.build_map(client, get_index(index), request).response


@router.get(
    "/{site_id}/{index}/map.tif",
    response_class=Response,
    responses={200: {"content": {"image/tiff": {}}}},
)
def get_index_geotiff(index: IndexKey, client: ClientDep, request: RequestDep) -> Response:
    """FLOAT32 GeoTIFF: band 1 index value (NaN = none), band 2 pixel status."""
    with _translate_errors():
        result = analysis.build_map(client, get_index(index), request)
    scene = result.response.traceability.selected_scene
    stamp = scene.acquired_at.strftime("%Y%m%d") if scene else "scene"
    filename = f"ramsar{request.site_id}_{index.value}_{stamp}.tif"
    return Response(
        content=result.geotiff,
        media_type="image/tiff",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # hit: the raster produced for the map request is reused, no new processing.
            "X-Result-Cache": (result.response.traceability.result_cache or {}).get(
                "status", "miss"
            ),
        },
    )


@router.get("/{site_id}/{index}/timeseries", response_model=TimeSeriesResponse)
def get_index_time_series(
    index: IndexKey, client: ClientDep, request: RequestDep
) -> TimeSeriesResponse:
    with _translate_errors():
        return analysis.build_time_series(client, get_index(index), request)
