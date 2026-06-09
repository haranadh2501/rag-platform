'use client';

import { useState } from 'react';
import type { DocumentOut } from '@admin-types';

// Mock knowledge sources — replaced by GET /admin/documents in Phase 3.
const MOCK_DOCUMENTS: DocumentOut[] = [
  {
    id: 'doc-001',
    tenant_id: 'tenant-abc',
    title: 'Onboarding Guide Q1 2026',
    source_type: 'pdf',
    source_url: null,
    status: 'completed',
    chunk_count: 42,
    error_message: null,
    created_at: '2026-05-20T09:15:00Z',
  },
  {
    id: 'doc-002',
    tenant_id: 'tenant-abc',
    title: 'Product Roadmap 2026',
    source_type: 'docx',
    source_url: null,
    status: 'processing',
    chunk_count: 0,
    error_message: null,
    created_at: '2026-06-02T08:00:00Z',
  },
  {
    id: 'doc-003',
    tenant_id: 'tenant-abc',
    title: 'https://docs.example.com/api-reference',
    source_type: 'url',
    source_url: 'https://docs.example.com/api-reference',
    status: 'failed',
    chunk_count: 0,
    error_message: 'HTTP 403 fetching source URL.',
    failed_stage: 'validated',
    created_at: '2026-06-01T14:30:00Z',
  },
  {
    id: 'doc-004',
    tenant_id: 'tenant-abc',
    title: 'Support FAQ v2',
    source_type: 'txt',
    source_url: null,
    status: 'pending',
    chunk_count: 0,
    error_message: null,
    created_at: '2026-06-02T10:45:00Z',
  },
];

// Mock storage quota — replaced by GET /admin/tenants/:id or quota endpoint in Phase 3.
const MOCK_QUOTA = { usedMb: 140, totalMb: 500 };

function barColor(pct: number): string {
  if (pct >= 95) return 'bg-red-500';
  if (pct >= 80) return 'bg-amber-500';
  return 'bg-emerald-500';
}

function StorageQuotaCard({ usedMb, totalMb }: { usedMb: number; totalMb: number }) {
  const pct = Math.min(Math.round((usedMb / totalMb) * 100), 100);
  const label =
    totalMb >= 1024
      ? `${(totalMb / 1024).toFixed(0)} GB`
      : `${totalMb} MB`;

  return (
    <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-medium text-slate-700">Storage used</span>
        <span className="text-slate-500">
          {usedMb} MB of {label}
        </span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-2.5 rounded-full transition-all ${barColor(pct)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-slate-400">
        {pct}% used · turns amber at 80%, red at 95%
      </p>
    </div>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function StatusBadge({ doc }: { doc: DocumentOut }) {
  switch (doc.status) {
    case 'pending':
      return <span className="text-sm text-slate-400">● Pending</span>;
    case 'processing':
      return (
        <span className="inline-flex items-center gap-1.5 text-sm text-blue-500">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-blue-200 border-t-blue-600" />
          Processing…
        </span>
      );
    case 'completed':
      return <span className="text-sm text-emerald-500">● Completed</span>;
    case 'failed':
      return (
        <div>
          <span className="text-sm text-red-500">✕ Failed</span>
          {doc.error_message && (
            <p className="mt-0.5 text-xs text-red-400">{doc.error_message}</p>
          )}
        </div>
      );
  }
}

type UploadTab = 'file' | 'url';

function UploadSourcePanel() {
  const [activeTab, setActiveTab] = useState<UploadTab>('file');

  const tabClass = (tab: UploadTab) =>
    activeTab === tab
      ? 'border-b-2 border-indigo-600 px-4 py-2.5 text-sm font-medium text-indigo-600'
      : 'px-4 py-2.5 text-sm font-medium text-slate-400 hover:text-slate-600';

  return (
    <div className="mb-6 overflow-hidden rounded-lg border border-slate-200 bg-white">
      {/* Tab bar */}
      <div className="flex border-b border-slate-200">
        <button type="button" onClick={() => setActiveTab('file')} className={tabClass('file')}>
          Upload File
        </button>
        <button type="button" onClick={() => setActiveTab('url')} className={tabClass('url')}>
          Add by URL
        </button>
      </div>

      <div className="p-6">
        {/* Upload File panel */}
        {activeTab === 'file' && (
          <div className="rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center">
            <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-sm">
              <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m6.75 12-3-3m0 0-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-700">
              Drag &amp; drop PDF, DOCX, or TXT
            </p>
            <p className="mt-1 text-xs text-slate-400">or</p>
            <button
              type="button"
              disabled
              className="mt-2 cursor-not-allowed rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white opacity-40"
            >
              Browse files
            </button>
            <p className="mt-3 text-xs text-slate-400">Max 25 MB · 20 uploads/hour</p>
          </div>
        )}

        {/* Add by URL panel */}
        {activeTab === 'url' && (
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">
                URL
              </label>
              <input
                type="url"
                placeholder="https://example.com/document"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">
                Title <span className="font-normal text-slate-400">(optional)</span>
              </label>
              <input
                type="text"
                placeholder="e.g. API Reference"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <button
              type="button"
              disabled
              className="cursor-not-allowed rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white opacity-40"
            >
              Add source
            </button>
          </div>
        )}

        {/* MOCK_N8N notice */}
        <p className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
          <span className="font-medium">MOCK_N8N=true</span> — uploads are disabled until n8n workflows are connected.
        </p>
      </div>
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <main className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Documents</h1>
        <p className="mt-1 text-sm text-slate-500">
          Manage your tenant knowledge base documents.
        </p>
      </div>

      <UploadSourcePanel />

      {/* Storage quota card */}
      <StorageQuotaCard usedMb={MOCK_QUOTA.usedMb} totalMb={MOCK_QUOTA.totalMb} />

      {/* Document table */}
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {['Title', 'Type', 'Status', 'Chunks', 'Uploaded', 'Actions'].map(
                (col) => (
                  <th
                    key={col}
                    className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-slate-500"
                  >
                    {col}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {MOCK_DOCUMENTS.map((doc) => (
              <tr key={doc.id} className="hover:bg-slate-50">
                <td className="max-w-xs truncate px-4 py-3 text-sm font-medium text-slate-800">
                  {doc.title}
                </td>
                <td className="px-4 py-3 text-xs uppercase tracking-wide text-slate-500">
                  {doc.source_type}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge doc={doc} />
                </td>
                <td className="px-4 py-3 text-sm text-slate-600">
                  {doc.status === 'completed' ? doc.chunk_count : '—'}
                </td>
                <td className="px-4 py-3 text-sm text-slate-500">
                  {formatDate(doc.created_at)}
                </td>
                <td className="px-4 py-3 text-sm text-slate-400">—</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
