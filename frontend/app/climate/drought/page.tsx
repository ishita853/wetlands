import type { Metadata } from "next";

import { ClimateThemePage } from "@/components/climate/climate-theme-page";

export const metadata: Metadata = { title: "Wetland Drought — Climate Monitoring" };

export default function DroughtPage({ searchParams }: PageProps<"/climate/drought">) {
  return <ClimateThemePage themeKey="wetland-drought" searchParams={searchParams} />;
}
