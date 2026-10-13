"use client";

import {
  type ImageSource,
  LngLatBounds,
  Map as MapLibreMap,
  NavigationControl,
  setWorkerUrl,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";

const absolute = (path: string) => new URL(path, window.location.origin).href;

export type IndexRaster = {
  /** PNG data URI rendered by the backend from the Sentinel Hub index raster. */
  dataUri: string;
  /** [lon, lat] corners: top-left, top-right, bottom-right, bottom-left. */
  coordinates: [number, number][];
};

function geometryBounds(geometry: GeoJSON.Geometry): LngLatBounds | null {
  const bounds = new LngLatBounds();
  let found = false;
  const visit = (value: unknown): void => {
    if (Array.isArray(value) && typeof value[0] === "number") {
      bounds.extend([value[0] as number, value[1] as number]);
      found = true;
    } else if (Array.isArray(value)) {
      value.forEach(visit);
    }
  };
  if ("coordinates" in geometry) visit(geometry.coordinates);
  return found ? bounds : null;
}

/**
 * Index raster over satellite imagery (Esri World Imagery), with the analysis
 * boundary outlined. The raster is exactly what the backend returned for the
 * selected Sentinel-2 acquisition; nothing is drawn when there is none.
 */
export function IndexMap({
  latitude,
  longitude,
  boundary,
  raster,
  ariaLabel,
  className,
}: {
  latitude: number;
  longitude: number;
  boundary: GeoJSON.Geometry | null;
  raster: IndexRaster | null;
  ariaLabel: string;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [loaded, setLoaded] = useState(false);

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
          { id: "background", type: "background", paint: { "background-color": "#1f2a3a" } },
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
        customAttribution: "Index: Copernicus Sentinel-2 L2A via Sentinel Hub (CDSE)",
      },
    });
    map.touchZoomRotate.disableRotation();
    map.addControl(new NavigationControl({ showCompass: false }), "top-left");
    map.on("load", () => {
      // Credits are required by the imagery and Copernicus licences: keep them one
      // click away behind the (i) button instead of over the map.
      map
        .getContainer()
        .querySelector(".maplibregl-ctrl-attrib")
        ?.classList.remove("maplibregl-compact-show");
      setLoaded(true);
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      setLoaded(false);
    };
  }, [latitude, longitude]);

  // Index raster (below the boundary outline).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loaded) return;
    if (map.getLayer("index")) map.removeLayer("index");
    if (map.getSource("index")) map.removeSource("index");
    if (!raster) return;
    const [tl, tr, br, bl] = raster.coordinates;
    map.addSource("index", {
      type: "image",
      url: raster.dataUri,
      coordinates: [tl, tr, br, bl] as ImageSource["coordinates"],
    });
    map.addLayer(
      {
        id: "index",
        type: "raster",
        source: "index",
        paint: {
          "raster-opacity": 0.92,
          "raster-resampling": "nearest",
          "raster-fade-duration": 0,
        },
      },
      map.getLayer("roi-halo") ? "roi-halo" : undefined,
    );
  }, [raster, loaded]);

  // Analysis boundary.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loaded) return;
    for (const id of ["roi-line", "roi-halo"]) if (map.getLayer(id)) map.removeLayer(id);
    if (map.getSource("roi")) map.removeSource("roi");
    if (!boundary) return;
    map.addSource("roi", {
      type: "geojson",
      data: { type: "Feature", geometry: boundary, properties: {} },
    });
    map.addLayer({
      id: "roi-halo",
      type: "line",
      source: "roi",
      paint: { "line-color": "#14244b", "line-width": 4, "line-opacity": 0.6 },
    });
    map.addLayer({
      id: "roi-line",
      type: "line",
      source: "roi",
      paint: { "line-color": "#ffffff", "line-width": 1.75 },
    });
    const bounds = geometryBounds(boundary);
    if (bounds) map.fitBounds(bounds, { padding: 32, duration: 0, maxZoom: 15 });
  }, [boundary, loaded]);

  return <div ref={containerRef} role="region" aria-label={ariaLabel} className={className} />;
}
