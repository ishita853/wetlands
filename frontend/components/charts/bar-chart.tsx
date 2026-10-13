"use client";

import type { EChartsOption } from "echarts";
import ReactECharts from "echarts-for-react";
import { useMemo } from "react";

import { axisStyle, baseChartOption } from "@/lib/charts/theme";
import { chartPalette } from "@/lib/maps/palette";

export interface BarChartProps {
  categories: (string | number)[];
  values: (number | null)[];
  /** Horizontal bars (long category labels, rankings). */
  horizontal?: boolean;
  unit?: string;
  height?: number;
  ariaLabel: string;
  formatValue?: (value: number) => string;
  /** Index of a bar to emphasise (others are shown lighter). */
  highlightIndex?: number | null;
}

/** Single-series bar chart: one hue, rounded data ends, 2px gaps. */
export function BarChart({
  categories,
  values,
  horizontal = false,
  unit,
  height = 300,
  ariaLabel,
  formatValue = (v) => v.toLocaleString("en-IN"),
  highlightIndex = null,
}: BarChartProps) {
  const option = useMemo<EChartsOption>(() => {
    const categoryAxis = {
      type: "category" as const,
      data: categories.map(String),
      ...axisStyle,
      splitLine: { show: false },
      axisLabel: {
        ...axisStyle.axisLabel,
        interval: horizontal ? 0 : ("auto" as const),
        width: horizontal ? 150 : undefined,
        overflow: horizontal ? ("truncate" as const) : undefined,
      },
      inverse: horizontal,
    };
    const valueAxis = { type: "value" as const, ...axisStyle, minInterval: 1 };
    const radius = horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0];

    return {
      ...baseChartOption(),
      aria: { enabled: true, label: { description: ariaLabel } },
      tooltip: {
        ...baseChartOption().tooltip,
        trigger: "axis",
        axisPointer: { type: "shadow", shadowStyle: { color: "rgba(36,59,108,0.06)" } },
        valueFormatter: (v) =>
          typeof v === "number" ? `${formatValue(v)}${unit ? ` ${unit}` : ""}` : "—",
      },
      xAxis: horizontal ? valueAxis : categoryAxis,
      yAxis: horizontal ? categoryAxis : valueAxis,
      series: [
        {
          type: "bar",
          data: values.map((v, i) => ({
            value: v,
            itemStyle: {
              color:
                highlightIndex === null || highlightIndex === i ? chartPalette.primary : "#a9b3cc",
              borderRadius: radius,
            },
          })),
          barCategoryGap: "18%",
          barMaxWidth: 28,
        },
      ],
    };
  }, [categories, values, horizontal, unit, ariaLabel, formatValue, highlightIndex]);

  return <ReactECharts option={option} style={{ height }} notMerge lazyUpdate />;
}
