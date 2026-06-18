'use client';

// AuthGuard shell — checks localStorage token presence only.
// No backend token verification. No role checks.
// TODO: wire 401 redirect in apiClient.ts once this guard is confirmed working.

import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '../../lib/authContext';

export default function AuthGuard({ children }: { children: ReactNode }) {
  const { isAuthenticated, isHydrated } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (isHydrated && !isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isHydrated, isAuthenticated, pathname, router]);

  // Spinner while hydrating localStorage token, and while redirect is in flight.
  if (!isHydrated || !isAuthenticated) {
    return (
      <div className="flex h-full items-center justify-center py-20">
        <span
          className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600"
          aria-label="Loading"
        />
      </div>
    );
  }

  return <>{children}</>;
}
