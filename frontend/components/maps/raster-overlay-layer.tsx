export interface RasterOverlayLayerProps {
  /** URL of a georeferenced raster tile source (e.g. a processed GeoTIFF). */
  sourceUrl: string;
  opacity?: number;
}

/**
 * Placeholder for a deck.gl BitmapLayer / TileLayer rendering processed
 * raster datasets (e.g. Sentinel Hub or Earth Engine exports) over the
 * base map. Implemented in a future step.
 */
export function RasterOverlayLayer(_props: RasterOverlayLayerProps): null {
  return null;
}
