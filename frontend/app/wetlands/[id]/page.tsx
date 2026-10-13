import { Download, ExternalLink, FileText } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { SiteGallery } from "@/components/wetlands/site-gallery";
import { SiteMapPanel } from "@/components/wetlands/site-map-panel";
import { climateThemes, ramsarCredit } from "@/config/site";
import { getRamsarSite, getRamsarSites, getSitePoints, type RamsarSite } from "@/lib/data/ramsar";
import { getSiteImages } from "@/lib/data/site-images";
import { formatDate } from "@/lib/utils/format";
import { cn } from "@/lib/utils";

export function generateStaticParams() {
  return getRamsarSites().map((site) => ({ id: String(site.id) }));
}

export async function generateMetadata({ params }: PageProps<"/wetlands/[id]">): Promise<Metadata> {
  const { id } = await params;
  const site = getRamsarSite(Number(id));
  return { title: site ? `${site.name} — Ramsar Site` : "Ramsar Site" };
}

/** 31.39628 → 31°23'46"N (seconds truncated, as on the Ramsar site pages) */
function toDms(value: number, pos: string, neg: string) {
  const abs = Math.abs(value);
  const d = Math.floor(abs);
  const m = Math.floor((abs - d) * 60);
  const s = Math.floor(((abs - d) * 60 - m) * 60);
  return `${d}°${String(m).padStart(2, "0")}'${String(s).padStart(2, "0")}"${value >= 0 ? pos : neg}`;
}

const ha = (value: number) =>
  value.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 3 });

function siteCsv(site: RamsarSite) {
  const rows: [string, string | number | null][] = [
    ["Ramsar Site no.", site.id],
    ["Site name", site.name],
    ["State / UT", site.state],
    ["District", site.district],
    ["Designation date", site.designationDate],
    ["Area (ha)", site.areaHa],
    ["Latitude", site.latitude],
    ["Longitude", site.longitude],
    ["Maximum elevation (m)", site.elevationMaxM],
    ["Minimum elevation (m)", site.elevationMinM],
    ["Ramsar criteria", site.criteria.join("; ")],
    ["Wetland types", Object.values(site.wetlandTypes).flat().join("; ")],
    ["Montreux Record", site.montreuxListed],
    ["Management plan available", site.managementPlanAvailable],
    ["Management plan implemented", site.managementPlanImplemented],
    ["Ecosystem services", site.ecosystemServices.join("; ")],
    ["Threats", site.threats.join("; ")],
    ["Source", `${ramsarCredit.text} (${ramsarCredit.href})`],
  ];
  const cell = (v: string | number | null) => `"${String(v ?? "").replaceAll('"', '""')}"`;
  return ["Field,Value", ...rows.map(([k, v]) => `${cell(k)},${cell(v)}`)].join("\n");
}

/**
 * The dataset lists services flat, each category ("… Services") followed by
 * its items; regroup them for display.
 */
function groupServices(items: string[]) {
  const groups: { category: string; items: string[] }[] = [];
  for (const item of items) {
    if (/Services$/.test(item)) groups.push({ category: item, items: [] });
    else if (groups.length) groups[groups.length - 1].items.push(item);
    else groups.push({ category: "Other services", items: [item] });
  }
  return groups;
}

/** Wetland type codes arrive as "A: Permanent shallow marine waters". */
function splitType(type: string) {
  const match = /^([A-Za-z0-9]+):\s*(.*)$/.exec(type);
  return match ? { code: match[1], label: match[2] } : { code: null, label: type };
}

function SectionHeading({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2
      id={id}
      className="scroll-mt-24 border-l-4 border-sedge pl-3 text-xl font-bold tracking-tight text-foreground"
    >
      {children}
    </h2>
  );
}

