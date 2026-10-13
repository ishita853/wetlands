import type { EChartsOption } from "echarts";

import { baseChartOption } from "@/lib/charts/theme";
import type { TimeSeriesSeries } from "@/types/chart";

export function buildTimeSeriesOption(series: TimeSeriesSeries[]): EChartsOption {
  return {
    ...baseChartOption(),
    legend: series.length > 1 ? { top: 0 } : undefined,
    xAxis: { type: "time" },
    yAxis: { type: "value" },
    series: series.map((s) => ({
      name: s.name,
      type: "line",
      showSymbol: false,
      data: s.points.map((point) => [point.timestamp, point.value]),
    })),
  };
}
