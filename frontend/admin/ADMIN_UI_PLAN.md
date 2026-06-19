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
- [x] Create `src/lib/apiClient.ts` — `apiRequest<T>()`: base URL from `NEXT_PUBLIC_API_URL`, supports GET/POST/PATCH/DELETE, JSON + FormData bodies, 204 handling, `ApiError` with `status` + `detail` message; `setAuthToken`/`getAuthToken` module-level store; 401 throws `ApiError` with TODO for authContext redirect
  > **Auth strategy resolved**: stateless `Authorization: Bearer` on every request. `POST /auth/login`
  > returns `access_token` in JSON body; `authContext` stores it in `localStorage` (key: `access_token`)
  > and calls `setAuthToken(token)`. On app load `authContext` hydrates from `localStorage`.
  > Login route is `/login` (shared — not `/admin/login`). `authContext.tsx` is done — see item below.
- [x] Create `src/lib/authContext.tsx` — `AuthProvider` + `useAuth()`; exposes `token`, `user: UserOut | null`, `isAuthenticated`, `isHydrated`, `login(token, user)`, `logout()`; stores `access_token` + `user_context` in `localStorage`; hydrates both on mount via `useEffect`; logout clears both; `AuthProvider` wraps all routes from root layout (no JWT decode; no AuthGuard; no redirect)
  > `login(token, user)` stores `UserOut` from `POST /auth/login` response under `user_context` key. User hydrated from `localStorage` on mount; `JSON.parse` failure discards silently. Not backend-verified on every request — `GET /auth/me` wiring is a separate pending phase.
- [x] Move `AuthProvider` to root `src/app/layout.tsx`; removed from admin layout; login page calls `useAuth().login(access_token, user)` — `authContext` is the single write point for `access_token` + `user_context` (localStorage + apiClient in-memory store); no direct `localStorage` writes outside `authContext`
- [x] Create `src/app/login/page.tsx` — placeholder shell: email input, password input, disabled "Sign in" button, amber notice (`POST /auth/login` wiring in a later phase); server component; no submit logic; no redirect; shared route `/login`
- [x] Wire `src/app/login/page.tsx` — `POST /auth/login` (via `src/lib/authApi.ts`) → `useAuth().login(access_token, user)` → `router.replace(next || '/admin/documents')`
  > **Contract source**: Auth.json (Postman collection, IISc RAG — Auth M2) confirmed against `specs/openapi.yaml`. No conflict. Request: `{ email, password }`; response: `{ access_token, token_type, user }`. Rate-limited to 5/min per IP.
  > **Auth boundary**: `AuthProvider` is in root `layout.tsx` (available to all routes including `/login`). Login page calls `useAuth().login(access_token, user)` — `authContext` is the single place that writes `localStorage` and updates the in-memory `apiClient` store. No direct `localStorage` writes in the login page.
  > **Integration scope**: this is the only Auth API integration in this phase. Document page wiring (`GET /admin/documents`, upload, URL ingest, detail, delete) is Phase 3 — separate from login. All document pages remain mock/placeholder.

## Phase 2 — Shared Layout
- [x] `src/app/admin/layout.tsx` — full sidebar + header shell (Documents, Users, Tenants🔒, Settings; Knowledge Base footer)
- [x] `src/app/admin/documents/page.tsx` — mock UI with upload panel, quota card, document table, and pipeline stepper
- [x] Sidebar collapses to hamburger on < 768 px
- [x] Active nav item: `indigo-600` left border + background tint
- [x] `AuthGuard` shell (`src/components/admin/AuthGuard.tsx`) — client component; redirects to `/login?next=<path>` when `localStorage` token absent; loading spinner while `isHydrated=false`; wraps `{children}` inside `AdminShellLayout`; localStorage-only check — no backend token verification; no role checks
- [x] Header: avatar initial from `user.email.charAt(0)`, role badge from `user.role` (via `roleBadgeLabel()`), tenant pill shows `user.tenant_id.slice(0, 8)` with full ID in `title` attribute; all fall back gracefully when `user` is null (pre-hydration); sourced from `POST /auth/login` response stored in `authContext`
  > No logout button is rendered in the header yet — the header JSX contains only the tenant pill, role badge, and avatar. Logout button must be added and wired to `authContext.logout()` in the next phase. "Acme Corp" tenant name replaced by `tenant_id` prefix until `GET /auth/me` / tenant name API is wired.
- [x] Wire header logout button → `POST /auth/logout` (via `logoutApi()` in `src/lib/authApi.ts`) → `authContext.logout()` clears `access_token` + `user_context` from localStorage and in-memory store → `router.replace('/login')`; button disabled + spinner while in-flight; local auth always cleared even if backend logout fails
  > Bearer token sent automatically by `apiRequest()` from the in-memory store (no hardcoded JWT). `logoutApi()` returns `Promise<void>`; response body (`{ message?: string }` or empty) is discarded. `handleLogout()` in `AdminShellLayout` uses try/catch/finally so `logout()` + redirect always execute. `AuthGuard` remains localStorage-only check — no change.
