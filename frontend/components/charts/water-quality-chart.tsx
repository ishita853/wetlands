import { TimeSeriesChart, type TimeSeriesChartProps } from "@/components/charts/time-series-chart";

/** Water-quality parameter chart. Domain-specific alias over TimeSeriesChart. */
export function WaterQualityChart(props: TimeSeriesChartProps) {
  return <TimeSeriesChart {...props} />;
}
