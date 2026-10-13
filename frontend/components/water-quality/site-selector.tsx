"use client";

import { Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import type { WaterQualitySite } from "@/types/water-quality";

type Filter = "all" | "available" | "unavailable";

/** All 101 Ramsar Sites, searchable, with water-quality availability for each. */
export function SiteSelector({
  sites,
  selectedId,
  onSelect,
}: {
  sites: WaterQualitySite[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  const [query, setQuery] = useState("");
  const listRef = useRef<HTMLUListElement>(null);

  // Keep the selected site visible in the list (e.g. when opened via ?site=),
  // scrolling only the list itself, never the page.
  useEffect(() => {
    const list = listRef.current;
    const item = list?.querySelector<HTMLElement>('[aria-current="true"]');
    if (!list || !item) return;
    const top = item.offsetTop - list.offsetTop;
    if (top < list.scrollTop || top + item.offsetHeight > list.scrollTop + list.clientHeight) {
      list.scrollTop = Math.max(0, top - list.clientHeight / 2 + item.offsetHeight / 2);
    }
  }, [selectedId]);
  const [filter, setFilter] = useState<Filter>("all");

  const counts = useMemo(
    () => ({
      all: sites.length,
      available: sites.filter((s) => s.availability === "available").length,
      unavailable: sites.filter((s) => s.availability !== "available").length,
    }),
    [sites],
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return sites.filter((s) => {
      if (filter === "available" && s.availability !== "available") return false;
      if (filter === "unavailable" && s.availability === "available") return false;
      if (!q) return true;
      return (
        s.name.toLowerCase().includes(q) ||
        s.state.toLowerCase().includes(q) ||
        String(s.id).includes(q)
      );
    });
  }, [sites, query, filter]);

  return (
    <div className="flex flex-col self-start rounded-sm border border-border bg-card">
      <div className="space-y-3 border-b border-border p-3">
        <h2 className="text-xs font-bold tracking-[0.14em] text-muted-foreground uppercase">
          Ramsar Sites ({sites.length})
        </h2>
        <label className="relative block">
          <span className="sr-only">Search by site name, state or Ramsar ID</span>
          <Search
            className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Site, state or Ramsar ID"
            className="h-9 w-full rounded-sm border border-input bg-card pr-3 pl-8 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/30"
          />
        </label>
        <div role="radiogroup" aria-label="Filter by analysis availability" className="flex gap-1">
          {(["all", "available", "unavailable"] as Filter[]).map((f) => (
            <button
              key={f}
              type="button"
              role="radio"
              aria-checked={filter === f}
              onClick={() => setFilter(f)}
              className={cn(
                "flex-1 rounded-sm border px-2 py-1 text-xs font-medium capitalize transition-colors",
                filter === f
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border text-foreground hover:border-primary hover:text-primary",
              )}
            >
              {f} ({counts[f]})
            </button>
          ))}
        </div>
      </div>
      <ul
        ref={listRef}
        className="relative max-h-[26rem] min-h-0 flex-1 overflow-y-auto"
        aria-label="Ramsar Sites"
      >
        {visible.map((site) => {
          const selected = site.id === selectedId;
          return (
            <li key={site.id} className="border-b border-border last:border-b-0">
              <button
                type="button"
                onClick={() => onSelect(site.id)}
                aria-current={selected ? "true" : undefined}
                className={cn(
                  "w-full px-3 py-2.5 text-left transition-colors",
                  selected
                    ? "bg-primary/8 shadow-[inset_3px_0_0_var(--primary)]"
                    : "hover:bg-muted",
                )}
              >
                <span className="block text-sm font-medium text-foreground">{site.name}</span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  {site.state} · Ramsar {site.id}
                </span>
              </button>
            </li>
          );
        })}
        {visible.length === 0 ? (
          <li className="px-3 py-6 text-center text-sm text-muted-foreground">
            No matching sites.
          </li>
        ) : null}
      </ul>
    </div>
  );
}
