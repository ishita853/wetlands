"use client";

import type { EChartsOption } from "echarts";
import ReactECharts from "echarts-for-react";
import { useMemo } from "react";

import { axisStyle, baseChartOption } from "@/lib/charts/theme";
import { chartPalette } from "@/lib/maps/palette";
import type { TimeSeriesPoint } from "@/types/water-quality";

const fmt = (v: number | null) =>
  v === null
    ? "—"
    : v.toLocaleString("en-IN", { minimumFractionDigits: 3, maximumFractionDigits: 3 });

/** Axis bounds fitted to the observed means (0.1 steps), kept inside the index range. */
function fittedRange(points: TimeSeriesPoint[], visMin: number, visMax: number) {
  const values = points.map((p) => p.mean).filter((v): v is number => v !== null);
  if (!values.length) return { min: visMin, max: visMax };
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const pad = Math.max((hi - lo) * 0.1, 0.05);
  return {
    min: Math.max(visMin, Math.floor((lo - pad) * 10) / 10),
    max: Math.min(visMax, Math.ceil((hi + pad) * 10) / 10),
  };
}

/**
 * ROI-mean index for each Sentinel-2 acquisition day returned by the backend.
 * One marker per observation; nothing is drawn between observations, so no
 * value is implied where none exists.
 */
export function IndexTimeSeriesChart({
  points,
  indexKey,
  visMin,
  visMax,
  height = 340,
}: {
  points: TimeSeriesPoint[];
  indexKey: string;
  visMin: number;
  visMax: number;
  height?: number;
}) {
  const option = useMemo<EChartsOption>(() => {
    const base = baseChartOption();
    const byTime = new Map(points.map((p) => [Date.parse(p.date), p]));
    const range = fittedRange(points, visMin, visMax);
    return {
      ...base,
      aria: {
        enabled: true,
        label: {
          description: `${indexKey} wetland mean for ${points.length} Sentinel-2 observation days`,
        },
      },
      grid: { ...(base.grid as object), top: 16, bottom: 48 },
      tooltip: {
        ...base.tooltip,
        trigger: "item",
        formatter: (params) => {
          const item = Array.isArray(params) ? params[0] : params;
          const t = (item.value as [number, number])[0];
          const p = byTime.get(t);
          if (!p) return "";
          return [
            `<strong>${new Date(p.date).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" })}</strong>`,
            `${indexKey} mean: <strong>${fmt(p.mean)}</strong>`,
            `Min / max: ${fmt(p.min)} / ${fmt(p.max)}`,
            `Valid pixels: ${p.valid_pixels} of ${p.sample_count}`,
          ].join("<br/>");
        },
      },
      xAxis: { type: "time", ...axisStyle, splitLine: { show: false } },
      yAxis: { type: "value", min: range.min, max: range.max, ...axisStyle },
      dataZoom: [
        { type: "inside", filterMode: "none" },
        {
          type: "slider",
          height: 18,
          bottom: 8,
          filterMode: "none",
          borderColor: chartPalette.axis,
        },
      ],
      series: [
        {
          name: `${indexKey} observation`,
          type: "scatter",
          data: points.map((p) => [Date.parse(p.date), p.mean]),
          symbolSize: 5,
          itemStyle: { color: chartPalette.primary, opacity: 0.85 },
          emphasis: { scale: 1.8 },
        },
      ],
    };
  }, [points, indexKey, visMin, visMax]);

  return <ReactECharts option={option} style={{ height }} notMerge lazyUpdate />;
}
