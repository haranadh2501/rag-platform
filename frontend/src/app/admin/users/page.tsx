'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '../../../lib/authContext';
import { listUsersApi, createUserApi } from '../../../lib/userApi';
import { ApiError } from '../../../lib/apiClient';
import type { UserOut, UserRole } from '@admin-types';

type InviteRole = Extract<UserRole, 'admin' | 'user'>;
type RoleFilter = UserRole | 'all';

interface PageError {
  message: string;
  detail: string;
}

function classifyFetchError(err: unknown): PageError {
  const technical = `Technical detail: ${err instanceof Error ? err.message : String(err)}`;
  if (err instanceof ApiError) {
    if (err.status === 401) return { message: 'Your session expired. Please sign in again.', detail: technical };
    if (err.status === 403) return { message: 'You do not have permission to view users.', detail: technical };
    if (err.status >= 500) return { message: 'The user service is having trouble. Please try again later.', detail: technical };
    return { message: 'Could not load users. Please try again.', detail: technical };
  }
  return { message: 'Could not reach the user service. Check backend availability or CORS.', detail: technical };
}

function classifyCreateError(err: unknown): PageError {
  const technical = `Technical detail: ${err instanceof Error ? err.message : String(err)}`;
  if (err instanceof ApiError) {
    if (err.status === 401) return { message: 'Your session expired. Please sign in again.', detail: technical };
    if (err.status === 403) return { message: 'You do not have permission to create users.', detail: technical };
    if (err.status === 409) return { message: 'A user with this email already exists.', detail: technical };
    if (err.status === 429) return { message: 'Too many requests. Please try again in a minute.', detail: technical };
    if (err.status >= 500) return { message: 'The user service is having trouble. Please try again later.', detail: technical };
    // 400/422 or duplicate keyword in detail
    const msg = err.message.toLowerCase();
    if (msg.includes('already exists') || msg.includes('duplicate') || msg.includes('unique')) {
      return { message: 'A user with this email already exists.', detail: technical };
    }
    return { message: 'Please check the user details and try again.', detail: technical };
  }
  return { message: 'Could not reach the user service. Check backend availability or CORS.', detail: technical };
}

const ROLE_FILTER_OPTIONS: { value: RoleFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'super_admin', label: 'Super Admin' },
  { value: 'admin', label: 'Admin' },
  { value: 'user', label: 'User' },
];

function roleBadgeLabel(role: UserRole): string {
  if (role === 'super_admin') return 'Super Admin';
  if (role === 'admin') return 'Admin';
  return 'User';
}

