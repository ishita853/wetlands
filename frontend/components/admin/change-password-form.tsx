"use client";

import { useActionState } from "react";

import { changePasswordAction } from "@/app/admin/actions";
import { FormMessage } from "@/components/admin/form-message";
import { inputClass, labelClass, primaryButton } from "@/components/admin/styles";

export function ChangePasswordForm() {
  const [state, action, pending] = useActionState(changePasswordAction, undefined);

  return (
    <form action={action} className="space-y-4">
      {state?.error ? <FormMessage tone="error" title={state.error} items={state.errors} /> : null}
      <div>
        <label htmlFor="current_password" className={labelClass}>
          Current password
        </label>
        <input
          id="current_password"
          name="current_password"
          type="password"
          autoComplete="current-password"
          required
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="new_password" className={labelClass}>
          New password
        </label>
        <input
          id="new_password"
          name="new_password"
          type="password"
          autoComplete="new-password"
          minLength={12}
          required
          aria-describedby="password-rules"
          className={inputClass}
        />
        <ul
          id="password-rules"
          className="mt-2 list-disc space-y-0.5 pl-5 text-xs text-muted-foreground"
        >
          <li>At least 12 characters</li>
          <li>At least three of: lowercase, uppercase, digits, symbols</li>
          <li>Must not contain the username or reuse the initial password</li>
        </ul>
      </div>
      <div>
        <label htmlFor="confirm_password" className={labelClass}>
          Confirm new password
        </label>
        <input
          id="confirm_password"
          name="confirm_password"
          type="password"
          autoComplete="new-password"
          required
          className={inputClass}
        />
      </div>
      <button type="submit" disabled={pending} className={`${primaryButton} w-full`}>
        {pending ? "Saving…" : "Change password"}
      </button>
    </form>
  );
}
