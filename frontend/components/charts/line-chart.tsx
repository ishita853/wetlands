"use client";

import type { EChartsOption } from "echarts";
import ReactECharts from "echarts-for-react";
import { useMemo } from "react";

import { axisStyle, baseChartOption } from "@/lib/charts/theme";
import { chartPalette } from "@/lib/maps/palette";

export type LineSeries = {
  name: string;
  values: (number | null)[];
  /** "area" shades under the line (single-series magnitude only). */
  style?: "line" | "area" | "dashed";
};

export interface LineChartProps {
  x: (string | number)[];
  series: LineSeries[];
  unit?: string;
  height?: number;
  ariaLabel: string;
  formatValue?: (value: number) => string;
}

// Fixed categorical order: navy, then sedge. Never cycled.
const SERIES_COLOURS = [chartPalette.primary, chartPalette.secondary];

/** Line chart for change over time: 2px lines, crosshair tooltip, one y-axis. */
export function LineChart({
  x,
  series,
  unit,
  height = 300,
  ariaLabel,
  formatValue = (v) => v.toLocaleString("en-IN", { maximumFractionDigits: 2 }),
}: LineChartProps) {
  const option = useMemo<EChartsOption>(() => {
    const base = baseChartOption();
    return {
      ...base,
      aria: { enabled: true, label: { description: ariaLabel } },
      grid: { ...(base.grid as object), top: series.length > 1 ? 36 : 16 },
      legend:
        series.length > 1
          ? {
              top: 0,
              left: 0,
              icon: "roundRect",
              itemWidth: 14,
              itemHeight: 3,
              textStyle: { color: chartPalette.text },
            }
          : undefined,
      tooltip: {
        ...base.tooltip,
        trigger: "axis",
        axisPointer: { type: "line", lineStyle: { color: chartPalette.axis } },
        valueFormatter: (v) =>
          typeof v === "number" ? `${formatValue(v)}${unit ? ` ${unit}` : ""}` : "no data",
      },
      xAxis: {
        type: "category",
        data: x.map(String),
        boundaryGap: false,
        ...axisStyle,
        splitLine: { show: false },
      },
      yAxis: { type: "value", ...axisStyle, scale: false },
      series: series.slice(0, SERIES_COLOURS.length).map((s, i) => ({
        name: s.name,
        type: "line",
        data: s.values,
        connectNulls: false,
        showSymbol: false,
        symbolSize: 8,
        lineStyle: {
          width: 2,
          color: SERIES_COLOURS[i],
          type: s.style === "dashed" ? "dashed" : "solid",
        },
        itemStyle: { color: SERIES_COLOURS[i] },
        areaStyle: s.style === "area" ? { color: SERIES_COLOURS[i], opacity: 0.1 } : undefined,
        emphasis: { focus: "series" },
      })),
    };
  }, [x, series, unit, ariaLabel, formatValue]);

  return <ReactECharts option={option} style={{ height }} notMerge lazyUpdate />;
}
