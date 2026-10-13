import { ChevronRight } from "lucide-react";
import Link from "next/link";

import { PageContainer } from "@/components/layout/page-container";

export type Crumb = { title: string; href?: string };

/**
 * Inner-page header band: breadcrumb trail, page title and a short
 * description. Keeps every section page on the same institutional rhythm.
 */
export function PageHeader({
  title,
  description,
  crumbs = [],
  children,
}: {
  title: string;
  description?: React.ReactNode;
  crumbs?: Crumb[];
  children?: React.ReactNode;
}) {
  const trail: Crumb[] = [{ title: "Home", href: "/" }, ...crumbs];

  return (
    <div className="border-b border-border bg-muted">
      <PageContainer className="py-6 sm:py-8">
        <nav aria-label="Breadcrumb">
          <ol className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
            {trail.map((crumb, i) => (
              <li key={`${crumb.title}-${i}`} className="flex items-center gap-1">
                {i > 0 ? <ChevronRight className="size-3.5" aria-hidden="true" /> : null}
                {crumb.href ? (
                  <Link href={crumb.href} className="hover:text-primary hover:underline">
                    {crumb.title}
                  </Link>
                ) : (
                  <span>{crumb.title}</span>
                )}
              </li>
            ))}
            <li className="flex items-center gap-1" aria-current="page">
              <ChevronRight className="size-3.5" aria-hidden="true" />
              <span className="font-medium text-foreground">{title}</span>
            </li>
          </ol>
        </nav>
        <h1 className="mt-3 text-2xl font-bold tracking-tight text-foreground after:mt-2.5 after:block after:h-0.75 after:w-16 after:bg-sedge sm:text-3xl">
          {title}
        </h1>
        {description ? (
          <div className="mt-4 max-w-3xl text-base leading-relaxed text-foreground/80">
            {description}
          </div>
        ) : null}
        {children}
      </PageContainer>
    </div>
  );
}
