/**
 * Map and chart colours. Canvas renderers (MapLibre, ECharts) need sRGB
 * values, so these are the exact sRGB equivalents of the portal's oklch
 * tokens in app/globals.css.
 */
export const mapPalette = {
  sea: "#a9d3ea",
  seaShelf: "#c4e2f1",
  neighbourLand: "#e4dfd0",
  land: "#f8f0d4",
  landHighlight: "#cfe7c3",
  stateLine: "#9a8a6a",
  stateLineHighlight: "#14244b", // --masthead
  districtLine: "#c7ccd8",
  site: "#236436", // --sedge-strong
  siteStroke: "#ffffff",
  siteSelected: "#243b6c", // --primary
  valueStroke: "#14244b",
  noData: "#a3a9b4",
} as const;

/** Chart ink and marks. */
export const chartPalette = {
  primary: "#243b6c", // --primary (navy): single-series marks
  secondary: "#4a9a5e", // --sedge: second series / reference line
  text: "#2c3140",
  muted: "#6b7285",
  grid: "#dfe8f0",
  axis: "#bccad8",
} as const;

/**
 * Sequential ramp for dot-density colouring of an indicator: one hue
 * (sedge, oklch h=150), lightness stepping 0.90 → 0.36. Light steps are
 * low-contrast on the land fill, so coloured dots also get a navy outline,
 * and every value is available in the tooltip and data table.
 */
export const sequentialRamp = ["#c8e8cd", "#94cf9f", "#63af75", "#3d8e53", "#256b3a", "#134924"];
