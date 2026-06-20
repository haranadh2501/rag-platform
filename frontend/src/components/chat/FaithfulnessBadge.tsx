interface FaithfulnessBadgeProps {
  score: number | null | undefined;
}

export default function FaithfulnessBadge({ score }: FaithfulnessBadgeProps) {
  if (score === null || score === undefined) {
    return (
      <span className="text-xs text-slate-400" title="No grounding score available for this answer">
        ● Not scored
      </span>
    );
  }

  if (score >= 0.85) {
    return (
      <span className="text-xs text-emerald-600" title="Answer is well-grounded in the cited sources">
        ● Grounded ({score.toFixed(2)})
      </span>
    );
  }

  if (score >= 0.7) {
    return (
      <span className="text-xs text-amber-600" title="Answer is partially grounded — review the cited sources">
        ● Partially grounded ({score.toFixed(2)})
      </span>
    );
  }

  return (
    <span className="text-xs text-red-600" title="Answer may not be fully supported by the cited sources">
      ● Low confidence ({score.toFixed(2)})
    </span>
  );
}
