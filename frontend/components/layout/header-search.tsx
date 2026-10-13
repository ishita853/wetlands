import { Search } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Site search entry point. Submits to the Ramsar Wetlands page as `?q=`;
 * that page will consume the query once the wetland dataset is connected.
 */
export function HeaderSearch({
  className,
  id = "site-search",
}: {
  className?: string;
  id?: string;
}) {
  return (
    <form action="/wetlands" role="search" className={cn("flex w-full", className)}>
      <label htmlFor={id} className="sr-only">
        Search Ramsar wetlands
      </label>
      <input
        id={id}
        name="q"
        type="search"
        placeholder="Search wetlands"
        autoComplete="off"
        className="h-10 min-w-0 flex-1 rounded-l-sm border border-r-0 border-input bg-card px-3 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:ring-3 focus-visible:ring-sedge/50"
      />
      <button
        type="submit"
        aria-label="Submit search"
        className="flex h-10 w-11 shrink-0 items-center justify-center rounded-r-sm bg-sedge-strong text-white transition-colors outline-none hover:bg-[color-mix(in_oklch,var(--sedge-strong),black_15%)] focus-visible:ring-3 focus-visible:ring-sedge/50"
      >
        <Search className="size-4" aria-hidden="true" />
      </button>
    </form>
  );
}