function StatusBadge({ value }: { value: string | null }) {
  if (!value) return <span className="text-muted-foreground">Not reported</span>;
  const yes = value.toLowerCase() === "yes";
  const no = value.toLowerCase() === "no";
  return (
    <span
      className={cn(
        "inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold",
        yes && "bg-accent text-accent-foreground",
        no && "bg-muted text-muted-foreground",
        !yes && !no && "bg-secondary text-secondary-foreground",
      )}
    >
      {value}
    </span>
  );
}

function SideCard({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-md border border-border bg-card p-4 shadow-xs", className)}>
      <h2 className="text-xs font-bold tracking-[0.14em] text-muted-foreground uppercase">
        {title}
      </h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export default async function WetlandDetailPage({ params }: PageProps<"/wetlands/[id]">) {
  const { id } = await params;
  const site = getRamsarSite(Number(id));
  if (!site) notFound();

  const images = getSiteImages(site.id, site.name);
  const groups = Object.entries(site.wetlandTypes);
  const services = groupServices(site.ecosystemServices);
  const elevation =
    site.elevationMinM !== null && site.elevationMaxM !== null
      ? site.elevationMinM === site.elevationMaxM
        ? `${site.elevationMaxM.toLocaleString("en-IN")} m`
        : `${site.elevationMinM.toLocaleString("en-IN")}–${site.elevationMaxM.toLocaleString("en-IN")} m`
      : null;
  const risUrl = `https://rsis.ramsar.org/ris/${site.id}`;
  const csvHref = `data:text/csv;charset=utf-8,${encodeURIComponent(siteCsv(site))}`;
  const [lead, ...rest] = site.summary;

  const stats = [
    { label: "Area", value: `${ha(site.areaHa)} ha` },
    { label: "Designated", value: formatDate(site.designationDate) },
    { label: "Elevation", value: elevation ?? "Not reported" },
    {
      label: "Ramsar criteria met",
      value: site.criteria.length ? `${site.criteria.length} of 9` : "Not listed",
    },
  ];

  const sections = [
    { id: "about", title: "About the site", show: true },
    { id: "photographs", title: "Photographs", show: true },
    { id: "character", title: "Wetland character", show: true },
    { id: "services", title: "Ecosystem services", show: services.length > 0 },
    { id: "threats", title: "Reported threats", show: site.threats.length > 0 },
    { id: "management", title: "Protection & management", show: true },
  ].filter((s) => s.show);

  const downloadLink =
    "flex items-center gap-3 rounded-sm px-2 py-2 text-sm transition-colors outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50";

  return (
    <>
      <PageHeader
        title={site.name}
        crumbs={[{ title: "Ramsar Wetlands", href: "/wetlands" }]}
        description={
          <p>
            Ramsar Site no. {site.id} · {site.district}, {site.state}
            {groups.length ? ` · ${groups.map(([group]) => group).join(", ")}` : ""}
          </p>
        }
      >
        <dl className="mt-6 grid grid-cols-2 border-t border-l border-border bg-card lg:grid-cols-4">
          {stats.map(({ label, value }) => (
            <div key={label} className="border-r border-b border-border px-4 py-3.5">
              <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
              <dd className="mt-1 truncate text-lg font-bold text-primary sm:text-xl">{value}</dd>
            </div>
          ))}
        </dl>
      </PageHeader>

      <PageContainer className="grid gap-10 py-10 lg:grid-cols-[minmax(0,1fr)_22rem] lg:py-12">
        <div className="min-w-0 space-y-12">
          <nav aria-label="On this page" className="-mb-4">
            <ul className="flex flex-wrap gap-2">
              {sections.map((s) => (
                <li key={s.id}>
                  <a
                    href={`#${s.id}`}
                    className="inline-block rounded-full border border-border bg-card px-3 py-1 text-sm text-foreground/80 transition-colors hover:border-primary/40 hover:text-primary"
                  >
                    {s.title}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <section aria-labelledby="about">
            <SectionHeading id="about">About the site</SectionHeading>
            <div className="mt-4 max-w-3xl space-y-4 leading-relaxed text-foreground/85">
              {lead ? (
                <>
                  <p className="text-lg leading-relaxed text-foreground">{lead}</p>
                  {rest.map((paragraph, i) => (
                    <p key={i}>{paragraph}</p>
                  ))}
                </>
              ) : (
                <p className="text-muted-foreground">No summary is available for this site.</p>
              )}
            </div>
          </section>

          <section aria-labelledby="photographs">
            <SectionHeading id="photographs">Photographs</SectionHeading>
            <div className="mt-4">
              <SiteGallery images={images} siteName={site.name} />
            </div>
          </section>

          <section aria-labelledby="character">
            <SectionHeading id="character">Wetland character</SectionHeading>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {groups.map(([group, types]) => (
                <div key={group} className="rounded-md border border-border bg-card p-4">
                  <h3 className="text-sm font-semibold text-primary">{group}</h3>
                  <ul className="mt-3 space-y-2 text-sm">
                    {(types ?? []).map((type) => {
                      const { code, label } = splitType(type);
                      return (
                        <li key={type} className="flex items-start gap-2.5">
                          {code ? (
                            <span className="mt-px flex h-5 min-w-6 shrink-0 items-center justify-center rounded-sm bg-muted px-1 text-[11px] font-bold text-muted-foreground">
                              {code}
                            </span>
                          ) : null}
                          <span className="text-foreground/85">{label}</span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
              <div className="rounded-md border border-border bg-card p-4 sm:col-span-2">
                <h3 className="text-sm font-semibold text-primary">Ramsar criteria met</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  The nine criteria under which a wetland qualifies as internationally important.
                </p>
                <ol className="mt-3 flex flex-wrap gap-2" aria-label="Criteria 1 to 9">
                  {Array.from({ length: 9 }, (_, i) => i + 1).map((n) => {
                    const met = site.criteria.includes(n);
                    return (
                      <li
                        key={n}
                        className={cn(
                          "flex size-9 items-center justify-center rounded-full text-sm font-bold",
                          met
                            ? "bg-sedge-strong text-white"
                            : "border border-dashed border-border text-muted-foreground",
                        )}
                      >
                        {n}
                        <span className="sr-only">{met ? " (met)" : " (not met)"}</span>
                      </li>
                    );
                  })}
                </ol>
              </div>
            </div>
          </section>

          {services.length ? (
            <section aria-labelledby="services">
              <SectionHeading id="services">Ecosystem services</SectionHeading>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {services.map((group) => (
                  <div
                    key={group.category}
                    className="rounded-md border border-border border-t-4 border-t-sedge bg-card p-4"
                  >
                    <h3 className="text-sm font-semibold text-foreground">{group.category}</h3>
                    {group.items.length ? (
                      <ul className="mt-2 space-y-1 text-sm text-foreground/80">
                        {group.items.map((item) => (
                          <li key={item} className="flex gap-2">
                            <span aria-hidden="true" className="text-sedge">
                              •
                            </span>
                            {item}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {site.threats.length ? (
            <section aria-labelledby="threats">
              <SectionHeading id="threats">Reported threats</SectionHeading>
              <ul className="mt-4 flex flex-wrap gap-2">
                {site.threats.map((threat) => (
                  <li
                    key={threat}
                    className="rounded-full border border-[oklch(0.85_0.06_70)] bg-[oklch(0.97_0.03_80)] px-3 py-1 text-sm text-[oklch(0.42_0.08_60)] dark:border-[oklch(0.45_0.06_70)] dark:bg-[oklch(0.3_0.04_70)] dark:text-[oklch(0.9_0.05_80)]"
                  >
                    {threat}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section aria-labelledby="management">
            <SectionHeading id="management">Protection &amp; management</SectionHeading>
            <dl className="mt-4 divide-y divide-border rounded-md border border-border bg-card">
              {[
                [
                  "Management plan available",
                  <StatusBadge key="a" value={site.managementPlanAvailable} />,
                ],
                [
                  "Management plan implemented",
                  <StatusBadge key="i" value={site.managementPlanImplemented} />,
                ],
                ["On the Montreux Record", <StatusBadge key="m" value={site.montreuxListed} />],
                ...(site.nationalDesignation
                  ? [["National designation", site.nationalDesignation] as const]
                  : []),
                ...(site.globalDesignations
                  ? [["International designations", site.globalDesignations] as const]
                  : []),
              ].map(([label, value]) => (
                <div
                  key={label as string}
                  className="grid gap-1 px-4 py-3 text-sm sm:grid-cols-[14rem_1fr] sm:items-center sm:gap-4"
                >
                  <dt className="text-muted-foreground">{label}</dt>
                  <dd className="text-foreground">{value}</dd>
                </div>
              ))}
            </dl>
          </section>
        </div>

        <aside className="space-y-5">
          <SiteMapPanel sites={getSitePoints()} siteId={site.id} />

          <SideCard title="Location">
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-muted-foreground">State / UT</dt>
                <dd className="text-right font-medium">{site.state}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted-foreground">District</dt>
                <dd className="text-right font-medium">{site.district}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted-foreground">Coordinates</dt>
                <dd className="text-right font-medium tabular-nums">
                  {toDms(site.latitude, "N", "S")}
                  <br />
                  {toDms(site.longitude, "E", "W")}
                </dd>
              </div>
            </dl>
            {site.administrativeRegion ? (
              <p className="mt-3 border-t border-border pt-3 text-xs leading-relaxed text-muted-foreground">
                {site.administrativeRegion}
              </p>
            ) : null}
          </SideCard>

          <SideCard title="Documents & data">
            <ul className="-mx-2 space-y-0.5">
              <li>
                <a href={risUrl} target="_blank" rel="noopener noreferrer" className={downloadLink}>
                  <FileText className="size-4.5 shrink-0 text-primary" aria-hidden="true" />
                  <span className="flex-1">
                    <span className="block font-medium text-foreground">
                      Ramsar Information Sheet
                    </span>
                    {site.lastPublicationDate ? (
                      <span className="text-xs text-muted-foreground">
                        Published {formatDate(site.lastPublicationDate)}
                      </span>
                    ) : null}
                  </span>
                  <ExternalLink className="size-3.5 text-muted-foreground" aria-hidden="true" />
                  <span className="sr-only"> (opens in a new tab)</span>
                </a>
              </li>
              <li>
                <a href={csvHref} download={`ramsar-site-${site.id}.csv`} className={downloadLink}>
                  <Download className="size-4.5 shrink-0 text-primary" aria-hidden="true" />
                  <span className="flex-1">
                    <span className="block font-medium text-foreground">Site data</span>
                    <span className="text-xs text-muted-foreground">CSV</span>
                  </span>
                </a>
              </li>
            </ul>
          </SideCard>

          <SideCard title="Water quality">
            <p className="text-sm text-muted-foreground">
              Sentinel-2 water-quality indices (NDCI, NDTI, NDWI, NDMI) and whether this site has a
              validated analysis boundary.
            </p>
            <Link
              href={`/water-quality?site=${site.id}`}
              className="mt-2 inline-block rounded-sm border border-border px-2.5 py-1.5 text-sm font-medium text-primary transition-colors hover:border-primary/40 hover:bg-muted"
            >
              Water-quality analysis
            </Link>
          </SideCard>

          <SideCard title="Climate monitoring">
            <ul className="grid grid-cols-2 gap-2 text-sm">
              {climateThemes.map((theme) => (
                <li key={theme.href}>
                  <Link
                    href={`${theme.href}?site=${site.id}`}
                    className="block rounded-sm border border-border px-2.5 py-1.5 font-medium text-primary transition-colors hover:border-primary/40 hover:bg-muted"
                  >
                    {theme.title}
                  </Link>
                </li>
              ))}
            </ul>
          </SideCard>

          <p className="px-1 text-xs text-muted-foreground">
            Site information courtesy of the{" "}
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
        </aside>
      </PageContainer>
    </>
  );
}
