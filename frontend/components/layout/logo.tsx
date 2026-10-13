import Link from "next/link";

import { cn } from "@/lib/utils";
import { siteConfig } from "@/config/site";

/**
 * Typographic portal identity, set on the dark masthead. No official logo or
 * emblem has been supplied, so none is imitated; if one is provided later it
 * slots in to the left of the wordmark without changing the header structure.
 */
export function Logo({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn(
        "flex min-w-0 flex-col outline-none focus-visible:ring-3 focus-visible:ring-sedge/70",
        className,
      )}
      aria-label={`${siteConfig.shortName} ${siteConfig.tagline} — home`}
    >
      <span className="text-xl leading-tight font-bold tracking-tight text-masthead-foreground sm:text-2xl">
        {siteConfig.shortName}
      </span>
      <span className="mt-0.5 text-xs leading-snug font-medium tracking-wide text-masthead-muted uppercase sm:text-[0.8125rem]">
        {siteConfig.tagline}
      </span>
    </Link>
  );
}
