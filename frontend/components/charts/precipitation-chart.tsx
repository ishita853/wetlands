import { TimeSeriesChart, type TimeSeriesChartProps } from "@/components/charts/time-series-chart";

/** Precipitation indicator chart. Domain-specific alias over TimeSeriesChart. */
export function PrecipitationChart(props: TimeSeriesChartProps) {
  return <TimeSeriesChart {...props} />;
}
