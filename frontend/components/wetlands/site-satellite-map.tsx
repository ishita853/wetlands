"use client";

import { Map as MapLibreMap, Marker, NavigationControl, setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

import { mapPalette } from "@/lib/maps/palette";

const absolute = (path: string) => new URL(path, window.location.origin).href;

/**
 * Close-up of one Ramsar Site on satellite imagery (Esri World Imagery,
 * imagery only — no labels or boundary lines are drawn over it).
 */
export function SiteSatelliteMap({
  latitude,
  longitude,
  name,
  className,
}: {
  latitude: number;
  longitude: number;
  name: string;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    setWorkerUrl(absolute("/vendor/maplibre/maplibre-gl-worker.mjs"));
    const map = new MapLibreMap({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          imagery: {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            maxzoom: 18,
            attribution: "Imagery © Esri, Maxar, Earthstar Geographics",
          },
        },
        layers: [
          { id: "sea", type: "background", paint: { "background-color": mapPalette.sea } },
          { id: "imagery", type: "raster", source: "imagery" },
        ],
      },
      center: [longitude, latitude],
      zoom: 11,
      minZoom: 4,
      maxZoom: 17,
      dragRotate: false,
      pitchWithRotate: false,
      cooperativeGestures: true,
      attributionControl: {
        compact: true,
        customAttribution: "Site location: Ramsar Convention on Wetlands",
      },
    });
    map.touchZoomRotate.disableRotation();
    map.addControl(new NavigationControl({ showCompass: false }), "top-left");

    const dot = document.createElement("div");
    dot.className = "size-4 rounded-full border-2 border-white bg-orange-500 shadow-md";
    dot.setAttribute("aria-hidden", "true");
    new Marker({ element: dot }).setLngLat([longitude, latitude]).addTo(map);

    return () => map.remove();
  }, [latitude, longitude]);

  return (
    <div
      ref={containerRef}
      role="region"
      aria-label={`Satellite view of ${name}`}
      className={className}
    />
  );
}
