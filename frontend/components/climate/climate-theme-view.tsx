"use client";

import { Database } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { BarChart } from "@/components/charts/bar-chart";
import { ChartFigure } from "@/components/charts/chart-figure";
import { LineChart } from "@/components/charts/line-chart";
import { RamsarMap, type SiteColouring } from "@/components/maps/ramsar-map";
import type { ClimateDataset, ClimateThemeDef } from "@/lib/data/climate";
import type { RamsarSitePoint } from "@/lib/data/ramsar";
import { sequentialRamp } from "@/lib/maps/palette";
import { cn } from "@/lib/utils";

const ALL_YEARS = "mean";

const fieldClass =
  "mt-1 h-10 w-full rounded-sm border border-input bg-card px-3 text-sm text-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring/30";

function mean(values: (number | null | undefined)[]) {
  const valid = values.filter((v): v is number => typeof v === "number");
  return valid.length ? valid.reduce((a, b) => a + b, 0) / valid.length : null;
}

function round(value: number | null, digits = 2) {
  return value === null ? null : Number(value.toFixed(digits));
}

/** Quantile class breaks → strictly ascending [value, colour] stops. */
function quantileStops(values: number[]): [number, string][] {
  if (!values.length) return [];
  const sorted = [...values].sort((a, b) => a - b);
  const n = sequentialRamp.length;
  const stops: [number, string][] = [];
  for (let i = 0; i < n; i++) {
    const q = sorted[Math.round((i / (n - 1)) * (sorted.length - 1))];
    if (!stops.length || q > stops[stops.length - 1][0]) stops.push([q, sequentialRamp[i]]);
  }
  if (stops.length === 1) stops.push([stops[0][0] + 1e-9, sequentialRamp[n - 1]]);
  return stops;
}

function Definition({
  theme,
  dataset,
}: {
  theme: ClimateThemeDef;
  dataset: ClimateDataset | null;
}) {
  return (
    <div className="rounded-sm border border-border border-t-4 border-t-sedge bg-card p-5">
      <h2 className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">
        Indicator definition
      </h2>
      <div className="mt-2 space-y-2 text-sm leading-relaxed text-foreground/85">
        {theme.definition.map((line, i) => (
          <p key={i}>{line}</p>
        ))}
        {dataset?.method ? <p>{dataset.method}</p> : null}
      </div>
      {dataset ? (
        <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 border-t border-border pt-3 text-sm">
          <dt className="text-muted-foreground">Source</dt>
          <dd>{dataset.source}</dd>
          <dt className="text-muted-foreground">Baseline</dt>
          <dd>{dataset.baseline}</dd>
          <dt className="text-muted-foreground">Period</dt>
          <dd>
            {dataset.years[0]}–{dataset.years[dataset.years.length - 1]}
          </dd>
          {dataset.updated ? (
            <>
              <dt className="text-muted-foreground">Updated</dt>
              <dd>{dataset.updated}</dd>
            </>
          ) : null}
        </dl>
      ) : null}
    </div>
  );
}

function AwaitingData({ theme, sites }: { theme: ClimateThemeDef; sites: RamsarSitePoint[] }) {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="min-w-0">
        <RamsarMap
          sites={sites}
          cooperativeGestures
          ariaLabel={`Ramsar Sites monitored for ${theme.title.toLowerCase()}`}
          className="h-[26rem] sm:h-[34rem]"
        />
        <p className="mt-2 text-xs text-muted-foreground">
          Dot-density map of the {sites.length} Ramsar Site locations. Dots will be coloured by the
          selected {theme.title.toLowerCase()} indicator once the dataset is loaded.
        </p>
      </div>
      <div className="space-y-5">
        <Definition theme={theme} dataset={null} />
        <div className="rounded-sm border border-dashed border-input bg-muted p-5">
          <div className="flex items-center gap-2">
            <Database className="size-4 text-primary" aria-hidden="true" />
            <h2 className="font-semibold text-foreground">Indicator dataset not yet loaded</h2>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            No {theme.title.toLowerCase()} values are shown until the project dataset is supplied.
            The analysis will provide:
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-foreground/85">
            <li>Dot-density map of sites coloured by indicator value</li>
            <li>National trend across all Ramsar Sites</li>
            <li>Site ranking and state/UT comparison</li>
            <li>Time series for any individual site</li>
          </ul>
          <p className="mt-3 text-xs text-muted-foreground">
            Expected metrics:{" "}
            {theme.recommendedMetrics.map((m) => `${m.label} (${m.unit})`).join("; ")}.
          </p>
        </div>
      </div>
    </div>
  );
}

