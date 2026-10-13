"""The four GEE indices: definitions, evalscripts (executed in Node) and palette rendering."""

import json
import shutil
import subprocess

import numpy as np
import pytest

from app.processing.water_quality.indices import INDICES, IndexKey
from app.processing.water_quality.raster import colorize
from app.services.copernicus.evalscripts import (
    PIXEL_CLOUD_MASKED,
    PIXEL_NO_DATA,
    PIXEL_UNDEFINED,
    PIXEL_VALID,
    map_evalscript,
    statistics_evalscript,
)

# Straight from the GEE script: normalizedDifference([a, b]), palette, legend.
GEE_REFERENCE = {
    "NDCI": (("B5", "B4"), ["lightblue", "7CFC00", "808000", "006400"]),
    "NDTI": (("B3", "B4"), ["red", "A6CAE0", "00008B"]),
    "NDWI": (("B3", "B8"), ["32CD32", "yellow", "blue"]),
    "NDMI": (("B8", "B11"), ["#00008B", "#800080", "lightgreen", "darkgreen"]),
}
SENTINEL_HUB_BANDS = {"B3": "B03", "B4": "B04", "B5": "B05", "B8": "B08", "B11": "B11"}


def test_exactly_the_four_gee_indices():
    assert set(INDICES) == {IndexKey.NDCI, IndexKey.NDTI, IndexKey.NDWI, IndexKey.NDMI}


@pytest.mark.parametrize("key", list(GEE_REFERENCE))
def test_bands_palette_and_range_match_gee(key):
    index = INDICES[IndexKey(key)]
    (gee_a, gee_b), gee_palette = GEE_REFERENCE[key]
    assert (index.gee_band_a, index.gee_band_b) == (gee_a, gee_b)
    assert (index.band_a, index.band_b) == (SENTINEL_HUB_BANDS[gee_a], SENTINEL_HUB_BANDS[gee_b])
    assert list(index.gee_palette) == gee_palette
    assert (index.vis_min, index.vis_max) == (-1.0, 1.0)
    assert index.formula == f"({index.band_a} - {index.band_b}) / ({index.band_a} + {index.band_b})"
    # Legend uses exactly the palette colours.
    assert {e.color for e in index.legend} == set(index.palette)


def test_css_colour_names_resolved_to_hex():
    assert INDICES[IndexKey.NDCI].palette[0] == "#ADD8E6"  # lightblue
    assert INDICES[IndexKey.NDWI].palette[1:] == ("#FFFF00", "#0000FF")  # yellow, blue
    assert INDICES[IndexKey.NDMI].palette[2:] == ("#90EE90", "#006400")  # lightgreen, darkgreen


@pytest.mark.parametrize("key", list(GEE_REFERENCE))
def test_statistics_evalscript_has_no_cloud_mask(key):
    script = statistics_evalscript(INDICES[IndexKey(key)])
    assert "SCL" not in script
    assert 'units: "DN"' in script


def _run_node(script: str, samples: list[dict]) -> list:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js not available to execute evalscripts")
    program = f"{script}\nconsole.log(JSON.stringify({json.dumps(samples)}.map(evaluatePixel)));"
    result = subprocess.run([node, "-e", program], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


@pytest.mark.parametrize("key", list(GEE_REFERENCE))
def test_map_evalscript_computes_normalized_difference(key):
    index = INDICES[IndexKey(key)]
    a, b = index.band_a, index.band_b
    samples = [
        {a: 3000, b: 1000, "SCL": 6, "dataMask": 1},  # water, valid
        {a: 3000, b: 1000, "SCL": 9, "dataMask": 1},  # cloud high probability
        {a: 3000, b: 1000, "SCL": 3, "dataMask": 1},  # cloud shadow: NOT masked (as GEE QA60)
        {a: 0, b: 0, "SCL": 6, "dataMask": 1},  # undefined ratio
        {a: 3000, b: 1000, "SCL": 0, "dataMask": 0},  # no data
    ]
    out = _run_node(map_evalscript(index), samples)
    assert out[0] == [pytest.approx(0.5), PIXEL_VALID]
    assert out[1] == [None, PIXEL_CLOUD_MASKED]  # NaN serializes as null
    assert out[2] == [pytest.approx(0.5), PIXEL_VALID]
    assert out[3] == [None, PIXEL_UNDEFINED]
    assert out[4] == [None, PIXEL_NO_DATA]


@pytest.mark.parametrize("key", list(GEE_REFERENCE))
def test_statistics_evalscript_is_unmasked(key):
    index = INDICES[IndexKey(key)]
    a, b = index.band_a, index.band_b
    samples = [
        {a: 1000, b: 3000, "dataMask": 1},
        {a: 0, b: 0, "dataMask": 1},
        {a: 1, b: 1, "dataMask": 0},
    ]
    out = _run_node(statistics_evalscript(index), samples)
    assert out[0] == {"index": [pytest.approx(-0.5)], "dataMask": [1]}
    assert out[1] == {"index": [None], "dataMask": [0]}
    assert out[2] == {"index": [None], "dataMask": [0]}


def test_colorize_matches_gee_palette_interpolation():
    ndti = INDICES[IndexKey.NDTI]  # red at -1, A6CAE0 at 0, 00008B at +1
    values = np.array([[-1.0, 0.0, 1.0, -5.0, 5.0, 0.5, np.nan]], dtype=np.float32)
    rgba = colorize(values, ndti)[0]
    assert tuple(rgba[0]) == (255, 0, 0, 255)
    assert tuple(rgba[1]) == (0xA6, 0xCA, 0xE0, 255)
    assert tuple(rgba[2]) == (0x00, 0x00, 0x8B, 255)
    assert tuple(rgba[3]) == (255, 0, 0, 255)  # clamped below min
    assert tuple(rgba[4]) == (0x00, 0x00, 0x8B, 255)  # clamped above max
    # Halfway between A6CAE0 and 00008B.
    assert tuple(rgba[5]) == (83, 101, 182, 255)
    assert rgba[6][3] == 0  # no value -> transparent


def test_colorize_four_stop_palette_positions():
    ndci = INDICES[IndexKey.NDCI]  # stops at -1, -1/3, 1/3, 1
    rgba = colorize(np.array([[-1 / 3, 1 / 3]], dtype=np.float32), ndci)[0]
    assert tuple(rgba[0][:3]) == (0x7C, 0xFC, 0x00)
    assert tuple(rgba[1][:3]) == (0x80, 0x80, 0x00)
