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
