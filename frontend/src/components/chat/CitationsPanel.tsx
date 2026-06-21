'use client';

import { useState } from 'react';
import type { SourceChunk } from '../../../chat/types/chat';

interface CitationsPanelProps {
  sources: SourceChunk[];
}

export default function CitationsPanel({ sources }: CitationsPanelProps) {
  const [open, setOpen] = useState(false);
  const safeSources = sources ?? [];

  if (safeSources.length === 0) {
    return <p className="px-1 text-xs text-slate-400">No citations available</p>;
  }

  return (
    <div className="mt-2 overflow-hidden rounded-lg border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
      >
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true">📄</span>
          {safeSources.length} {safeSources.length === 1 ? 'source' : 'sources'}
        </span>
        <svg
          className={`h-3.5 w-3.5 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {open && (
        <div className="flex flex-col gap-2 border-t border-slate-100 bg-slate-50/60 p-2">
          {safeSources.map((source, index) => (
            <div key={`${source.document_id}-${index}`} className="rounded-md border border-slate-200 bg-white p-3">
              <p className="flex flex-wrap items-baseline gap-1 text-xs font-medium text-slate-700">
                <span>Source {index + 1}</span>
                <span className="text-slate-400">·</span>
                <span>{source.title}</span>
                {source.page_number !== null && <span className="text-slate-400">p.{source.page_number}</span>}
                <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">
                  score {source.score.toFixed(2)}
                </span>
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-500">{source.chunk_text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
