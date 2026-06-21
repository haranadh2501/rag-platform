'use client';

import { useState } from 'react';
import type { KeyboardEvent } from 'react';

interface MessageInputProps {
  onSubmit: (value: string) => void;
  disabled?: boolean;
}

export default function MessageInput({ onSubmit, disabled = false }: MessageInputProps) {
  const [value, setValue] = useState('');

  const canSubmit = value.trim().length > 0 && !disabled;

  function handleSubmit() {
    if (!canSubmit) return;
    onSubmit(value.trim());
    setValue('');
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="sticky bottom-0 z-10 flex items-end gap-2 border-t border-slate-200 bg-white px-3 py-3 sm:px-4">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        rows={1}
        placeholder="Ask anything about your knowledge base…"
        className="flex-1 resize-none rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-[var(--accent-600)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-600)] disabled:opacity-60"
      />
      <button
        type="button"
        onClick={handleSubmit}
        disabled={!canSubmit}
        aria-disabled={!canSubmit}
        className="shrink-0 rounded-full bg-[var(--accent-600)] px-4 py-2 text-sm font-medium text-white transition hover:bg-[var(--accent-700)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-600)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Send
      </button>
    </div>
  );
}
