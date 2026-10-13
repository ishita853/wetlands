import type { GeoPoint } from "@/types/map";

export interface HeatmapLayerProps {
  points: (GeoPoint & { weight?: number })[];
}

/**
 * Placeholder for a deck.gl HeatmapLayer (@deck.gl/aggregation-layers).
 * Implemented in a future step.
 */
export function HeatmapLayer(_props: HeatmapLayerProps): null {
  return null;
}
