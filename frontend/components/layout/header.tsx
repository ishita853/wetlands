import { HeaderSearch } from "@/components/layout/header-search";
import { Logo } from "@/components/layout/logo";
import { PageContainer } from "@/components/layout/page-container";
import { MobileNavigation } from "@/components/navigation/mobile-navigation";
import { Navigation } from "@/components/navigation/navigation";

/**
 * Institutional header: dark masthead (identity + search) above a light,
 * sticky primary navigation bar. The navigation is a sibling of <header>
 * (not a child) so it can stay pinned while the masthead scrolls away.
 */
export function Header() {
  return (
    <>
      <header className="bg-masthead text-masthead-foreground">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-sm focus:bg-background focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-primary focus:ring-3 focus:ring-sedge focus:outline-none"
        >
          Skip to main content
        </a>
        <PageContainer className="flex min-h-20 items-center justify-between gap-6 py-3 sm:min-h-22">
          <Logo />
          <HeaderSearch className="hidden max-w-60 md:flex lg:max-w-xs" />
          <MobileNavigation />
        </PageContainer>
        {/* Sedge hairline separating identity from navigation */}
        <div aria-hidden="true" className="h-1 bg-sedge" />
      </header>
      <Navigation />
    </>
  );
}
