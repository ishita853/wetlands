import type { GeoPoint } from "@/types/map";

export interface WetlandPointsLayerProps {
  points: GeoPoint[];
  onPointClick?: (point: GeoPoint) => void;
}

/**
 * Placeholder for a deck.gl ScatterplotLayer rendering Ramsar wetland
 * point locations over the base map. Layer construction and MapLibre
 * interleaving via @deck.gl/mapbox are implemented in a future step.
 */
export function WetlandPointsLayer(_props: WetlandPointsLayerProps): null {
  return null;
}
