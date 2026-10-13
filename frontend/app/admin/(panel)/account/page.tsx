import type { Metadata } from "next";
import Link from "next/link";

import { secondaryButton } from "@/components/admin/styles";
import { requireAdmin } from "@/lib/auth/session";

export const metadata: Metadata = { title: "Account — Administration" };

const ROLE_LABELS = {
  SUPER_ADMIN: "Administrator",
  DATA_MANAGER: "Data manager",
  VIEWER: "Viewer",
} as const;

export default async function AccountPage() {
  const { user } = await requireAdmin();

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold text-foreground">Account</h1>
      <dl className="mt-5 divide-y divide-border rounded-sm border border-border bg-card text-sm">
        <div className="grid grid-cols-[9rem_1fr] px-4 py-3">
          <dt className="text-muted-foreground">Username</dt>
          <dd className="font-semibold">{user.username}</dd>
        </div>
        <div className="grid grid-cols-[9rem_1fr] px-4 py-3">
          <dt className="text-muted-foreground">Role</dt>
          <dd>{ROLE_LABELS[user.role]}</dd>
        </div>
      </dl>
      <Link href="/admin/change-password" className={`${secondaryButton} mt-5`}>
        Change password
      </Link>
    </div>
  );
}
