"""Methodology constants for reproducing the GEE application on Sentinel Hub.

The GEE collection `COPERNICUS/S2_SR_HARMONIZED` is the scientific reference.
Sentinel Hub `sentinel-2-l2a` is the closest available source, but it is not
identical; every known difference is listed in PROCESSING_DIFFERENCES and is
returned with each analysis (docs/gee-functional-specification.md §2.2).
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

REFERENCE_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
SENTINEL_HUB_DATA_TYPE = "sentinel-2-l2a"

# GEE: .filterDate('2022-11-01', '2026-05-30') — the end date is exclusive.
DEFAULT_START = date(2022, 11, 1)
DEFAULT_END_EXCLUSIVE = date(2026, 5, 30)

# GEE: CLOUDY_PIXEL_PERCENTAGE < 100 (strictly less than), tile-level metadata.
DEFAULT_MAX_CLOUD_PERCENT = 100.0

# Sentinel Hub input processing. harmonizeValues=true removes the processing
# baseline 04.00 BOA_ADD_OFFSET like the HARMONIZED collection does; DN units
# keep GEE's SR x 10000 encoding (the scale cancels in a normalized difference).
HARMONIZE_VALUES = True
INPUT_UNITS = "DN"

# Map: migration substitute for the GEE QA60 bits 10/11 mask. Sen2Cor scene
# classes 8 (cloud medium probability), 9 (cloud high probability), 10 (thin
# cirrus). Not identical to QA60, which Sentinel Hub does not provide.
MAP_CLOUD_MASK_SCL_CLASSES = (8, 9, 10)

# Map: target ground resolution (native for B03/B04/B08) and the largest
# raster side requested from the Process API.
MAP_TARGET_RESOLUTION_M = 10.0
MAP_MAX_SIDE_PX = 2500
# Half-width of the Process API time window around the selected scene. It
# isolates the selected acquisition pass (orbits over the same area are days
# apart); Sentinel Hub mosaics the pass's tiles inside the ROI.
MAP_SCENE_WINDOW_MINUTES = 30

# Charts: GEE ui.Chart.image.series(reducer=mean, scale=1000), no cloud mask.
CHART_SCALE_M = 1000.0
# Sentinel Hub has no mean/area downsampling; BILINEAR is the documented
# closest choice to GEE's mean-pyramid reads (difference X3).
CHART_DOWNSAMPLING = "BILINEAR"
CHART_AGGREGATION_INTERVAL = "P1D"
CHART_REDUCER = "mean"


@dataclass(frozen=True)
class ProcessingDifference:
    code: str
    applies_to: tuple[Literal["map", "timeseries"], ...]
    summary: str


PROCESSING_DIFFERENCES: tuple[ProcessingDifference, ...] = (
    ProcessingDifference(
        "X1",
        ("map",),
        "Cloud mask: GEE masks QA60 bits 10/11; QA60 is not available through Sentinel Hub, "
        "so Sentinel-2 SCL classes 8, 9 and 10 are used as the migration substitute. "
        "SCL masking is not identical to QA60.",
    ),
    ProcessingDifference(
        "X2",
        ("map", "timeseries"),
        "Tiles: GEE processes each Sentinel-2 granule (MGRS tile) separately; Sentinel Hub "
        "mosaics all tiles of the selected acquisition inside the ROI. The map may cover more "
        "of the ROI than GEE's single tile, and the time series has one value per day instead "
        "of one per granule.",
    ),
    ProcessingDifference(
        "X3",
        ("timeseries",),
        "1000 m aggregation: GEE reads mean-aggregated image pyramids and weights partially "
        "covered pixels; Sentinel Hub resamples to 1000 m with BILINEAR downsampling and has "
        "no area-average mode. Values can differ, most for wetlands smaller than a 1 km pixel.",
    ),
    ProcessingDifference(
        "X4",
        ("map", "timeseries"),
        "Processing baseline: GEE and Copernicus Data Space may hold different ESA processing "
        "versions (Collection-1 reprocessing, up to 2023-12-13) of the same acquisition. "
        "No correction is applied; under validation.",
    ),
    ProcessingDifference(
        "X5",
        ("map", "timeseries"),
        "Low values: Sentinel Hub harmonizeValues clamps negative reflectance to 0. GEE's "
        "handling of the same pixels is under validation; no further clamping or replacement "
        "is applied here. Pixels where both bands are 0 have no defined index and are "
        "reported as no-data.",
    ),
    ProcessingDifference(
        "X6",
        ("timeseries",),
        "Cloud threshold: GEE keeps tiles with CLOUDY_PIXEL_PERCENTAGE < threshold; the "
        "Sentinel Hub maxCloudCoverage filter keeps tiles with cloud cover <= threshold, so "
        "tiles exactly at the threshold are included.",
    ),
)


def differences_for(kind: Literal["map", "timeseries"]) -> list[ProcessingDifference]:
    return [d for d in PROCESSING_DIFFERENCES if kind in d.applies_to]
