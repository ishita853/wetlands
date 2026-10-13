import { KeyRound } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";

import { logoutAction } from "@/app/admin/actions";
import { ChangePasswordForm } from "@/components/admin/change-password-form";
import { FormMessage } from "@/components/admin/form-message";
import { PageContainer } from "@/components/layout/page-container";
import { getCurrentAdmin } from "@/lib/auth/session";

export default async function ChangePasswordPage() {
  const user = await getCurrentAdmin();
  if (!user) redirect("/admin/login");

  return (
    <div className="bg-muted">
      <PageContainer className="flex justify-center py-12 sm:py-16">
        <div className="w-full max-w-md rounded-sm border border-border border-t-4 border-t-sedge bg-card p-6 shadow-sm sm:p-8">
          <div className="flex items-center gap-2 text-primary">
            <KeyRound className="size-5" aria-hidden="true" />
            <h1 className="text-xl font-bold">Change password</h1>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Signed in as <strong className="text-foreground">{user.username}</strong>. Changing the
            password signs out every other session.
          </p>

          {user.must_change_password ? (
            <FormMessage tone="error" title="Set a new password to continue" className="mt-4">
              <p className="mt-0.5">
                This account is using its initial password, which was shared by email. Choose a new
                password before using the administration area.
              </p>
            </FormMessage>
          ) : null}

          <div className="mt-6">
            <ChangePasswordForm />
          </div>

          <div className="mt-6 flex items-center justify-between border-t border-border pt-4 text-sm">
            {user.must_change_password ? (
              <span />
            ) : (
              <Link href="/admin/dashboard" className="font-medium text-primary hover:underline">
                Back to dashboard
              </Link>
            )}
            <form action={logoutAction}>
              <button
                type="submit"
                className="font-medium text-muted-foreground hover:text-primary hover:underline"
              >
                Sign out
              </button>
            </form>
          </div>
        </div>
      </PageContainer>
    </div>
  );
}
