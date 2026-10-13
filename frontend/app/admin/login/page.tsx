import { Lock } from "lucide-react";
import { redirect } from "next/navigation";

import { LoginForm } from "@/components/admin/login-form";
import { PageContainer } from "@/components/layout/page-container";
import { getCurrentAdmin } from "@/lib/auth/session";

export default async function AdminLoginPage() {
  const user = await getCurrentAdmin();
  if (user) redirect(user.must_change_password ? "/admin/change-password" : "/admin/dashboard");

  return (
    <div className="bg-muted">
      <PageContainer className="flex justify-center py-12 sm:py-16">
        <div className="w-full max-w-md rounded-sm border border-border border-t-4 border-t-sedge bg-card p-6 shadow-sm sm:p-8">
          <div className="flex items-center gap-2 text-primary">
            <Lock className="size-5" aria-hidden="true" />
            <h1 className="text-xl font-bold">Administrator sign-in</h1>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            For portal data managers. Datasets uploaded here are validated and published on the
            public climate monitoring pages.
          </p>
          <div className="mt-6">
            <LoginForm />
          </div>
          <p className="mt-6 border-t border-border pt-4 text-xs text-muted-foreground">
            Access is restricted to authorised personnel. After five failed attempts the account is
            locked for 15 minutes.
          </p>
        </div>
      </PageContainer>
    </div>
  );
}
