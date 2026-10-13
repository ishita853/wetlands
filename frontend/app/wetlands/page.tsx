import type { Metadata } from "next";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { WetlandExplorer } from "@/components/wetlands/wetland-explorer";
import { getRamsarSummary, getSitePoints } from "@/lib/data/ramsar";

export const metadata: Metadata = { title: "Ramsar Wetlands of India" };

export default async function WetlandsPage({ searchParams }: PageProps<"/wetlands">) {
  const { q } = await searchParams;
  const summary = getRamsarSummary();

  return (
    <>
      <PageHeader
        title="Ramsar Wetlands of India"
        crumbs={[]}
        description={
          <p>
            Explore all {summary.siteCount} Ramsar Sites across {summary.stateCount} states and
            union territories. Search or filter the list, select a site on the map, and open its
            profile for designation details, wetland types and ecological character.
          </p>
        }
      />
      <PageContainer className="section-y">
        <WetlandExplorer sites={getSitePoints()} initialQuery={typeof q === "string" ? q : ""} />
      </PageContainer>
    </>
  );
}
