import * as React from "react";

import { cn } from "@/lib/utils";

function Eyebrow({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="eyebrow"
      className={cn("text-xs font-semibold tracking-wider text-primary uppercase", className)}
      {...props}
    />
  );
}

function PageHeading({ className, ...props }: React.ComponentProps<"h1">) {
  return (
    <h1
      data-slot="page-heading"
      className={cn("text-2xl font-bold tracking-tight text-foreground sm:text-3xl", className)}
      {...props}
    />
  );
}

/**
 * Institutional section title: restrained size with a short sedge-green rule
 * beneath — the portal's recurring heading marker. `as` keeps the heading
 * level correct wherever it is used.
 */
function SectionTitle({
  as: Tag = "h2",
  className,
  children,
  ...props
}: React.ComponentProps<"h2"> & { as?: "h1" | "h2" | "h3" }) {
  return (
    <Tag
      data-slot="section-title"
      className={cn(
        "text-2xl font-bold tracking-tight text-foreground after:mt-2.5 after:block after:h-0.75 after:w-16 after:bg-sedge sm:text-[1.75rem]",
        className,
      )}
      {...props}
    >
      {children}
    </Tag>
  );
}

function SectionHeading({ className, ...props }: React.ComponentProps<"h2">) {
  return (
    <h2
      data-slot="section-heading"
      className={cn("text-xl font-bold tracking-tight text-foreground sm:text-2xl", className)}
      {...props}
    />
  );
}

function SubsectionHeading({ className, ...props }: React.ComponentProps<"h3">) {
  return (
    <h3
      data-slot="subsection-heading"
      className={cn("text-lg font-semibold text-foreground", className)}
      {...props}
    />
  );
}

function Lead({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="lead"
      className={cn("text-base leading-relaxed text-muted-foreground sm:text-lg", className)}
      {...props}
    />
  );
}

function Muted({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p data-slot="muted" className={cn("text-sm text-muted-foreground", className)} {...props} />
  );
}

export { Eyebrow, PageHeading, SectionTitle, SectionHeading, SubsectionHeading, Lead, Muted };
