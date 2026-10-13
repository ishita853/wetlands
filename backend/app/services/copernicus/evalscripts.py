"""Evalscript generators for the four GEE indices.

Both scripts compute exactly (a - b) / (a + b) from the shared index table.
Nothing is clamped or rescaled here; the only pixels without a value are
Sentinel Hub no-data, pixels where a + b = 0 (the ratio is undefined), and, on
maps only, the SCL cloud/cirrus substitute for the GEE QA60 mask.
"""

import json

from app.processing.water_quality.indices import IndexDefinition
from app.processing.water_quality.methodology import INPUT_UNITS, MAP_CLOUD_MASK_SCL_CLASSES

# Values of the second band of the map raster.
PIXEL_NO_DATA = 0  # outside the ROI or no Sentinel-2 data
PIXEL_VALID = 1
PIXEL_CLOUD_MASKED = 2  # SCL class in MAP_CLOUD_MASK_SCL_CLASSES
PIXEL_UNDEFINED = 3  # a + b == 0


def map_evalscript(index: IndexDefinition) -> str:
    """Process API: FLOAT32 [index value (NaN if none), pixel status]."""
    a, b = index.band_a, index.band_b
    return f"""//VERSION=3
// {index.key}: {index.formula}  (GEE: {index.gee_expression})
const SCL_CLOUD_CLASSES = {json.dumps(list(MAP_CLOUD_MASK_SCL_CLASSES))};

function setup() {{
  return {{
    input: [{{ bands: ["{a}", "{b}", "SCL", "dataMask"], units: "{INPUT_UNITS}" }}],
    output: {{ bands: 2, sampleType: "FLOAT32" }},
  }};
}}

function evaluatePixel(sample) {{
  if (sample.dataMask === 0) return [NaN, {PIXEL_NO_DATA}];
  if (SCL_CLOUD_CLASSES.includes(sample.SCL)) return [NaN, {PIXEL_CLOUD_MASKED}];
  const sum = sample.{a} + sample.{b};
  if (sum === 0) return [NaN, {PIXEL_UNDEFINED}];
  return [(sample.{a} - sample.{b}) / sum, {PIXEL_VALID}];
}}
"""


def statistics_evalscript(index: IndexDefinition) -> str:
    """Statistical API: unmasked index (as in the GEE charts) plus dataMask."""
    a, b = index.band_a, index.band_b
    return f"""//VERSION=3
// {index.key}: {index.formula}  (GEE: {index.gee_expression}); no cloud mask, as in GEE charts
function setup() {{
  return {{
    input: [{{ bands: ["{a}", "{b}", "dataMask"], units: "{INPUT_UNITS}" }}],
    output: [
      {{ id: "index", bands: 1, sampleType: "FLOAT32" }},
      {{ id: "dataMask", bands: 1 }},
    ],
  }};
}}

function evaluatePixel(sample) {{
  const sum = sample.{a} + sample.{b};
  if (sample.dataMask === 0 || sum === 0) return {{ index: [NaN], dataMask: [0] }};
  return {{ index: [(sample.{a} - sample.{b}) / sum], dataMask: [1] }};
}}
"""
