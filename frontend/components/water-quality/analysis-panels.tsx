import { AlertTriangle, Info, SatelliteDish } from "lucide-react";

import type { ErrorKind, WaterQualityError } from "@/lib/api/water-quality";
import { cn } from "@/lib/utils";
import type { Traceability, WaterQualitySite } from "@/types/water-quality";

/** Human label for the backend's analysis polygon source. */
export function boundarySourceLabel(source: string | null): string {
  if (source === "provided_roi") return "RSIS (Ramsar Sites Information Service)";
  if (source === "imported_roi") return "Imported ROI (project-supplied shapefile)";
  if (source === "gee_roi") return "Application ROI";
  if (source === "official_boundary") return "RSIS official boundary";
  return "Not available";
}

function Details({ children }: { children: React.ReactNode }) {
  return (
    <details className="mt-3 text-xs">
      <summary className="cursor-pointer font-medium text-primary">Technical details</summary>
      <div className="mt-2 rounded-sm border border-border bg-card p-2.5 leading-relaxed break-words text-muted-foreground">
        {children}
      </div>
    </details>
  );
}

function Notice({
  tone,
  title,
  children,
}: {
  tone: "warning" | "error" | "info";
  title: string;
  children: React.ReactNode;
}) {
  const Icon = tone === "info" ? Info : tone === "warning" ? AlertTriangle : SatelliteDish;
  return (
    <div
      role={tone === "info" ? "status" : "alert"}
      className={cn(
        "rounded-sm border p-4",
        tone === "warning" && "border-amber-300 bg-amber-50",
        tone === "error" && "border-destructive/30 bg-destructive/5",
        tone === "info" && "border-border bg-muted",
      )}
    >
      <div className="flex items-start gap-2.5">
        <Icon className="mt-0.5 size-4.5 shrink-0 text-foreground/70" aria-hidden="true" />
        <div className="min-w-0 text-sm">
          <p className="font-semibold text-foreground">{title}</p>
          <div className="mt-1 text-foreground/80">{children}</div>
        </div>
      </div>
    </div>
  );
}

/** A site in the list without a usable analysis polygon (no request is made). */
export function UnavailableNotice({ site }: { site: WaterQualitySite }) {
  if (site.availability === "unknown") {
    return (
      <Notice tone="error" title="Analysis availability could not be determined">
        The portal&apos;s water-quality service could not be reached. Try again shortly.
      </Notice>
    );
  }
  return (
    <Notice
      tone="warning"
      title="Water-quality analysis is currently unavailable for this Ramsar site"
    >
      <p>
        {site.availability === "geometry_invalid"
          ? "The published boundary polygon for this site is geometrically invalid (a self-intersecting outline), so it has been rejected rather than silently repaired. A validated analysis boundary is therefore not available."
          : "A validated analysis boundary is not available for this site. No official Ramsar boundary polygon is published for it, and the portal does not approximate boundaries from the site's coordinates."}
      </p>
      <p className="mt-2 text-xs text-muted-foreground">
        This is a limitation of the wetland boundary data, not of Sentinel-2 satellite coverage.
      </p>
    </Notice>
  );
}

const ERROR_COPY: Record<ErrorKind, { title: string; body: string; tone: "warning" | "error" }> = {
  boundary: {
    tone: "warning",
    title: "Water-quality analysis is currently unavailable for this Ramsar site",
    body: "A validated analysis boundary is not available. This is not a limitation of Sentinel-2 satellite coverage.",
  },
  no_scenes: {
    tone: "warning",
    title: "No Sentinel-2 observation matches the selected filters",
    body: "No Sentinel-2 L2A scene intersecting the wetland meets the selected period and cloud threshold. Widen the date range or raise the cloud threshold.",
  },
  not_configured: {
    tone: "error",
    title: "Satellite processing service unavailable",
    body: "The Copernicus Data Space processing service is not configured on the portal server.",
  },
  service: {
    tone: "error",
    title: "Satellite processing service error",
    body: "The Copernicus Data Space / Sentinel Hub service did not complete the request. Please try again shortly.",
  },
  invalid_request: {
    tone: "warning",
    title: "The selected parameters are not valid",
    body: "Check the date range and cloud threshold.",
  },
  network: {
    tone: "error",
    title: "Data service unreachable",
    body: "The portal's data service could not be reached. Please try again shortly.",
  },
  unknown: {
    tone: "error",
    title: "The analysis could not be completed",
    body: "An unexpected error occurred. Please try again.",
  },
};

