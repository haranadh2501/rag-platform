/**
 * Onboarding API helpers — public endpoints, no auth token required.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface OnboardingRegisterPayload {
  company_name: string;
  company_slug: string;
  admin_email: string;
  admin_password: string;
  plan: 'free' | 'pro';
}

export interface OnboardingRegisterResponse {
  tenant: {
    id: string;
    name: string;
    slug: string;
    plan: string;
    is_active: boolean;
    created_at: string;
  };
  admin_user: {
    id: string;
    email: string;
    role: string;
    tenant_id: string;
    is_active: boolean;
    created_at: string;
  };
  access_token: string;
}

async function onboardingFetch<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  let fetchBody: BodyInit | undefined;

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    fetchBody = JSON.stringify(body);
  }

  const res = await fetch(`${BASE_URL}${path}`, { method, headers, body: fetchBody });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const err = (await res.json()) as { detail?: unknown };
      if (typeof err?.detail === 'string') message = err.detail;
    } catch { /* keep default */ }
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}

export async function registerTenantApi(payload: OnboardingRegisterPayload): Promise<OnboardingRegisterResponse> {
  return onboardingFetch<OnboardingRegisterResponse>('POST', '/onboarding/register', payload);
}

export async function checkSlugApi(slug: string): Promise<{ available: boolean }> {
  return onboardingFetch<{ available: boolean }>('GET', `/onboarding/check-slug?slug=${encodeURIComponent(slug)}`);
}
