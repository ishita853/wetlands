import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import { BackendError, backendFetch } from "@/lib/api/backend";
import { SESSION_COOKIE } from "@/lib/auth/constants";

/**
 * Admin session: the backend's JWT, kept in an httpOnly cookie so page
 * scripts cannot read it. Every check re-validates the token with the
 * backend (/auth/me), which rejects expired or revoked sessions.
 */
export type AdminUser = {
  username: string;
  role: "SUPER_ADMIN" | "DATA_MANAGER" | "VIEWER";
  must_change_password: boolean;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  must_change_password: boolean;
};

export async function setSession(token: TokenResponse) {
  (await cookies()).set(SESSION_COOKIE, token.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: token.expires_in,
  });
}

export async function clearSession() {
  (await cookies()).delete(SESSION_COOKIE);
}

export async function getSessionToken(): Promise<string | null> {
  return (await cookies()).get(SESSION_COOKIE)?.value ?? null;
}

/** Current admin, or null if not signed in / session invalid. Cached per request. */
export const getCurrentAdmin = cache(async (): Promise<AdminUser | null> => {
  const token = await getSessionToken();
  if (!token) return null;
  try {
    return await backendFetch<AdminUser>("/auth/me", { token });
  } catch (error) {
    if (error instanceof BackendError && error.status === 401) return null;
    throw error;
  }
});

/**
 * Guards admin pages: sends signed-out visitors to the login page and a
 * user with a pending initial password to the change-password page.
 */
export async function requireAdmin(): Promise<{ user: AdminUser; token: string }> {
  const user = await getCurrentAdmin();
  const token = await getSessionToken();
  if (!user || !token) redirect("/admin/login");
  if (user.must_change_password) redirect("/admin/change-password");
  return { user, token };
}
