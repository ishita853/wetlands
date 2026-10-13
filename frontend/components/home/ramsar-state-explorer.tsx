"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { RamsarMap } from "@/components/maps/ramsar-map";
import type { RamsarSitePoint } from "@/lib/data/ramsar";
import { cn } from "@/lib/utils";

/**
 * Homepage map + state index. Selecting a state highlights it on the map and
 * lists its sites; selecting a dot shows that site with a link to its page.
 */
export function RamsarStateExplorer({
  sites,
  className,
}: {
  sites: RamsarSitePoint[];
  className?: string;
}) {
  const [state, setState] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const byState = useMemo(() => {
    const counts = new Map<string, number>();
    for (const site of sites) counts.set(site.state, (counts.get(site.state) ?? 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  }, [sites]);
  const max = byState[0]?.[1] ?? 1;

  const selected = sites.find((s) => s.id === selectedId) ?? null;
  const stateSites = state
    ? sites.filter((s) => s.state === state).sort((a, b) => a.name.localeCompare(b.name))
    : [];

  return (
    <div className={cn("grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]", className)}>
      <div className="min-w-0">
        <RamsarMap
          sites={sites}
          selectedId={selectedId}
          onSelect={(id) => {
            setSelectedId(id);
            if (id !== null) setState(sites.find((s) => s.id === id)?.state ?? null);
          }}
          highlightState={state}
          cooperativeGestures
          className="h-[26rem] sm:h-[32rem] lg:h-[36rem]"
        />
        <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-full border border-white bg-[#2f6f45] ring-1 ring-[#2f6f45]" />
            Ramsar Site ({sites.length})
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-0 w-4 border-t border-[#7b86a3]" />
            State / UT boundary
          </span>
          <span>Select a site or a state to explore.</span>
        </div>
      </div>

      <aside
        aria-label="Ramsar Sites by state"
        className="flex max-h-[36rem] min-h-0 flex-col rounded-sm border border-border bg-card"
      >
        {selected ? (
          <div className="border-b border-border bg-accent/60 px-4 py-3">
            <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Selected site
            </p>
            <p className="mt-1 font-bold text-primary">{selected.name}</p>
            <p className="text-sm text-muted-foreground">
              {selected.district}, {selected.state} · Designated {selected.designationYear}
            </p>
            <Link
              href={`/wetlands/${selected.id}`}
              className="mt-1.5 inline-block text-sm font-semibold text-primary underline underline-offset-2 hover:no-underline"
            >
              View site profile
            </Link>
          </div>
        ) : null}

        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h3 className="text-sm font-semibold text-foreground">
            {state ? state : "Sites by State / UT"}
          </h3>
          {state ? (
            <button
              type="button"
              onClick={() => {
                setState(null);
                setSelectedId(null);
              }}
              className="text-sm font-medium text-primary underline underline-offset-2 hover:no-underline"
            >
              All states
            </button>
          ) : null}
        </div>

        <ul className="min-h-0 flex-1 overflow-y-auto py-1">
          {state
            ? stateSites.map((site) => (
                <li key={site.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(site.id)}
                    aria-current={site.id === selectedId ? "true" : undefined}
                    className={cn(
                      "flex w-full items-baseline justify-between gap-3 border-l-3 px-4 py-2 text-left text-sm transition-colors hover:bg-muted",
                      site.id === selectedId
                        ? "border-sedge bg-muted font-semibold"
                        : "border-transparent",
                    )}
                  >
                    <span className="text-foreground">{site.name}</span>
                    <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                      {site.designationYear}
                    </span>
                  </button>
                </li>
              ))
            : byState.map(([name, count]) => (
                <li key={name}>
                  <button
                    type="button"
                    onClick={() => {
                      setState(name);
                      setSelectedId(null);
                    }}
                    className="group grid w-full grid-cols-[minmax(0,1fr)_2rem] items-center gap-x-3 px-4 py-1.5 text-left text-sm transition-colors hover:bg-muted"
                  >
                    <span className="truncate text-foreground group-hover:text-primary">
                      {name}
                    </span>
                    <span className="text-right font-semibold text-primary tabular-nums">
                      {count}
                    </span>
                    <span aria-hidden="true" className="col-span-2 mt-1 h-1 bg-muted">
                      <span
                        className="block h-full bg-sedge"
                        style={{ width: `${(count / max) * 100}%` }}
                      />
                    </span>
                  </button>
                </li>
              ))}
        </ul>
      </aside>
    </div>
  );
}
