import type { Metadata } from "next";
import { connection } from "next/server";
import Link from "next/link";

import { BarChart } from "@/components/charts/bar-chart";
import { ChartFigure } from "@/components/charts/chart-figure";
import { LineChart } from "@/components/charts/line-chart";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { getClimateStatus } from "@/lib/data/climate";
import { WETLAND_GROUPS, getRamsarSites } from "@/lib/data/ramsar";

export const metadata: Metadata = { title: "Analysis" };

const SOURCE = "Ramsar Convention on Wetlands";

function countBy<T>(items: T[], key: (item: T) => string) {
  const counts = new Map<string, number>();
  for (const item of items) counts.set(key(item), (counts.get(key(item)) ?? 0) + 1);
  return counts;
}

export default async function AnalysisPage() {
  // Rendered per request: datasets can be published at any time from the admin area.
  await connection();
  const sites = getRamsarSites();

  // Designations per year, every year from the first designation to the latest.
  const years = sites.map((s) => s.designationYear);
  const first = Math.min(...years);
  const last = Math.max(...years);
  const yearAxis = Array.from({ length: last - first + 1 }, (_, i) => first + i);
  const perYear = countBy(sites, (s) => String(s.designationYear));
  const perYearValues = yearAxis.map((y) => perYear.get(String(y)) ?? 0);
  let running = 0;
  const cumulative = perYearValues.map((v) => (running += v));

  const byState = [...countBy(sites, (s) => s.state).entries()].sort(
    (a, b) => b[1] - a[1] || a[0].localeCompare(b[0]),
  );

  const areaByState = new Map<string, number>();
  for (const s of sites) areaByState.set(s.state, (areaByState.get(s.state) ?? 0) + s.areaHa);
  const areaRanked = [...areaByState.entries()].sort((a, b) => b[1] - a[1]);

  const groupCounts = WETLAND_GROUPS.map(
    (group) => sites.filter((s) => group in s.wetlandTypes).length,
  );

  const climate = getClimateStatus();
  const busiest = yearAxis[perYearValues.indexOf(Math.max(...perYearValues))];

  return (
    <>
      <PageHeader
        title="Analysis"
        description={
          <p>
            Graphical analysis of India&apos;s Ramsar Site network, and of the four climate
            monitoring themes across the {sites.length} sites as indicator datasets are loaded.
          </p>
        }
      />

      <PageContainer className="section-y space-y-12">
        <section aria-labelledby="network-heading">
          <h2 id="network-heading" className="text-xl font-bold text-foreground">
            Ramsar Site network
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            India&apos;s first Ramsar Sites were designated in {first}. {busiest} saw the most
            designations in a single year ({Math.max(...perYearValues)}).
          </p>

          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <ChartFigure
              title="Ramsar Sites designated per year"
              subtitle={`Number of sites, ${first}–${last}`}
              source={SOURCE}
              table={{
                columns: ["Year", "Sites designated"],
                rows: yearAxis.map((y, i) => [y, perYearValues[i]]).filter(([, v]) => v),
              }}
            >
              <BarChart
                categories={yearAxis}
                values={perYearValues}
                unit="sites"
                ariaLabel="Bar chart of Ramsar Sites designated in India per year"
              />
            </ChartFigure>

            <ChartFigure
              title="Growth of the Ramsar Site network"
              subtitle="Cumulative number of Ramsar Sites in India"
              source={SOURCE}
              table={{
                columns: ["Year", "Total sites"],
                rows: yearAxis.map((y, i) => [y, cumulative[i]]),
              }}
            >
              <LineChart
                x={yearAxis}
                series={[{ name: "Ramsar Sites", values: cumulative, style: "area" }]}
                unit="sites"
                ariaLabel="Line chart of the cumulative number of Ramsar Sites in India"
              />
            </ChartFigure>

            <ChartFigure
              title="Ramsar Sites by State / UT"
              subtitle="Number of sites"
              source={SOURCE}
              table={{ columns: ["State / UT", "Sites"], rows: byState }}
            >
              <BarChart
                categories={byState.map(([name]) => name)}
                values={byState.map(([, n]) => n)}
                horizontal
                unit="sites"
                height={Math.max(300, byState.length * 22)}
                ariaLabel="Horizontal bar chart of Ramsar Sites per state and union territory"
              />
            </ChartFigure>

            <ChartFigure
              title="Designated area by State / UT"
              subtitle="Total Ramsar Site area, hectares"
              source={SOURCE}
              table={{
                columns: ["State / UT", "Area (ha)"],
                rows: areaRanked.map(([name, ha]) => [
                  name,
                  Math.round(ha).toLocaleString("en-IN"),
                ]),
              }}
            >
              <BarChart
                categories={areaRanked.map(([name]) => name)}
                values={areaRanked.map(([, ha]) => Math.round(ha))}
                horizontal
                unit="ha"
                height={Math.max(300, areaRanked.length * 22)}
                ariaLabel="Horizontal bar chart of designated Ramsar Site area per state"
              />
            </ChartFigure>

            <ChartFigure
              title="Ramsar Sites by wetland type"
              subtitle="Sites containing each Ramsar wetland-type group (a site can contain several)"
              source={SOURCE}
              table={{
                columns: ["Wetland type group", "Sites"],
                rows: WETLAND_GROUPS.map((g, i) => [g, groupCounts[i]]),
              }}
              className="lg:col-span-2"
            >
              <BarChart
                categories={[...WETLAND_GROUPS]}
                values={groupCounts}
                horizontal
                unit="sites"
                height={160}
                ariaLabel="Bar chart of Ramsar Sites by wetland type group"
              />
            </ChartFigure>
          </div>
        </section>

        <section aria-labelledby="climate-analysis-heading">
          <h2 id="climate-analysis-heading" className="text-xl font-bold text-foreground">
            Climate indicator analysis
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Each theme page provides a dot-density map of the Ramsar Sites coloured by the selected
            indicator, national and state-level trends, site rankings and per-site time series.
          </p>
          <div className="mt-4 overflow-x-auto rounded-sm border border-border bg-card">
            <table className="w-full min-w-xl text-left text-sm">
              <thead className="bg-muted text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 font-semibold">Theme</th>
                  <th className="px-4 py-2.5 font-semibold">Dataset</th>
                  <th className="px-4 py-2.5 font-semibold">Period</th>
                  <th className="px-4 py-2.5 font-semibold">Sites covered</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {climate.map(({ theme, loaded, years: span, siteCount, source }) => (
                  <tr key={theme.key}>
                    <td className="px-4 py-3">
                      <Link
                        href={theme.href}
                        className="font-semibold text-primary hover:underline"
                      >
                        {theme.title}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      {loaded ? (
                        <span className="text-foreground">{source}</span>
                      ) : (
                        <span className="text-muted-foreground">Not yet loaded</span>
                      )}
                    </td>
                    <td className="px-4 py-3 tabular-nums">
                      {span ? `${span[0]}–${span[1]}` : "—"}
                    </td>
                    <td className="px-4 py-3 tabular-nums">
                      {loaded ? `${siteCount} of ${sites.length}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </PageContainer>
    </>
  );
}
