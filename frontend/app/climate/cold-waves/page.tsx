import type { Metadata } from "next";

import { ClimateThemePage } from "@/components/climate/climate-theme-page";

export const metadata: Metadata = { title: "Cold Waves — Climate Monitoring" };

export default function ColdWavesPage({ searchParams }: PageProps<"/climate/cold-waves">) {
  return <ClimateThemePage themeKey="cold-waves" searchParams={searchParams} />;
}
