'use client';

import { useState } from 'react';
import { useAuth } from '../../../lib/authContext';
import type { UserOut, UserRole } from '@admin-types';

// Mock users — replaced by GET /admin/users in Phase 5.
const MOCK_USERS: UserOut[] = [
  {
    id: 'user-001',
    email: 'admin@example.com',
    role: 'super_admin',
    tenant_id: '11111111-1111-1111-1111-111111111111',
    is_active: true,
    created_at: '2026-01-15T10:00:00Z',
  },
  {
    id: 'user-002',
    email: 'alice@acme.com',
    role: 'admin',
    tenant_id: '11111111-1111-1111-1111-111111111111',
    is_active: true,
    created_at: '2026-02-10T14:30:00Z',
  },
  {
    id: 'user-003',
    email: 'bob@acme.com',
    role: 'user',
    tenant_id: '11111111-1111-1111-1111-111111111111',
    is_active: true,
    created_at: '2026-03-20T09:15:00Z',
  },
  {
    id: 'user-004',
    email: 'charlie@acme.com',
    role: 'user',
    tenant_id: '11111111-1111-1111-1111-111111111111',
    is_active: false,
    created_at: '2026-04-05T11:00:00Z',
  },
];

type InviteRole = Extract<UserRole, 'admin' | 'user'>;
type RoleFilter = UserRole | 'all';

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

  // Table filters
  const [searchEmail, setSearchEmail] = useState('');
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all');

  // Invite drawer state
  const [open, setOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<InviteRole>('user');
  const [invitePassword, setInvitePassword] = useState('');

  const filteredUsers = MOCK_USERS.filter((u) => {
    const matchesEmail = u.email.toLowerCase().includes(searchEmail.toLowerCase());
    const matchesRole = roleFilter === 'all' || u.role === roleFilter;
    return matchesEmail && matchesRole;
  });

  const hasActiveFilter = searchEmail.length > 0 || roleFilter !== 'all';

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

      <p className="mb-3 text-xs text-slate-400">
        Mock data — live list requires{' '}
        <code className="rounded bg-slate-100 px-0.5">GET /admin/users</code> (Phase 5).
      </p>

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
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-400">
                  {hasActiveFilter
                    ? 'No users match the current filters.'
                    : 'No users found.'}
                </td>
              </tr>
            ) : (
              filteredUsers.map((u) => {
                const isCurrent = u.email === currentUser?.email;
                return (
                  <tr key={u.id} className="hover:bg-slate-50">
                    {/* Email */}
                    <td className="px-4 py-3 text-sm">
                      <span className="font-medium text-slate-800">{u.email}</span>
                      {isCurrent && (
                        <span className="ml-2 inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                          You
                        </span>
                      )}
                    </td>

                    {/* Role pill */}
                    <td className="px-4 py-3">
                      <span className={roleBadgeClass(u.role)}>
                        {roleBadgeLabel(u.role)}
                      </span>
                    </td>

                    {/* Active */}
                    <td className="px-4 py-3 text-sm">
                      {u.is_active ? (
                        <span className="text-emerald-600">✓ Active</span>
                      ) : (
                        <span className="text-slate-400">Inactive</span>
                      )}
                    </td>

                    {/* Joined */}
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {formatDate(u.created_at)}
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3 text-sm">
                      {isCurrent ? (
                        <span className="text-slate-400" title="Cannot deactivate your own account">
                          —
                        </span>
                      ) : (
                        <button
                          type="button"
                          disabled
                          title="API pending — wired in Phase 5 once blockers are resolved"
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
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-slate-900/50"
            aria-hidden="true"
            onClick={() => setOpen(false)}
          />

          {/* Slide-over panel */}
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="invite-drawer-title"
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col overflow-y-auto bg-white shadow-xl"
          >
            {/* Drawer header */}
            <div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-6 py-4">
              <div>
                <h2
                  id="invite-drawer-title"
                  className="text-base font-semibold text-slate-900"
                >
                  Invite User
                </h2>
                <p className="mt-0.5 text-xs text-slate-500">
                  Admin-provisioned — not a public self-registration.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
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

            {/* Blocker notice */}
            <div className="mx-6 mt-5 shrink-0 rounded-md border border-amber-200 bg-amber-50 p-4 text-xs text-amber-800">
              <p className="font-semibold">API wiring pending — resolve blockers first</p>
              <ul className="mt-2 list-disc space-y-1 pl-4">
                <li>
                  <strong>phone_number</strong> is required by team spec but absent from{' '}
                  <code className="rounded bg-amber-100 px-0.5">RegisterRequest</code> in{' '}
                  <code className="rounded bg-amber-100 px-0.5">openapi.yaml</code> — backend
                  schema must be updated before this field can be sent.
                </li>
                <li>
                  <strong>409 duplicate email</strong> response not defined in{' '}
                  <code className="rounded bg-amber-100 px-0.5">openapi.yaml</code> — backend owns
                  unique-email enforcement; frontend will surface the{' '}
                  <code className="rounded bg-amber-100 px-0.5">detail</code> field once the 409
                  shape is documented.
                </li>
                <li>
                  <strong>Password/temp-password</strong> behaviour unconfirmed — backend
                  auto-generate vs. admin-set not yet documented.
                </li>
                <li>
                  <strong>Slack onboarding lookup</strong> by email is backend-owned; no frontend
                  action required.
                </li>
              </ul>
            </div>

            {/* Form fields */}
            <div className="flex-1 px-6 py-5">
              <div className="space-y-5">

                {/* Email */}
                <div>
                  <label
                    htmlFor="invite-email"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Email <span className="text-red-500" aria-hidden="true">*</span>
                  </label>
                  <input
                    id="invite-email"
                    type="email"
                    autoComplete="off"
                    placeholder="user@example.com"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                {/* Phone number — required by team, blocked at schema level */}
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
                    Required by team spec. Disabled until{' '}
                    <code className="rounded bg-slate-100 px-0.5">phone_number</code> is added to{' '}
                    <code className="rounded bg-slate-100 px-0.5">RegisterRequest</code> in
                    openapi.yaml.
                  </p>
                </div>

                {/* Role */}
                <div>
                  <label
                    htmlFor="invite-role"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Role <span className="text-red-500" aria-hidden="true">*</span>
                  </label>
                  <select
                    id="invite-role"
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as InviteRole)}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>

                {/* Tenant — read-only, derived from JWT */}
                <div>
                  <label className="block text-xs font-medium text-slate-700">
                    Tenant
                  </label>
                  <input
                    type="text"
                    readOnly
                    value={currentUser?.tenant_id ?? 'derived from your JWT'}
                    aria-readonly="true"
                    className="mt-1 w-full cursor-default rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400"
                  />
                  <p className="mt-1 text-xs text-slate-400">
                    <code>tenant_id</code> in <code>RegisterRequest</code> is populated from your
                    JWT — not editable here.
                  </p>
                </div>

                {/* Password / Temp password */}
                <div>
                  <label
                    htmlFor="invite-password"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Password / Temp password{' '}
                    <span className="text-red-500" aria-hidden="true">*</span>
                  </label>
                  <input
                    id="invite-password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="••••••••"
                    value={invitePassword}
                    onChange={(e) => setInvitePassword(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                  <p className="mt-1 text-xs text-amber-700">
                    Required by <code>RegisterRequest</code>. Confirm with the backend team whether
                    the backend auto-generates a temporary password or the admin sets one here.
                    Frontend never stores or logs passwords; backend owns hashing.
                  </p>
                </div>

              </div>
            </div>

            {/* Drawer footer */}
            <div className="shrink-0 border-t border-slate-200 px-6 py-4">
              <button
                type="button"
                disabled
                aria-disabled="true"
                className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                Send invite — API pending
              </button>
              <p className="mt-2 text-center text-xs text-slate-400">
                <code>POST /admin/users/invite</code> wired in Phase 5 once blockers are cleared.
              </p>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
