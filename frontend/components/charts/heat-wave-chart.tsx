import { TimeSeriesChart, type TimeSeriesChartProps } from "@/components/charts/time-series-chart";

/** Heat-wave indicator chart. Domain-specific alias over TimeSeriesChart. */
export function HeatWaveChart(props: TimeSeriesChartProps) {
  return <TimeSeriesChart {...props} />;
}
