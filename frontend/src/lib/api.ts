/**
 * Thin API client for the Sankalp AI FastAPI backend.
 *
 * - JWT is held in memory only (module scope). It survives client-side
 *   navigation but is lost on a hard reload — by design.
 * - Every request auto-attaches `Authorization: Bearer <token>` when a token
 *   is present.
 * - On 401 for an *authenticated* request (a token was attached), the client
 *   clears the token and bounces the browser to "/" (the login screen). A
 *   401 on the login call itself (no token yet) simply throws the error.
 */
import type { AuthUser } from "./types";

let token: string | null = null;
let user: AuthUser | null = null;

export function setToken(t: string | null): void {
  token = t;
}
export function getToken(): string | null {
  return token;
}
export function clearToken(): void {
  token = null;
}

export function setUser(u: AuthUser | null): void {
  user = u;
}
export function getUser(): AuthUser | null {
  return user;
}
export function clearUser(): void {
  user = null;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function buildUrl(path: string, params?: Record<string, unknown>): string {
  let url = path;
  if (params) {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") q.append(k, String(v));
    }
    const qs = q.toString();
    if (qs) url += (path.includes("?") ? "&" : "?") + qs;
  }
  return url;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  params?: Record<string, unknown>
): Promise<T> {
  const url = buildUrl(path, params);
  const hadToken = !!token;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      "Network error — cannot reach the server. Is the backend running on :8000?",
      0
    );
  }

  if (res.status === 401) {
    if (hadToken) {
      clearToken();
      clearUser();
      if (typeof window !== "undefined") window.location.href = "/";
    }
    let detail = "Invalid credentials";
    try {
      const j = await res.json();
      detail = j.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, 401);
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      detail = j.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function apiGet<T>(
  path: string,
  params?: Record<string, unknown>
): Promise<T> {
  return request<T>("GET", path, undefined, params);
}

export function apiPost<T>(
  path: string,
  body?: unknown
): Promise<T> {
  return request<T>("POST", path, body);
}
