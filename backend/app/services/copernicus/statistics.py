"""Statistical API: ROI-mean index time series, reproducing the GEE charts.

GEE: ui.Chart.image.series(collection.select(INDEX), roi.geometry(),
     ee.Reducer.mean(), scale=1000), no cloud mask, CLOUDY_PIXEL_PERCENTAGE < 100.

Here: ROI polygon in its UTM zone, resx = resy = 1000 m, daily intervals, the
unmasked index evalscript, and the mean of valid pixels. No images are
downloaded. The request is split into calendar years to keep each call small.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from shapely import Geometry
from shapely.geometry import mapping

from app.processing.water_quality.indices import IndexDefinition
from app.processing.water_quality.methodology import (
    CHART_AGGREGATION_INTERVAL,
    CHART_DOWNSAMPLING,
    CHART_SCALE_M,
    HARMONIZE_VALUES,
    SENTINEL_HUB_DATA_TYPE,
)
from app.services.copernicus.catalog import day_start, iso_z
from app.services.copernicus.client import CopernicusClient
from app.services.copernicus.evalscripts import statistics_evalscript
from app.services.copernicus.geometry import epsg_uri, reproject, utm_epsg_for


@dataclass(frozen=True)
class Observation:
    date: date
    mean: float
    min: float | None
    max: float | None
    st_dev: float | None
    valid_pixels: int
    sample_count: int


@dataclass(frozen=True)
class TimeSeries:
    observations: list[Observation]
    # Days returned by Sentinel Hub with no valid pixel in the ROI.
    days_without_valid_pixels: int
    interval_errors: list[str]
    crs_epsg: int


def year_chunks(start: date, end_exclusive: date) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    current = start
    while current < end_exclusive:
        next_year = date(current.year + 1, 1, 1)
        chunk_end = min(next_year, end_exclusive)
        chunks.append((current, chunk_end))
        current = chunk_end
    return chunks


def build_statistics_request(
    index: IndexDefinition,
    roi_lonlat: Geometry,
    start: date,
    end_exclusive: date,
    max_cloud_percent: float,
) -> dict[str, Any]:
    utm = utm_epsg_for(roi_lonlat)
    return {
        "input": {
            "bounds": {
                "geometry": mapping(reproject(roi_lonlat, 4326, utm)),
                "properties": {"crs": epsg_uri(utm)},
            },
            "data": [
                {
                    "type": SENTINEL_HUB_DATA_TYPE,
                    "dataFilter": {"maxCloudCoverage": max_cloud_percent},
                    "processing": {
                        "harmonizeValues": HARMONIZE_VALUES,
                        "downsampling": CHART_DOWNSAMPLING,
                    },
                }
            ],
        },
        "aggregation": {
            "timeRange": {
                "from": iso_z(day_start(start)),
                "to": iso_z(day_start(end_exclusive)),
            },
            "aggregationInterval": {"of": CHART_AGGREGATION_INTERVAL},
            "evalscript": statistics_evalscript(index),
            "resx": CHART_SCALE_M,
            "resy": CHART_SCALE_M,
        },
    }


def fetch_time_series(
    client: CopernicusClient,
    index: IndexDefinition,
    roi_lonlat: Geometry,
    start: date,
    end_exclusive: date,
    max_cloud_percent: float,
) -> TimeSeries:
    observations: dict[date, Observation] = {}
    empty_days = 0
    errors: list[str] = []
    for chunk_start, chunk_end in year_chunks(start, end_exclusive):
        request = build_statistics_request(
            index, roi_lonlat, chunk_start, chunk_end, max_cloud_percent
        )
        body = client.post_json(client.config.COPERNICUS_STATISTICS_URL, request)
        for entry in body.get("data", []):
            parsed = parse_interval(entry)
            if isinstance(parsed, str):
                errors.append(parsed)
            elif parsed is None:
                empty_days += 1
            elif start <= parsed.date < end_exclusive:
                observations[parsed.date] = parsed
    return TimeSeries(
        observations=[observations[d] for d in sorted(observations)],
        days_without_valid_pixels=empty_days,
        interval_errors=errors,
        crs_epsg=utm_epsg_for(roi_lonlat),
    )


def parse_interval(entry: dict[str, Any]) -> Observation | str | None:
    """An Observation, None for a day without valid pixels, or an error message."""
    interval_from = (entry.get("interval") or {}).get("from", "")
    if "error" in entry:
        error = entry["error"]
        message = error.get("message") if isinstance(error, dict) else error
        return f"{interval_from[:10]}: {message}"

    stats = (((entry.get("outputs") or {}).get("index") or {}).get("bands", {}).get("B0", {})).get(
        "stats"
    ) or {}
    sample_count = int(stats.get("sampleCount") or 0)
    valid = sample_count - int(stats.get("noDataCount") or 0)
    mean = _number(stats.get("mean"))
    if valid <= 0 or mean is None:
        return None
    return Observation(
        date=datetime.fromisoformat(interval_from.replace("Z", "+00:00")).date(),
        mean=mean,
        min=_number(stats.get("min")),
        max=_number(stats.get("max")),
        st_dev=_number(stats.get("stDev")),
        valid_pixels=valid,
        sample_count=sample_count,
    )


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number  # NaN
