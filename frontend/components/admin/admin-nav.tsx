"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const tabs = [
  { title: "Dashboard", href: "/admin/dashboard" },
  { title: "Datasets", href: "/admin/datasets" },
  { title: "Upload dataset", href: "/admin/datasets/upload" },
  { title: "Account", href: "/admin/account" },
];

export function AdminNav() {
  const pathname = usePathname();
  // Longest matching tab wins, so /admin/datasets/upload is not also "Datasets".
  const active = tabs
    .filter((t) => pathname === t.href || pathname.startsWith(`${t.href}/`))
    .sort((a, b) => b.href.length - a.href.length)[0]?.href;

  return (
    <nav aria-label="Administration" className="-mb-px flex gap-1 overflow-x-auto">
      {tabs.map((tab) => (
        <Link
          key={tab.href}
          href={tab.href}
          aria-current={tab.href === active ? "page" : undefined}
          className={cn(
            "border-b-3 px-3 py-2.5 text-sm font-medium whitespace-nowrap transition-colors",
            tab.href === active
              ? "border-sedge font-semibold text-primary"
              : "border-transparent text-foreground/75 hover:text-primary",
          )}
        >
          {tab.title}
        </Link>
      ))}
    </nav>
  );
}
