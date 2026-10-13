import type { Feature, MultiPolygon, Polygon } from "geojson";

export interface WetlandBoundaryLayerProps {
  boundaries: Feature<Polygon | MultiPolygon>[];
}

/**
 * Placeholder for a deck.gl GeoJsonLayer rendering wetland boundary
 * polygons sourced from the backend's PostGIS geometry columns.
 * Implemented in a future step.
 */
export function WetlandBoundaryLayer(_props: WetlandBoundaryLayerProps): null {
  return null;
}
