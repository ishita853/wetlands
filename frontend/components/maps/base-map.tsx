"use client";

import { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

import { DEFAULT_MAP_STYLE_URL } from "@/lib/maps/style";
import type { MapViewState } from "@/types/map";

interface BaseMapProps {
  initialViewState: MapViewState;
  styleUrl?: string;
  className?: string;
}

/**
 * India map container. Wetland points, boundaries, and overlay layers are
 * added by wrapping components via deck.gl's MapboxOverlay control in a
 * future step — this component only owns the base MapLibre instance.
 */
export function BaseMap({ initialViewState, styleUrl, className }: BaseMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const resolvedStyleUrl = styleUrl ?? DEFAULT_MAP_STYLE_URL;

  useEffect(() => {
    if (!containerRef.current || !resolvedStyleUrl) return;

    mapRef.current = new MapLibreMap({
      container: containerRef.current,
      style: resolvedStyleUrl,
      center: [initialViewState.longitude, initialViewState.latitude],
      zoom: initialViewState.zoom,
    });

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [
    resolvedStyleUrl,
    initialViewState.longitude,
    initialViewState.latitude,
    initialViewState.zoom,
  ]);

  if (!resolvedStyleUrl) {
    return (
      <div
        className={
          className ??
          "flex h-full min-h-64 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground"
        }
      >
        Map placeholder — set NEXT_PUBLIC_MAP_STYLE_URL to render the base map.
      </div>
    );
  }

  return <div ref={containerRef} className={className ?? "h-full min-h-64 w-full rounded-md"} />;
}
