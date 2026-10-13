"use client";

import type { FeatureCollection, Point } from "geojson";
import { Layers, Minus, Plus, RotateCcw } from "lucide-react";
import {
  Map as MapLibreMap,
  type ExpressionSpecification,
  type GeoJSONSource,
  type MapLayerMouseEvent,
  type StyleSpecification,
  setWorkerUrl,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useMemo, useRef, useState } from "react";

import type { RamsarSitePoint } from "@/lib/data/ramsar";
import { mapPalette } from "@/lib/maps/palette";
import { cn } from "@/lib/utils";

const INDIA_BOUNDS: [[number, number], [number, number]] = [
  [67.5, 6.2],
  [97.8, 37.4],
];

// GeoJSON is fetched inside MapLibre's web worker, where root-relative URLs
// do not resolve — always hand it absolute URLs.
const absolute = (path: string) => new URL(path, window.location.origin).href;

const baseStyle = (): StyleSpecification => ({
  version: 8,
  sources: {
    // Coastline-only land (Natural Earth, no country borders) so the sea and
    // neighbouring landmass read clearly; India's official states draw on top.
    land: { type: "geojson", data: absolute("/data/region-land.geojson") },
    states: { type: "geojson", data: absolute("/data/india-states.geojson") },
  },
  layers: [
    { id: "sea", type: "background", paint: { "background-color": mapPalette.sea } },
    {
      id: "sea-shelf",
      type: "line",
      source: "land",
      paint: { "line-color": mapPalette.seaShelf, "line-width": 10, "line-blur": 8 },
    },
    { id: "land-fill", type: "fill", source: "land", paint: { "fill-color": mapPalette.neighbourLand } },
    { id: "states-fill", type: "fill", source: "states", paint: { "fill-color": mapPalette.land } },
    {
      id: "states-highlight",
      type: "fill",
      source: "states",
      filter: ["==", ["get", "name"], ""],
      paint: { "fill-color": mapPalette.landHighlight },
    },
    {
      id: "states-line",
      type: "line",
      source: "states",
      paint: { "line-color": mapPalette.stateLine, "line-width": 0.8 },
    },
    {
      id: "states-line-highlight",
      type: "line",
      source: "states",
      filter: ["==", ["get", "name"], ""],
      paint: { "line-color": mapPalette.stateLineHighlight, "line-width": 1.6 },
    },
  ],
});

export type SiteColouring = {
  /** Value per Ramsar site id; sites without a value are drawn grey. */
  values: Record<number, number | null>;
  /** [value, colour] stops for a linear ramp. */
  stops: [number, string][];
};

export interface RamsarMapProps {
  sites: RamsarSitePoint[];
  selectedId?: number | null;
  onSelect?: (id: number | null) => void;
  /** Highlights and zooms to one state/UT. */
  highlightState?: string | null;
  colouring?: SiteColouring;
  /** Scale dot size by site area (explorer); fixed size otherwise. */
  sizeByArea?: boolean;
  /** Require Ctrl/⌘ + scroll to zoom — for maps embedded in long pages. */
  cooperativeGestures?: boolean;
  className?: string;
  ariaLabel?: string;
}

function toFeatureCollection(sites: RamsarSitePoint[], colouring?: SiteColouring) {
  return {
    type: "FeatureCollection",
    features: sites.map((site) => ({
      type: "Feature",
      id: site.id,
      geometry: { type: "Point", coordinates: [site.longitude, site.latitude] },
      properties: {
        id: site.id,
        name: site.name,
        state: site.state,
        areaHa: site.areaHa,
        value: colouring ? (colouring.values[site.id] ?? null) : null,
      },
    })),
  } satisfies FeatureCollection<Point>;
}

function circleColor(colouring?: SiteColouring): ExpressionSpecification | string {
  if (!colouring || colouring.stops.length === 0) return mapPalette.site;
  const ramp: ExpressionSpecification = [
    "interpolate",
    ["linear"],
    ["to-number", ["get", "value"]],
    ...colouring.stops.flat(),
  ] as unknown as ExpressionSpecification;
  return ["case", ["==", ["get", "value"], null], mapPalette.noData, ramp];
}

function circleRadius(sizeByArea: boolean): ExpressionSpecification | number {
  if (!sizeByArea) return ["interpolate", ["linear"], ["zoom"], 4, 5, 8, 8];
  // Square-root scaling keeps dot area proportional to site area.
  return ["interpolate", ["linear"], ["sqrt", ["get", "areaHa"]], 0, 4, 100, 7, 650, 14];
}

/**
 * National map of India's Ramsar Sites, drawn on the project-supplied India
 * state boundaries over a coastline-only land mask (no country borders, so the
 * official boundary is the only one shown). Districts load on demand from the
 * layer control.
 */