- [ ] Call `GET /auth/me` after login to get fresh `email` + `role`; expose via `authContext`; unblocks role-based guards (Tenants 403) and ensures header reflects server-authoritative user data

## Phase 3 — Documents Page
- [ ] `src/app/admin/documents/page.tsx` — wire to real backend (`GET /admin/documents`, `POST /admin/documents/upload`)
- [x] `UploadSourcePanel` — tabbed: file drag-drop tab (upload disabled) + URL ingest tab
- [x] URL ingestion — Add by URL tab wired to n8n webhook (demo mode): `src/lib/n8nIngestionApi.ts` POSTs `{ document_id, tenant_id, source_type: "url", source_url, title }` to `NEXT_PUBLIC_N8N_INGEST_WEBHOOK_URL`; `document_id` generated client-side via `crypto.randomUUID()`; `tenant_id` from `NEXT_PUBLIC_DEMO_TENANT_ID` (demo shortcut until `GET /auth/me` is wired); URL validated client-side; "Add source" enabled only when URL is valid + env vars present; loading/success/error states shown inline
  > **Demo-only path (deprecated from UI)**: `n8nIngestionApi.ts` is kept for reference; the Documents page no longer calls it. UI now calls `POST /admin/documents/url` via `documentApi.ts`.
  > `NEXT_PUBLIC_N8N_INGEST_WEBHOOK_URL` and `NEXT_PUBLIC_DEMO_TENANT_ID` added to `.env.example`.
- [x] URL ingestion backend API wiring — Add by URL now calls `POST /admin/documents/url` via `src/lib/documentApi.ts` → `apiRequest<DocumentOut>()` → Bearer token attached automatically by `apiClient`; backend owns JWT validation, tenant isolation, and n8n trigger; no direct browser → n8n call; response `DocumentOut` used for the optimistic row (real `id`, `title`, `source_type`, `source_url`, `status`, `chunk_count`, `error_message`, `created_at`); `webhookConfigured` env-var check removed; "Webhook not configured" amber notice removed; `n8nIngestionApi` no longer imported in `documents/page.tsx`; footer note updated to reflect backend call
  > Bearer token comes from `apiClient` in-memory store (set at login); not hardcoded. Backend returns 202 `DocumentOut`. `GET /admin/documents` polling/list refresh remains pending (Phase 3).
- [x] URL ingestion error UX polish — `classifyUrlError(err: unknown): UrlSubmitError` helper classifies by `ApiError.status`: 401 → "session expired", 403 → "no permission", 404 → "endpoint not available", 429 → "too many requests", 5xx → "service trouble", no-response/network/CORS → "could not reach service"; all paths include `Technical detail: <original message>` in muted sub-text; `urlError` state changed to `{ message, detail } | null`; error panel renders `urlError.message` as body and `urlError.detail` as muted line; `aria-live="assertive"` preserved; no optimistic row inserted on failure; button re-enables after failure; `ApiError` imported from `apiClient.ts`
- [x] URL ingestion accepted-state UX — on submit, button shows spinner + "Submitting…"; on accepted webhook response: "Request accepted" inline panel with `aria-live="polite"`, URL/title fields cleared, optimistic local-only `pending` row prepended to table (title = submitted title or URL hostname, source_type = url, status = pending, created_at = current timestamp, id = separate `crypto.randomUUID()`); optimistic row shows pipeline stepper at stage 0 (uploaded) only; row marked "Local preview — real status appears after GET /admin/documents is wired."; filter auto-switches to All if current filter would hide pending rows; on failure: "Could not submit URL" inline panel with error detail in muted sub-text, `aria-live="assertive"`, button returns to normal
  > Optimistic row is local/demo-only — it is never persisted. Actual persistence and searchability depend on n8n executing the ingestion pipeline and writing to the backend DB. Row will not survive page refresh and does NOT count as confirmation of successful ingestion. `GET /admin/documents` list API wiring remains pending (Phase 3 — see task below).
- [x] URL ingestion optimistic pending→processing UX — after n8n accepts the request, the optimistic row starts as `pending`; 1500 ms later the same row transitions locally to `processing` (via `setTimeout` + `setOptimisticDocs` map). The stepper advances from stage 0 (uploaded) to the active parsed_ocr stage (index 2) automatically via the existing `pipelineStateFromDocument` helper. This gives demo-quality ingestion progress feedback without backend polling. Helper text updated to "Local preview — real status appears after GET /admin/documents is wired." Row never auto-completes; completed status requires real backend data from `GET /admin/documents`.
  > pending→processing transition is a local demo-only timer. It is NOT correlated with actual n8n pipeline progress. Real status from backend remains pending (Phase 3).
