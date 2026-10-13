import fs from "node:fs";
import path from "node:path";

import { z } from "zod";

import { getRamsarSites } from "@/lib/data/ramsar";

/**
 * Climate indicator datasets are supplied by the project team as JSON files
 * in data/climate/<theme>.json (format: data/climate/README.md). Nothing is
 * computed or estimated here — a missing file means the theme shows its
 * "dataset not loaded" state. Files are validated at build time.
 */

export type ClimateThemeKey =
  "wetland-drought" | "precipitation-extremes" | "heat-waves" | "cold-waves";

export type ClimateThemeDef = {
  key: ClimateThemeKey;
  title: string;
  href: string;
  summary: string;
  /** Agreed indicator definition (percentile-based, WMO/ETCCDI style). */
  definition: string[];
  /** Metrics the team is expected to supply, in display order. */
  recommendedMetrics: { key: string; label: string; unit: string }[];
};

export const BASELINE = "1991–2020";

export const climateThemeDefs: Record<ClimateThemeKey, ClimateThemeDef> = {
  "wetland-drought": {
    key: "wetland-drought",
    title: "Wetland Drought",
    href: "/climate/drought",
    summary:
      "Deficits in water availability at each Ramsar Site, expressed as a standardised drought index relative to the site's own climate.",
    definition: [
      `Drought is measured with a 3-month standardised index (SPEI-3, or SPI-3 where evapotranspiration is unavailable) fitted to each site's ${BASELINE} baseline.`,
      "A month is a drought month when the index is at or below −1.0 (moderate drought or worse); at or below −1.5 is severe, and at or below −2.0 extreme.",
    ],
    recommendedMetrics: [
      { key: "drought_months", label: "Drought months (index ≤ −1.0)", unit: "months/year" },
      { key: "min_index", label: "Lowest 3-month index", unit: "index" },
    ],
  },
  "precipitation-extremes": {
    key: "precipitation-extremes",
    title: "Precipitation Extremes",
    href: "/climate/precipitation",
    summary:
      "Very heavy rainfall and prolonged dry spells at each Ramsar Site, using percentile thresholds from the site's own record.",
    definition: [
      `A very wet day is a day whose rainfall exceeds the 95th percentile of wet-day (≥ 1 mm) rainfall at the site over ${BASELINE}.`,
      "Dry spells are runs of consecutive days with less than 1 mm of rainfall.",
    ],
    recommendedMetrics: [
      { key: "r95p", label: "Rainfall on very wet days (R95p)", unit: "mm/year" },
      { key: "rx1day", label: "Maximum 1-day rainfall (Rx1day)", unit: "mm" },
      { key: "cdd", label: "Longest dry spell (CDD)", unit: "days" },
    ],
  },
  "heat-waves": {
    key: "heat-waves",
    title: "Heat Waves",
    href: "/climate/heat-waves",
    summary:
      "Spells of unusually high daily maximum temperature at each Ramsar Site, relative to that site's own climate.",
    definition: [
      `A heat wave is a run of at least 3 consecutive days on which the daily maximum temperature exceeds the site's 90th percentile for that calendar day (15-day window, ${BASELINE}).`,
      "Percentile thresholds make the definition comparable across high-altitude, inland and coastal sites.",
    ],
    recommendedMetrics: [
      { key: "hw_events", label: "Heat-wave events", unit: "events/year" },
      { key: "hw_days", label: "Heat-wave days", unit: "days/year" },
      { key: "hw_max_duration", label: "Longest heat wave", unit: "days" },
    ],
  },
  "cold-waves": {
    key: "cold-waves",
    title: "Cold Waves",
    href: "/climate/cold-waves",
    summary:
      "Spells of unusually low daily minimum temperature at each Ramsar Site, relative to that site's own climate.",
    definition: [
      `A cold wave is a run of at least 3 consecutive days on which the daily minimum temperature falls below the site's 10th percentile for that calendar day (15-day window, ${BASELINE}).`,
      "Percentile thresholds make the definition comparable across high-altitude, inland and coastal sites.",
    ],
    recommendedMetrics: [
      { key: "cw_events", label: "Cold-wave events", unit: "events/year" },
      { key: "cw_days", label: "Cold-wave days", unit: "days/year" },
      { key: "cw_max_duration", label: "Longest cold wave", unit: "days" },
    ],
  },
};

export const climateThemeOrder: ClimateThemeKey[] = [
  "wetland-drought",
  "precipitation-extremes",
  "heat-waves",
  "cold-waves",
];

const metricSchema = z.object({
  key: z.string().min(1),
  label: z.string().min(1),
  unit: z.string().min(1),
  description: z.string().optional(),
  /** Keyed by Ramsar Site number; each array aligns with `years`. */
  values: z.record(z.string().regex(/^\d+$/), z.array(z.number().nullable())),
});

const datasetSchema = z.object({
  theme: z.enum(["wetland-drought", "precipitation-extremes", "heat-waves", "cold-waves"]),
  source: z.string().min(1),
  baseline: z.string().min(1),
  method: z.string().optional(),
  updated: z.string().optional(),
  years: z.array(z.number().int()).min(1),
  metrics: z.array(metricSchema).min(1),
});

export type ClimateDataset = z.infer<typeof datasetSchema>;
export type ClimateMetric = ClimateDataset["metrics"][number];

// CLIMATE_DATA_DIR lets a deployment (or the backend pipeline) supply the
// files from elsewhere; defaults to the repository's data/climate folder.
const CLIMATE_DIR = process.env.CLIMATE_DATA_DIR ?? path.join(process.cwd(), "data", "climate");

/** Loads and validates data/climate/<theme>.json, or returns null if absent. */
export function getClimateDataset(theme: ClimateThemeKey): ClimateDataset | null {
  const file = path.join(CLIMATE_DIR, `${theme}.json`);
  if (!fs.existsSync(file)) return null;

  const parsed = datasetSchema.safeParse(JSON.parse(fs.readFileSync(file, "utf8")));
  if (!parsed.success) {
    throw new Error(`Invalid climate dataset ${file}:\n${z.prettifyError(parsed.error)}`);
  }
  const data = parsed.data;
  if (data.theme !== theme) {
    throw new Error(`${file} declares theme "${data.theme}", expected "${theme}"`);
  }

  if (data.years.some((year, i) => i > 0 && year <= data.years[i - 1])) {
    throw new Error(`${file}: "years" must be in increasing order without repeats`);
  }
  const keys = data.metrics.map((m) => m.key);
  if (new Set(keys).size !== keys.length) {
    throw new Error(`${file}: metric keys must be unique`);
  }

  const knownIds = new Set(getRamsarSites().map((s) => String(s.id)));
  for (const metric of data.metrics) {
    for (const [siteId, series] of Object.entries(metric.values)) {
      if (!knownIds.has(siteId)) {
        throw new Error(`${file}: metric "${metric.key}" has unknown Ramsar Site ${siteId}`);
      }
      if (series.length !== data.years.length) {
        throw new Error(
          `${file}: metric "${metric.key}", site ${siteId} has ${series.length} values for ${data.years.length} years`,
        );
      }
    }
  }
  return data;
}

export function getClimateStatus() {
  return climateThemeOrder.map((key) => {
    const data = getClimateDataset(key);
    return {
      theme: climateThemeDefs[key],
      loaded: data !== null,
      years: data ? [data.years[0], data.years[data.years.length - 1]] : null,
      siteCount: data ? new Set(data.metrics.flatMap((m) => Object.keys(m.values))).size : 0,
      source: data?.source ?? null,
    };
  });
}
