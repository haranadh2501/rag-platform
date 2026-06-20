/**
 * Auth API helpers for the Admin Portal (M8).
 * Source of truth: Auth.json (Postman collection, IISc RAG — Auth M2) + specs/openapi.yaml.
 * Both agree: POST /auth/login with { email, password } returns { access_token, token_type, user }.
 *
 * Note: /auth/login is rate-limited to 5 attempts/min per IP (per Auth.json description).
 */

import { apiRequest } from './apiClient';
import type { UserOut } from '@admin-types';

/** POST /auth/login 200 response — consistent between Auth.json and openapi.yaml. */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

/**
 * POST /auth/login
 *
 * Throws ApiError(401) for invalid credentials (same error for wrong email or wrong password).
 * Throws ApiError(N) for any other non-2xx backend response.
 * Token storage is handled by authContext.login() — not the caller.
 */
export async function loginApi(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('POST', '/auth/login', { email, password });
}

/**
 * POST /auth/logout — blacklists the current JWT in Redis server-side.
 *
 * The Bearer token is attached automatically by apiRequest() from the in-memory
 * store (populated by authContext.login()). No request body required.
 * Returns { message: string } on success; empty body on some implementations —
 * both handled gracefully (apiRequest returns undefined for empty bodies).
 *
 * IMPORTANT: callers must clear local auth state via authContext.logout() and
 * redirect to /login regardless of whether this call succeeds or fails.
 * A network error or expired-token 401 must not leave the user stuck.
 */
export async function logoutApi(): Promise<void> {
  await apiRequest<{ message?: string }>('POST', '/auth/logout');
}
