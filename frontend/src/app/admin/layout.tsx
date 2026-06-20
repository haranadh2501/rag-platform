'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import AuthGuard from '../../components/admin/AuthGuard';
import { logoutApi } from '../../lib/authApi';
import { useAuth } from '../../lib/authContext';

interface NavItem {
  label: string;
  href: string;
  /** Prefix used for active-state check when it differs from href (e.g. /chat/new active on /chat/*). */
  matchPrefix?: string;
  icon: React.ReactElement;
  locked?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: 'Documents',
    href: '/admin/documents',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
      </svg>
    ),
  },
  {
    label: 'Users',
    href: '/admin/users',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
      </svg>
    ),
  },
  {
    label: 'Tenants',
    href: '/admin/tenants',
    locked: true,
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
      </svg>
    ),
  },
  {
    label: 'Settings',
    href: '/admin/settings',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
      </svg>
    ),
  },
  {
    label: 'Chat',
    href: '/chat/new',
    matchPrefix: '/chat',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
      </svg>
    ),
  },
];

function roleBadgeLabel(role: string): string {
  if (role === 'super_admin') return 'Super Admin';
  if (role === 'admin') return 'Admin';
  if (role === 'user') return 'User';
  return role;
}

export default function AdminShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const { user, logout } = useAuth();

  const pageTitle =
    NAV_ITEMS.find((item) => pathname.startsWith(item.href))?.label ?? 'Admin';

  async function handleLogout(): Promise<void> {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await logoutApi();
    } catch {
      // Backend logout failed (network error, already-expired token, etc.).
      // Local auth state is cleared in finally regardless — user must never be stuck.
    } finally {
      logout();
      router.replace('/login');
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* ── Mobile overlay ─────────────────────────────────── */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-slate-900/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar ────────────────────────────────────────── */}
      <aside
        className={[
          'fixed inset-y-0 left-0 z-30 flex w-60 flex-col bg-white shadow-sm',
          'transition-transform duration-200 ease-in-out',
          'md:static md:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
        aria-label="Sidebar"
      >
        {/* Logo / brand */}
        <div className="flex h-16 shrink-0 items-center border-b border-slate-100 px-6">
          <span className="text-sm font-semibold tracking-wide text-indigo-600">
            RAG Platform
          </span>
        </div>

        {/* Nav items */}
        <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Admin navigation">
          <ul className="space-y-0.5" role="list">
            {NAV_ITEMS.map(({ label, href, matchPrefix, icon, locked }) => {
              const active = pathname.startsWith(matchPrefix ?? href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={() => setSidebarOpen(false)}
                    aria-current={active ? 'page' : undefined}
                    className={[
                      'group flex items-center gap-3 rounded-md border-l-2 px-3 py-2 text-sm font-medium',
                      'focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500',
                      active
                        ? 'border-indigo-600 bg-indigo-50 text-indigo-600'
                        : 'border-transparent text-slate-600 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600',
                    ].join(' ')}
                  >
                    <span className={['shrink-0', active ? 'text-indigo-500' : 'text-slate-400 group-hover:text-indigo-500'].join(' ')}>
                      {icon}
                    </span>
                    <span className="flex-1">{label}</span>
                    {locked && (
                      <svg className="h-3.5 w-3.5 shrink-0 text-slate-300" fill="currentColor" viewBox="0 0 20 20" aria-label="super_admin only">
                        <path fillRule="evenodd" d="M10 1a4.5 4.5 0 0 0-4.5 4.5V9H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-.5V5.5A4.5 4.5 0 0 0 10 1Zm3 8V5.5a3 3 0 1 0-6 0V9h6Z" clipRule="evenodd" />
                      </svg>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Knowledge base footer */}
        <div className="shrink-0 border-t border-slate-100 px-5 py-4">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
            Knowledge Base
          </p>
          <p className="mt-1 text-xs text-slate-400 leading-relaxed">
            Upload documents, manage users, and configure your tenant&apos;s knowledge base from this portal.
          </p>
        </div>
      </aside>

      {/* ── Main column (header + content) ─────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* ── Header ───────────────────────────────────────── */}
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 shadow-sm md:px-6">

          {/* Left: hamburger (mobile) + page title */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 md:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
              </svg>
            </button>

            {/* Separator between hamburger and title on mobile */}
            <div className="h-5 w-px bg-slate-200 md:hidden" aria-hidden="true" />

            <h1 className="text-sm font-semibold text-slate-800">{pageTitle}</h1>
          </div>

          {/* Right: tenant · divider · role badge + avatar */}
          <div className="flex items-center gap-3">

            {/* Tenant pill — shows tenant_id[:8] until tenant name API or GET /auth/me is wired */}
            <span
              className="hidden items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 sm:flex"
              title={user?.tenant_id ?? 'Tenant ID unavailable'}
            >
              <svg className="h-3.5 w-3.5 shrink-0 text-slate-400" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
              </svg>
              {user?.tenant_id ? user.tenant_id.slice(0, 8) + '…' : '—'}
            </span>

            <div className="hidden h-5 w-px bg-slate-200 sm:block" aria-hidden="true" />

            {/* Role badge + avatar — sourced from POST /auth/login user object */}
            <div className="flex items-center gap-2.5">
              <span className="hidden rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-600/20 sm:block">
                {user ? roleBadgeLabel(user.role) : 'Admin'}
              </span>
              <div
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white ring-2 ring-white"
                aria-label={user ? `Signed in as ${user.email}` : 'User account'}
              >
                {user?.email?.charAt(0).toUpperCase() ?? 'A'}
              </div>
            </div>

            <div className="hidden h-5 w-px bg-slate-200 sm:block" aria-hidden="true" />

            {/* Sign out — calls POST /auth/logout then clears local auth regardless of result */}
            <button
              type="button"
              onClick={handleLogout}
              disabled={loggingOut}
              aria-label={loggingOut ? 'Signing out…' : 'Sign out'}
              className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loggingOut ? (
                <span
                  className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600"
                  aria-hidden="true"
                />
              ) : (
                <svg className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
                </svg>
              )}
              <span className="hidden sm:inline">{loggingOut ? 'Signing out…' : 'Sign out'}</span>
            </button>
          </div>
        </header>

        {/* Page content — AuthGuard redirects to /login when no localStorage token */}
        <main className="flex-1 overflow-y-auto">
          <AuthGuard>{children}</AuthGuard>
        </main>
      </div>
    </div>
  );
}
