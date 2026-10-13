import { Upload } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { publishDatasetAction, unpublishDatasetAction } from "@/app/admin/actions";
import { FormMessage } from "@/components/admin/form-message";
import { StatusBadge } from "@/components/admin/status-badge";
import { primaryButton, secondaryButton } from "@/components/admin/styles";
import { backendFetch } from "@/lib/api/backend";
import type { AdminDataset } from "@/lib/api/admin-types";
import { requireAdmin } from "@/lib/auth/session";
import { formatDate } from "@/lib/utils/format";

export const metadata: Metadata = { title: "Datasets — Administration" };

const DONE: Record<string, string> = {
  publish: "Dataset published. The public page now shows this version.",
  unpublish: "Dataset withdrawn. The public page shows “dataset not yet loaded”.",
};

function formatBytes(bytes: number) {
  return bytes < 1024 * 1024
    ? `${(bytes / 1024).toFixed(1)} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default async function AdminDatasetsPage({ searchParams }: PageProps<"/admin/datasets">) {
  const { token } = await requireAdmin();
  const { done, error } = await searchParams;
  const datasets = await backendFetch<AdminDataset[]>("/admin/datasets", { token });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Datasets</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Every upload is kept, including files that failed validation. Publish any valid version
            to make it live, or to roll back to an earlier one.
          </p>
        </div>
        <Link href="/admin/datasets/upload" className={primaryButton}>
          <Upload className="size-4" aria-hidden="true" />
          Upload dataset
        </Link>
      </div>

      {typeof done === "string" && DONE[done] ? (
        <FormMessage tone="success" title={DONE[done]} />
      ) : null}
      {typeof error === "string" ? <FormMessage tone="error" title={error} /> : null}

      {datasets.length === 0 ? (
        <p className="rounded-sm border border-dashed border-input bg-muted px-4 py-10 text-center text-sm text-muted-foreground">
          No datasets have been uploaded yet.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-sm border border-border bg-card">
          <table className="w-full min-w-3xl text-left text-sm">
            <thead className="bg-muted text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Dataset</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold">Contents</th>
                <th className="px-4 py-2.5 font-semibold">Uploaded</th>
                <th className="px-4 py-2.5 font-semibold">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border align-top">
              {datasets.map((d) => (
                <tr key={d.id}>
                  <td className="px-4 py-3">
                    <p className="font-semibold text-foreground">{d.name}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {formatBytes(d.size_bytes)} · SHA-256 {d.sha256.slice(0, 12)}…
                    </p>
                    {d.description ? (
                      <p className="mt-1 max-w-sm text-xs text-foreground/80">{d.description}</p>
                    ) : null}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={d.status} />
                  </td>
                  <td className="px-4 py-3">
                    {d.summary ? (
                      <p className="text-xs text-foreground/85">
                        {d.summary.years ? `${d.summary.years[0]}–${d.summary.years[1]}` : "—"} ·{" "}
                        {d.summary.siteCount} sites · {d.summary.metrics.length} indicator
                        {d.summary.metrics.length === 1 ? "" : "s"}
                        <br />
                        <span className="text-muted-foreground">{d.summary.source}</span>
                      </p>
                    ) : d.validation_errors?.length ? (
                      <details className="text-xs">
                        <summary className="cursor-pointer font-medium text-destructive">
                          {d.validation_errors.length} problem
                          {d.validation_errors.length === 1 ? "" : "s"} found
                        </summary>
                        <ul className="mt-1.5 max-w-md list-disc space-y-0.5 pl-4 text-foreground/85">
                          {d.validation_errors.map((e, i) => (
                            <li key={i}>{e}</li>
                          ))}
                        </ul>
                      </details>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs whitespace-nowrap text-muted-foreground">
                    {formatDate(d.created_at)}
                    <br />
                    {d.uploaded_by_username ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {d.status === "PUBLISHED" ? (
                      <form action={unpublishDatasetAction}>
                        <input type="hidden" name="id" value={d.id} />
                        <button type="submit" className={secondaryButton}>
                          Unpublish
                        </button>
                      </form>
                    ) : d.status === "VALIDATED" || d.status === "SUPERSEDED" ? (
                      <form action={publishDatasetAction}>
                        <input type="hidden" name="id" value={d.id} />
                        <button type="submit" className={secondaryButton}>
                          {d.status === "SUPERSEDED" ? "Republish" : "Publish"}
                        </button>
                      </form>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
