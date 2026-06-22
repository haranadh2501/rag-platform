'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getDocumentApi } from '../../../../lib/documentApi';
import { ApiError } from '../../../../lib/apiClient';
import StatusBadge from '../../../../components/admin/StatusBadge';
import type { DocumentOut } from '@admin-types';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

interface DetailFetchError {
  message: string;
  detail: string;
}

function classifyDetailError(err: unknown): DetailFetchError {
  const technical = `Technical detail: ${err instanceof Error ? err.message : String(err)}`;
  if (err instanceof ApiError) {
    if (err.status === 400) return { message: 'The document id is invalid.', detail: technical };
    if (err.status === 401) return { message: 'Your session expired. Please sign in again.', detail: technical };
    if (err.status === 403) return { message: 'You do not have permission to view this document.', detail: technical };
    if (err.status === 404) return { message: 'This document was not found.', detail: technical };
    if (err.status === 429) return { message: 'Too many requests. Please try again in a minute.', detail: technical };
    if (err.status >= 500) return { message: 'The document service is having trouble. Please try again later.', detail: technical };
    return { message: 'The document service did not respond. Please try again in a moment.', detail: technical };
  }
  return {
    message: 'Could not reach the document service. Check backend availability or CORS.',
    detail: technical,
  };
}

export default function DocumentDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const [doc, setDoc] = useState<DocumentOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<DetailFetchError | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setFetchError(null);
    getDocumentApi(params.id)
      .then((result) => {
        if (cancelled) return;
        setDoc(result);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setFetchError(classifyDetailError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  return (
    <main className="p-6">
      <Link
        href="/admin/documents"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700"
      >
        ← Back to Documents
      </Link>

      {loading && (
        <div className="mt-6 animate-pulse space-y-3">
          <div className="h-6 w-1/3 rounded bg-slate-100" />
          <div className="h-40 w-full rounded-lg bg-slate-100" />
        </div>
      )}

      {!loading && fetchError && (
        <div
          role="alert"
          aria-live="assertive"
          className="mt-6 rounded-md border border-red-200 bg-red-50 p-3"
        >
          <p className="text-sm font-medium text-red-800">Could not load document</p>
          <p className="mt-1 text-xs text-red-700">{fetchError.message}</p>
          <p className="mt-1 text-xs text-red-400">{fetchError.detail}</p>
        </div>
      )}

      {!loading && !fetchError && doc && (
        <>
          <div className="mt-6">
            <h1 className="text-xl font-semibold text-slate-900">{doc.title}</h1>
          </div>

          {(doc.status === 'pending' || doc.status === 'processing') && (
            <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700">
              Ingestion is still in progress. This document is not yet searchable.
            </div>
          )}

          {doc.status === 'failed' && doc.error_message && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <p className="font-medium">Ingestion failed</p>
              <p className="mt-1 text-red-600">{doc.error_message}</p>
            </div>
          )}

          <dl className="mt-6 divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white text-sm">
            <div className="flex gap-6 px-4 py-3">
              <dt className="w-28 shrink-0 font-medium text-slate-500">Type</dt>
              <dd className="uppercase tracking-wide text-slate-700">{doc.source_type}</dd>
            </div>
            <div className="flex gap-6 px-4 py-3">
              <dt className="w-28 shrink-0 font-medium text-slate-500">Status</dt>
              <dd><StatusBadge status={doc.status} /></dd>
            </div>
            <div className="flex gap-6 px-4 py-3">
              <dt className="w-28 shrink-0 font-medium text-slate-500">Chunks</dt>
              <dd className="text-slate-700">
                {doc.status === 'completed' ? doc.chunk_count : '—'}
              </dd>
            </div>
            <div className="flex gap-6 px-4 py-3">
              <dt className="w-28 shrink-0 font-medium text-slate-500">Uploaded</dt>
              <dd className="text-slate-700">{formatDate(doc.created_at)}</dd>
            </div>
            <div className="flex gap-6 px-4 py-3">
              <dt className="w-28 shrink-0 font-medium text-slate-500">Source</dt>
              <dd className="break-all text-slate-700">
                {doc.source_url ? (
                  <a
                    href={doc.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 hover:text-indigo-800"
                  >
                    {doc.source_url}
                  </a>
                ) : (
                  '—'
                )}
              </dd>
            </div>
            <div className="flex gap-6 px-4 py-3">
              <dt className="w-28 shrink-0 font-medium text-slate-500">Document ID</dt>
              <dd className="break-all font-mono text-xs text-slate-500">{doc.id}</dd>
            </div>
            <div className="flex gap-6 px-4 py-3">
              <dt className="w-28 shrink-0 font-medium text-slate-500">Tenant ID</dt>
              <dd className="break-all font-mono text-xs text-slate-500">{doc.tenant_id}</dd>
            </div>
          </dl>

          <div className="mt-6 flex items-center justify-end gap-3">
            <p className="text-xs text-slate-400">
              Delete requires ConfirmDialog — wired in a later phase.
            </p>
            <button
              type="button"
              disabled
              className="cursor-not-allowed rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white opacity-40"
            >
              Delete Document
            </button>
          </div>
        </>
      )}
    </main>
  );
}
