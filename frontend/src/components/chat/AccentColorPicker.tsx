'use client';

import { ACCENTS } from '../../lib/chat/accentTheme';
import { useAccentTheme } from './AccentThemeProvider';

export default function AccentColorPicker() {
  const { accentKey, setAccentKey } = useAccentTheme();

  return (
    <div role="group" aria-label="Chat accent color" className="flex items-center gap-2 px-4 py-2.5">
      {ACCENTS.map((accent) => {
        const selected = accent.key === accentKey;
        return (
          <button
            key={accent.key}
            type="button"
            onClick={() => setAccentKey(accent.key)}
            aria-pressed={selected}
            aria-label={`${accent.label} accent color`}
            title={accent.label}
            className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-slate-900"
            style={{
              backgroundColor: accent.swatch,
              borderColor: selected ? '#0f172a' : 'transparent',
            }}
          >
            {selected && (
              <svg className="h-2.5 w-2.5 text-white" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path
                  fillRule="evenodd"
                  d="M16.704 5.29a1 1 0 0 1 0 1.42l-7.25 7.25a1 1 0 0 1-1.42 0l-3.25-3.25a1 1 0 1 1 1.42-1.42l2.54 2.54 6.54-6.54a1 1 0 0 1 1.42 0Z"
                  clipRule="evenodd"
                />
              </svg>
            )}
          </button>
        );
      })}
    </div>
  );
}
