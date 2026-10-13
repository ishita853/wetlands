import type { Metadata } from "next";

import { ClimateThemePage } from "@/components/climate/climate-theme-page";

export const metadata: Metadata = { title: "Heat Waves — Climate Monitoring" };

export default function HeatWavesPage({ searchParams }: PageProps<"/climate/heat-waves">) {
  return <ClimateThemePage themeKey="heat-waves" searchParams={searchParams} />;
}
