import { TimeSeriesChart, type TimeSeriesChartProps } from "@/components/charts/time-series-chart";

/** Climate anomaly chart (deviation from baseline). Domain-specific alias over TimeSeriesChart. */
export function ClimateAnomalyChart(props: TimeSeriesChartProps) {
  return <TimeSeriesChart {...props} />;
}
