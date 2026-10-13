import { env } from "@/config/env";
import type { IndexKey, MapResponse, RoiFeature, TimeSeriesResponse } from "@/types/water-quality";

/**
 * Browser-side calls to the public water-quality endpoints. Credentials for
 * Copernicus stay in the backend; these requests carry none.
 */

export type ErrorKind =
  | "boundary" // HTTP 409: no validated analysis polygon for the site
  | "no_scenes" // no Sentinel-2 scene matched the filters
  | "not_configured" // satellite service not configured on the server
  | "service" // Sentinel Hub / Copernicus failure, rate limit or timeout
  | "invalid_request"
  | "network"
  | "unknown";

export class WaterQualityError extends Error {
  constructor(
    public status: number,
    public kind: ErrorKind,
    public code: string | null,
    /** Technical detail from the backend, shown in a details area only. */
    public detail: string | null,
  ) {
    super(detail ?? `Request failed (${status}).`);
    this.name = "WaterQualityError";
  }
}

function classify(status: number, code: string | null): ErrorKind {
  if (status === 409 || code?.startsWith("roi_")) return "boundary";
  if (code === "no_scenes") return "no_scenes";
  if (code === "copernicus_not_configured") return "not_configured";
  if (status === 422) return "invalid_request";
  if ([502, 503, 504].includes(status)) return "service";
  return "unknown";
}

async function getJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${env.apiUrl}/api/v1${path}`, {
      headers: { Accept: "application/json" },
    });
  } catch {
    throw new WaterQualityError(
      0,
      "network",
      null,
      "The portal's data service could not be reached.",
    );
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail: string | null = null;
    try {
      const body = await response.json();
      const d = body?.detail;
      if (d && typeof d === "object" && !Array.isArray(d)) {
        code = typeof d.code === "string" ? d.code : null;
        detail = typeof d.message === "string" ? d.message : null;
      } else if (typeof d === "string") {
        detail = d;
      } else if (Array.isArray(d)) {
        detail = d.map((x: { msg?: string }) => x?.msg ?? String(x)).join(" ");
      }
    } catch {
      // Non-JSON error body.
    }
    throw new WaterQualityError(response.status, classify(response.status, code), code, detail);
  }
  return (await response.json()) as T;
}

export type AnalysisParams = {
  siteId: number;
  index: IndexKey;
  start: string;
  end: string;
  maxCloud: number;
};

function query(p: AnalysisParams) {
  return new URLSearchParams({
    start: p.start,
    end: p.end,
    max_cloud: String(p.maxCloud),
  }).toString();
}

export function fetchIndexMap(p: AnalysisParams) {
  return getJson<MapResponse>(`/water-quality/${p.siteId}/${p.index}/map?${query(p)}`);
}

export function fetchIndexTimeSeries(p: AnalysisParams) {
  return getJson<TimeSeriesResponse>(
    `/water-quality/${p.siteId}/${p.index}/timeseries?${query(p)}`,
  );
}

/** The polygon the analysis uses (roi=analysis). */
export function fetchAnalysisBoundary(siteId: number) {
  return getJson<RoiFeature>(`/wetlands/${siteId}/roi`);
}

export function geotiffUrl(p: AnalysisParams) {
  return `${env.apiUrl}/api/v1/water-quality/${p.siteId}/${p.index}/map.tif?${query(p)}`;
}
