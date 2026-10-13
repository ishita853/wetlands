// Server-side only (uses backendFetch); never import in client components.
import { backendFetch } from "@/lib/api/backend";
import { getRamsarSites } from "@/lib/data/ramsar";
import type {
  AvailabilityStatus,
  BackendWetland,
  IndexDefinition,
  WaterQualitySite,
} from "@/types/water-quality";

export type WaterQualityPageData = {
  sites: WaterQualitySite[];
  indices: IndexDefinition[];
  /** Set when the backend could not be reached; availability is then unknown. */
  serviceError: string | null;
};

function availabilityOf(w: BackendWetland | undefined): AvailabilityStatus {
  if (!w) return "unknown";
  const b = w.boundaries;
  if (b.water_quality_analysis.status === "available") return "available";
  if (b.provided_roi.status === "invalid" || b.official_boundary.status === "invalid") {
    return "geometry_invalid";
  }
  return "boundary_unavailable";
}

/**
 * All 101 Ramsar Sites from the master list, each with the backend's current
 * water-quality availability. Sites are never dropped: if the backend is
 * unreachable, availability is "unknown".
 */
export async function getWaterQualityPageData(): Promise<WaterQualityPageData> {
  let wetlands: BackendWetland[] = [];
  let indices: IndexDefinition[] = [];
  let serviceError: string | null = null;
  try {
    [wetlands, indices] = await Promise.all([
      backendFetch<BackendWetland[]>("/wetlands"),
      backendFetch<IndexDefinition[]>("/water-quality/indices"),
    ]);
  } catch {
    serviceError =
      "The water-quality service could not be reached, so analysis availability is not known.";
  }
  const byId = new Map(wetlands.map((w) => [w.ramsar_site_id, w]));

  const sites = getRamsarSites()
    .map((site): WaterQualitySite => {
      const w = byId.get(site.id);
      const availability = availabilityOf(w);
      return {
        id: site.id,
        name: site.name,
        state: site.state,
        district: site.district,
        designationYear: site.designationYear,
        areaHa: site.areaHa,
        latitude: site.latitude,
        longitude: site.longitude,
        availability,
        analysisSource: w?.boundaries.water_quality_analysis.source ?? null,
        reason:
          availability === "available"
            ? null
            : (w?.boundaries.water_quality_analysis.reason ?? null),
        officialBoundaryStatus: w?.boundaries.official_boundary.status ?? null,
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name));

  return { sites, indices, serviceError };
}