export function ClimateThemeView({
  theme,
  sites,
  dataset,
  initialSiteId = null,
}: {
  theme: ClimateThemeDef;
  sites: RamsarSitePoint[];
  dataset: ClimateDataset | null;
  initialSiteId?: number | null;
}) {
  const [metricKey, setMetricKey] = useState(dataset?.metrics[0]?.key ?? "");
  const [year, setYear] = useState<string>(
    dataset ? String(dataset.years[dataset.years.length - 1]) : ALL_YEARS,
  );
  const [siteId, setSiteId] = useState<number | null>(initialSiteId);

  const metric = dataset?.metrics.find((m) => m.key === metricKey) ?? dataset?.metrics[0];

  const analysis = useMemo(() => {
    if (!dataset || !metric) return null;
    const yearIndex = year === ALL_YEARS ? -1 : dataset.years.indexOf(Number(year));
    const valueFor = (id: number): number | null => {
      const series = metric.values[String(id)];
      if (!series) return null;
      return yearIndex === -1 ? mean(series) : (series[yearIndex] ?? null);
    };

    const values: Record<number, number | null> = {};
    for (const s of sites) values[s.id] = valueFor(s.id);
    const present = Object.values(values).filter((v): v is number => v !== null);
    const colouring: SiteColouring = { values, stops: quantileStops(present) };

    const national = dataset.years.map((_, i) =>
      round(mean(Object.values(metric.values).map((series) => series[i]))),
    );
    const reporting = dataset.years.map(
      (_, i) => Object.values(metric.values).filter((series) => series[i] !== null).length,
    );

    const ranked = sites
      .map((s) => ({ site: s, value: values[s.id] }))
      .filter((r): r is { site: RamsarSitePoint; value: number } => r.value !== null)
      .sort((a, b) => b.value - a.value);

    const stateMap = new Map<string, number[]>();
    for (const r of ranked)
      stateMap.set(r.site.state, [...(stateMap.get(r.site.state) ?? []), r.value]);
    const states = [...stateMap.entries()]
      .map(([name, vals]) => ({ name, value: round(mean(vals))!, n: vals.length }))
      .sort((a, b) => b.value - a.value);

    return { colouring, national, reporting, ranked, states, present };
  }, [dataset, metric, year, sites]);

  if (!dataset || !metric || !analysis) return <AwaitingData theme={theme} sites={sites} />;

  const periodLabel =
    year === ALL_YEARS ? `mean ${dataset.years[0]}–${dataset.years.at(-1)}` : year;
  const selected = sites.find((s) => s.id === siteId) ?? null;
  const selectedSeries = selected ? (metric.values[String(selected.id)] ?? null) : null;
  const top = analysis.ranked.slice(0, 15);
  // Emphasise the selected site only when it is in the top list.
  const topIndex = top.findIndex((r) => r.site.id === siteId);
  const stops = analysis.colouring.stops;

  return (
    <div className="space-y-6">
      <div className="grid gap-3 rounded-sm border border-border bg-card p-4 sm:grid-cols-3">
        <div>
          <label htmlFor="metric" className="text-xs font-semibold text-muted-foreground">
            Indicator
          </label>
          <select
            id="metric"
            value={metric.key}
            onChange={(e) => setMetricKey(e.target.value)}
            className={fieldClass}
          >
            {dataset.metrics.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label} ({m.unit})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="year" className="text-xs font-semibold text-muted-foreground">
            Year
          </label>
          <select
            id="year"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            className={fieldClass}
          >
            <option value={ALL_YEARS}>
              Mean {dataset.years[0]}–{dataset.years.at(-1)}
            </option>
            {[...dataset.years].reverse().map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="site" className="text-xs font-semibold text-muted-foreground">
            Site time series
          </label>
          <select
            id="site"
            value={siteId ?? ""}
            onChange={(e) => setSiteId(e.target.value ? Number(e.target.value) : null)}
            className={fieldClass}
          >
            <option value="">Select a Ramsar Site…</option>
            {[...sites]
              .sort((a, b) => a.name.localeCompare(b.name))
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
          </select>
        </div>
        {metric.description ? (
          <p className="text-sm text-muted-foreground sm:col-span-3">{metric.description}</p>
        ) : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0">
          <RamsarMap
            sites={sites}
            colouring={analysis.colouring}
            selectedId={siteId}
            onSelect={setSiteId}
            cooperativeGestures
            ariaLabel={`Dot-density map of ${metric.label}, ${periodLabel}`}
            className="h-[26rem] sm:h-[34rem]"
          />
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
            <span className="font-semibold text-foreground">
              {metric.label} ({metric.unit}), {periodLabel}
            </span>
            <span className="flex items-center gap-1" aria-hidden="true">
              {stops.map(([value, colour], i) => (
                <span key={i} className="flex flex-col items-center gap-0.5">
                  <span
                    className="block h-2.5 w-8 border border-[#14244b]/40"
                    style={{ backgroundColor: colour }}
                  />
                  <span className="tabular-nums">{round(value, 1)}</span>
                </span>
              ))}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-full bg-[#a3a9b4]" /> No data
            </span>
            <span>
              {analysis.present.length} of {sites.length} sites with values · quantile classes
            </span>
          </div>
        </div>
        <Definition theme={theme} dataset={dataset} />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ChartFigure
          title={`${metric.label} — all-site average`}
          subtitle={`Mean across Ramsar Sites with data, ${metric.unit}`}
          source={dataset.source}
          table={{
            columns: ["Year", `Mean (${metric.unit})`, "Sites reporting"],
            rows: dataset.years.map((y, i) => [y, analysis.national[i], analysis.reporting[i]]),
          }}
        >
          <LineChart
            x={dataset.years}
            series={[{ name: "All-site average", values: analysis.national }]}
            unit={metric.unit}
            ariaLabel={`Line chart of the all-site average ${metric.label} by year`}
          />
        </ChartFigure>

        <ChartFigure
          title={selected ? selected.name : "Individual site"}
          subtitle={
            selected
              ? `${metric.label}, ${metric.unit} — compared with the all-site average`
              : "Select a site on the map or from the list above"
          }
          source={dataset.source}
          table={
            selectedSeries
              ? {
                  columns: ["Year", selected!.name, "All-site average"],
                  rows: dataset.years.map((y, i) => [y, selectedSeries[i], analysis.national[i]]),
                }
              : undefined
          }
        >
          {selected && selectedSeries ? (
            <LineChart
              x={dataset.years}
              series={[
                { name: selected.name, values: selectedSeries },
                { name: "All-site average", values: analysis.national, style: "dashed" },
              ]}
              unit={metric.unit}
              ariaLabel={`Line chart of ${metric.label} at ${selected.name}`}
            />
          ) : (
            <div
              className={cn(
                "flex h-[300px] items-center justify-center px-6 text-center text-sm text-muted-foreground",
              )}
            >
              {selected
                ? `No ${metric.label.toLowerCase()} values for ${selected.name} in this dataset.`
                : "No site selected."}
            </div>
          )}
        </ChartFigure>

        <ChartFigure
          title={`Highest ${metric.label.toLowerCase()} — top ${top.length} sites`}
          subtitle={`${metric.unit}, ${periodLabel}`}
          source={dataset.source}
          table={{
            columns: ["Rank", "Site", "State / UT", metric.unit],
            rows: analysis.ranked.map((r, i) => [i + 1, r.site.name, r.site.state, round(r.value)]),
          }}
        >
          <BarChart
            categories={top.map((r) => r.site.name)}
            values={top.map((r) => round(r.value))}
            horizontal
            unit={metric.unit}
            height={Math.max(260, top.length * 24)}
            highlightIndex={topIndex >= 0 ? topIndex : null}
            ariaLabel={`Ranking of sites by ${metric.label}`}
          />
        </ChartFigure>

        <ChartFigure
          title="State / UT comparison"
          subtitle={`Mean of site values, ${metric.unit}, ${periodLabel}`}
          source={dataset.source}
          table={{
            columns: ["State / UT", `Mean (${metric.unit})`, "Sites"],
            rows: analysis.states.map((s) => [s.name, s.value, s.n]),
          }}
        >
          <BarChart
            categories={analysis.states.map((s) => s.name)}
            values={analysis.states.map((s) => s.value)}
            horizontal
            unit={metric.unit}
            height={Math.max(260, analysis.states.length * 22)}
            ariaLabel={`State comparison of ${metric.label}`}
          />
        </ChartFigure>
      </div>

      {selected ? (
        <p className="text-sm">
          <Link
            href={`/wetlands/${selected.id}`}
            className="font-semibold text-primary hover:underline"
          >
            Open the {selected.name} site profile
          </Link>
        </p>
      ) : null}
    </div>
  );
}
