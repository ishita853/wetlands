import type { Metadata } from "next";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { WaterQualityExplorer } from "@/components/water-quality/water-quality-explorer";
import { getWaterQualityPageData } from "@/lib/data/water-quality";

export const metadata: Metadata = { title: "Water Quality Monitoring" };

export default async function WaterQualityPage({ searchParams }: PageProps<"/water-quality">) {
  const [{ site }, data] = await Promise.all([searchParams, getWaterQualityPageData()]);
  const requested = typeof site === "string" ? Number(site) : NaN;
  const initialSiteId = data.sites.some((s) => s.id === requested) ? requested : null;

  return (
    <>
      <PageHeader
        title="Water Quality Monitoring"
        description={
          <p>
            Satellite water-quality indices (NDCI, NDTI, NDWI and NDMI) for India&apos;s Ramsar
            Sites, computed from Copernicus Sentinel-2 Level-2A surface reflectance within each
            wetland&apos;s validated boundary.
          </p>
        }
      />
      <PageContainer className="section-y">
        <WaterQualityExplorer
          sites={data.sites}
          indices={data.indices}
          serviceError={data.serviceError}
          initialSiteId={initialSiteId}
        />
      </PageContainer>
    </>
  );
}
