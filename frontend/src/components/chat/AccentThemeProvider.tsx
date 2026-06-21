'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import {
  ACCENT_STORAGE_KEY,
  DEFAULT_ACCENT_KEY,
  getAccentByKey,
  type AccentDefinition,
} from '../../lib/chat/accentTheme';

interface AccentThemeContextValue {
  accentKey: string;
  accent: AccentDefinition;
  setAccentKey: (key: string) => void;
}

const AccentThemeContext = createContext<AccentThemeContextValue | null>(null);

export function useAccentTheme(): AccentThemeContextValue {
  const ctx = useContext(AccentThemeContext);
  if (!ctx) {
    throw new Error('useAccentTheme must be used within AccentThemeProvider');
  }
  return ctx;
}

interface AccentThemeProviderProps {
  children: ReactNode;
}

/**
 * Injects the selected accent's colors as CSS variables on a `display: contents`
 * wrapper, so descendants can use them via Tailwind's `bg-[var(--accent-600)]`
 * arbitrary-value syntax without any extra prop-drilling or re-render coupling.
 */
export default function AccentThemeProvider({ children }: AccentThemeProviderProps) {
  const [accentKey, setAccentKeyState] = useState(DEFAULT_ACCENT_KEY);

  useEffect(() => {
    const stored = window.localStorage.getItem(ACCENT_STORAGE_KEY);
    if (stored) {
      setAccentKeyState(stored);
    }
  }, []);

  function setAccentKey(key: string) {
    setAccentKeyState(key);
    window.localStorage.setItem(ACCENT_STORAGE_KEY, key);
  }

  const accent = getAccentByKey(accentKey);
  const style = { display: 'contents', ...accent.vars } as CSSProperties;

  return (
    <AccentThemeContext.Provider value={{ accentKey, accent, setAccentKey }}>
      <div style={style}>{children}</div>
    </AccentThemeContext.Provider>
  );
}
