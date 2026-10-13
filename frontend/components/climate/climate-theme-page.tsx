import Link from "next/link";

import { ClimateThemeView } from "@/components/climate/climate-theme-view";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import {
  climateThemeDefs,
  climateThemeOrder,
  getClimateDataset,
  type ClimateThemeKey,
} from "@/lib/data/climate";
import { getSitePoints } from "@/lib/data/ramsar";
import { cn } from "@/lib/utils";

/** Shared server page for the four climate monitoring themes. */
export async function ClimateThemePage({
  themeKey,
  searchParams,
}: {
  themeKey: ClimateThemeKey;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const theme = climateThemeDefs[themeKey];
  const sites = getSitePoints();
  const { site } = await searchParams;
  const siteId =
    typeof site === "string" && sites.some((s) => s.id === Number(site)) ? Number(site) : null;

  return (
    <>
      <PageHeader
        title={theme.title}
        crumbs={[{ title: "Climate Monitoring", href: "/climate" }]}
        description={<p>{theme.summary}</p>}
      >
        <nav aria-label="Climate themes" className="mt-5 flex flex-wrap gap-2">
          {climateThemeOrder.map((key) => {
            const t = climateThemeDefs[key];
            const active = key === themeKey;
            return (
              <Link
                key={key}
                href={t.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-sm border px-3 py-1.5 text-sm font-medium transition-colors",
                  active
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-card text-foreground hover:border-primary hover:text-primary",
                )}
              >
                {t.title}
              </Link>
            );
          })}
        </nav>
      </PageHeader>
      <PageContainer className="section-y">
        <ClimateThemeView
          theme={theme}
          sites={sites}
          dataset={getClimateDataset(themeKey)}
          initialSiteId={siteId}
        />
      </PageContainer>
    </>
  );
}
