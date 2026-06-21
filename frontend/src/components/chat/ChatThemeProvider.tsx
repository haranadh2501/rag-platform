'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

export type ChatThemeMode = 'light' | 'dark';

const STORAGE_KEY = 'chat-theme';

interface ChatThemeContextValue {
  mode: ChatThemeMode;
  toggle: () => void;
}

const ChatThemeContext = createContext<ChatThemeContextValue | null>(null);

export function useChatTheme(): ChatThemeContextValue {
  const ctx = useContext(ChatThemeContext);
  if (!ctx) {
    throw new Error('useChatTheme must be used within ChatThemeProvider');
  }
  return ctx;
}

interface ChatThemeProviderProps {
  children: ReactNode;
}

/**
 * Scopes light/dark mode to the Chat UI only: applies Tailwind's `dark` class
 * to a wrapper div instead of <html>, so `dark:` variants activate for
 * descendants here without affecting the rest of the app.
 */
export default function ChatThemeProvider({ children }: ChatThemeProviderProps) {
  const [mode, setMode] = useState<ChatThemeMode>('light');

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') {
      setMode(stored);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setMode('dark');
    }
  }, []);

  function toggle() {
    setMode((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark';
      window.localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  }

  return (
    <ChatThemeContext.Provider value={{ mode, toggle }}>
      <div className={mode === 'dark' ? 'dark' : undefined}>{children}</div>
    </ChatThemeContext.Provider>
  );
}
