import { ExternalLink } from "lucide-react";
import Link from "next/link";

import { PageContainer } from "@/components/layout/page-container";
import { Waves } from "@/components/ui/waves";
import { adminNav, climateThemes, ramsarCredit, referenceSources, siteConfig } from "@/config/site";

const exploreLinks = [
  { title: "About", href: "/about" },
  { title: "Ramsar Wetlands", href: "/wetlands" },
  { title: "Water Quality", href: "/water-quality" },
  { title: "Analysis", href: "/analysis" },
  { title: "Datasets", href: "/datasets" },
  adminNav,
];

const columns = [
  { id: "footer-explore", title: "Explore", links: exploreLinks },
  { id: "footer-climate", title: "Climate", links: climateThemes },
];

const linkClass =
  "text-foreground/85 underline-offset-4 transition-colors hover:text-primary hover:underline";

export function SiteFooter() {
  return (
    <footer className="relative mt-auto overflow-hidden border-t border-border bg-linear-to-b from-background to-secondary text-foreground">
      <Waves className="text-primary/10" />

      <PageContainer className="relative grid gap-10 py-14 md:grid-cols-[1.6fr_1fr_1fr] md:gap-8 lg:py-16">
        <div className="max-w-xl">
          <p className="font-serif text-3xl leading-tight font-bold tracking-tight text-foreground sm:text-4xl">
            {siteConfig.shortName}
          </p>
          <p className="mt-1 text-sm font-semibold tracking-wide text-sedge-strong uppercase">
            {siteConfig.tagline}
          </p>
          <p className="mt-4 text-[0.9375rem] leading-relaxed text-foreground/80">
            {siteConfig.description}
          </p>

          <ul className="mt-6 flex flex-wrap gap-2.5" aria-label="Reference sources">
            {Object.values(referenceSources).map((source) => (
              <li key={source.href}>
                <a
                  href={source.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/80 px-3.5 py-1.5 text-sm text-primary shadow-xs transition-colors outline-none hover:border-primary/40 hover:bg-card focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  {source.title}
                  <ExternalLink className="size-3.5" aria-hidden="true" />
                  <span className="sr-only"> (opens in a new tab)</span>
                </a>
              </li>
            ))}
          </ul>
        </div>

        {columns.map((column) => (
          <nav key={column.id} aria-labelledby={column.id}>
            <h2
              id={column.id}
              className="font-serif text-sm font-bold tracking-[0.25em] text-foreground uppercase"
            >
              {column.title}
            </h2>
            <ul className="mt-5 space-y-3.5 text-[0.9375rem]">
              {column.links.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className={linkClass}>
                    {link.title}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </PageContainer>

      <div className="relative border-t border-border">
        <PageContainer className="flex flex-col gap-2 py-5 text-sm text-foreground/75 sm:flex-row sm:items-center sm:justify-between">
          <p>
            © {new Date().getFullYear()} {siteConfig.name}
          </p>
          <p>
            Ramsar Site data courtesy of the{" "}
            <a
              href={ramsarCredit.href}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-primary"
            >
              {ramsarCredit.text}
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          </p>
        </PageContainer>
      </div>
    </footer>
  );
}
