import Link from 'next/link';
import type { DocumentOut } from '@admin-types';
import StatusBadge from '../../../../components/admin/StatusBadge';

// Placeholder mock — replaced by GET /admin/documents/{id} in Phase 4.
const MOCK_DETAIL: DocumentOut = {
  id: 'doc-001',
  tenant_id: 'tenant-abc',
  title: 'Onboarding Guide Q1 2026',
  source_type: 'pdf',
  source_url: null,
  status: 'failed',
  chunk_count: 0,
  error_message: 'HTTP 403 fetching source URL.',
  failed_stage: 'validated',
  created_at: '2026-05-20T09:15:00Z',
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export default function DocumentDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const doc = MOCK_DETAIL;

  return (
    <main className="p-6">
      <Link
        href="/admin/documents"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700"
      >
        ← Back to Documents
      </Link>

      <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-700">
        Placeholder — data will be fetched from{' '}
        <code className="rounded bg-amber-100 px-1">
          GET /admin/documents/{params.id}
        </code>{' '}
        in Phase 4. Showing mock document below.
      </div>

      <div className="mt-6">
        <h1 className="text-xl font-semibold text-slate-900">{doc.title}</h1>
      </div>

      {doc.status === 'failed' && doc.error_message && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <p className="font-medium">Ingestion failed</p>
          <p className="mt-1 text-red-600">{doc.error_message}</p>
        </div>
      )}

      <dl className="mt-6 divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white text-sm">
        <div className="flex gap-6 px-4 py-3">
          <dt className="w-24 shrink-0 font-medium text-slate-500">Type</dt>
          <dd className="uppercase tracking-wide text-slate-700">{doc.source_type}</dd>
        </div>
        <div className="flex gap-6 px-4 py-3">
          <dt className="w-24 shrink-0 font-medium text-slate-500">Status</dt>
          <dd><StatusBadge status={doc.status} /></dd>
        </div>
        <div className="flex gap-6 px-4 py-3">
          <dt className="w-24 shrink-0 font-medium text-slate-500">Chunks</dt>
          <dd className="text-slate-700">
            {doc.status === 'completed' ? doc.chunk_count : '—'}
          </dd>
        </div>
        <div className="flex gap-6 px-4 py-3">
          <dt className="w-24 shrink-0 font-medium text-slate-500">Uploaded</dt>
          <dd className="text-slate-700">{formatDate(doc.created_at)}</dd>
        </div>
        <div className="flex gap-6 px-4 py-3">
          <dt className="w-24 shrink-0 font-medium text-slate-500">Source</dt>
          <dd className="break-all text-slate-700">{doc.source_url ?? '—'}</dd>
        </div>
      </dl>

      <div className="mt-6 flex items-center justify-end gap-3">
        <p className="text-xs text-slate-400">
          Delete requires ConfirmDialog — wired in Phase 4.
        </p>
        <button
          type="button"
          disabled
          className="cursor-not-allowed rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white opacity-40"
        >
          Delete Document
        </button>
      </div>
    </main>
  );
}
