import type { DocumentStatus } from '@admin-types';

interface StatusBadgeProps {
  status: DocumentStatus;
  errorMessage?: string | null;
}

export default function StatusBadge({ status, errorMessage }: StatusBadgeProps) {
  switch (status) {
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
          {errorMessage && (
            <p className="mt-0.5 break-words text-xs text-red-400">{errorMessage}</p>
          )}
        </div>
      );
  }
}
