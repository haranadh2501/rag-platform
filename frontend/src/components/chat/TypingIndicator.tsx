'use client';

import { useEffect, useState } from 'react';

const STAGES = [
  'Searching knowledge base…',
  'Reading source chunks…',
  'Drafting grounded answer…',
  'Checking citations…',
];

const STAGE_INTERVAL_MS = 1600;

export default function TypingIndicator() {
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStageIndex((prev) => Math.min(prev + 1, STAGES.length - 1));
    }, STAGE_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-2 px-4 py-2" role="status" aria-label="Assistant is typing">
      <span className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400" />
      </span>
      <span className="text-xs text-slate-500">{STAGES[stageIndex]}</span>
    </div>
  );
}
