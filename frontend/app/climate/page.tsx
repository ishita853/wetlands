import { ArrowRight } from "lucide-react";
import type { Metadata } from "next";
import { connection } from "next/server";
import Link from "next/link";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { BASELINE, getClimateStatus } from "@/lib/data/climate";
import { getRamsarSummary } from "@/lib/data/ramsar";

export const metadata: Metadata = { title: "Climate Monitoring" };

export default async function ClimatePage() {
  // Rendered per request: datasets can be published at any time from the admin area.
  await connection();
  const status = getClimateStatus();
  const { siteCount } = getRamsarSummary();

  return (
    <>
      <PageHeader
        title="Climate Monitoring"
        description={
          <p>
            Monitoring of climate extremes at India&apos;s {siteCount} Ramsar Sites across four
            themes. Each theme provides a dot-density map of site locations coloured by the
            indicator, with graphical analysis of national, state and site-level patterns. All
            indicators are percentile-based, relative to each site&apos;s own {BASELINE} climate.
          </p>
        }
      />
      <PageContainer className="section-y">
        <ul className="grid gap-5 md:grid-cols-2">
          {status.map(({ theme, loaded, years, siteCount: covered }) => (
            <li key={theme.key}>
              <Link
                href={theme.href}
                className="group flex h-full flex-col rounded-sm border border-border border-t-4 border-t-sedge bg-card p-5 transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="text-lg font-bold text-primary">{theme.title}</h2>
                  <span
                    className={
                      loaded
                        ? "rounded-sm bg-accent px-2 py-0.5 text-xs font-semibold text-accent-foreground"
                        : "rounded-sm border border-border px-2 py-0.5 text-xs font-medium text-muted-foreground"
                    }
                  >
                    {loaded ? `Data ${years?.[0]}–${years?.[1]}` : "Dataset pending"}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-foreground/85">{theme.summary}</p>
                <p className="mt-3 text-xs text-muted-foreground">
                  Indicators: {theme.recommendedMetrics.map((m) => m.label).join(" · ")}
                  {loaded ? ` · ${covered} sites covered` : ""}
                </p>
                <span className="mt-auto inline-flex items-center gap-1.5 pt-4 text-sm font-semibold text-primary">
                  Open {theme.title.toLowerCase()} analysis
                  <ArrowRight
                    className="size-4 transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none"
                    aria-hidden="true"
                  />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </PageContainer>
    </>
  );
}
