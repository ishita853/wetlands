"use client";

import { useState } from "react";

import { SiteLocationMap } from "@/components/wetlands/site-location-map";
import { SiteSatelliteMap } from "@/components/wetlands/site-satellite-map";
import type { RamsarSitePoint } from "@/lib/data/ramsar";
import { cn } from "@/lib/utils";

const views = [
  { id: "satellite", label: "Satellite" },
  { id: "india", label: "Location in India" },
] as const;

/** Site map with a switch between a satellite close-up and the national locator. */
export function SiteMapPanel({ sites, siteId }: { sites: RamsarSitePoint[]; siteId: number }) {
  const [view, setView] = useState<(typeof views)[number]["id"]>("satellite");
  const site = sites.find((s) => s.id === siteId);

  return (
    <div>
      <div
        role="group"
        aria-label="Map view"
        className="mb-2 inline-flex rounded-sm border border-border bg-card p-0.5"
      >
        {views.map((v) => (
          <button
            key={v.id}
            type="button"
            aria-pressed={view === v.id}
            onClick={() => setView(v.id)}
            className={cn(
              "rounded-[0.2rem] px-3 py-1 text-sm transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
              view === v.id
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {v.label}
          </button>
        ))}
      </div>
      {view === "satellite" && site ? (
        <SiteSatelliteMap
          latitude={site.latitude}
          longitude={site.longitude}
          name={site.name}
          className="h-80 overflow-hidden rounded-md border border-border"
        />
      ) : (
        <SiteLocationMap sites={sites} siteId={siteId} />
      )}
    </div>
  );
}
