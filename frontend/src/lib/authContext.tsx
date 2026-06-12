'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { setAuthToken } from './apiClient';

const STORAGE_KEY = 'access_token';

interface AuthContextValue {
  token: string | null;
  isAuthenticated: boolean;
  /** False until the localStorage hydration effect has run on the client. */
  isHydrated: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);

  // Hydrate token from localStorage on first client render.
  // isHydrated prevents AuthGuard from flashing a redirect before the
  // token is read (will be used when AuthGuard is wired in Phase 2).
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setToken(stored);
      setAuthToken(stored);
    }
    setIsHydrated(true);
  }, []);

  function login(newToken: string): void {
    localStorage.setItem(STORAGE_KEY, newToken);
    setToken(newToken);
    setAuthToken(newToken);
  }

  function logout(): void {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setAuthToken(null);
    // TODO: redirect to /login?next=<current-path> once AuthGuard is wired (Phase 2).
  }

  return (
    <AuthContext.Provider
      value={{ token, isAuthenticated: token !== null, isHydrated, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error('useAuth must be called within <AuthProvider>');
  }
  return ctx;
}
