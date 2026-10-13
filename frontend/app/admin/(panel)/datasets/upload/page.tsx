import type { Metadata } from "next";

import { UploadForm } from "@/components/admin/upload-form";
import { BASELINE, climateThemeDefs, climateThemeOrder } from "@/lib/data/climate";

export const metadata: Metadata = { title: "Upload dataset — Administration" };

export default async function UploadDatasetPage({
  searchParams,
}: PageProps<"/admin/datasets/upload">) {
  const { theme } = await searchParams;
  const themes = climateThemeOrder.map((key) => ({
    key,
    title: climateThemeDefs[key].title,
    href: climateThemeDefs[key].href,
  }));

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="min-w-0">
        <h1 className="text-2xl font-bold text-foreground">Upload a climate indicator dataset</h1>
        <p className="mt-1 mb-5 text-sm text-muted-foreground">
          The file is checked before anything is published. If it has problems, you get the full
          list and the public page stays as it is.
        </p>
        <UploadForm
          themes={themes}
          initialTheme={typeof theme === "string" && theme in climateThemeDefs ? theme : undefined}
        />
      </div>

      <aside className="h-fit space-y-3 rounded-sm border border-border bg-muted p-5 text-sm">
        <h2 className="font-semibold text-foreground">File checklist</h2>
        <ul className="list-disc space-y-1.5 pl-5 text-foreground/85">
          <li>
            JSON with <code className="text-xs">theme</code>,{" "}
            <code className="text-xs">source</code>, <code className="text-xs">baseline</code>,{" "}
            <code className="text-xs">years</code> and <code className="text-xs">metrics</code>
          </li>
          <li>
            <code className="text-xs">theme</code> matches the theme selected here
          </li>
          <li>Years in increasing order, no repeats</li>
          <li>Sites keyed by official Ramsar Site number (e.g. Lonar Lake = 2441)</li>
          <li>
            One value per year for each site; <code className="text-xs">null</code> for a missing
            year, not 0
          </li>
          <li>Percentile indicators relative to the {BASELINE} baseline</li>
        </ul>
        <p className="border-t border-border pt-3 text-xs text-muted-foreground">
          The full format, with the agreed indicator definitions, is in{" "}
          <code>frontend/data/climate/README.md</code> in the project repository.
        </p>
      </aside>
    </div>
  );
}
