import { ArrowRight, Upload } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { FormMessage } from "@/components/admin/form-message";
import { StatusBadge } from "@/components/admin/status-badge";
import { primaryButton } from "@/components/admin/styles";
import { climateThemeDefs, type ClimateThemeKey } from "@/lib/data/climate";
import { backendFetch } from "@/lib/api/backend";
import type { AdminDataset, ClimateThemeStatus } from "@/lib/api/admin-types";
import { requireAdmin } from "@/lib/auth/session";
import { formatDate } from "@/lib/utils/format";

export const metadata: Metadata = { title: "Dashboard — Administration" };

export default async function AdminDashboardPage({ searchParams }: PageProps<"/admin/dashboard">) {
  const { token } = await requireAdmin();
  const { password } = await searchParams;
  const [themes, datasets] = await Promise.all([
    backendFetch<ClimateThemeStatus[]>("/admin/climate-themes", { token }),
    backendFetch<AdminDataset[]>("/admin/datasets", { token }),
  ]);
  const recent = datasets.slice(0, 5);

  return (
    <div className="space-y-10">
      {password === "changed" ? (
        <FormMessage tone="success" title="Password changed">
          <p className="mt-0.5">Other sessions for this account have been signed out.</p>
        </FormMessage>
      ) : null}

      <section aria-labelledby="themes-heading">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 id="themes-heading" className="text-2xl font-bold text-foreground">
              Climate indicator datasets
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              The version published for each theme is what the public climate pages show.
            </p>
          </div>
          <Link href="/admin/datasets/upload" className={primaryButton}>
            <Upload className="size-4" aria-hidden="true" />
            Upload dataset
          </Link>
        </div>

        <ul className="mt-5 grid gap-4 md:grid-cols-2">
          {themes.map(({ theme, title, published }) => {
            const def = climateThemeDefs[theme as ClimateThemeKey];
            return (
              <li
                key={theme}
                className="rounded-sm border border-border border-t-4 border-t-sedge bg-card p-5"
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="text-lg font-bold text-primary">{title}</h2>
                  {published ? (
                    <StatusBadge status="PUBLISHED" />
                  ) : (
                    <span className="rounded-sm border border-border px-2 py-0.5 text-xs font-medium text-muted-foreground">
                      Nothing published
                    </span>
                  )}
                </div>
                {published?.summary ? (
                  <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
                    <dt className="text-muted-foreground">File</dt>
                    <dd className="truncate">{published.original_filename}</dd>
                    <dt className="text-muted-foreground">Period</dt>
                    <dd>
                      {published.summary.years
                        ? `${published.summary.years[0]}–${published.summary.years[1]}`
                        : "—"}
                    </dd>
                    <dt className="text-muted-foreground">Sites</dt>
                    <dd>{published.summary.siteCount} of 101</dd>
                    <dt className="text-muted-foreground">Published</dt>
                    <dd>{published.published_at ? formatDate(published.published_at) : "—"}</dd>
                  </dl>
                ) : (
                  <p className="mt-3 text-sm text-muted-foreground">
                    The public page shows &ldquo;dataset not yet loaded&rdquo;.
                  </p>
                )}
                <div className="mt-4 flex flex-wrap gap-4 text-sm">
                  <Link
                    href={`/admin/datasets/upload?theme=${theme}`}
                    className="font-semibold text-primary hover:underline"
                  >
                    Upload a new version
                  </Link>
                  {def ? (
                    <Link
                      href={def.href}
                      className="font-medium text-foreground/80 hover:text-primary hover:underline"
                    >
                      View public page
                    </Link>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-labelledby="recent-heading">
        <div className="flex items-center justify-between gap-3">
          <h2 id="recent-heading" className="text-lg font-bold text-foreground">
            Recent uploads
          </h2>
          <Link
            href="/admin/datasets"
            className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline"
          >
            All datasets
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>
        {recent.length ? (
          <ul className="mt-3 divide-y divide-border rounded-sm border border-border bg-card">
            {recent.map((d) => (
              <li
                key={d.id}
                className="flex flex-wrap items-center justify-between gap-2 px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-foreground">{d.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(d.created_at)} · {d.uploaded_by_username ?? "—"}
                  </p>
                </div>
                <StatusBadge status={d.status} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 rounded-sm border border-dashed border-input bg-muted px-4 py-6 text-center text-sm text-muted-foreground">
            No datasets have been uploaded yet.
          </p>
        )}
      </section>
    </div>
  );
}
