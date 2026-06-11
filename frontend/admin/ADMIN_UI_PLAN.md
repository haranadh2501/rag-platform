# ADMIN_UI_PLAN.md — Admin Portal Implementation Plan

> Owner: M8. Check off tasks as you complete them. One PR per phase; title: `feat(admin-ui): <phase-name>`.

## Phase 1 — Scaffold
- [x] Next.js 14 project created: package.json, tsconfig.json, next.config.mjs, tailwind.config.ts, postcss.config.js, .eslintrc.json
- [x] `@admin-types` path alias wired in tsconfig.json → `./admin/types/admin`
- [x] `next-env.d.ts` committed so `tsc --noEmit` runs without a prior build
- [x] Run `npm install` — package-lock.json generated (node v24.16.0 / npm 11.13.0)
- [x] `npm run typecheck` — passed (0 errors)
- [x] `npm run lint` — passed (0 warnings, 0 errors)
- [x] `npm run build` — passed; Next.js 14.2.35; 3 routes compiled (/, /admin, /admin/documents)
- [ ] Run `npx openapi-typescript ../../specs/openapi.yaml -o src/types/openapi.ts`
- [ ] Create `src/lib/apiClient.ts` — fetch wrapper: attaches `Authorization: Bearer`, handles `401` → clear token → redirect to `/login?next=`
- [ ] Create `src/lib/authContext.tsx` — `AuthContext` with `user`, `role`, `login()`, `logout()`

## Phase 2 — Shared Layout
- [x] `src/app/admin/layout.tsx` — full sidebar + header shell (Documents, Users, Tenants🔒, Settings; Knowledge Base footer)
- [x] `src/app/admin/documents/page.tsx` — mock UI with upload panel, quota card, document table, and pipeline stepper
- [x] Sidebar collapses to hamburger on < 768 px
- [x] Active nav item: `indigo-600` left border + background tint
- [ ] `AuthGuard` HOC — redirect to `/login?next=<path>` when no JWT cookie
- [ ] Header: real tenant name + user menu + logout action (currently static "Acme Corp" / "A" avatar)

## Phase 3 — Documents Page
- [ ] `src/app/admin/documents/page.tsx` — wire to real backend (`GET /admin/documents`, `POST /admin/documents/upload`, `POST /admin/documents/url`)
- [x] `UploadSourcePanel` — tabbed: file drag-drop tab + URL ingest tab (mock; upload disabled, MOCK_N8N notice shown)
- [ ] Client-side MIME + size (> 25 MB) validation before any network request
- [ ] XHR progress bar during file upload
- [x] `StorageQuotaBar` — mock quota values; amber at 80 %, red at 95 % (mock)
- [x] `DocumentTable` — columns: Title, Type, Status, Chunks, Uploaded, Actions (mock data)
- [x] `StatusBadge` — pending (slate) / processing (blue spinner) / completed (emerald) / failed (red X + error message) (mock)
- [x] Pipeline stepper: uploaded → validated → parsed/OCR → chunked → embedded → stored; always-visible beneath each row (mock; expand/collapse is a future enhancement)
- [x] Stepper: failed state shows red stage marker + `error_message`; completed state shows chunk count + indexed timestamp (mock)
- [ ] 5 s polling for rows in `pending` or `processing`; stop when all rows reach a terminal state
- [x] Filter bar by status — client-side filter over mock data; indigo active state; empty state row when no matches (mock)
- [ ] Pagination 20/page (`GET /admin/documents?page=&per_page=20`)
- [ ] `ConfirmDialog` before delete; empty state when no documents

## Phase 4 — Document Detail Page
- [ ] `src/app/admin/documents/[id]/page.tsx` — fetches `GET /admin/documents/{id}`
- [ ] Renders title, type, status badge, chunk count, upload time, source path
- [ ] `status === 'failed'`: red alert box with `error_message` above delete button
- [ ] Delete → `ConfirmDialog` → `DELETE /admin/documents/{id}` → redirect + success toast

## Phase 5 — Users Page
- [x] `src/app/admin/users/page.tsx` — placeholder shell: title, description, empty table skeleton (mock; no backend, no auth)
- [ ] `UserTable` — email, role pill (indigo/blue/slate), active, joined, Deactivate action (hidden for own row)
- [ ] `InviteUserDrawer` — slide-over: email + role dropdown → `POST /admin/users/invite`; success inserts row + closes drawer

## Phase 6 — Tenants Page
- [x] `src/app/admin/tenants/page.tsx` — placeholder shell: title, super_admin badge, amber dev note, empty table skeleton (mock; no backend, no auth)
- [ ] `src/app/admin/tenants/page.tsx` — renders 403 state for `admin` role; full table for `super_admin`
- [ ] `TenantTable` — name, slug, plan, active, created, Edit / Deactivate actions
- [ ] `TenantModal` — create (`POST /admin/tenants`) + edit (`PATCH /admin/tenants/{id}`)
- [ ] Deactivate → `ConfirmDialog` → `PATCH` with `is_active: false`

## Phase 7 — Settings Page
- [x] `src/app/admin/settings/page.tsx` — placeholder shell: tenant info card (static placeholders), channel status row (Web/WhatsApp/Slack), rate limit text (mock; no backend)
- [ ] Tenant info card: name, slug (read-only), plan badge — wired to real tenant data
- [ ] Channel status row: Web ✓ · WhatsApp · Slack — grey when not configured per backend config
- [ ] Rate limits info: "20 uploads / hour per tenant"

## Phase 8 — Polish
- [ ] Dark mode toggle (`next-themes`); all components use `dark:` variants; persists across navigation
- [ ] Loading skeletons on initial page fetch (not just spinners)
- [ ] Error toasts on API failure — display `response.detail`
- [ ] 429 toast: "Upload limit reached (20/hour). Try again later."
- [ ] Responsive review at 375 px, 768 px, 1280 px
- [ ] All interactive elements keyboard-navigable with `focus-visible:ring-2 ring-indigo-500`