- [ ] File upload (PDF/DOCX/TXT) — XHR + progress bar pending (Phase 3); MOCK notice shown in file tab
- [ ] Client-side MIME + size (> 25 MB) validation before any network request
- [x] `StorageQuotaBar` — mock quota values; amber at 80 %, red at 95 % (mock)
- [x] `DocumentTable` — columns: Title, Type, Status, Chunks, Uploaded, Actions (mock data)
- [x] `StatusBadge` — pending (slate) / processing (blue spinner) / completed (emerald) / failed (red X + error message) (mock)
- [x] `StatusBadge` extracted to `src/components/admin/StatusBadge.tsx`; replaces inline logic in both `documents/page.tsx` and `documents/[id]/page.tsx`
- [x] Pipeline stepper: uploaded → validated → parsed/OCR → chunked → embedded → stored; always-visible beneath each row (mock; expand/collapse is a future enhancement)
- [x] Stepper: failed state shows red stage marker + `error_message`; completed state shows chunk count + indexed timestamp (mock)
- [ ] 5 s polling for rows in `pending` or `processing`; stop when all rows reach a terminal state
- [x] Filter bar by status — client-side filter over mock data; indigo active state; empty state row when no matches (mock)
- [ ] Pagination 20/page (`GET /admin/documents?page=&per_page=20`)
- [x] Actions column: "Detail" link → `/admin/documents/[doc.id]` for `completed` and `failed` rows; `pending` and `processing` rows show "—" (mock; Delete and Retry not yet wired)
- [ ] `ConfirmDialog` before delete; empty state when no documents

## Phase 4 — Document Detail Page
- [x] `src/app/admin/documents/[id]/page.tsx` — placeholder shell: back link, amber dev notice, mock title / type / status / chunks / uploaded / source, failed-state red alert, disabled Delete button (mock; no backend, no ConfirmDialog)
- [ ] `src/app/admin/documents/[id]/page.tsx` — wire to `GET /admin/documents/{id}`; replace mock with real fetched document
- [ ] `status === 'failed'`: red alert box with `error_message` above delete button (live data)
- [ ] Delete → `ConfirmDialog` → `DELETE /admin/documents/{id}` → redirect to `/admin/documents` + success toast

## Phase 5 — Users Page
- [x] `src/app/admin/users/page.tsx` — placeholder shell: title, description, empty table skeleton (mock; no backend, no auth)
- [x] Invite User drawer placeholder — "Invite user" button opens right-side slide-over with email, role (admin/user), tenant_id (read-only/JWT-derived), password, and phone_number (disabled, Blocked badge) fields; submit disabled; amber blocker notice inline; no API call fires; first-time users are admin-provisioned via this drawer, not public self-registered; all users (first-time and returning) authenticate at `/login`
- [x] `UserTable` mock — `MOCK_USERS: UserOut[]` (4 users: super_admin, admin, user×2 one inactive); email search + role filter (All/Super Admin/Admin/User); role pills (indigo/blue/slate); active badge; formatted join date; "You" emerald badge on current-user row (matched by `useAuth().user?.email`); current-user row shows "—" for Actions; other rows show disabled "Deactivate" with tooltip "API pending — wired in Phase 5 once blockers are resolved"; empty state "No users match the current filters."; mock data notice with `GET /admin/users` pending note
- [x] Invite User drawer updated — removed "M1"/"M2" internal names; phone_number badge changed from red "Blocked" to amber "Required by team · Schema pending"; tenant_id field shows `currentUser?.tenant_id` when available; password note updated to remove reference to M2; submit button text "Send invite — API pending"; footer note references Phase 5; `useAuth()` imported for current-user detection and tenant_id display
- [ ] `InviteUserDrawer` wiring — slide-over: email + role dropdown → `POST /admin/users/invite`; success inserts row + closes drawer
  > **Contract** (openapi.yaml): `RegisterRequest { email, password, tenant_id, role? }`. `tenant_id` from caller JWT. Auth.json also documents `POST /auth/register` (identical schema, admin-gated).
  > **Blocked — raise with M1/M2 before wiring**:
  > (a) `password` field required by schema but absent from drawer spec — backend must auto-generate (undocumented) or drawer must add field;
  > (b) `phone_number` not in `RegisterRequest` — raise with M1 to update `openapi.yaml` before adding phone field;
  > (c) 409 for duplicate email not defined in `openapi.yaml` — raise with M1/M2; backend owns unique-email enforcement, frontend surfaces `detail` field.

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
