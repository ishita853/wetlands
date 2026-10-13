"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, ExternalLink, Loader2, Play } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { ChartFigure } from "@/components/charts/chart-figure";
import {
  AnalysisError,
  ProvenancePanel,
  UnavailableNotice,
  boundarySourceLabel,
} from "@/components/water-quality/analysis-panels";
import { IndexLegend } from "@/components/water-quality/index-legend";
import { IndexMap } from "@/components/water-quality/index-map";
import { IndexTimeSeriesChart } from "@/components/water-quality/index-time-series-chart";
import { Methodology } from "@/components/water-quality/methodology";
import { SiteSelector } from "@/components/water-quality/site-selector";
import {
  type AnalysisParams,
  fetchAnalysisBoundary,
  fetchIndexMap,
  fetchIndexTimeSeries,
  geotiffUrl,
} from "@/lib/api/water-quality";
import { cn } from "@/lib/utils";
import type {
  IndexDefinition,
  IndexKey,
  TimeSeriesPoint,
  WaterQualitySite,
} from "@/types/water-quality";

// Reference period of the GEE application (end date excluded), as in the backend defaults.
const DEFAULT_START = "2022-11-01";
const DEFAULT_END = "2026-05-30";
const DEFAULT_MAX_CLOUD = 100;

const fieldClass =
  "mt-1 h-9 w-full rounded-sm border border-input bg-card px-2.5 text-sm text-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring/30";

const num = (v: number | null, digits = 3) =>
  v === null
    ? "—"
    : v.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });

function SiteInfo({ site }: { site: WaterQualitySite }) {
  return (
    <section
      aria-labelledby="wq-site"
      className="rounded-sm border border-border bg-card p-4 sm:p-5"
    >
      <div>
        <h2 id="wq-site" className="text-lg font-semibold text-foreground">
          {site.name}
        </h2>
        <p className="text-sm text-muted-foreground">
          Ramsar Site no. {site.id} · {site.state}
        </p>
      </div>
      <dl className="mt-4 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2 xl:grid-cols-3">
        <div>
          <dt className="text-xs text-muted-foreground">Designated</dt>
          <dd className="font-medium">{site.designationYear}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Area (Ramsar)</dt>
          <dd className="font-medium tabular-nums">
            {site.areaHa.toLocaleString("en-IN", { maximumFractionDigits: 1 })} ha
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Coordinates</dt>
          <dd className="font-medium tabular-nums">
            {site.latitude.toFixed(4)}° N, {site.longitude.toFixed(4)}° E
          </dd>
        </div>
        <div className="sm:col-span-2 xl:col-span-3">
          <dt className="text-xs text-muted-foreground">Analysis boundary</dt>
          <dd className="font-medium">
            {site.availability === "available"
              ? boundarySourceLabel(site.analysisSource)
              : "No validated analysis boundary"}
          </dd>
        </div>
      </dl>
      <Link
        href={`/wetlands/${site.id}`}
        className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
      >
        Site profile
        <ExternalLink className="size-3.5" aria-hidden="true" />
      </Link>
    </section>
  );
}

function toCsv(indexKey: string, points: TimeSeriesPoint[]) {
  const header =
    "date_utc,index,mean,min,max,st_dev,valid_pixels,sample_count,tiles,tile_cloud_cover_percent,product_ids";
  const rows = points.map((p) =>
    [
      p.date,
      indexKey,
      p.mean,
      p.min ?? "",
      p.max ?? "",
      p.st_dev ?? "",
      p.valid_pixels,
      p.sample_count,
      p.scenes.map((s) => s.tile_id ?? "").join(" "),
      p.scenes.map((s) => s.cloud_cover ?? "").join(" "),
      p.scenes.map((s) => s.id).join(" "),
    ].join(","),
  );
  return [header, ...rows].join("\n");
}

function LoadingState({ message }: { message: string }) {
  return (
    <div
      role="status"
      className="flex items-center gap-2 rounded-sm border border-dashed border-input bg-muted px-4 py-6 text-sm text-muted-foreground"
    >
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      {message}
    </div>
  );
}

