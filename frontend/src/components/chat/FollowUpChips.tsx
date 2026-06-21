interface FollowUpChipsProps {
  questions: string[];
  onSelect: (question: string) => void;
}

export default function FollowUpChips({ questions, onSelect }: FollowUpChipsProps) {
  const visible = (questions ?? []).slice(0, 3);

  if (visible.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2 px-1">
      {visible.map((question, index) => (
        <button
          key={`${question}-${index}`}
          type="button"
          onClick={() => onSelect(question)}
          className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
        >
          {question}
        </button>
      ))}
    </div>
  );
}
