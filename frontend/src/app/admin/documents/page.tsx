'use client';

import Link from 'next/link';
import { useEffect, useRef, useState, Fragment, type ChangeEvent, type DragEvent, type FormEvent } from 'react';
import { ingestDocumentUrlApi, listDocumentsApi, uploadDocumentApi } from '../../../lib/documentApi';
import { ApiError } from '../../../lib/apiClient';
import StatusBadge from '../../../components/admin/StatusBadge';
import { pipelineStateFromDocument, INGESTION_STAGES } from '@admin-types';
import type { DocumentOut, PipelineState, IngestionStage, DocumentStatus } from '@admin-types';

// Mock storage quota — replaced by GET /admin/tenants/:id or quota endpoint in a future phase.
const MOCK_QUOTA = { usedMb: 140, totalMb: 500 };

const STAGE_LABELS: Record<IngestionStage, string> = {
  uploaded: 'Uploaded',
  validated: 'Validated',
  parsed_ocr: 'Parsed / OCR',
  chunked: 'Chunked',
  embedded: 'Embedded',
  stored: 'Stored',
};

type FilterOption = DocumentStatus | 'all';

const FILTER_OPTIONS: { value: FilterOption; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
];

type DotState = 'done' | 'running' | 'failed' | 'future';

function getDotState(
  i: number,
  state: PipelineState,
  status: DocumentOut['status'],
): DotState {
  if (state.failedIndex !== null) {
    if (i < state.failedIndex) return 'done';
    if (i === state.failedIndex) return 'failed';
    return 'future';
  }
  if (status === 'completed') return 'done';
  if (status === 'processing') {
    if (i < state.activeIndex) return 'done';
    if (i === state.activeIndex) return 'running';
    return 'future';
  }
  // pending: stage 0 (uploaded) is complete; rest not yet started
  if (i <= state.activeIndex) return 'done';
  return 'future';
}

function DotIcon({ state }: { state: DotState }) {
  switch (state) {
    case 'done':
      return <span className="flex h-3 w-3 rounded-full bg-emerald-500" />;
    case 'running':
      return <span className="h-3 w-3 animate-spin rounded-full border-2 border-blue-200 border-t-blue-600" />;
    case 'failed':
      return (
        <span className="flex h-3 w-3 items-center justify-center rounded-full bg-red-500 text-[7px] font-bold leading-none text-white">
          ✕
        </span>
      );
    case 'future':
      return <span className="h-3 w-3 rounded-full border-2 border-slate-200 bg-white" />;
  }
}

function PipelineStepper({ doc }: { doc: DocumentOut }) {
  const state = pipelineStateFromDocument(doc);
  const failedStage =
    state.failedIndex !== null ? INGESTION_STAGES[state.failedIndex] : undefined;

  return (
    <div className="border-t border-slate-100 bg-slate-50 px-4 py-3">
      {/* Desktop: horizontal stepper */}
      <div className="hidden items-start md:flex">
        {INGESTION_STAGES.map((stage, i) => {
          const dotSt = getDotState(i, state, doc.status);
          return (
            <Fragment key={stage}>
              {i > 0 && (
                <div
                  className={`mt-1.5 h-px flex-1 ${
                    getDotState(i - 1, state, doc.status) === 'done'
                      ? 'bg-emerald-400'
                      : 'bg-slate-200'
                  }`}
                />
              )}
              <div className="flex shrink-0 flex-col items-center">
                <DotIcon state={dotSt} />
                <span
                  className={`mt-1 whitespace-nowrap text-[9px] font-medium ${
                    dotSt === 'failed'
                      ? 'text-red-500'
                      : dotSt === 'done'
                        ? 'text-emerald-600'
                        : dotSt === 'running'
                          ? 'text-blue-500'
                          : 'text-slate-400'
                  }`}
                >
                  {STAGE_LABELS[stage]}
                </span>
              </div>
            </Fragment>
          );
        })}
      </div>

      {/* Mobile: compact vertical stepper — same data, no horizontal overflow */}
      <div className="flex flex-col gap-1.5 md:hidden">
        {INGESTION_STAGES.map((stage, i) => {
          const dotSt = getDotState(i, state, doc.status);
          return (
            <div key={stage} className="flex items-center gap-2">
              <DotIcon state={dotSt} />
              <span
                className={`text-xs font-medium ${
                  dotSt === 'failed'
                    ? 'text-red-500'
                    : dotSt === 'done'
                      ? 'text-emerald-600'
                      : dotSt === 'running'
                        ? 'text-blue-500'
                        : 'text-slate-400'
                }`}
              >
                {STAGE_LABELS[stage]}
              </span>
            </div>
          );
        })}
      </div>

      {failedStage && state.errorMessage && (
        <p className="mt-2 break-words text-xs text-red-500">
          Failed at: {STAGE_LABELS[failedStage]} — {state.errorMessage}
        </p>
      )}
      {doc.status === 'completed' && state.chunkCount !== null && state.indexedAt && (
        <p className="mt-2 text-xs text-emerald-600">
          {state.chunkCount} chunks · indexed {formatDate(state.indexedAt)}
        </p>
      )}
    </div>
  );
}

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

