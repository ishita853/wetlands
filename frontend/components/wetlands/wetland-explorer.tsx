"use client";

import { Search, X } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { RamsarMap } from "@/components/maps/ramsar-map";
import type { RamsarSitePoint, WetlandGroup } from "@/lib/data/ramsar";
import { cn } from "@/lib/utils";

const GROUP_LABELS: Record<WetlandGroup, string> = {
  "Inland wetlands": "Inland",
  "Marine or coastal wetlands": "Marine / coastal",
  "Human-made wetlands": "Human-made",
};

const fieldClass =
  "h-10 w-full rounded-sm border border-input bg-card px-3 text-sm text-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring/30";

function formatArea(ha: number) {
  return `${ha.toLocaleString("en-IN", { maximumFractionDigits: ha < 100 ? 1 : 0 })} ha`;
}

export function WetlandExplorer({
  sites,
  initialQuery = "",
}: {
  sites: RamsarSitePoint[];
  initialQuery?: string;
}) {
  const [query, setQuery] = useState(initialQuery);
  const [state, setState] = useState("");
  const [group, setGroup] = useState<WetlandGroup | "">("");
  const [sort, setSort] = useState<"name" | "year" | "area">("name");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const states = useMemo(() => [...new Set(sites.map((s) => s.state))].sort(), [sites]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = sites.filter(
      (s) =>
        (!q ||
          s.name.toLowerCase().includes(q) ||
          s.state.toLowerCase().includes(q) ||
          s.district.toLowerCase().includes(q)) &&
        (!state || s.state === state) &&
        (!group || s.groups.includes(group)),
    );
    return list.sort((a, b) =>
      sort === "year"
        ? b.designationYear - a.designationYear || a.name.localeCompare(b.name)
        : sort === "area"
          ? b.areaHa - a.areaHa
          : a.name.localeCompare(b.name),
    );
  }, [sites, query, state, group, sort]);

  const selected = sites.find((s) => s.id === selectedId) ?? null;
  const filtersActive = Boolean(query || state || group);

  return (
    <div>
      <form
        role="search"
        onSubmit={(event) => event.preventDefault()}
        className="grid gap-3 rounded-sm border border-border bg-card p-4 sm:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))]"
      >
        <div>
          <label htmlFor="explorer-q" className="text-xs font-semibold text-muted-foreground">
            Search
          </label>
          <div className="relative mt-1">
            <Search
              className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <input
              id="explorer-q"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Site, district or state"
              className={cn(fieldClass, "pl-9")}
            />
          </div>
        </div>
        <div>
          <label htmlFor="explorer-state" className="text-xs font-semibold text-muted-foreground">
            State / UT
          </label>
          <select
            id="explorer-state"
            value={state}
            onChange={(event) => setState(event.target.value)}
            className={cn(fieldClass, "mt-1")}
          >
            <option value="">All states and UTs</option>
            {states.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="explorer-type" className="text-xs font-semibold text-muted-foreground">
            Wetland type
          </label>
          <select
            id="explorer-type"
            value={group}
            onChange={(event) => setGroup(event.target.value as WetlandGroup | "")}
            className={cn(fieldClass, "mt-1")}
          >
            <option value="">All types</option>
            {(Object.keys(GROUP_LABELS) as WetlandGroup[]).map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="explorer-sort" className="text-xs font-semibold text-muted-foreground">
            Sort by
          </label>
          <select
            id="explorer-sort"
            value={sort}
            onChange={(event) => setSort(event.target.value as typeof sort)}
            className={cn(fieldClass, "mt-1")}
          >
            <option value="name">Name (A–Z)</option>
            <option value="year">Designation (newest)</option>
            <option value="area">Area (largest)</option>
          </select>
        </div>
      </form>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm">
        <p className="text-muted-foreground" aria-live="polite">
          Showing <strong className="text-foreground">{filtered.length}</strong> of {sites.length}{" "}
          Ramsar Sites
        </p>
        {filtersActive ? (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setState("");
              setGroup("");
            }}
            className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
          >
            <X className="size-3.5" aria-hidden="true" />
            Clear filters
          </button>
        ) : null}
      </div>

      <div className="mt-3 grid gap-5 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <ul
          aria-label="Ramsar Sites"
          className="order-2 max-h-[40rem] divide-y divide-border overflow-y-auto rounded-sm border border-border bg-card lg:order-1"
        >
          {filtered.map((site) => {
            const active = site.id === selectedId;
            return (
              <li key={site.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(site.id)}
                  aria-current={active ? "true" : undefined}
                  className={cn(
                    "w-full border-l-3 px-4 py-2.5 text-left transition-colors hover:bg-muted focus-visible:bg-muted focus-visible:outline-none",
                    active ? "border-sedge bg-muted" : "border-transparent",
                  )}
                >
                  <span className="block text-sm font-semibold text-primary">{site.name}</span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">
                    {site.state} · {site.designationYear} · {formatArea(site.areaHa)}
                  </span>
                </button>
              </li>
            );
          })}
          {filtered.length === 0 ? (
            <li className="px-4 py-8 text-center text-sm text-muted-foreground">
              No Ramsar Sites match these filters.
            </li>
          ) : null}
        </ul>

        <div className="relative order-1 min-w-0 lg:order-2">
          <RamsarMap
            sites={filtered}
            selectedId={selectedId}
            onSelect={setSelectedId}
            highlightState={state || null}
            sizeByArea
            className="h-[26rem] sm:h-[34rem] lg:h-[40rem]"
          />
          {selected ? (
            <div className="absolute right-3 bottom-8 left-3 rounded-sm border border-border border-l-4 border-l-sedge bg-card p-4 shadow-md sm:right-auto sm:w-80">
              <button
                type="button"
                onClick={() => setSelectedId(null)}
                aria-label="Close site details"
                className="absolute top-2 right-2 rounded-sm p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
              <p className="pr-6 font-bold text-primary">{selected.name}</p>
              <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                <dt className="text-muted-foreground">Location</dt>
                <dd>
                  {selected.district}, {selected.state}
                </dd>
                <dt className="text-muted-foreground">Designated</dt>
                <dd>{selected.designationYear}</dd>
                <dt className="text-muted-foreground">Area</dt>
                <dd>{formatArea(selected.areaHa)}</dd>
                <dt className="text-muted-foreground">Type</dt>
                <dd>{selected.groups.map((g) => GROUP_LABELS[g]).join(", ")}</dd>
              </dl>
              <Link
                href={`/wetlands/${selected.id}`}
                className="mt-3 inline-flex h-9 items-center rounded-sm bg-primary px-3 text-sm font-semibold text-primary-foreground hover:bg-masthead"
              >
                View site profile
              </Link>
            </div>
          ) : null}
          <p className="mt-2 text-xs text-muted-foreground">
            Dot size is proportional to designated site area.
          </p>
        </div>
      </div>
    </div>
  );
}
