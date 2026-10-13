import { TimeSeriesChart, type TimeSeriesChartProps } from "@/components/charts/time-series-chart";

/** Multi-series comparative chart (e.g. across wetlands or indicators). */
export function ComparativeChart(props: TimeSeriesChartProps) {
  return <TimeSeriesChart {...props} />;
}
