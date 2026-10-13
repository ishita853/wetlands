import { TimeSeriesChart, type TimeSeriesChartProps } from "@/components/charts/time-series-chart";

/** Drought indicator chart. Domain-specific alias over TimeSeriesChart. */
export function DroughtChart(props: TimeSeriesChartProps) {
  return <TimeSeriesChart {...props} />;
}