type UploadTab = 'file' | 'url';

function isValidUrl(value: string): boolean {
  try {
    const u = new URL(value);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

interface UrlSubmitError {
  message: string;
  detail: string;
}

function classifyUrlError(err: unknown): UrlSubmitError {
  const technical = `Technical detail: ${err instanceof Error ? err.message : String(err)}`;
  if (err instanceof ApiError) {
    if (err.status === 400) return { message: 'Please check the URL and title.', detail: technical };
    if (err.status === 401) return { message: 'Your session expired. Please sign in again.', detail: technical };
    if (err.status === 403) return { message: 'You do not have permission to add documents.', detail: technical };
    if (err.status === 404) return { message: 'The Add by URL endpoint is not available yet.', detail: technical };
    if (err.status === 409) return { message: 'This document may already exist.', detail: technical };
    if (err.status === 422) return { message: 'The submitted URL or title is invalid.', detail: technical };
    if (err.status === 429) return { message: 'Too many requests. Please try again in a minute.', detail: technical };
    if (err.status >= 500) return { message: 'The document service is having trouble. Please try again later.', detail: technical };
    return { message: 'The document service did not respond. Please try again in a moment.', detail: technical };
  }
  return {
    message: 'Could not reach the document service. Check backend availability or CORS.',
    detail: technical,
  };
}

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024; // 25 MB — matches backend MAX_UPLOAD_BYTES
const ALLOWED_FILE_EXTENSIONS = ['.pdf', '.docx', '.txt'];

function isAllowedFile(file: File): boolean {
  const lower = file.name.toLowerCase();
  return ALLOWED_FILE_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function classifyFileUploadError(err: unknown): UrlSubmitError {
  const technical = `Technical detail: ${err instanceof Error ? err.message : String(err)}`;
  if (err instanceof ApiError) {
    if (err.status === 400) return { message: 'Please check the selected file.', detail: technical };
    if (err.status === 401) return { message: 'Your session expired. Please sign in again.', detail: technical };
    if (err.status === 403) return { message: 'You do not have permission to upload documents.', detail: technical };
    if (err.status === 413) return { message: 'Upload limit exceeded. Please choose a smaller file or free up storage.', detail: technical };
    if (err.status === 415) return { message: 'Unsupported file type. Upload PDF, DOCX, or TXT.', detail: technical };
    if (err.status === 422) return { message: 'The uploaded file is invalid.', detail: technical };
    if (err.status === 429) return { message: 'Upload limit reached. Please try again later.', detail: technical };
    if (err.status >= 500) return { message: 'The document service is having trouble. Please try again later.', detail: technical };
    return { message: 'The document service did not respond. Please try again in a moment.', detail: technical };
  }
  return {
    message: 'Could not reach the document service. Check backend availability or CORS.',
    detail: technical,
  };
}

interface ListFetchError {
  message: string;
  detail: string;
}

function classifyListError(err: unknown): ListFetchError {
  const technical = `Technical detail: ${err instanceof Error ? err.message : String(err)}`;
  if (err instanceof ApiError) {
    if (err.status === 401) return { message: 'Your session expired. Please sign in again.', detail: technical };
    if (err.status === 403) return { message: 'You do not have permission to view documents.', detail: technical };
    if (err.status === 404) return { message: 'The documents endpoint is not available yet.', detail: technical };
    if (err.status === 429) return { message: 'Too many requests. Please try again in a minute.', detail: technical };
    if (err.status >= 500) return { message: 'The document service is having trouble. Please try again later.', detail: technical };
    return { message: 'The document service did not respond. Please try again in a moment.', detail: technical };
  }
  return {
    message: 'Could not reach the document service. Check backend availability or CORS.',
    detail: technical,
  };
}

interface UploadSourcePanelProps {
  onAccepted: (doc: DocumentOut) => void;
}

function UploadSourcePanel({ onAccepted }: UploadSourcePanelProps) {
  const [activeTab, setActiveTab] = useState<UploadTab>('file');
  const [urlInput, setUrlInput] = useState('');
  const [titleInput, setTitleInput] = useState('');
  const [urlLoading, setUrlLoading] = useState(false);
  const [urlSuccess, setUrlSuccess] = useState(false);
  const [urlError, setUrlError] = useState<UrlSubmitError | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileTitleInput, setFileTitleInput] = useState('');
  const [fileValidationError, setFileValidationError] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileProgress, setFileProgress] = useState(0);
  const [fileSuccess, setFileSuccess] = useState(false);
  const [fileError, setFileError] = useState<UrlSubmitError | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const urlValid = isValidUrl(urlInput);
  const titleValid = titleInput.trim().length > 0;
  const canSubmitUrl = urlValid && titleValid && !urlLoading;

  async function handleUrlSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmitUrl) return;
    setUrlError(null);
    setUrlSuccess(false);
    setUrlLoading(true);
    const trimmedUrl = urlInput.trim();
    const trimmedTitle = titleInput.trim();
    try {
      const doc = await ingestDocumentUrlApi({
        url: trimmedUrl,
        title: trimmedTitle,
      });
      setUrlInput('');
      setTitleInput('');
      setUrlSuccess(true);
      onAccepted(doc);
    } catch (err) {
      setUrlError(classifyUrlError(err));
    } finally {
      setUrlLoading(false);
    }
  }

  function handleFileSelected(file: File): void {
    setFileSuccess(false);
    setFileError(null);
    if (!isAllowedFile(file)) {
      setFileValidationError('Unsupported file type. Upload PDF, DOCX, or TXT.');
      setSelectedFile(null);
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setFileValidationError('Upload limit exceeded. Please choose a smaller file or free up storage.');
      setSelectedFile(null);
      return;
    }
    setFileValidationError(null);
    setSelectedFile(file);
  }

  function handleFileInputChange(e: ChangeEvent<HTMLInputElement>): void {
    const file = e.target.files?.[0];
    if (file) handleFileSelected(file);
    e.target.value = '';
  }

  function handleDrop(e: DragEvent<HTMLDivElement>): void {
    e.preventDefault();
    setIsDragOver(false);
    if (fileLoading) return;
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileSelected(file);
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>): void {
    e.preventDefault();
    if (!fileLoading) setIsDragOver(true);
  }

  function handleDragLeave(): void {
    setIsDragOver(false);
  }

  async function handleFileSubmit(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    if (!selectedFile || fileLoading) return;
    setFileError(null);
    setFileSuccess(false);
    setFileLoading(true);
    setFileProgress(0);
    try {
      const doc = await uploadDocumentApi({
        file: selectedFile,
        title: fileTitleInput.trim() || undefined,
        onProgress: setFileProgress,
      });
      setSelectedFile(null);
      setFileTitleInput('');
      setFileSuccess(true);
      onAccepted(doc);
    } catch (err) {
      setFileError(classifyFileUploadError(err));
    } finally {
      setFileLoading(false);
      setFileProgress(0);
    }
  }

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
        {/* Upload File panel — calls POST /admin/documents/upload via documentApi (XHR) */}
        {activeTab === 'file' && (
          <form onSubmit={handleFileSubmit} noValidate className="space-y-3">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`rounded-lg border-2 border-dashed p-6 text-center transition-colors sm:p-8 ${
                isDragOver ? 'border-indigo-400 bg-indigo-50' : 'border-slate-300 bg-slate-50'
              }`}
            >
              <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-sm">
                <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m6.75 12-3-3m0 0-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-slate-700">
                {selectedFile ? selectedFile.name : 'Drag & drop PDF, DOCX, or TXT'}
              </p>
              <p className="mt-1 text-xs text-slate-400">or</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
                className="hidden"
                disabled={fileLoading}
                onChange={handleFileInputChange}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={fileLoading}
                className="mt-2 w-full rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto"
              >
                Browse files
              </button>
              <p className="mt-3 text-xs text-slate-400">Max 25 MB · PDF, DOCX, or TXT · 20 uploads/hour</p>
            </div>

            {fileValidationError && (
              <p className="text-xs text-red-500">{fileValidationError}</p>
            )}

            {selectedFile && (
              <div>
                <label
                  htmlFor="file-title-input"
                  className="mb-1 block text-xs font-medium text-slate-700"
                >
                  Title <span className="font-normal text-slate-400">(optional)</span>
                </label>
                <input
                  id="file-title-input"
                  type="text"
                  placeholder="Defaults to the file name"
                  value={fileTitleInput}
                  onChange={(e) => setFileTitleInput(e.target.value)}
                  disabled={fileLoading}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
                />
              </div>
            )}

            {fileLoading && (
              <div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                  <div
                    className="h-2 rounded-full bg-indigo-600 transition-all"
                    style={{ width: `${fileProgress}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-400">Uploading… {fileProgress}%</p>
              </div>
            )}

            {fileError && (
              <div role="alert" aria-live="assertive" className="rounded-md border border-red-200 bg-red-50 p-3">
                <p className="text-sm font-medium text-red-800">Could not upload file</p>
                <p className="mt-1 text-xs text-red-700">{fileError.message}</p>
                <p className="mt-1 text-xs text-red-400">{fileError.detail}</p>
              </div>
            )}

            {fileSuccess && (
              <div role="status" aria-live="polite" className="rounded-md border border-emerald-200 bg-emerald-50 p-3">
                <p className="text-sm font-medium text-emerald-800">Upload accepted</p>
                <p className="mt-1 text-xs text-emerald-700">
                  We have started ingesting this file. It may take a few minutes before it
                  appears as searchable knowledge.
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={!selectedFile || fileLoading}
              aria-disabled={!selectedFile || fileLoading}
              className="flex w-full items-center justify-center gap-1.5 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto sm:justify-start"
            >
              {fileLoading && (
                <span
                  className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"
                  aria-hidden="true"
                />
              )}
              {fileLoading ? 'Uploading…' : 'Upload file'}
            </button>

            <p className="text-xs text-slate-400">
              Sends{' '}
              <code className="rounded bg-slate-100 px-0.5">POST /admin/documents/upload</code>
              {' '}— backend validates the JWT, file type/size, tenant quota and rate limit, and
              triggers n8n.
            </p>
          </form>
        )}

        {/* Add by URL panel — calls POST /admin/documents/url via documentApi */}
        {activeTab === 'url' && (
          <form onSubmit={handleUrlSubmit} noValidate className="space-y-3">
            <div>
              <label
                htmlFor="url-source-input"
                className="mb-1 block text-xs font-medium text-slate-700"
              >
                URL <span className="text-red-500" aria-hidden="true">*</span>
              </label>
              <input
                id="url-source-input"
                type="url"
                placeholder="https://example.com/document"
                value={urlInput}
                onChange={(e) => { setUrlInput(e.target.value); setUrlSuccess(false); }}
                disabled={urlLoading}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
              />
              {urlInput.length > 0 && !urlValid && (
                <p className="mt-1 text-xs text-red-500">
                  Must be a valid http:// or https:// URL.
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="url-title-input"
                className="mb-1 block text-xs font-medium text-slate-700"
              >
                Title <span className="text-red-500" aria-hidden="true">*</span>
              </label>
              <input
                id="url-title-input"
                type="text"
                placeholder="e.g. API Reference"
                value={titleInput}
                onChange={(e) => setTitleInput(e.target.value)}
                disabled={urlLoading}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
              />
              {titleInput.length === 0 && (
                <p className="mt-1 text-xs text-slate-400">Required.</p>
              )}
            </div>

            {urlError && (
              <div role="alert" aria-live="assertive" className="rounded-md border border-red-200 bg-red-50 p-3">
                <p className="text-sm font-medium text-red-800">Could not submit URL</p>
                <p className="mt-1 text-xs text-red-700">{urlError.message}</p>
                <p className="mt-1 text-xs text-red-400">{urlError.detail}</p>
              </div>
            )}

            {urlSuccess && (
              <div role="status" aria-live="polite" className="rounded-md border border-emerald-200 bg-emerald-50 p-3">
                <p className="text-sm font-medium text-emerald-800">Request accepted</p>
                <p className="mt-1 text-xs text-emerald-700">
                  We have started ingesting this URL. It may take a few minutes before it appears
                  as searchable knowledge.
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={!canSubmitUrl}
              aria-disabled={!canSubmitUrl}
              className="flex w-full items-center justify-center gap-1.5 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto sm:justify-start"
            >
              {urlLoading && (
                <span
                  className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"
                  aria-hidden="true"
                />
              )}
              {urlLoading ? 'Submitting…' : 'Add source'}
            </button>

            <p className="text-xs text-slate-400">
              Sends{' '}
              <code className="rounded bg-slate-100 px-0.5">POST /admin/documents/url</code>
              {' '}— backend validates the JWT, enforces tenant isolation, and triggers n8n.
            </p>
          </form>
        )}
      </div>
    </div>
  );
}

const PER_PAGE_OPTIONS = [10, 20, 50];

export default function DocumentsPage() {
  const [activeFilter, setActiveFilter] = useState<FilterOption>('all');
  const [optimisticDocs, setOptimisticDocs] = useState<DocumentOut[]>([]);
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<ListFetchError | null>(null);
  // Bumped after a successful "Add by URL" submit to force a refetch of page 1
  // even when `page` is already 1 (and therefore wouldn't otherwise change).
  const [refetchToken, setRefetchToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setFetchError(null);
    listDocumentsApi({ page, perPage })
      .then((result) => {
        if (cancelled) return;
        setDocuments(result.documents);
        setTotal(result.total);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setFetchError(classifyListError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [page, perPage, refetchToken]);

  // Optimistic rows from "Add by URL" disappear once GET /admin/documents
  // returns the same id as a persisted row, avoiding a duplicate entry.
  const persistedIds = new Set(documents.map((d) => d.id));
  const visibleOptimisticDocs = optimisticDocs.filter((d) => !persistedIds.has(d.id));
  const optimisticIds = new Set(visibleOptimisticDocs.map((d) => d.id));
  const allDocs = [...visibleOptimisticDocs, ...documents];
  const filteredDocs =
    activeFilter === 'all'
      ? allDocs
      : allDocs.filter((d) => d.status === activeFilter);

  const totalPages = Math.max(1, Math.ceil(total / perPage));
  const rangeStart = total === 0 ? 0 : (page - 1) * perPage + 1;
  const rangeEnd = Math.min(page * perPage, total);

  function handleAccepted(doc: DocumentOut): void {
    setOptimisticDocs((prev) => [doc, ...prev]);
    // Switch to All if the current filter would hide the newly inserted row.
    if (activeFilter !== 'all' && activeFilter !== doc.status) {
      setActiveFilter('all');
    }
    // Prefer a real refetch of page 1 (where a newly created document appears)
    // over the local optimistic row now that GET /admin/documents is wired.
    // The optimistic row above covers the brief gap until this refetch resolves
    // and is then deduped once the persisted row with the same id is returned.
    setPage(1);
    setRefetchToken((t) => t + 1);
    // If backend returned pending, advance locally to processing after 1500 ms for
    // demo feedback in case the refetch above is still in flight.
    if (doc.status === 'pending') {
      setTimeout(() => {
        setOptimisticDocs((prev) =>
          prev.map((d): DocumentOut => (d.id === doc.id ? { ...d, status: 'processing' } : d)),
        );
      }, 1500);
    }
  }

  function handlePreviousPage(): void {
    setPage((p) => Math.max(1, p - 1));
  }

  function handleNextPage(): void {
    setPage((p) => p + 1);
  }

  function handlePerPageChange(e: ChangeEvent<HTMLSelectElement>): void {
    setPerPage(Number(e.target.value));
    setPage(1);
  }

  return (
    <main className="p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Documents</h1>
        <p className="mt-1 text-sm text-slate-500">
          Manage your tenant knowledge base documents.
        </p>
      </div>

      <UploadSourcePanel onAccepted={handleAccepted} />

      {/* Storage quota card */}
      <StorageQuotaCard usedMb={MOCK_QUOTA.usedMb} totalMb={MOCK_QUOTA.totalMb} />

      {/* Filter bar */}
      <div className="mb-4 flex flex-wrap gap-1">
        {FILTER_OPTIONS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => setActiveFilter(value)}
            className={
              activeFilter === value
                ? 'rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white'
                : 'rounded-md px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100'
            }
          >
            {label}
          </button>
        ))}
      </div>

      {fetchError && (
        <div
          role="alert"
          aria-live="assertive"
          className="mb-4 rounded-md border border-red-200 bg-red-50 p-3"
        >
          <p className="text-sm font-medium text-red-800">Could not load documents</p>
          <p className="mt-1 text-xs text-red-700">{fetchError.message}</p>
          <p className="mt-1 text-xs text-red-400">{fetchError.detail}</p>
        </div>
      )}

      {/* Document table — desktop/tablet (md+) only; mobile uses stacked cards below */}
      <div className="hidden overflow-hidden rounded-lg border border-slate-200 bg-white md:block">
        <div className="overflow-x-auto">
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
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={`doc-skeleton-${i}`} className="animate-pulse">
                    <td colSpan={6} className="px-4 py-3">
                      <div className="h-4 w-full rounded bg-slate-100" />
                    </td>
                  </tr>
                ))
              ) : filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-400">
                    No {activeFilter === 'all' ? '' : `${activeFilter} `}documents.
                  </td>
                </tr>
              ) : filteredDocs.map((doc) => (
                <Fragment key={doc.id}>
                  <tr className="hover:bg-slate-50">
                    <td className="max-w-xs truncate px-4 py-3 text-sm font-medium text-slate-800">
                      {doc.title}
                    </td>
                    <td className="px-4 py-3 text-xs uppercase tracking-wide text-slate-500">
                      {doc.source_type}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={doc.status} errorMessage={doc.error_message} />
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {doc.status === 'completed' ? doc.chunk_count : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {doc.status === 'completed' || doc.status === 'failed' ? (
                        <Link
                          href={`/admin/documents/${doc.id}`}
                          className="text-indigo-600 hover:text-indigo-800"
                        >
                          Detail
                        </Link>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td colSpan={6} className="p-0">
                      <PipelineStepper doc={doc} />
                      {optimisticIds.has(doc.id) && (doc.status === 'pending' || doc.status === 'processing') && (
                        <p className="border-t border-slate-100 bg-slate-50 px-4 pb-2.5 pt-0 text-xs text-slate-400">
                          Status preview — live updates require{' '}
                          <code className="rounded bg-slate-100 px-0.5">GET /admin/documents</code>{' '}
                          polling.
                        </p>
                      )}
                    </td>
                  </tr>
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Document cards — mobile (< md) only; same data as the table above */}
      <div className="space-y-3 md:hidden">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div
              key={`doc-skeleton-card-${i}`}
              className="animate-pulse rounded-lg border border-slate-200 bg-white p-4"
            >
              <div className="h-4 w-2/3 rounded bg-slate-100" />
              <div className="mt-2 h-3 w-1/3 rounded bg-slate-100" />
            </div>
          ))
        ) : filteredDocs.length === 0 ? (
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-10 text-center text-sm text-slate-400">
            No {activeFilter === 'all' ? '' : `${activeFilter} `}documents.
          </div>
        ) : filteredDocs.map((doc) => (
          <div key={doc.id} className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <div className="p-4">
              <div className="flex items-start justify-between gap-3">
                <p className="break-words text-sm font-medium text-slate-800">{doc.title}</p>
                <span className="shrink-0 text-xs uppercase tracking-wide text-slate-500">
                  {doc.source_type}
                </span>
              </div>
              <div className="mt-2">
                <StatusBadge status={doc.status} errorMessage={doc.error_message} />
              </div>
              <dl className="mt-3 space-y-1 text-xs text-slate-500">
                <div className="flex items-center justify-between gap-2">
                  <dt>Chunks</dt>
                  <dd className="text-slate-700">
                    {doc.status === 'completed' ? doc.chunk_count : '—'}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <dt>Uploaded</dt>
                  <dd className="text-slate-700">{formatDate(doc.created_at)}</dd>
                </div>
                {doc.source_url && (
                  <div className="flex items-center justify-between gap-2">
                    <dt className="shrink-0">Source</dt>
                    <dd className="min-w-0 flex-1 truncate text-right text-slate-700">
                      {doc.source_url}
                    </dd>
                  </div>
                )}
              </dl>
              <div className="mt-3">
                {doc.status === 'completed' || doc.status === 'failed' ? (
                  <Link
                    href={`/admin/documents/${doc.id}`}
                    className="text-sm text-indigo-600 hover:text-indigo-800"
                  >
                    View detail →
                  </Link>
                ) : (
                  <span className="text-xs text-slate-400">Detail available once processing finishes</span>
                )}
              </div>
            </div>
            <PipelineStepper doc={doc} />
            {optimisticIds.has(doc.id) && (doc.status === 'pending' || doc.status === 'processing') && (
              <p className="border-t border-slate-100 bg-slate-50 px-4 pb-2.5 pt-2 text-xs text-slate-400">
                Status preview — live updates require{' '}
                <code className="rounded bg-slate-100 px-0.5">GET /admin/documents</code> polling.
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Pagination controls */}
      <div className="mt-3 flex flex-col gap-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
        <p>{total === 0 ? 'No documents' : `${rangeStart}-${rangeEnd} of ${total}`}</p>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <label htmlFor="documents-per-page" className="text-xs text-slate-500">
            Rows per page
          </label>
          <select
            id="documents-per-page"
            value={perPage}
            onChange={handlePerPageChange}
            disabled={loading}
            className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
          >
            {PER_PAGE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <span aria-live="polite" className="text-xs text-slate-500">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            onClick={handlePreviousPage}
            disabled={page <= 1 || loading}
            aria-label="Previous page"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={handleNextPage}
            disabled={page * perPage >= total || loading}
            aria-label="Next page"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </main>
  );
}
