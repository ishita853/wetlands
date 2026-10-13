import { TimeSeriesChart, type TimeSeriesChartProps } from "@/components/charts/time-series-chart";

/** Cold-wave indicator chart. Domain-specific alias over TimeSeriesChart. */
export function ColdWaveChart(props: TimeSeriesChartProps) {
  return <TimeSeriesChart {...props} />;
}
