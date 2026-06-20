'use client';

import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '../../lib/authContext';

export default function ChatAuthGuard({ children }: { children: ReactNode }) {
  const { isAuthenticated, isHydrated } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (isHydrated && !isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isHydrated, isAuthenticated, pathname, router]);

  if (!isHydrated || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <span
          className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600"
          aria-label="Loading"
        />
      </div>
    );
  }

  return <>{children}</>;
}
