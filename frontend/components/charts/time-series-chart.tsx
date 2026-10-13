"use client";

import ReactECharts from "echarts-for-react";

import { buildTimeSeriesOption } from "@/lib/charts/options";
import type { TimeSeriesSeries } from "@/types/chart";

export interface TimeSeriesChartProps {
  series: TimeSeriesSeries[];
  height?: number;
}

/** Generic reusable time-series chart. Renders whatever series it is given. */
export function TimeSeriesChart({ series, height = 320 }: TimeSeriesChartProps) {
  if (series.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground"
        style={{ height }}
      >
        No data to display.
      </div>
    );
  }

  return (
    <ReactECharts option={buildTimeSeriesOption(series)} style={{ height }} notMerge lazyUpdate />
  );
}
