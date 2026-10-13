import { serverEnv } from "@/config/env";

/** Error from the FastAPI backend, with its human-readable `detail`. */
export class BackendError extends Error {
  constructor(
    public status: number,
    public detail: string | string[],
  ) {
    super(Array.isArray(detail) ? detail.join(" ") : detail);
    this.name = "BackendError";
  }
}

/**
 * Server-side call to the backend API (Server Components / Server Actions
 * only — the bearer token never reaches the browser).
 */
export async function backendFetch<T>(
  path: string,
  { token, ...init }: RequestInit & { token?: string } = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${serverEnv.apiUrl}/api/v1${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        ...(init.body && !(init.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new BackendError(503, "The portal's data service is not reachable. Try again shortly.");
  }

  if (!response.ok) {
    let detail: string | string[] = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string" || Array.isArray(body.detail)) {
        // FastAPI validation errors are objects; flatten them to messages.
        detail = Array.isArray(body.detail)
          ? body.detail.map((d: unknown) =>
              typeof d === "string" ? d : ((d as { msg?: string }).msg ?? String(d)),
            )
          : body.detail;
      }
    } catch {
      // Non-JSON error body — keep the generic message.
    }
    throw new BackendError(response.status, detail);
  }
  return (await response.json()) as T;
}
