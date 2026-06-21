interface ChatEmptyStateProps {
  onSelectPrompt?: (prompt: string) => void;
}

const SAMPLE_PROMPTS = [
  'Summarize the onboarding guide in three bullet points',
  'What does the return policy cover?',
  'List the setup steps for a new account',
];

export default function ChatEmptyState({ onSelectPrompt }: ChatEmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
      <div className="w-full max-w-md rounded-2xl border border-slate-100 bg-white p-8 shadow-sm">
        <div
          aria-hidden="true"
          className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-indigo-50 text-lg"
        >
          💬
        </div>

        <h2 className="mt-4 text-lg font-semibold text-slate-800">How can I help with your knowledge base?</h2>
        <p className="mt-2 text-sm text-slate-500">
          Ask a question and I&apos;ll answer using your uploaded documents, with citations back to the exact
          source passages used.
        </p>

        <div className="mt-6 flex flex-col gap-2 text-left">
          {SAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onSelectPrompt?.(prompt)}
              className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 transition hover:border-[var(--accent-200)] hover:bg-[var(--accent-50)] hover:text-[var(--accent-700)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-600)] focus-visible:ring-offset-2"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
