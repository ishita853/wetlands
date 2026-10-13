import { ArrowRight, ExternalLink } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { SectionTitle } from "@/components/ui/typography";
import { climateThemes, ramsarCredit, referenceSources, siteConfig } from "@/config/site";
import { BASELINE } from "@/lib/data/climate";
import { getRamsarSummary } from "@/lib/data/ramsar";
import { formatDate } from "@/lib/utils/format";

export const metadata: Metadata = { title: "About the Portal" };

/** The nine Ramsar criteria for identifying Wetlands of International Importance. */
const RAMSAR_CRITERIA = [
  "Contains a representative, rare or unique example of a natural or near-natural wetland type.",
  "Supports vulnerable, endangered or critically endangered species or threatened ecological communities.",
  "Supports populations of plant or animal species important for maintaining the biological diversity of a region.",
  "Supports species at a critical stage in their life cycles, or provides refuge during adverse conditions.",
  "Regularly supports 20,000 or more waterbirds.",
  "Regularly supports 1% of the individuals in a population of one species or subspecies of waterbird.",
  "Supports a significant proportion of indigenous fish species, life-history stages or interactions.",
  "Is an important source of food, spawning ground, nursery or migration path for fish.",
  "Regularly supports 1% of the individuals in a population of one species or subspecies of wetland-dependent non-avian animal.",
];

