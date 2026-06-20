interface ClarificationBannerProps {
  requiresClarification: boolean;
}

export default function ClarificationBanner({ requiresClarification }: ClarificationBannerProps) {
  if (!requiresClarification) {
    return null;
  }

  return (
    <div role="alert" className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
      This answer may be incomplete — try adding more detail to your question so it can be answered from the
      available sources.
    </div>
  );
}