export function AnalysisError({ error }: { error: unknown }) {
  const e = error as WaterQualityError;
  const copy = ERROR_COPY[e?.kind ?? "unknown"] ?? ERROR_COPY.unknown;
  return (
    <Notice tone={copy.tone} title={copy.title}>
      <p>{copy.body}</p>
      {e?.detail && e.kind !== "boundary" ? (
        <Details>
          {e.detail}
          {e.status ? ` (HTTP ${e.status}${e.code ? `, ${e.code}` : ""})` : null}
        </Details>
      ) : null}
    </Notice>
  );
}

/**
 * Backend trace text minus references to the migration's reference application
 * (kept in the API for audit, not shown to portal users).
 */
function withoutReferenceApp(text: string) {
  return text
    .replace(/\s*\([^)]*\bGEE\b[^)]*\)/g, "")
    .replace(/,\s*as in the GEE [^.;]*/g, "")
    .split(/(?<=\.)\s+/)
    .filter((sentence) => !/\bGEE\b|QA60/.test(sentence))
    .join(" ")
    .trim();
}

/** "http://www.opengis.net/def/crs/EPSG/0/32643" → "EPSG:32643". */
function epsgLabel(uri: string) {
  const match = /EPSG\/0\/(\d+)$/.exec(uri);
  return match ? `EPSG:${match[1]}` : uri;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-3 py-1.5 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words text-foreground">{children}</dd>
    </div>
  );
}

/** Where every value came from, as returned by the backend with the result. */
export function ProvenancePanel({ trace, title }: { trace: Traceability; title: string }) {
  return (
    <details className="rounded-sm border border-border bg-card">
      <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-foreground">
        {title}
      </summary>
      <div className="border-t border-border px-4 py-3">
        <dl className="divide-y divide-border">
          <Row label="Satellite data">
            Sentinel-2 Level-2A surface reflectance ({trace.sentinel_hub_data_type})
          </Row>
          <Row label="Processing">
            Copernicus Data Space Ecosystem — Sentinel Hub {trace.sentinel_hub_api}
          </Row>
          <Row label="Analysis boundary">
            {boundarySourceLabel(trace.roi.source)} · version{" "}
            <span className="font-mono text-xs">{trace.roi.version}</span> ·{" "}
            {trace.roi.area_ha.toLocaleString("en-IN", { maximumFractionDigits: 1 })} ha
          </Row>
          <Row label="Index">
            {trace.index.key} = {trace.index.formula}
          </Row>
          <Row label="Period">
            {trace.date_range.start} to {trace.date_range.end_exclusive} (end date excluded)
          </Row>
          <Row label="Cloud filter">
            {trace.cloud_filter.property} {withoutReferenceApp(trace.cloud_filter.rule)}
          </Row>
          <Row label="Cloud handling">{withoutReferenceApp(trace.cloud_handling)}</Row>
          <Row label="Spatial">
            {trace.spatial.resolution_m.toLocaleString("en-IN")} m · {trace.spatial.aggregation} ·{" "}
            {epsgLabel(trace.spatial.request_crs)}
          </Row>
          <Row label="Generated">
            {new Date(trace.generated_at).toUTCString()}
            {trace.result_cache?.status === "hit"
              ? " (reused from the result cache; no new satellite processing)"
              : null}
          </Row>
        </dl>
      </div>
    </details>
  );
}
