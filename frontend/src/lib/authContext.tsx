'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { setAuthToken } from './apiClient';
import type { UserOut } from '@admin-types';

const TOKEN_KEY = 'access_token';
const USER_KEY = 'user_context';

interface AuthContextValue {
  token: string | null;
  /** User object from the POST /auth/login response, restored from localStorage on hydration.
   *  Null before hydration or when logged out. Not backend-verified on every request —
   *  GET /auth/me wiring is a separate pending phase. */
  user: UserOut | null;
  isAuthenticated: boolean;
  /** False until the localStorage hydration effect has run on the client. */
  isHydrated: boolean;
  login: (token: string, user: UserOut) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserOut | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);

  // Hydrate token and user from localStorage on first client render.
  // isHydrated prevents AuthGuard from flashing a redirect before the
  // token is read.
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    const storedUser = localStorage.getItem(USER_KEY);

    if (storedToken) {
      setToken(storedToken);
      setAuthToken(storedToken);
    }
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser) as UserOut);
      } catch {
        // Corrupt storage — discard silently.
        localStorage.removeItem(USER_KEY);
      }
    }
    setIsHydrated(true);
  }, []);

  function login(newToken: string, newUser: UserOut): void {
    localStorage.setItem(TOKEN_KEY, newToken);
    localStorage.setItem(USER_KEY, JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
    setAuthToken(newToken);
  }

  function logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
    setAuthToken(null);
    // TODO: redirect to /login?next=<current-path> once apiClient.ts 401 handler is wired.
  }

  return (
    <AuthContext.Provider
      value={{ token, user, isAuthenticated: token !== null, isHydrated, login, logout }}
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
