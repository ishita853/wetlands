import type { GeoPoint } from "@/types/map";

export interface DotDensityLayerProps {
  points: GeoPoint[];
}

/**
 * Placeholder for a deck.gl dot-density visualization (e.g. built on
 * ScatterplotLayer or GridLayer from @deck.gl/aggregation-layers).
 * Implemented in a future step.
 */
export function DotDensityLayer(_props: DotDensityLayerProps): null {
  return null;
}
