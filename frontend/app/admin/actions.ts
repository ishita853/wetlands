"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { BackendError, backendFetch } from "@/lib/api/backend";
import type { AdminDataset } from "@/lib/api/admin-types";
import {
  clearSession,
  getSessionToken,
  requireAdmin,
  setSession,
  type TokenResponse,
} from "@/lib/auth/session";

export type FormState =
  | {
      error?: string;
      errors?: string[];
      /** Echoed back so React's post-submit form reset keeps the username. */
      username?: string;
    }
  | undefined;

function messages(error: unknown): string[] {
  if (error instanceof BackendError) {
    return Array.isArray(error.detail) ? error.detail : [error.detail];
  }
  return ["Something went wrong. Try again."];
}

/** Pages whose content depends on published climate datasets. */
function revalidateClimatePages() {
  revalidatePath("/", "layout");
}

export async function loginAction(_: FormState, formData: FormData): Promise<FormState> {
  const username = String(formData.get("username") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  if (!username || !password) return { error: "Enter your username and password.", username };

  let token: TokenResponse;
  try {
    token = await backendFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  } catch (error) {
    return { error: messages(error)[0], username };
  }
  await setSession(token);
  redirect(token.must_change_password ? "/admin/change-password" : "/admin/dashboard");
}

export async function logoutAction() {
  await clearSession();
  redirect("/admin/login");
}

export async function changePasswordAction(_: FormState, formData: FormData): Promise<FormState> {
  const token = await getSessionToken();
  if (!token) redirect("/admin/login");

  const current = String(formData.get("current_password") ?? "");
  const next = String(formData.get("new_password") ?? "");
  const confirm = String(formData.get("confirm_password") ?? "");
  if (!current || !next) return { error: "Fill in all fields." };
  if (next !== confirm) return { error: "The new passwords do not match." };

  let fresh: TokenResponse;
  try {
    fresh = await backendFetch<TokenResponse>("/auth/change-password", {
      method: "POST",
      token,
      body: JSON.stringify({ current_password: current, new_password: next }),
    });
  } catch (error) {
    if (error instanceof BackendError && error.status === 401) redirect("/admin/login");
    const list = messages(error);
    return list.length > 1
      ? { error: "Choose a stronger password:", errors: list }
      : { error: list[0] };
  }
  await setSession(fresh);
  redirect("/admin/dashboard?password=changed");
}

export type UploadState = { dataset?: AdminDataset; error?: string } | undefined;

export async function uploadClimateDatasetAction(
  _: UploadState,
  formData: FormData,
): Promise<UploadState> {
  const { token } = await requireAdmin();
  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0)
    return { error: "Choose a .json file to upload." };

  const body = new FormData();
  body.set("theme", String(formData.get("theme") ?? ""));
  body.set("publish", formData.get("publish") === "on" ? "true" : "false");
  const description = String(formData.get("description") ?? "").trim();
  if (description) body.set("description", description);
  body.set("file", file, file.name);

  try {
    const dataset = await backendFetch<AdminDataset>("/admin/datasets/climate", {
      method: "POST",
      token,
      body,
    });
    if (dataset.status === "PUBLISHED") revalidateClimatePages();
    revalidatePath("/admin", "layout");
    return { dataset };
  } catch (error) {
    return { error: messages(error).join(" ") };
  }
}

async function datasetAction(id: string, action: "publish" | "unpublish") {
  const { token } = await requireAdmin();
  try {
    await backendFetch<AdminDataset>(`/admin/datasets/${encodeURIComponent(id)}/${action}`, {
      method: "POST",
      token,
    });
  } catch (error) {
    redirect(`/admin/datasets?error=${encodeURIComponent(messages(error)[0])}`);
  }
  revalidateClimatePages();
  redirect(`/admin/datasets?done=${action}`);
}

export async function publishDatasetAction(formData: FormData) {
  await datasetAction(String(formData.get("id")), "publish");
}

export async function unpublishDatasetAction(formData: FormData) {
  await datasetAction(String(formData.get("id")), "unpublish");
}
