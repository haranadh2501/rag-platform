/**
 * n8n URL ingestion helper — DEMO / DEV MODE ONLY.
 *
 * Architecture note:
 * This module posts the ingest payload directly from the browser to the n8n
 * webhook URL. That is intentional for demo and local-dev environments only.
 *
 * In production the frontend should call POST /admin/documents/url on the
 * FastAPI backend; the backend then triggers the n8n webhook server-side so
 * the webhook URL is never exposed in the browser bundle.
 *
 * Demo shortcuts used here:
 * - document_id is generated client-side (crypto.randomUUID()). In production
 *   the backend creates and owns the document record.
 * - tenant_id is read from NEXT_PUBLIC_DEMO_TENANT_ID until GET /auth/me is
 *   wired to authContext and the real tenant is available from the JWT.
 * - Document persistence and list refresh depend on n8n/backend writing to
 *   the database. The document table remains mock until GET /admin/documents
 *   is wired in Phase 3.
 * - Slack onboarding lookup by email is backend-owned; no frontend action.
 */

export interface N8nUrlIngestPayload {
  document_id: string;
  tenant_id: string;
  source_type: 'url';
  source_url: string;
  title: string;
}

/**
 * POST a URL ingest payload to the n8n webhook.
 *
 * Reads NEXT_PUBLIC_N8N_INGEST_WEBHOOK_URL and NEXT_PUBLIC_DEMO_TENANT_ID
 * (Next.js inlines NEXT_PUBLIC_* vars at build time from .env.local).
 *
 * Throws Error on missing config or non-2xx webhook response.
 */
export async function ingestUrlViaN8n(
  sourceUrl: string,
  title: string,
): Promise<void> {
  const webhookUrl = process.env.NEXT_PUBLIC_N8N_INGEST_WEBHOOK_URL;
  const tenantId = process.env.NEXT_PUBLIC_DEMO_TENANT_ID;

  if (!webhookUrl) {
    throw new Error('NEXT_PUBLIC_N8N_INGEST_WEBHOOK_URL is not configured.');
  }
  if (!tenantId) {
    throw new Error('NEXT_PUBLIC_DEMO_TENANT_ID is not configured.');
  }

  const payload: N8nUrlIngestPayload = {
    document_id: crypto.randomUUID(),
    tenant_id: tenantId,
    source_type: 'url',
    source_url: sourceUrl,
    title: title || urlHostname(sourceUrl),
  };

  const res = await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.text();
      if (body) detail = body;
    } catch {
      // ignore — keep default detail
    }
    throw new Error(`Webhook error: ${detail}`);
  }
}

function urlHostname(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}
