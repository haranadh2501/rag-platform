# ADMIN_UI_PLAN.md — Admin Portal Implementation Plan

> Owner: M8. Check off tasks as you complete them. One PR per phase; title: `feat(admin-ui): <phase-name>`.

## Phase 1 — Scaffold
- [ ] Confirm `npm run dev` opens http://localhost:3000
- [ ] Run `npx openapi-typescript ../../specs/openapi.yaml -o src/types/openapi.ts`
- [ ] Copy `frontend/admin/types/admin.ts` → `frontend/src/types/admin.ts`
- [ ] Create `src/lib/apiClient.ts` — fetch wrapper: attaches `Authorization: Bearer`, handles `401` → clear token → redirect to `/login?next=`
- [ ] Create `src/lib/authContext.tsx` — `AuthContext` with `user`, `role`, `login()`, `logout()`

## Phase 2 — Shared Layout
- [ ] `src/app/admin/layout.tsx` — wraps all `/admin/*` pages with `AuthGuard`; redirects to `/login?next=` when unauthenticated
- [ ] `src/components/admin/AdminLayout.tsx` — 240 px sidebar (Documents, Users, Tenants🔒, Settings, Chat→) + header (tenant name, user menu, logout)
- [ ] Sidebar collapses to hamburger on < 768 px
- [ ] Active nav item: `indigo-600` left border + background tint

## Phase 3 — Documents Page
- [ ] `src/app/admin/documents/page.tsx`
- [ ] `DocumentUploadPanel` — tabbed: file drag-drop with XHR progress bar + URL ingest form
- [ ] Client-side MIME + size (> 25 MB) validation before any network request
- [ ] `StorageQuotaBar` — reads tenant storage metadata; amber at 80 %, red at 95 %
- [ ] `DocumentTable` — columns: Title, Type, Status, Chunks, Uploaded, Actions
- [ ] `StatusBadge` — pending (slate) / processing (blue spinner) / completed (emerald) / failed (red X + tooltip)
- [ ] Row-expand stage stepper: uploaded → validated → parsed/OCR → chunked → embedded → stored
- [ ] Stepper: failed state shows red stage marker + `error_message`; completed state shows chunk count + indexed timestamp
- [ ] 5 s polling for rows in `pending` or `processing`; stop when all rows reach a terminal state
- [ ] Filter bar by status + pagination 20/page
- [ ] `ConfirmDialog` before delete; empty state when no documents

## Phase 4 — Document Detail Page
- [ ] `src/app/admin/documents/[id]/page.tsx` — fetches `GET /admin/documents/{id}`
- [ ] Renders title, type, status badge, chunk count, upload time, source path
- [ ] `status === 'failed'`: red alert box with `error_message` above delete button
- [ ] Delete → `ConfirmDialog` → `DELETE /admin/documents/{id}` → redirect + success toast

## Phase 5 — Users Page
- [ ] `src/app/admin/users/page.tsx`
- [ ] `UserTable` — email, role pill (indigo/blue/slate), active, joined, Deactivate action (hidden for own row)
- [ ] `InviteUserDrawer` — slide-over: email + role dropdown → `POST /admin/users/invite`; success inserts row + closes drawer

## Phase 6 — Tenants Page
- [ ] `src/app/admin/tenants/page.tsx` — renders 403 state for `admin` role; full table for `super_admin`
- [ ] `TenantTable` — name, slug, plan, active, created, Edit / Deactivate actions
- [ ] `TenantModal` — create (`POST /admin/tenants`) + edit (`PATCH /admin/tenants/{id}`)
- [ ] Deactivate → `ConfirmDialog` → `PATCH` with `is_active: false`

## Phase 7 — Settings Page
- [ ] `src/app/admin/settings/page.tsx`
- [ ] Tenant info card: name, slug (read-only), plan badge
- [ ] Channel status row: Web ✓ · WhatsApp · Slack (grey if not configured)
- [ ] Rate limits info: "20 uploads / hour per tenant"

## Phase 8 — Polish
- [ ] Dark mode toggle (`next-themes`); all components use `dark:` variants; persists across navigation
- [ ] Loading skeletons on initial page fetch (not just spinners)
- [ ] Error toasts on API failure — display `response.detail`
- [ ] 429 toast: "Upload limit reached (20/hour). Try again later."
- [ ] Responsive review at 375 px, 768 px, 1280 px
- [ ] All interactive elements keyboard-navigable with `focus-visible:ring-2 ring-indigo-500`
