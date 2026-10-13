"use client";

import { LogIn } from "lucide-react";
import { useActionState } from "react";

import { loginAction } from "@/app/admin/actions";
import { FormMessage } from "@/components/admin/form-message";
import { inputClass, labelClass, primaryButton } from "@/components/admin/styles";

export function LoginForm() {
  const [state, action, pending] = useActionState(loginAction, undefined);

  return (
    <form action={action} className="space-y-4" noValidate>
      {state?.error ? <FormMessage tone="error" title={state.error} /> : null}
      <div>
        <label htmlFor="username" className={labelClass}>
          Username
        </label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          defaultValue={state?.username}
          required
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="password" className={labelClass}>
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className={inputClass}
        />
      </div>
      <button type="submit" disabled={pending} className={`${primaryButton} w-full`}>
        <LogIn className="size-4" aria-hidden="true" />
        {pending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
