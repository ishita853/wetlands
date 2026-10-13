"use client";

import { useRouter } from "next/navigation";

import { RamsarMap } from "@/components/maps/ramsar-map";
import type { RamsarSitePoint } from "@/lib/data/ramsar";

/** Site profile locator: all sites shown, this one ringed; other dots navigate. */
export function SiteLocationMap({ sites, siteId }: { sites: RamsarSitePoint[]; siteId: number }) {
  const router = useRouter();
  const site = sites.find((s) => s.id === siteId);

  return (
    <div>
      <RamsarMap
        sites={sites}
        selectedId={siteId}
        highlightState={site?.state ?? null}
        onSelect={(id) => {
          if (id !== null && id !== siteId) router.push(`/wetlands/${id}`);
        }}
        cooperativeGestures
        ariaLabel={`Location of ${site?.name ?? "this site"}`}
        className="h-80"
      />
      <p className="mt-1.5 text-xs text-muted-foreground">
        Select another dot to open that site&apos;s profile.
      </p>
    </div>
  );
}
