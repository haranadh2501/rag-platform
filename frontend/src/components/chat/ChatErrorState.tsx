interface ChatErrorStateProps {
  onRetry?: () => void;
}

export default function ChatErrorState({ onRetry }: ChatErrorStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
      <p className="text-sm font-medium text-slate-700">Something went wrong fetching that answer.</p>
      <p className="max-w-sm text-xs text-slate-400">
        This may be a temporary issue. You can try sending your question again.
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white"
        >
          Retry
        </button>
      )}
    </div>
  );
}
