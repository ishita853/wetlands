export type ClimateIndicatorType = "DROUGHT" | "PRECIPITATION" | "HEAT_WAVE" | "COLD_WAVE";

export interface ClimateObservation {
  id: string;
  wetlandId: string;
  indicatorType: ClimateIndicatorType;
  observedAt: string;
  value: number;
  unit: string;
  source: string;
}