export function WaterQualityExplorer({
  sites,
  indices,
  serviceError,
  initialSiteId,
}: {
  sites: WaterQualitySite[];
  indices: IndexDefinition[];
  serviceError: string | null;
  initialSiteId: number | null;
}) {
  const [siteId, setSiteId] = useState<number | null>(initialSiteId);
  const [indexKey, setIndexKey] = useState<IndexKey>((indices[0]?.key as IndexKey) ?? "NDCI");
  const [start, setStart] = useState(DEFAULT_START);
  const [end, setEnd] = useState(DEFAULT_END);
  const [maxCloud, setMaxCloud] = useState(DEFAULT_MAX_CLOUD);
  const [submitted, setSubmitted] = useState<AnalysisParams | null>(null);

  const site = useMemo(() => sites.find((s) => s.id === siteId) ?? null, [sites, siteId]);
  const available = site?.availability === "available";
  const activeIndex = indices.find((i) => i.key === (submitted?.index ?? indexKey)) ?? indices[0];

  const selectSite = (id: number) => {
    setSiteId(id);
    setSubmitted(null); // never reuse another site's request
    window.history.replaceState(null, "", `?site=${id}`);
  };

  const boundary = useQuery({
    queryKey: ["wq-boundary", siteId],
    queryFn: () => fetchAnalysisBoundary(siteId as number),
    enabled: available,
    retry: false,
    staleTime: Infinity,
  });
  const map = useQuery({
    queryKey: ["wq-map", submitted],
    queryFn: () => fetchIndexMap(submitted as AnalysisParams),
    enabled: submitted !== null,
    retry: false,
    staleTime: Infinity,
  });
  const series = useQuery({
    queryKey: ["wq-series", submitted],
    queryFn: () => fetchIndexTimeSeries(submitted as AnalysisParams),
    enabled: submitted !== null,
    retry: false,
    staleTime: Infinity,
  });

  const paramError =
    start >= end
      ? "The start date must be before the end date."
      : !(maxCloud > 0 && maxCloud <= 100)
        ? "The cloud threshold must be greater than 0 and at most 100 %."
        : null;

  // The results on screen always belong to the last run; flag when controls differ.
  const settingsChanged =
    submitted !== null &&
    (submitted.index !== indexKey ||
      submitted.start !== start ||
      submitted.end !== end ||
      submitted.maxCloud !== maxCloud);

  const run = () => {
    if (!site || !available || paramError) return;
    setSubmitted({ siteId: site.id, index: indexKey, start, end, maxCloud });
  };

  const csvHref = useMemo(() => {
    if (!series.data) return null;
    return `data:text/csv;charset=utf-8,${encodeURIComponent(toCsv(series.data.index.key, series.data.points))}`;
  }, [series.data]);

  return (
    <div className="space-y-8">
      {serviceError ? (
        <p
          role="alert"
          className="rounded-sm border border-destructive/30 bg-destructive/5 p-3 text-sm"
        >
          {serviceError}
        </p>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[20rem_minmax(0,1fr)]">
        <SiteSelector sites={sites} selectedId={siteId} onSelect={selectSite} />

        <div className="min-w-0 space-y-5">
          {!site ? (
            <div className="rounded-sm border border-dashed border-input bg-muted p-6 text-sm text-muted-foreground">
              Select a Ramsar Site from the list to view its analysis availability and run the
              water-quality analysis.
            </div>
          ) : (
            <>
              <SiteInfo site={site} />

              {!available ? (
                <UnavailableNotice site={site} />
              ) : (
                <>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      run();
                    }}
                    className="rounded-sm border border-border bg-card p-4 sm:p-5"
                    aria-labelledby="wq-controls"
                  >
                    <h2
                      id="wq-controls"
                      className="text-xs font-bold tracking-[0.14em] text-muted-foreground uppercase"
                    >
                      Analysis
                    </h2>
                    <fieldset className="mt-3">
                      <legend className="text-sm font-medium text-foreground">Index</legend>
                      <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                        {indices.map((index) => (
                          <label
                            key={index.key}
                            className={cn(
                              "flex cursor-pointer flex-col rounded-sm border px-3 py-2 text-sm transition-colors",
                              indexKey === index.key
                                ? "border-primary bg-primary/5"
                                : "border-border hover:border-primary/50",
                            )}
                          >
                            <span className="flex items-center gap-2">
                              <input
                                type="radio"
                                name="index"
                                value={index.key}
                                checked={indexKey === index.key}
                                onChange={() => setIndexKey(index.key)}
                                className="accent-[var(--primary)]"
                              />
                              <span className="font-semibold">{index.key}</span>
                            </span>
                            <span className="mt-0.5 text-xs text-muted-foreground">
                              {index.name}
                            </span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                    <div className="mt-4 grid gap-3 sm:grid-cols-3">
                      <label className="text-sm font-medium">
                        From
                        <input
                          type="date"
                          value={start}
                          min="2017-03-28"
                          onChange={(e) => setStart(e.target.value)}
                          className={fieldClass}
                          required
                        />
                      </label>
                      <label className="text-sm font-medium">
                        To (date excluded)
                        <input
                          type="date"
                          value={end}
                          onChange={(e) => setEnd(e.target.value)}
                          className={fieldClass}
                          required
                        />
                      </label>
                      <label className="text-sm font-medium">
                        Max. tile cloud cover (%)
                        <input
                          type="number"
                          min={1}
                          max={100}
                          step={1}
                          value={maxCloud}
                          onChange={(e) => setMaxCloud(Number(e.target.value))}
                          className={fieldClass}
                          required
                        />
                      </label>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Default period: {DEFAULT_START} to {DEFAULT_END}. The cloud threshold uses
                      Sentinel-2 tile-level cloud cover; 100 keeps every tile below 100 %.
                    </p>
                    {paramError ? (
                      <p role="alert" className="mt-2 text-sm text-destructive">
                        {paramError}
                      </p>
                    ) : null}
                    <button
                      type="submit"
                      disabled={!!paramError || map.isFetching || series.isFetching}
                      className="mt-4 inline-flex h-9 items-center gap-2 rounded-sm bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-50"
                    >
                      {map.isFetching || series.isFetching ? (
                        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                      ) : (
                        <Play className="size-4" aria-hidden="true" />
                      )}
                      Run analysis
                    </button>
                    {settingsChanged && submitted ? (
                      <p
                        role="status"
                        className="mt-3 rounded-sm border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950"
                      >
                        The results below are for {submitted.index}, {submitted.start} to{" "}
                        {submitted.end} (end excluded), tile cloud cover up to {submitted.maxCloud}{" "}
                        %. Run the analysis again to apply the changed settings.
                      </p>
                    ) : null}
                  </form>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {site && available ? (
        <div className="space-y-5">
          <section
            aria-labelledby="wq-map-title"
            className="rounded-sm border border-border bg-card"
          >
            <div className="border-b border-border px-4 py-3">
              <h2 id="wq-map-title" className="font-semibold text-foreground">
                {submitted ? `${submitted.index} map` : "Analysis boundary"}
              </h2>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {map.data?.traceability.selected_scene
                  ? `Sentinel-2 acquisition of ${new Date(map.data.traceability.selected_scene.acquired_at).toLocaleDateString("en-IN", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" })} (least cloudy in the period)`
                  : "Run the analysis to load the index for the selected period."}
              </p>
            </div>
            <div className="grid gap-0 xl:grid-cols-[minmax(0,1fr)_19rem]">
              <div className="relative min-w-0">
                <IndexMap
                  key={site.id}
                  latitude={site.latitude}
                  longitude={site.longitude}
                  boundary={boundary.data?.geometry ?? null}
                  raster={
                    map.data
                      ? {
                          dataUri: map.data.image.data_uri,
                          coordinates: map.data.image.coordinates,
                        }
                      : null
                  }
                  ariaLabel={`${site.name}: ${submitted?.index ?? "analysis boundary"} over satellite imagery`}
                  className="h-[24rem] sm:h-[30rem]"
                />
                {map.isFetching ? (
                  <div className="absolute inset-x-3 bottom-3">
                    <LoadingState message="Selecting the least-cloudy Sentinel-2 scene and processing the index via Sentinel Hub…" />
                  </div>
                ) : null}
              </div>
              <div className="space-y-4 border-t border-border p-4 xl:border-t-0 xl:border-l">
                {activeIndex ? <IndexLegend index={activeIndex} /> : null}
                {boundary.isError ? <AnalysisError error={boundary.error} /> : null}
                {map.isError ? <AnalysisError error={map.error} /> : null}
                {map.data ? (
                  <div className="text-xs text-muted-foreground">
                    <p>
                      Mean {map.data.index.key} {num(map.data.value_summary.mean)} (min{" "}
                      {num(map.data.value_summary.min)}, max {num(map.data.value_summary.max)}) over{" "}
                      {map.data.pixel_counts.valid.toLocaleString("en-IN")} valid pixels at{" "}
                      {map.data.traceability.spatial.resolution_m} m;{" "}
                      {map.data.pixel_counts.cloud_masked.toLocaleString("en-IN")} cloud-masked.
                    </p>
                    {submitted ? (
                      <a
                        href={geotiffUrl(submitted)}
                        className="mt-2 inline-flex items-center gap-1 font-medium text-primary hover:underline"
                      >
                        <Download className="size-3.5" aria-hidden="true" />
                        Index values (GeoTIFF, float32)
                      </a>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </div>
          </section>

          {submitted ? (
            series.isFetching ? (
              <LoadingState message="Computing the wetland-mean index for every Sentinel-2 acquisition in the period (Sentinel Hub Statistical API)…" />
            ) : series.isError ? (
              <AnalysisError error={series.error} />
            ) : series.data ? (
              <ChartFigure
                title={`${series.data.index.key} — wetland mean per Sentinel-2 acquisition day`}
                subtitle={`${series.data.points.length} observation days, ${series.data.traceability.date_range.start} to ${series.data.traceability.date_range.end_exclusive} (end excluded). Each point is one acquisition day.`}
                source={`Copernicus Sentinel-2 L2A via Copernicus Data Space Ecosystem (Sentinel Hub Statistical API); analysis boundary: ${boundarySourceLabel(series.data.traceability.roi.source)}.`}
                table={{
                  columns: [
                    "Date (UTC)",
                    "Mean",
                    "Min",
                    "Max",
                    "Std. dev.",
                    "Valid pixels",
                    "Tile",
                    "Tile cloud %",
                  ],
                  rows: series.data.points.map((p) => [
                    p.date,
                    num(p.mean),
                    num(p.min),
                    num(p.max),
                    num(p.st_dev),
                    `${p.valid_pixels} / ${p.sample_count}`,
                    p.scenes.map((s) => s.tile_id ?? "?").join(", ") || "—",
                    p.scenes.map((s) => s.cloud_cover ?? "—").join(", ") || "—",
                  ]),
                }}
              >
                {series.data.points.length ? (
                  <IndexTimeSeriesChart
                    points={series.data.points}
                    indexKey={series.data.index.key}
                    visMin={series.data.index.vis_min}
                    visMax={series.data.index.vis_max}
                  />
                ) : (
                  <p className="px-2 py-10 text-center text-sm text-muted-foreground">
                    Sentinel Hub returned no valid observations for this wetland and period.
                  </p>
                )}
                {csvHref ? (
                  <a
                    href={csvHref}
                    download={`ramsar${series.data.wetland.ramsar_site_id}_${series.data.index.key}_timeseries.csv`}
                    className="mx-2 mb-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                  >
                    <Download className="size-3.5" aria-hidden="true" />
                    Download time series (CSV)
                  </a>
                ) : null}
              </ChartFigure>
            ) : null
          ) : null}

          {map.data ? (
            <ProvenancePanel trace={map.data.traceability} title="Map data provenance" />
          ) : null}
        </div>
      ) : null}

      {indices.length ? <Methodology indices={indices} /> : null}
    </div>
  );
}
