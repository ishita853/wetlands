"""Reading the Process API index raster and rendering it like the GEE map layer.

GEE `addLayer(img, {min, max, palette})` spreads the palette colours evenly
over [min, max], interpolates linearly between them in RGB and clamps values
outside the range. `colorize` does the same; pixels without a value are
transparent (in GEE the red ROI layer shows through there).
"""

import warnings
from dataclasses import dataclass

import numpy as np
from rasterio.errors import NotGeoreferencedWarning
from rasterio.io import MemoryFile
from rasterio.transform import array_bounds

from app.processing.water_quality.indices import IndexDefinition
from app.services.copernicus.evalscripts import (
    PIXEL_CLOUD_MASKED,
    PIXEL_UNDEFINED,
    PIXEL_VALID,
)


@dataclass(frozen=True)
class IndexRaster:
    values: np.ndarray  # float32, NaN where no index value
    status: np.ndarray  # uint8, PIXEL_* codes
    bounds: tuple[float, float, float, float]  # west, south, east, north in raster CRS
    epsg: int | None

    def pixel_counts(self) -> dict[str, int]:
        return {
            "valid": int(np.count_nonzero(self.status == PIXEL_VALID)),
            "cloudMasked": int(np.count_nonzero(self.status == PIXEL_CLOUD_MASKED)),
            "undefinedIndex": int(np.count_nonzero(self.status == PIXEL_UNDEFINED)),
            "noDataOrOutsideRoi": int(
                np.count_nonzero(
                    ~np.isin(self.status, (PIXEL_VALID, PIXEL_CLOUD_MASKED, PIXEL_UNDEFINED))
                )
            ),
        }

    def value_summary(self) -> dict[str, float | None]:
        valid = self.values[np.isfinite(self.values)]
        if valid.size == 0:
            return {"min": None, "max": None, "mean": None}
        return {
            "min": float(valid.min()),
            "max": float(valid.max()),
            "mean": float(valid.mean()),
        }


def read_index_geotiff(data: bytes) -> IndexRaster:
    with MemoryFile(data) as memfile, memfile.open() as dataset:
        if dataset.count < 2:
            raise ValueError(f"Expected 2 bands (index, status), got {dataset.count}.")
        values = dataset.read(1).astype(np.float32)
        status = np.nan_to_num(dataset.read(2), nan=0).astype(np.uint8)
        bounds = array_bounds(dataset.height, dataset.width, dataset.transform)
        west, south, east, north = bounds[0], bounds[1], bounds[2], bounds[3]
        epsg = dataset.crs.to_epsg() if dataset.crs else None
    values[status != PIXEL_VALID] = np.nan
    return IndexRaster(values, status, (west, south, east, north), epsg)


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def colorize(values: np.ndarray, index: IndexDefinition) -> np.ndarray:
    """RGBA uint8 array (H, W, 4) using the GEE palette over [vis_min, vis_max]."""
    stops = np.array([_hex_to_rgb(c) for c in index.palette], dtype=np.float64)
    finite = np.isfinite(values)
    t = np.clip(
        (np.where(finite, values, index.vis_min) - index.vis_min) / (index.vis_max - index.vis_min),
        0.0,
        1.0,
    )
    position = t * (len(stops) - 1)
    lower = np.minimum(np.floor(position).astype(int), len(stops) - 2)
    fraction = (position - lower)[..., None]
    rgb = stops[lower] + (stops[lower + 1] - stops[lower]) * fraction
    rgba = np.zeros((*values.shape, 4), dtype=np.uint8)
    rgba[..., :3] = np.rint(rgb).astype(np.uint8)
    rgba[..., 3] = np.where(finite, 255, 0)
    return rgba


def encode_png(rgba: np.ndarray) -> bytes:
    height, width, _ = rgba.shape
    # A plain PNG for the web map overlay; georeferencing travels in the JSON.
    with warnings.catch_warnings(), MemoryFile() as memfile:
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with memfile.open(
            driver="PNG", width=width, height=height, count=4, dtype="uint8"
        ) as dataset:
            dataset.write(np.moveaxis(rgba, -1, 0))
        return memfile.read()