function ExternalA({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 font-medium text-primary underline underline-offset-2 hover:no-underline"
    >
      {children}
      <ExternalLink className="size-3.5" aria-hidden="true" />
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

export default function AboutPage() {
  const summary = getRamsarSummary();

  const figures = [
    { label: "Ramsar Sites in India", value: summary.siteCount.toLocaleString("en-IN") },
    { label: "States & Union Territories", value: summary.stateCount.toLocaleString("en-IN") },
    {
      label: "Total designated area",
      value: `${Math.round(summary.totalAreaHa).toLocaleString("en-IN")} ha`,
    },
    { label: "First designations", value: String(summary.earliest.designationYear) },
  ];

  const modules: {
    title: string;
    href: string;
    body: string;
  }[] = [
    {
      title: "Ramsar Wetlands",
      href: "/wetlands",
      body: "A profile for every Ramsar Site in India: location, area, designation date, wetland types, Ramsar criteria, ecosystem services and reported threats, with a map to explore them by state.",
    },
    {
      title: "Climate Monitoring",
      href: "/climate",
      body: "Four climate hazards tracked at each site — wetland drought, precipitation extremes, heat waves and cold waves — shown as site maps, trends and tables.",
    },
    {
      title: "Water Quality",
      href: "/water-quality",
      body: "Satellite-based water-quality indicators for Ramsar Sites, derived from Copernicus Sentinel imagery.",
    },
    {
      title: "Analysis",
      href: "/analysis",
      body: "National summaries of the Ramsar network: designations over time, distribution by state and wetland type, and site characteristics.",
    },
    {
      title: "Datasets",
      href: "/datasets",
      body: "A catalogue of the published datasets behind the portal, with descriptions and downloads.",
    },
  ];

  return (
    <>
      <PageHeader
        title="About the Portal"
        description={
          <p>
            The {siteConfig.name} brings together information on India&apos;s Wetlands of
            International Importance and tracks the climate and environmental pressures they face.
          </p>
        }
      >
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
      </PageHeader>

      {/* Purpose */}
      <PageContainer className="section-y grid gap-10 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <section aria-labelledby="purpose">
          <SectionTitle id="purpose">Purpose</SectionTitle>
          <div className="mt-5 max-w-3xl space-y-4 leading-relaxed text-foreground/85">
            <p>
              Wetlands store and regulate water, buffer floods and droughts, support fisheries and
              agriculture, and sustain some of the richest biodiversity in the country. They are
              also among the ecosystems most exposed to a changing climate.
            </p>
            <p>
              This portal gives researchers, site managers, policy makers and the public a single
              place to see where India&apos;s Ramsar Sites are, what makes each one important, and
              how climate extremes are changing at each site over time. Every figure on the portal
              is drawn from a published dataset, and each page names its source.
            </p>
          </div>
        </section>

        <aside className="self-start rounded-md border border-border border-t-4 border-t-sedge bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground">Latest designation</h2>
          <p className="mt-2 text-lg font-bold text-primary">
            <Link href={`/wetlands/${summary.latest.id}`} className="hover:underline">
              {summary.latest.name}
            </Link>
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {summary.latest.state} · designated {formatDate(summary.latest.designationDate)}
          </p>
          <Link
            href="/wetlands"
            className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline"
          >
            Explore all Ramsar Sites
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </aside>
      </PageContainer>

      {/* What the portal covers */}
      <section aria-labelledby="coverage" className="border-y border-border bg-secondary/60">
        <PageContainer className="section-y">
          <SectionTitle id="coverage">What the portal covers</SectionTitle>
          <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {modules.map((module) => (
              <li key={module.href}>
                <Link
                  href={module.href}
                  className="group flex h-full flex-col rounded-md border border-border bg-card p-5 transition-colors outline-none hover:border-primary/40 focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  <span className="text-base font-bold text-foreground group-hover:text-primary">
                    {module.title}
                  </span>
                  <span className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {module.body}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </PageContainer>
      </section>

      {/* Ramsar Sites */}
      <PageContainer className="section-y grid gap-10 lg:grid-cols-2">
        <section aria-labelledby="ramsar">
          <SectionTitle id="ramsar">What is a Ramsar Site?</SectionTitle>
          <div className="mt-5 space-y-4 leading-relaxed text-foreground/85">
            <p>
              The Convention on Wetlands, adopted in the Iranian city of Ramsar in 1971, is the
              intergovernmental treaty for the conservation and wise use of wetlands. Countries that
              join the Convention designate wetlands of international importance, known as Ramsar
              Sites, and commit to maintaining their ecological character.
            </p>
            <p>
              India&apos;s first Ramsar Sites were designated in {summary.earliest.designationYear}.
              The network now covers {summary.siteCount} sites across {summary.stateCount} states
              and Union Territories, from high-altitude lakes in Ladakh to coastal lagoons,
              mangroves and reservoirs.
            </p>
            <p>
              A wetland qualifies by meeting at least one of nine criteria. Each site profile on
              this portal shows which criteria that site meets.
            </p>
          </div>
        </section>

        <section aria-labelledby="criteria">
          <h2 id="criteria" className="text-lg font-bold text-foreground">
            The nine Ramsar criteria
          </h2>
          <ol className="mt-4 divide-y divide-border rounded-md border border-border bg-card">
            {RAMSAR_CRITERIA.map((text, i) => (
              <li key={i} className="flex gap-3 px-4 py-2.5 text-sm">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-sedge-strong text-xs font-bold text-white">
                  {i + 1}
                </span>
                <span className="text-foreground/85">{text}</span>
              </li>
            ))}
          </ol>
        </section>
      </PageContainer>

      {/* Data & methods */}
      <section aria-labelledby="methods" className="border-t border-border bg-secondary/60">
        <PageContainer className="section-y">
          <SectionTitle id="methods">Data and methods</SectionTitle>
          <div className="mt-6 grid gap-5 lg:grid-cols-3">
            <div className="rounded-md border border-border bg-card p-5">
              <h3 className="font-bold text-foreground">Ramsar Site information</h3>
              <p className="mt-2 text-sm leading-relaxed text-foreground/80">
                Site names, designation dates, areas, coordinates, wetland types, criteria,
                ecosystem services and threats come from the Ramsar Sites Information Service. The
                state and district shown for each site are found by placing its coordinates on the
                portal&apos;s India boundary data.
              </p>
            </div>
            <div className="rounded-md border border-border bg-card p-5">
              <h3 className="font-bold text-foreground">Climate indicators</h3>
              <p className="mt-2 text-sm leading-relaxed text-foreground/80">
                Each hazard is measured against the site&apos;s own climate over the {BASELINE}{" "}
                baseline, using percentile thresholds, so a high-altitude lake and a coastal lagoon
                are compared on equal terms. Full definitions are given on each climate theme page.
              </p>
              <ul className="mt-3 space-y-1 text-sm">
                {climateThemes.map((theme) => (
                  <li key={theme.href}>
                    <Link href={theme.href} className="text-primary hover:underline">
                      {theme.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-md border border-border bg-card p-5">
              <h3 className="font-bold text-foreground">Maps</h3>
              <p className="mt-2 text-sm leading-relaxed text-foreground/80">
                National maps are drawn on the portal&apos;s India state boundaries, with coastline
                from Natural Earth. Site close-ups use satellite imagery from Esri World Imagery.
                Maps are for information only; for official site boundaries refer to each
                site&apos;s Ramsar Information Sheet.
              </p>
            </div>
          </div>
        </PageContainer>
      </section>

      {/* Credits */}
      <PageContainer className="section-y">
        <SectionTitle id="credits">Credits and references</SectionTitle>
        <div className="mt-5 max-w-3xl space-y-4 leading-relaxed text-foreground/85">
          <p>
            Ramsar Site information is courtesy of the{" "}
            <ExternalA href={ramsarCredit.href}>{ramsarCredit.text}</ExternalA>. Official site
            records, including full Ramsar Information Sheets and boundary maps, are published on
            the Ramsar Sites Information Service and linked from each site profile.
          </p>
          <p>
            For national wetland programmes and state-level information, see the{" "}
            <ExternalA href={referenceSources.wetlandsOfIndia.href}>
              {referenceSources.wetlandsOfIndia.title}
            </ExternalA>
            .
          </p>
        </div>
      </PageContainer>
    </>
  );
}
