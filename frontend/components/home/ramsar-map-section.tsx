import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { RamsarStateExplorer } from "@/components/home/ramsar-state-explorer";
import { PageContainer } from "@/components/layout/page-container";
import { SectionTitle } from "@/components/ui/typography";
import { ramsarCredit } from "@/config/site";
import { getRamsarSummary, getSitePoints } from "@/lib/data/ramsar";
import { formatDate } from "@/lib/utils/format";

export function RamsarMapSection() {
  const sites = getSitePoints();
  const summary = getRamsarSummary();

  const figures = [
    { value: summary.siteCount.toString(), label: "Ramsar Sites" },
    { value: summary.stateCount.toString(), label: "States and Union Territories" },
    {
      value: `${Math.round(summary.totalAreaHa).toLocaleString("en-IN")} ha`,
      label: "Total designated area",
    },
    {
      value: summary.latest.name,
      label: `Latest designation · ${formatDate(summary.latest.designationDate)}`,
    },
  ];

  return (
    <section
      aria-labelledby="ramsar-map-heading"
      className="section-y border-t border-border bg-muted"
    >
      <PageContainer>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionTitle id="ramsar-map-heading">Ramsar Site Map of India</SectionTitle>
          <Link
            href="/wetlands"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary underline-offset-4 hover:underline"
          >
            Open the Wetland Explorer
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>

        <dl className="mt-6 grid grid-cols-2 border-t border-l border-border bg-card lg:grid-cols-4">
          {figures.map((figure) => (
            <div key={figure.label} className="border-r border-b border-border px-4 py-3.5">
              <dt className="text-xs font-medium text-muted-foreground">{figure.label}</dt>
              <dd className="mt-1 truncate text-lg font-bold text-primary sm:text-xl">
                {figure.value}
              </dd>
            </div>
          ))}
        </dl>

        <RamsarStateExplorer sites={sites} className="mt-5" />

        <p className="mt-3 text-xs text-muted-foreground">
          Site data courtesy of the{" "}
          <a
            href={ramsarCredit.href}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:text-primary"
          >
            {ramsarCredit.text}
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
          .
        </p>
      </PageContainer>
    </section>
  );
}
