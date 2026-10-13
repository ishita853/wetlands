"use client";

import { LogIn } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { PageContainer } from "@/components/layout/page-container";
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
} from "@/components/ui/navigation-menu";
import { adminNav, isNavGroup, mainNav } from "@/config/site";
import { cn } from "@/lib/utils";
import { isNavPathActive } from "@/lib/utils/nav";

// Light bar, full-height cells; the active item is marked by a sedge
// underline and heavier weight. No pills, no motion beyond colour.
const itemClass = (active: boolean) =>
  cn(
    "inline-flex h-12 items-center rounded-none px-3.5 text-[0.9375rem] font-medium whitespace-nowrap text-foreground/80 transition-colors outline-none hover:bg-muted hover:text-primary focus-visible:bg-muted focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-inset",
    "data-active:bg-transparent data-active:hover:bg-muted data-active:focus:bg-muted",
    active && "font-semibold text-primary shadow-[inset_0_-3px_0_var(--sedge)]",
  );

export function Navigation() {
  const pathname = usePathname();
  const adminActive = isNavPathActive(pathname, adminNav.href);

  return (
    <nav
      aria-label="Primary"
      className="sticky top-0 z-40 hidden border-b border-border bg-card shadow-[0_1px_3px_oklch(0_0_0/0.06)] lg:block"
    >
      <PageContainer className="flex items-stretch justify-between">
        <NavigationMenu viewport={false} className="max-w-none justify-start">
          <NavigationMenuList className="justify-start">
            {mainNav.map((entry) => {
              const active = isNavPathActive(pathname, entry.href);

              if (isNavGroup(entry)) {
                return (
                  <NavigationMenuItem key={entry.href}>
                    <NavigationMenuTrigger
                      className={cn(
                        itemClass(active),
                        "w-auto bg-transparent py-0 focus:bg-muted data-open:bg-muted data-open:hover:bg-muted data-open:focus:bg-muted data-popup-open:bg-muted",
                      )}
                    >
                      {entry.title}
                    </NavigationMenuTrigger>
                    <NavigationMenuContent className="group-data-[viewport=false]/navigation-menu:mt-0 group-data-[viewport=false]/navigation-menu:rounded-none group-data-[viewport=false]/navigation-menu:rounded-b-sm group-data-[viewport=false]/navigation-menu:border-t-3 group-data-[viewport=false]/navigation-menu:border-sedge group-data-[viewport=false]/navigation-menu:p-0 group-data-[viewport=false]/navigation-menu:shadow-md group-data-[viewport=false]/navigation-menu:ring-border">
                      <ul className="w-64 py-1">
                        <li>
                          <NavigationMenuLink
                            asChild
                            active={pathname === entry.href}
                            className="rounded-none px-3 py-2 font-semibold text-primary"
                          >
                            <Link href={entry.href}>Climate Monitoring Overview</Link>
                          </NavigationMenuLink>
                        </li>
                        <li aria-hidden="true" className="my-1 border-t border-border" />
                        {entry.items.map((item) => (
                          <li key={item.href}>
                            <NavigationMenuLink
                              asChild
                              active={pathname === item.href}
                              className="rounded-none border-l-3 border-transparent px-3 py-2 text-foreground data-active:border-primary data-active:font-semibold"
                            >
                              <Link href={item.href}>{item.title}</Link>
                            </NavigationMenuLink>
                          </li>
                        ))}
                      </ul>
                    </NavigationMenuContent>
                  </NavigationMenuItem>
                );
              }

              return (
                <NavigationMenuItem key={entry.href}>
                  <NavigationMenuLink asChild active={active} className={itemClass(active)}>
                    <Link href={entry.href} aria-current={active ? "page" : undefined}>
                      {entry.title}
                    </Link>
                  </NavigationMenuLink>
                </NavigationMenuItem>
              );
            })}
          </NavigationMenuList>
        </NavigationMenu>

        <Link
          href={adminNav.href}
          aria-current={adminActive ? "page" : undefined}
          className="my-auto inline-flex h-9 items-center gap-2 rounded-sm bg-primary px-3.5 text-sm font-semibold whitespace-nowrap text-primary-foreground transition-colors outline-none hover:bg-masthead focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <LogIn className="size-4" aria-hidden="true" />
          {adminNav.title}
        </Link>
      </PageContainer>
    </nav>
  );
}
