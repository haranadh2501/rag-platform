/**
 * Shared API client for the Admin Portal (M8).
 *
 * All requests attach `Authorization: Bearer <token>`. Token is injected by
 * authContext via setAuthToken() — not yet wired (see Phase 1 TODOs below).
 *
 * File uploads must use XMLHttpRequest directly (for progress events) — not
 * this helper. See CLAUDE.md key rules.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ── Token store ───────────────────────────────────────────────────────────────
// Module-level store keeps the token without coupling to browser APIs.
// TODO: authContext.tsx will call setAuthToken(token) on login and
//       setAuthToken(null) on logout once it is built (Phase 1).

let _token: string | null = null;

export function setAuthToken(token: string | null): void {
  _token = token;
}

export function getAuthToken(): string | null {
  return _token;
}

// ── Error class ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ── Core request ──────────────────────────────────────────────────────────────

/**
 * Make an authenticated JSON or FormData request to the FastAPI backend.
 *
 * @param method  HTTP verb
 * @param path    Path starting with `/`, e.g. `/admin/documents`
 * @param body    JSON-serialisable object, FormData, or undefined for no body
 * @returns       Parsed JSON response typed as T, or undefined for 204
 *
 * Throws ApiError on any non-2xx response.
 * For FormData bodies, do NOT set Content-Type — the browser adds the
 * multipart boundary automatically.
 */
export async function apiRequest<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {};

  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let fetchBody: BodyInit | undefined;
  if (body instanceof FormData) {
    fetchBody = body;
    // Content-Type intentionally omitted — browser sets multipart/form-data + boundary.
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    fetchBody = JSON.stringify(body);
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: fetchBody,
  });

  if (res.status === 401) {
    // TODO: clear token via setAuthToken(null) and redirect to
    //       `/login?next=<window.location.pathname>` once AuthGuard and
    //       authContext are wired (Phase 1). For now, throw so callers
    //       surface the error rather than silently swallowing it.
    throw new ApiError(401, 'Unauthorized');
  }

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const err = (await res.json()) as { detail?: unknown };
      if (typeof err?.detail === 'string') {
        message = err.detail;
      }
    } catch {
      // Body unreadable — keep the default message.
    }
    throw new ApiError(res.status, message);
  }

  // 204 No Content (e.g. DELETE /admin/documents/{id}) — no body to parse.
  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  if (!text) {
    return undefined as T;
  }

  return JSON.parse(text) as T;
}
