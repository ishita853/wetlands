import type { Metadata } from "next";

import { ClimateThemePage } from "@/components/climate/climate-theme-page";

export const metadata: Metadata = { title: "Precipitation Extremes — Climate Monitoring" };

export default function PrecipitationPage({ searchParams }: PageProps<"/climate/precipitation">) {
  return <ClimateThemePage themeKey="precipitation-extremes" searchParams={searchParams} />;
}