export function RamsarMap({
  sites,
  selectedId = null,
  onSelect,
  highlightState = null,
  colouring,
  sizeByArea = false,
  cooperativeGestures = false,
  className,
  ariaLabel = "Map of Ramsar Sites in India",
}: RamsarMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const onSelectRef = useRef(onSelect);
  const [ready, setReady] = useState(false);
  const [showDistricts, setShowDistricts] = useState(false);
  const [layersOpen, setLayersOpen] = useState(false);
  const [hover, setHover] = useState<{ x: number; y: number; name: string; state: string } | null>(
    null,
  );

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  const data = useMemo(() => toFeatureCollection(sites, colouring), [sites, colouring]);
  const dataRef = useRef(data);
  const sitesRef = useRef(sites);
  useEffect(() => {
    dataRef.current = data;
    sitesRef.current = sites;
  }, [data, sites]);

  // Create the map once.
  useEffect(() => {
    if (!containerRef.current) return;
    // Worker is served from public/ (see scripts/copy-maplibre-worker.mjs).
    setWorkerUrl(absolute("/vendor/maplibre/maplibre-gl-worker.mjs"));
    const map = new MapLibreMap({
      container: containerRef.current,
      style: baseStyle(),
      bounds: INDIA_BOUNDS,
      fitBoundsOptions: { padding: 16 },
      maxBounds: [
        [55, -2],
        [110, 45],
      ],
      minZoom: 3,
      maxZoom: 11,
      dragRotate: false,
      pitchWithRotate: false,
      touchPitch: false,
      cooperativeGestures,
      attributionControl: {
        compact: true,
        customAttribution: "Site data: Ramsar Convention on Wetlands",
      },
    });
    map.on("error", (event) => console.error("Map error:", event.error?.message ?? event));
    map.touchZoomRotate.disableRotation();
    map.keyboard.disableRotation();
    mapRef.current = map;

    map.on("load", () => {
      map.addSource("sites", { type: "geojson", data: dataRef.current });
      map.addLayer({
        id: "sites",
        type: "circle",
        source: "sites",
        paint: {
          "circle-color": mapPalette.site,
          "circle-radius": 5,
          "circle-stroke-color": mapPalette.siteStroke,
          "circle-stroke-width": 1.25,
          "circle-opacity": 0.92,
        },
      });
      map.addLayer({
        id: "sites-selected",
        type: "circle",
        source: "sites",
        filter: ["==", ["get", "id"], -1],
        paint: {
          "circle-color": "rgba(0,0,0,0)",
          "circle-radius": 11,
          "circle-stroke-color": mapPalette.siteSelected,
          "circle-stroke-width": 2.5,
        },
      });

      map.on("mousemove", "sites", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        if (!feature) return;
        map.getCanvas().style.cursor = "pointer";
        setHover({
          x: event.point.x,
          y: event.point.y,
          name: String(feature.properties.name),
          state: String(feature.properties.state),
        });
      });
      map.on("mouseleave", "sites", () => {
        map.getCanvas().style.cursor = "";
        setHover(null);
      });
      map.on("click", (event) => {
        const feature = map.queryRenderedFeatures(event.point, { layers: ["sites"] })[0];
        onSelectRef.current?.(feature ? Number(feature.properties.id) : null);
      });
      // Start the attribution collapsed (still one click away) so it never
      // covers the map on small panels.
      map
        .getContainer()
        .querySelector(".maplibregl-ctrl-attrib")
        ?.classList.remove("maplibregl-compact-show");
      setReady(true);
    });

    const resize = new ResizeObserver(() => map.resize());
    resize.observe(containerRef.current);

    return () => {
      resize.disconnect();
      map.remove();
      mapRef.current = null;
    };
    // cooperativeGestures is fixed per map instance
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Site data + styling.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    (map.getSource("sites") as GeoJSONSource | undefined)?.setData(data);
    map.setPaintProperty("sites", "circle-color", circleColor(colouring));
    map.setPaintProperty("sites", "circle-radius", circleRadius(sizeByArea));
    // Light ramp steps need an outline to stay visible on the land fill.
    const coloured = Boolean(colouring?.stops.length);
    map.setPaintProperty(
      "sites",
      "circle-stroke-color",
      coloured ? mapPalette.valueStroke : mapPalette.siteStroke,
    );
    map.setPaintProperty("sites", "circle-stroke-width", coloured ? 0.75 : 1.25);
  }, [ready, data, colouring, sizeByArea]);

  // Selection ring.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    map.setFilter("sites-selected", ["==", ["get", "id"], selectedId ?? -1]);
    const site = sitesRef.current.find((s) => s.id === selectedId);
    if (site) {
      map.easeTo({ center: [site.longitude, site.latitude], zoom: Math.max(map.getZoom(), 6) });
    }
  }, [ready, selectedId]);

  // State highlight + zoom.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const filter: ExpressionSpecification = ["==", ["get", "name"], highlightState ?? ""];
    map.setFilter("states-highlight", filter);
    map.setFilter("states-line-highlight", filter);
    const inState = highlightState
      ? sitesRef.current.filter((s) => s.state === highlightState)
      : [];
    if (inState.length) {
      const lons = inState.map((s) => s.longitude);
      const lats = inState.map((s) => s.latitude);
      map.fitBounds(
        [
          [Math.min(...lons) - 2.5, Math.min(...lats) - 2],
          [Math.max(...lons) + 2.5, Math.max(...lats) + 2],
        ],
        { padding: 24, maxZoom: 6.5 },
      );
    } else if (!highlightState) {
      map.fitBounds(INDIA_BOUNDS, { padding: 16 });
    }
  }, [ready, highlightState]);

  // Districts layer, loaded on first use.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    if (showDistricts && !map.getSource("districts")) {
      map.addSource("districts", {
        type: "geojson",
        data: absolute("/data/india-districts.geojson"),
      });
      map.addLayer(
        {
          id: "districts-line",
          type: "line",
          source: "districts",
          paint: { "line-color": mapPalette.districtLine, "line-width": 0.5 },
        },
        "states-line",
      );
    }
    if (map.getLayer("districts-line")) {
      map.setLayoutProperty("districts-line", "visibility", showDistricts ? "visible" : "none");
    }
  }, [ready, showDistricts]);

  const zoomBy = (delta: number) =>
    mapRef.current?.easeTo({ zoom: mapRef.current.getZoom() + delta });
  const reset = () => {
    onSelectRef.current?.(null);
    mapRef.current?.fitBounds(INDIA_BOUNDS, { padding: 16 });
  };

  const controlButton =
    "flex size-9 items-center justify-center text-foreground transition-colors outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-inset";

  return (
    <div className={cn("relative overflow-hidden rounded-sm border border-border", className)}>
      {/* maplibre-gl.css sets position:relative on this element, so size it as a full-height child rather than absolutely. */}
      <div ref={containerRef} role="region" aria-label={ariaLabel} className="h-full w-full" />

      {!ready ? (
        <div className="absolute inset-0 flex items-center justify-center bg-[#a9d3ea] text-sm text-muted-foreground">
          Loading map…
        </div>
      ) : null}

      <div className="absolute top-3 left-3 flex flex-col divide-y divide-border rounded-sm border border-border bg-card shadow-sm">
        <button
          type="button"
          onClick={() => zoomBy(1)}
          aria-label="Zoom in"
          className={controlButton}
        >
          <Plus className="size-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={() => zoomBy(-1)}
          aria-label="Zoom out"
          className={controlButton}
        >
          <Minus className="size-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={reset}
          aria-label="Reset to all of India"
          className={controlButton}
        >
          <RotateCcw className="size-4" aria-hidden="true" />
        </button>
      </div>

      <div className="absolute top-3 right-3">
        <button
          type="button"
          onClick={() => setLayersOpen((open) => !open)}
          aria-expanded={layersOpen}
          aria-label="Map layers"
          className={cn(controlButton, "rounded-sm border border-border bg-card shadow-sm")}
        >
          <Layers className="size-4" aria-hidden="true" />
        </button>
        {layersOpen ? (
          <div className="absolute top-11 right-0 w-48 rounded-sm border border-border bg-card p-3 text-sm shadow-md">
            <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Layers
            </p>
            <label className="mt-2 flex items-center gap-2">
              <input type="checkbox" checked disabled className="accent-[#2f6f45]" />
              Ramsar Sites
            </label>
            <label className="mt-1.5 flex items-center gap-2">
              <input type="checkbox" checked disabled className="accent-[#2f6f45]" />
              State boundaries
            </label>
            <label className="mt-1.5 flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={showDistricts}
                onChange={(event) => setShowDistricts(event.target.checked)}
                className="accent-[#2f6f45]"
              />
              District boundaries
            </label>
          </div>
        ) : null}
      </div>

      {hover ? (
        <div
          className="pointer-events-none absolute z-10 max-w-60 -translate-x-1/2 -translate-y-[calc(100%+12px)] rounded-sm border border-border bg-card px-2.5 py-1.5 text-xs shadow-md"
          style={{ left: hover.x, top: hover.y }}
        >
          <p className="font-semibold text-primary">{hover.name}</p>
          <p className="text-muted-foreground">{hover.state}</p>
        </div>
      ) : null}
    </div>
  );
}
