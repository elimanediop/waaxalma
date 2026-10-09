export type User = { user_id: string; email: string };
export type AuthState = { user: User; csrf_token: string };

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    credentials: "same-origin",
    cache: "no-store",
    ...init,
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      typeof error?.detail === "string" ? error.detail : `Request failed (${response.status})`,
    );
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}

export function isAuthenticationError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

/**
 * Authenticated state-changing requests must carry the CSRF token obtained
 * from /api/auth/me or /api/auth/login. Never persist it in localStorage.
 */
export function authenticatedMutation<T>(
  path: string,
  session: AuthState,
  init: RequestInit & { method: "POST" | "PUT" | "PATCH" | "DELETE" },
): Promise<T> {
  if (!session.csrf_token) {
    throw new Error("Missing CSRF token for authenticated mutation");
  }
  return api<T>(path, {
    ...init,
    headers: {
      ...init.headers,
      "X-CSRF-Token": session.csrf_token,
    },
  });
}
