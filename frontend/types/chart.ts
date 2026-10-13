export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
}

export interface TimeSeriesSeries {
  name: string;
  unit?: string;
  points: TimeSeriesPoint[];
}
