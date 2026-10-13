export const env = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
};

/**
 * Server-side base URL of the FastAPI backend. Inside Docker this is the
 * service name (http://backend:8000), which the browser cannot reach, so it
 * is kept separate from the public URL. Never import in client components.
 */
export const serverEnv = {
  apiUrl: process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
};
