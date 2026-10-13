"use client";

import { Upload } from "lucide-react";
import Link from "next/link";
import { useActionState } from "react";

import { uploadClimateDatasetAction } from "@/app/admin/actions";
import { FormMessage } from "@/components/admin/form-message";
import { inputClass, labelClass, primaryButton } from "@/components/admin/styles";

export type ThemeOption = { key: string; title: string; href: string };

export function UploadForm({
  themes,
  initialTheme,
}: {
  themes: ThemeOption[];
  initialTheme?: string;
}) {
  const [state, action, pending] = useActionState(uploadClimateDatasetAction, undefined);
  const dataset = state?.dataset;
  const theme = themes.find((t) => t.key === dataset?.theme);

  return (
    <div className="space-y-5">
      {state?.error ? <FormMessage tone="error" title={state.error} /> : null}
      {dataset?.status === "FAILED" ? (
        <FormMessage
          tone="error"
          title={`“${dataset.original_filename}” was not published — ${dataset.validation_errors?.length ?? 0} problem(s) found`}
          items={dataset.validation_errors ?? []}
        >
          <p className="mt-0.5">
            Fix these in the file and upload it again. The attempt is kept in the dataset history.
          </p>
        </FormMessage>
      ) : null}
      {dataset && dataset.status !== "FAILED" ? (
        <FormMessage
          tone="success"
          title={
            dataset.status === "PUBLISHED"
              ? `Published: ${dataset.name}`
              : `Valid, not published: ${dataset.name}`
          }
        >
          {dataset.summary ? (
            <p className="mt-0.5">
              {dataset.summary.years
                ? `${dataset.summary.years[0]}–${dataset.summary.years[1]}`
                : ""}{" "}
              · {dataset.summary.siteCount} Ramsar Sites ·{" "}
              {dataset.summary.metrics.map((m) => m.label).join(", ")}
            </p>
          ) : null}
          <p className="mt-1.5 flex flex-wrap gap-4">
            {dataset.status === "PUBLISHED" && theme ? (
              <Link
                href={theme.href}
                className="font-semibold text-primary underline underline-offset-2"
              >
                View the public page
              </Link>
            ) : (
              <Link
                href="/admin/datasets"
                className="font-semibold text-primary underline underline-offset-2"
              >
                Publish it from Datasets
              </Link>
            )}
          </p>
        </FormMessage>
      ) : null}

      <form action={action} className="space-y-5 rounded-sm border border-border bg-card p-5">
        <div>
          <label htmlFor="theme" className={labelClass}>
            Climate theme
          </label>
          <select
            id="theme"
            name="theme"
            defaultValue={initialTheme ?? themes[0]?.key}
            className={inputClass}
          >
            {themes.map((t) => (
              <option key={t.key} value={t.key}>
                {t.title}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="file" className={labelClass}>
            Dataset file (.json, up to 25 MB)
          </label>
          <input
            id="file"
            name="file"
            type="file"
            accept=".json,application/json"
            required
            className="mt-1 block w-full text-sm text-foreground file:mr-3 file:h-10 file:cursor-pointer file:rounded-sm file:border file:border-border file:bg-muted file:px-3 file:text-sm file:font-medium file:text-foreground hover:file:border-primary"
          />
        </div>
        <div>
          <label htmlFor="description" className={labelClass}>
            Note <span className="font-normal text-muted-foreground">(optional)</span>
          </label>
          <textarea
            id="description"
            name="description"
            rows={2}
            maxLength={2000}
            placeholder="e.g. Recomputed with IMD 2025 data release"
            className={`${inputClass} h-auto py-2`}
          />
        </div>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            name="publish"
            defaultChecked
            className="mt-0.5 size-4 accent-[#243b6c]"
          />
          <span>
            <span className="font-semibold">Publish immediately if the file is valid</span>
            <span className="block text-muted-foreground">
              Replaces the version currently shown on the public page. Earlier versions stay in the
              history and can be republished.
            </span>
          </span>
        </label>
        <button type="submit" disabled={pending} className={primaryButton}>
          <Upload className="size-4" aria-hidden="true" />
          {pending ? "Validating…" : "Upload and validate"}
        </button>
      </form>
    </div>
  );
}
