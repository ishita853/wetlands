"use client";

import { LogIn, Menu } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { HeaderSearch } from "@/components/layout/header-search";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { adminNav, isNavGroup, mainNav, siteConfig } from "@/config/site";
import { cn } from "@/lib/utils";
import { isNavPathActive } from "@/lib/utils/nav";

export function MobileNavigation() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const linkClass = (active: boolean) =>
    cn(
      "block border-l-3 border-transparent px-4 py-3 text-[0.9375rem] font-medium text-foreground transition-colors hover:bg-muted",
      active && "border-sedge bg-muted font-semibold text-primary",
    );

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button
          type="button"
          className="inline-flex h-10 shrink-0 items-center gap-2 rounded-sm border border-white/30 px-3 text-sm font-medium text-masthead-foreground transition-colors outline-none hover:bg-white/10 focus-visible:ring-3 focus-visible:ring-sedge/60 lg:hidden"
        >
          <Menu className="size-5" aria-hidden="true" />
          Menu
        </button>
      </SheetTrigger>
      <SheetContent
        side="right"
        className="w-full gap-0 p-0 sm:max-w-sm [&>[data-slot=sheet-close]]:text-masthead-foreground [&>[data-slot=sheet-close]]:hover:bg-white/15 [&>[data-slot=sheet-close]]:hover:text-masthead-foreground"
      >
        <SheetHeader className="border-b-4 border-sedge bg-masthead text-masthead-foreground">
          <SheetTitle className="text-masthead-foreground">{siteConfig.shortName}</SheetTitle>
          <SheetDescription className="text-masthead-muted">{siteConfig.tagline}</SheetDescription>
        </SheetHeader>

        <div className="border-b border-border p-4">
          <HeaderSearch id="mobile-site-search" />
        </div>

        <nav className="flex-1 overflow-y-auto py-2" aria-label="Primary (mobile)">
          <ul>
            {mainNav.map((entry) => {
              const active = isNavPathActive(pathname, entry.href);

              if (isNavGroup(entry)) {
                return (
                  <li key={entry.href}>
                    <Accordion
                      type="single"
                      collapsible
                      defaultValue={active ? entry.href : undefined}
                    >
                      <AccordionItem value={entry.href} className="border-none">
                        <AccordionTrigger
                          className={cn(
                            "rounded-none border-l-3 border-transparent px-4 py-3 text-[0.9375rem] font-medium text-foreground hover:bg-muted hover:no-underline",
                            active && "border-sedge text-primary",
                          )}
                        >
                          {entry.title}
                        </AccordionTrigger>
                        <AccordionContent className="pb-1 [&_a]:no-underline">
                          <ul className="ml-4 border-l border-border">
                            <li>
                              <Link
                                href={entry.href}
                                onClick={() => setOpen(false)}
                                className={linkClass(pathname === entry.href)}
                              >
                                Overview
                              </Link>
                            </li>
                            {entry.items.map((item) => (
                              <li key={item.href}>
                                <Link
                                  href={item.href}
                                  onClick={() => setOpen(false)}
                                  className={linkClass(pathname === item.href)}
                                >
                                  {item.title}
                                </Link>
                              </li>
                            ))}
                          </ul>
                        </AccordionContent>
                      </AccordionItem>
                    </Accordion>
                  </li>
                );
              }

              return (
                <li key={entry.href}>
                  <Link
                    href={entry.href}
                    onClick={() => setOpen(false)}
                    aria-current={active ? "page" : undefined}
                    className={linkClass(active)}
                  >
                    {entry.title}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="border-t border-border p-4">
          <Link
            href={adminNav.href}
            onClick={() => setOpen(false)}
            className="flex h-10 items-center justify-center gap-2 rounded-sm border border-primary text-sm font-semibold text-primary transition-colors hover:bg-primary hover:text-primary-foreground"
          >
            <LogIn className="size-4" aria-hidden="true" />
            {adminNav.title}
          </Link>
        </div>
      </SheetContent>
    </Sheet>
  );
}
