"""The four spectral indices of the GEE water-quality application.

This table is the single source of truth for band selection, formula,
visualization range, palette and legend. Evalscripts (map and statistics),
raster colourization and the legend served to the frontend are all generated
from it, so they cannot drift apart.

Reference: `COPERNICUS/S2_SR_HARMONIZED` in the GEE script, where every index
is `image.normalizedDifference([a, b])` = (a - b) / (a + b), visualized with
`{min: -1, max: 1, palette: [...]}` (docs/gee-functional-specification.md §4, §7, §8).
"""

from dataclasses import dataclass
from enum import StrEnum


class IndexKey(StrEnum):
    NDCI = "NDCI"
    NDTI = "NDTI"
    NDWI = "NDWI"
    NDMI = "NDMI"


@dataclass(frozen=True)
class LegendEntry:
    label: str
    color: str  # hex, as rendered


@dataclass(frozen=True)
class IndexDefinition:
    key: IndexKey
    name: str
    # Sentinel Hub `sentinel-2-l2a` band names (numerator a, denominator b).
    band_a: str
    band_b: str
    # The same bands as named in COPERNICUS/S2_SR_HARMONIZED.
    gee_band_a: str
    gee_band_b: str
    # Palette exactly as written in the GEE script, and the same colours in hex.
    gee_palette: tuple[str, ...]
    palette: tuple[str, ...]
    # Legend rows in the order the GEE app lists them (top to bottom).
    legend: tuple[LegendEntry, ...]
    vis_min: float = -1.0
    vis_max: float = 1.0

    @property
    def formula(self) -> str:
        return f"({self.band_a} - {self.band_b}) / ({self.band_a} + {self.band_b})"

    @property
    def gee_expression(self) -> str:
        return f"normalizedDifference(['{self.gee_band_a}', '{self.gee_band_b}'])"


INDICES: dict[IndexKey, IndexDefinition] = {
    IndexKey.NDCI: IndexDefinition(
        key=IndexKey.NDCI,
        name="Normalized Difference Chlorophyll Index",
        band_a="B05",
        band_b="B04",
        gee_band_a="B5",
        gee_band_b="B4",
        gee_palette=("lightblue", "7CFC00", "808000", "006400"),
        palette=("#ADD8E6", "#7CFC00", "#808000", "#006400"),
        legend=(
            LegendEntry("High Chlorophyll Content", "#006400"),
            LegendEntry("Moderate Chlorophyll Content", "#808000"),
            LegendEntry("Low Chlorophyll Content", "#7CFC00"),
            LegendEntry("Clear Water", "#ADD8E6"),
        ),
    ),
    IndexKey.NDTI: IndexDefinition(
        key=IndexKey.NDTI,
        name="Normalized Difference Turbidity Index",
        band_a="B03",
        band_b="B04",
        gee_band_a="B3",
        gee_band_b="B4",
        gee_palette=("red", "A6CAE0", "00008B"),
        palette=("#FF0000", "#A6CAE0", "#00008B"),
        legend=(
            LegendEntry("High Turbidity", "#FF0000"),
            LegendEntry("Moderate Turbidity", "#A6CAE0"),
            LegendEntry("Clear Water", "#00008B"),
        ),
    ),
    IndexKey.NDWI: IndexDefinition(
        key=IndexKey.NDWI,
        name="Normalized Difference Water Index",
        band_a="B03",
        band_b="B08",
        gee_band_a="B3",
        gee_band_b="B8",
        gee_palette=("32CD32", "yellow", "blue"),
        palette=("#32CD32", "#FFFF00", "#0000FF"),
        legend=(
            LegendEntry("Low Water Content", "#32CD32"),
            LegendEntry("Moderate Water Content", "#FFFF00"),
            LegendEntry("High Water Content", "#0000FF"),
        ),
    ),
    IndexKey.NDMI: IndexDefinition(
        key=IndexKey.NDMI,
        name="Normalized Difference Moisture Index",
        band_a="B08",
        band_b="B11",
        gee_band_a="B8",
        gee_band_b="B11",
        gee_palette=("#00008B", "#800080", "lightgreen", "darkgreen"),
        palette=("#00008B", "#800080", "#90EE90", "#006400"),
        legend=(
            LegendEntry("Negligible Vegetation", "#00008B"),
            LegendEntry("Low Moisture Vegetation", "#800080"),
            LegendEntry("Moderate Moisture Vegetation", "#90EE90"),
            LegendEntry("High Moisture Vegetation", "#006400"),
        ),
    ),
}


def get_index(key: IndexKey | str) -> IndexDefinition:
    return INDICES[IndexKey(key)]
