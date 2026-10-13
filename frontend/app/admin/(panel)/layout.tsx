import { LogOut, ShieldCheck } from "lucide-react";

import { logoutAction } from "@/app/admin/actions";
import { AdminNav } from "@/components/admin/admin-nav";
import { PageContainer } from "@/components/layout/page-container";
import { requireAdmin } from "@/lib/auth/session";

/** Every page in this group requires a signed-in administrator. */
export default async function AdminPanelLayout({ children }: { children: React.ReactNode }) {
  const { user } = await requireAdmin();

  return (
    <>
      <div className="border-b border-border bg-muted">
        <PageContainer>
          <div className="flex flex-wrap items-center justify-between gap-3 pt-5">
            <p className="flex items-center gap-2 text-sm font-semibold tracking-wide text-muted-foreground uppercase">
              <ShieldCheck className="size-4 text-sedge-strong" aria-hidden="true" />
              Portal administration
            </p>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-muted-foreground">
                Signed in as <strong className="text-foreground">{user.username}</strong>
              </span>
              <form action={logoutAction}>
                <button
                  type="submit"
                  className="inline-flex items-center gap-1.5 font-medium text-primary hover:underline"
                >
                  <LogOut className="size-4" aria-hidden="true" />
                  Sign out
                </button>
              </form>
            </div>
          </div>
          <div className="mt-3">
            <AdminNav />
          </div>
        </PageContainer>
      </div>
      <PageContainer className="section-y">{children}</PageContainer>
    </>
  );
}
