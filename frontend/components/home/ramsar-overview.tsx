import { ArrowRight, ExternalLink } from "lucide-react";
import Link from "next/link";

import { PageContainer } from "@/components/layout/page-container";
import { SectionTitle } from "@/components/ui/typography";
import { climateThemes, referenceSources } from "@/config/site";

// Scope statements describe what each module will cover — not measurements.
const themeScope: Record<string, string> = {
  "/climate/drought": "Wetland water deficit and drought conditions",
  "/climate/precipitation": "Extreme rainfall and dry-spell events",
  "/climate/heat-waves": "Periods of extreme high temperature",
  "/climate/cold-waves": "Periods of extreme low temperature",
};

export function RamsarOverview() {
  return (
    <section aria-labelledby="ramsar-overview-heading" className="section-y">
      <PageContainer className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_19rem] lg:gap-10">
        <div className="min-w-0">
          <SectionTitle id="ramsar-overview-heading">Ramsar Wetlands of India</SectionTitle>
          <div className="mt-5 max-w-3xl space-y-3 text-base leading-relaxed text-foreground/85">
            <p>
              Ramsar Sites are wetlands of international importance designated under the Ramsar
              Convention on Wetlands. This portal brings together spatial wetland information,
              climate indicators, and water-quality monitoring for India&apos;s Ramsar Sites in a
              single application for monitoring and analysis.
            </p>
            <p>
              Climate monitoring is organised around four themes. For each theme the portal will
              provide graphical analysis and a dot-density map of Ramsar Site locations.
            </p>
          </div>

          <h3 className="mt-8 text-sm font-semibold tracking-wide text-muted-foreground uppercase">
            Climate monitoring themes
          </h3>
          <ul className="mt-3 grid border-t border-l border-border sm:grid-cols-2">
            {climateThemes.map((theme) => (
              <li key={theme.href} className="border-r border-b border-border">
                <Link
                  href={theme.href}
                  className="group flex h-full items-start justify-between gap-3 bg-background px-4 py-3.5 transition-colors outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-inset"
                >
                  <span>
                    <span className="block font-semibold text-primary">{theme.title}</span>
                    <span className="mt-0.5 block text-sm text-muted-foreground">
                      {themeScope[theme.href]}
                    </span>
                  </span>
                  <ArrowRight
                    className="mt-1 size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary motion-reduce:transition-none"
                    aria-hidden="true"
                  />
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <aside aria-label="Key figure and sources" className="space-y-4">
          <div className="rounded-sm border border-border border-t-4 border-t-sedge bg-background p-5">
            <p className="text-4xl font-bold text-primary tabular-nums">101</p>
            <p className="mt-1 font-semibold text-foreground">Ramsar Sites in India</p>
            <p className="mt-3 border-t border-border pt-3 text-xs leading-relaxed text-muted-foreground">
              Source:{" "}
              <a
                href={referenceSources.ramsarIndia.href}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-primary underline underline-offset-2 hover:no-underline"
              >
                {referenceSources.ramsarIndia.title}
                <span className="sr-only"> (opens in a new tab)</span>
              </a>
            </p>
          </div>

          <div className="rounded-sm border border-border bg-muted p-5">
            <h3 className="text-sm font-semibold text-foreground">Related national resource</h3>
            <a
              href={referenceSources.wetlandsOfIndia.href}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-primary underline underline-offset-2 hover:no-underline"
            >
              {referenceSources.wetlandsOfIndia.title}
              <ExternalLink className="size-3.5" aria-hidden="true" />
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          </div>
        </aside>
      </PageContainer>
    </section>
  );
}