function roleBadgeClass(role: UserRole): string {
  if (role === 'super_admin') {
    return 'inline-flex rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700';
  }
  if (role === 'admin') {
    return 'inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700';
  }
  return 'inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700';
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export default function UsersPage() {
  const { user: currentUser } = useAuth();

  // Data state
  const [users, setUsers] = useState<UserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<PageError | null>(null);

  // Table filters
  const [searchEmail, setSearchEmail] = useState('');
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all');

  // Invite drawer state
  const [open, setOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<InviteRole>('user');
  const [invitePassword, setInvitePassword] = useState('');
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteError, setInviteError] = useState<PageError | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchUsers() {
      setLoading(true);
      setFetchError(null);
      try {
        const data = await listUsersApi();
        if (!cancelled) setUsers(data.users);
      } catch (err) {
        if (!cancelled) setFetchError(classifyFetchError(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void fetchUsers();
    return () => { cancelled = true; };
  }, []);

  const filteredUsers = users.filter((u) => {
    const matchesEmail = u.email.toLowerCase().includes(searchEmail.toLowerCase());
    const matchesRole = roleFilter === 'all' || u.role === roleFilter;
    return matchesEmail && matchesRole;
  });

  const hasActiveFilter = searchEmail.length > 0 || roleFilter !== 'all';

  const tenantId = currentUser?.tenant_id ?? '';
  const canSubmitInvite =
    inviteEmail.trim().length > 0 &&
    invitePassword.length >= 8 &&
    tenantId.length > 0 &&
    !inviteLoading;

  function closeDrawer() {
    setOpen(false);
    setInviteEmail('');
    setInviteRole('user');
    setInvitePassword('');
    setInviteError(null);
  }

  async function handleInviteSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmitInvite) return;

    setInviteLoading(true);
    setInviteError(null);

    try {
      const newUser = await createUserApi({
        email: inviteEmail.trim(),
        password: invitePassword,
        tenant_id: tenantId,
        role: inviteRole,
      });
      setUsers((prev) => [newUser, ...prev]);
      closeDrawer();
    } catch (err) {
      setInviteError(classifyCreateError(err));
    } finally {
      setInviteLoading(false);
    }
  }

  return (
    <main className="p-6">
      {/* ── Page header ──────────────────────────────────── */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Users</h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage tenant users and send invitations.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="shrink-0 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500"
        >
          Invite user
        </button>
      </div>

      {/* ── Search + role filter ─────────────────────────── */}
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <input
          type="search"
          placeholder="Search by email…"
          value={searchEmail}
          onChange={(e) => setSearchEmail(e.target.value)}
          className="w-60 rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <div className="flex gap-1">
          {ROLE_FILTER_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => setRoleFilter(value)}
              className={
                roleFilter === value
                  ? 'rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white'
                  : 'rounded-md px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100'
              }
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── List fetch error panel ───────────────────────── */}
      {fetchError && (
        <div
          role="alert"
          aria-live="assertive"
          className="mb-4 rounded-md border border-red-200 bg-red-50 p-3"
        >
          <p className="text-sm font-medium text-red-800">Could not load users</p>
          <p className="mt-1 text-xs text-red-700">{fetchError.message}</p>
          <p className="mt-1 text-xs text-red-400">{fetchError.detail}</p>
        </div>
      )}

      {/* ── User table ───────────────────────────────────── */}
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {['Email', 'Role', 'Active', 'Joined', 'Actions'].map((col) => (
                <th
                  key={col}
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-slate-500"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 5 }).map((__, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 animate-pulse rounded bg-slate-100" />
                    </td>
                  ))}
                </tr>
              ))
            ) : fetchError ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-400">
                  User list unavailable — see error above.
                </td>
              </tr>
            ) : filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-400">
                  {hasActiveFilter ? 'No users match the current filters.' : 'No users found.'}
                </td>
              </tr>
            ) : (
              filteredUsers.map((u) => {
                const isCurrent = u.email === currentUser?.email;
                return (
                  <tr key={u.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-sm">
                      <span className="font-medium text-slate-800">{u.email}</span>
                      {isCurrent && (
                        <span className="ml-2 inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                          You
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={roleBadgeClass(u.role)}>{roleBadgeLabel(u.role)}</span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {u.is_active ? (
                        <span className="text-emerald-600">✓ Active</span>
                      ) : (
                        <span className="text-slate-400">Inactive</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {formatDate(u.created_at)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {isCurrent ? (
                        <span className="text-slate-400" title="Cannot deactivate your own account">
                          —
                        </span>
                      ) : (
                        <button
                          type="button"
                          disabled
                          title="Deactivate API not yet wired"
                          className="cursor-not-allowed rounded border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-400 disabled:opacity-50"
                        >
                          Deactivate
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* ── Invite User drawer ───────────────────────────── */}
      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-slate-900/50"
            aria-hidden="true"
            onClick={closeDrawer}
          />

          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="invite-drawer-title"
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col overflow-y-auto bg-white shadow-xl"
          >
            {/* Drawer header */}
            <div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-6 py-4">
              <div>
                <h2 id="invite-drawer-title" className="text-base font-semibold text-slate-900">
                  Invite User
                </h2>
                <p className="mt-0.5 text-xs text-slate-500">
                  Admin-provisioned — not a public self-registration.
                </p>
              </div>
              <button
                type="button"
                onClick={closeDrawer}
                aria-label="Close drawer"
                className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500"
              >
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.5}
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Pending items notice */}
            <div className="mx-6 mt-5 shrink-0 rounded-md border border-amber-200 bg-amber-50 p-4 text-xs text-amber-800">
              <p className="font-semibold">Known pending items</p>
              <ul className="mt-2 list-disc space-y-1 pl-4">
                <li>
                  <strong>phone_number</strong> is required by team spec but absent from{' '}
                  <code className="rounded bg-amber-100 px-0.5">RegisterRequest</code> in{' '}
                  <code className="rounded bg-amber-100 px-0.5">openapi.yaml</code> — field is
                  visible but not sent until backend schema is updated.
                </li>
                <li>
                  <strong>Duplicate email (409)</strong> is not defined in{' '}
                  <code className="rounded bg-amber-100 px-0.5">openapi.yaml</code> — backend owns
                  enforcement; frontend surfaces the{' '}
                  <code className="rounded bg-amber-100 px-0.5">detail</code> field when the error
                  is returned.
                </li>
                <li>
                  <strong>Slack onboarding lookup</strong> by email is backend-owned; no frontend
                  action required.
                </li>
              </ul>
            </div>

            {/* Create error panel */}
            {inviteError && (
              <div
                role="alert"
                aria-live="assertive"
                className="mx-6 mt-4 shrink-0 rounded-md border border-red-200 bg-red-50 p-3"
              >
                <p className="text-sm font-medium text-red-800">Could not create user</p>
                <p className="mt-1 text-xs text-red-700">{inviteError.message}</p>
                <p className="mt-1 text-xs text-red-400">{inviteError.detail}</p>
              </div>
            )}

            {/* Form */}
            <form
              id="invite-form"
              onSubmit={(e) => { void handleInviteSubmit(e); }}
              className="flex-1 px-6 py-5"
            >
              <div className="space-y-5">

                {/* Email */}
                <div>
                  <label htmlFor="invite-email" className="block text-xs font-medium text-slate-700">
                    Email <span className="text-red-500" aria-hidden="true">*</span>
                  </label>
                  <input
                    id="invite-email"
                    type="email"
                    autoComplete="off"
                    required
                    placeholder="user@example.com"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    disabled={inviteLoading}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
                  />
                </div>

                {/* Phone number — visible, disabled, not submitted */}
                <div>
                  <label
                    htmlFor="invite-phone"
                    className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-700"
                  >
                    Phone number
                    <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-600/20">
                      Required by team · Schema pending
                    </span>
                  </label>
                  <input
                    id="invite-phone"
                    type="tel"
                    disabled
                    placeholder="+91 xxxxxxxxxx"
                    className="mt-1 w-full cursor-not-allowed rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400 disabled:opacity-50"
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Not sent to backend until{' '}
                    <code className="rounded bg-slate-100 px-0.5">phone_number</code> is added to{' '}
                    <code className="rounded bg-slate-100 px-0.5">RegisterRequest</code> in
                    openapi.yaml.
                  </p>
                </div>

                {/* Role */}
                <div>
                  <label htmlFor="invite-role" className="block text-xs font-medium text-slate-700">
                    Role <span className="text-red-500" aria-hidden="true">*</span>
                  </label>
                  <select
                    id="invite-role"
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as InviteRole)}
                    disabled={inviteLoading}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>

                {/* Tenant — read-only, derived from JWT */}
                <div>
                  <label className="block text-xs font-medium text-slate-700">Tenant</label>
                  <input
                    type="text"
                    readOnly
                    value={tenantId || 'derived from your JWT'}
                    aria-readonly="true"
                    className="mt-1 w-full cursor-default rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400"
                  />
                  <p className="mt-1 text-xs text-slate-400">
                    <code>tenant_id</code> is populated from your JWT — not editable here.
                  </p>
                </div>

                {/* Password */}
                <div>
                  <label htmlFor="invite-password" className="block text-xs font-medium text-slate-700">
                    Password / Temp password{' '}
                    <span className="text-red-500" aria-hidden="true">*</span>
                  </label>
                  <input
                    id="invite-password"
                    type="password"
                    autoComplete="new-password"
                    required
                    minLength={8}
                    placeholder="Min. 8 characters"
                    value={invitePassword}
                    onChange={(e) => setInvitePassword(e.target.value)}
                    disabled={inviteLoading}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Sent to backend only; cleared after success. Backend owns hashing — frontend
                    never stores passwords.
                  </p>
                </div>

              </div>
            </form>

            {/* Drawer footer */}
            <div className="shrink-0 border-t border-slate-200 px-6 py-4">
              <button
                type="submit"
                form="invite-form"
                disabled={!canSubmitInvite}
                aria-disabled={!canSubmitInvite}
                className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                {inviteLoading ? 'Creating user…' : 'Create user'}
              </button>
              <p className="mt-2 text-center text-xs text-slate-400">
                Calls{' '}
                <code className="rounded bg-slate-100 px-0.5">POST /auth/register</code>
                {' '}with Bearer token · backend persists user in DB.
              </p>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
