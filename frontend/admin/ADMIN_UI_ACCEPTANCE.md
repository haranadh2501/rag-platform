# ADMIN_UI_ACCEPTANCE.md — Admin Portal Acceptance Criteria

> Test against a live stack: `docker compose up -d` + backend (`uvicorn`) + frontend (`npm run dev`).
> Seed: `python -m app.scripts.seed_admin` creates `admin@example.com / changeme`.
>
> **No automated test runner is installed** (`package.json` has no jest/vitest/playwright/cypress).
> Current verification approach: `npm run typecheck` + `npm run lint` + `npm run build` + screenshot/manual review.
> End-to-end criteria below require a live stack and are not automatically tested.

## Auth & Route Guards

> **Login wired; user context stored; AuthProvider at root; AuthGuard active; document pages still mock.**
> `POST /auth/login` is wired in `src/app/login/page.tsx` via `src/lib/authApi.ts`. On success the page calls `useAuth().login(access_token, user)` — `authContext` stores both the token (`access_token` key) and the full `UserOut` object (`user_context` key) in `localStorage` and updates the in-memory apiClient store. The `UserOut` is sourced directly from the login response (`{ id, email, role, tenant_id, is_active, created_at }`). `authContext` hydrates both on mount. Admin header now shows live data: avatar initial from `user.email`, role badge from `user.role`, tenant pill from `user.tenant_id.slice(0, 8)`. All header values fall back gracefully when `user` is null. User data is **not backend-verified on each request** (localStorage-sourced); `GET /auth/me` wiring is a pending phase. `AuthProvider` lives in root `layout.tsx`. `AuthGuard` redirects `/admin/*` to `/login?next=<path>` on no token. Role checks, Tenants 403 state, logout action, and `apiClient.ts` 401 → redirect remain TODO. All document, user, tenant, and settings pages remain mock/placeholder. No automated test runner; verification is typecheck + browser check.

- [x] `/admin/documents` without token → redirects to `/login?next=/admin/documents` *(manual browser check — AuthGuard shell active)*
- [x] Login as `admin` or `super_admin` role with no `next` param → lands on `/admin/documents` *(requires live backend)*
- [x] Login as `user` role with no `next` param → redirects to `/chat/new` *(requires live backend)*
- [x] Login with safe `next` param (any role) → redirects to `next` regardless of role *(requires live backend)*
- [ ] Login as `user` role → `/admin/*` is inaccessible (redirect or 403) *(requires role checks — not yet implemented)*
- [ ] `/admin/tenants` as `admin` role → shows 403 state, not blank page or JS error *(requires role checks — not yet implemented)*

## Auth — Logout

> **Logout API wired** (`src/lib/authApi.ts` + `src/app/admin/layout.tsx`).
> The "Sign out" button in the admin header calls `logoutApi()` → `apiRequest<{ message?: string }>('POST', '/auth/logout')`.
> Bearer token is attached automatically by `apiRequest()` from the in-memory store (no hardcoded JWT).
> `handleLogout()` uses try/catch/finally: regardless of API success or failure, `authContext.logout()`
> clears `access_token` and `user_context` from `localStorage` and the in-memory apiClient store,
> then `router.replace('/login')` redirects. Button shows a spinner and is disabled while in-flight.
> `AuthGuard` remains a localStorage-only check — no change to guard behaviour.
> `GET /auth/me`, role guards, and Tenants 403 remain pending.
> No automated test runner; verification is typecheck + browser check against live stack.

- [ ] Clicking "Sign out" in the admin header sends `POST /auth/logout` with `Authorization: Bearer <token>` *(requires live backend)*
- [ ] After logout completes, `localStorage` keys `access_token` and `user_context` are both absent *(verifiable via `npm run dev` + browser DevTools → Application → Local Storage)*
- [ ] After logout, browser navigates to `/login` *(verifiable via `npm run dev`)*
- [ ] If `POST /auth/logout` fails (network error, expired token, server error), local auth state is still cleared and browser still redirects to `/login` *(verifiable via `npm run dev` with network request blocked in DevTools)*

## Login Page (`/login`)

> **Wired — manual browser checks required for live-stack criteria.**
> `src/app/login/page.tsx` calls `POST /auth/login` via `src/lib/authApi.ts`. On success:
> calls `useAuth().login(access_token, user)` — `authContext` writes both `access_token` and
> `user_context` (the full `UserOut`) to `localStorage` and updates the apiClient in-memory store
> (single write point); redirects to `?next` path (if safe) or `/admin/documents`. On 401: inline
> "Invalid email or password" error; no token stored. Button disabled until both fields are
> non-empty; `aria-live` error region for screen readers.
> Auth contract sourced from Auth.json (Postman) and confirmed against `specs/openapi.yaml`.
> No automated test runner; verification is typecheck + lint + build + browser check against live stack.

- [x] Valid credentials → `POST /auth/login` → `access_token` in `localStorage` → redirect *(manual browser check with live backend)*
- [x] Invalid credentials → inline "Invalid email or password" error; no redirect; no token stored *(manual browser check)*
- [x] Empty form → Sign in button disabled; no API call fires *(verifiable via `npm run dev`)*

## Documents Page — Upload

> **URL ingestion wired (demo mode) with accepted-state UX; file upload remains disabled.**
> Add by URL tab posts `{ document_id, tenant_id, source_type: "url", source_url, title }` to
> `NEXT_PUBLIC_N8N_INGEST_WEBHOOK_URL` via `src/lib/n8nIngestionApi.ts`.
> On submit: button shows spinner + "Submitting…" (disabled). On accepted response: "Request
> accepted" inline panel (aria-live="polite"); URL and title fields cleared; an optimistic local-only
> `pending` row is prepended to the table top — title is the submitted title or URL hostname
> fallback; row shows pipeline stepper at stage 0 only; row is labelled "Local preview — real row
> appears after GET /admin/documents is wired." If the current filter would hide pending rows,
> filter auto-switches to All. On failure: "Could not submit URL" panel with error detail in muted
> sub-text (aria-live="assertive"); button returns to normal. Optimistic row is local/demo-only —
> never persisted, does not survive page refresh, does NOT confirm successful ingestion. Actual
> persistence depends on n8n writing to the backend DB. `GET /admin/documents` list API wiring
> remains pending (Phase 3). File upload disabled. No automated test runner.

**Add by URL — verifiable via `npm run dev` + live backend:**
- [x] Invalid URL (e.g. `not-a-url`) → "Add source" button disabled; no network request *(verifiable via `npm run dev`)*
- [x] Partially typed URL → inline "Must be a valid http:// or https:// URL" error shown *(verifiable via `npm run dev`)*
- [ ] Valid URL → clicking "Add source" shows spinner + "Submitting…" and sends `POST /admin/documents/url` to backend *(requires live backend + .env.local `NEXT_PUBLIC_API_URL`)*
- [ ] Request includes `Authorization: Bearer <token>` header; no direct n8n request appears in browser Network tab *(requires live backend + browser DevTools Network)*
- [ ] Backend accepts request → "Request accepted" panel appears; URL and title fields cleared; row inserted from returned `DocumentOut` fields *(requires live backend)*
- [ ] Invalid/expired token → backend returns 401 → "Unauthorized" error shown in error panel; no row inserted *(requires live backend)*
- [x] Accepted URL appears as a row at the top of the document table using backend-returned `id`, `title`, `source_type`, `status`, `created_at` *(verifiable via `npm run dev` with mock response)*
- [x] If backend returns `pending`, row shows stage-0 pipeline stepper; after ~1500 ms row advances locally to Processing *(verifiable via `npm run dev`)*
- [x] Optimistic row labelled "Status preview — live updates require GET /admin/documents polling." only while pending/processing *(verifiable via `npm run dev`)*
- [x] Row does not claim completion unless backend returned `completed` status *(verifiable via `npm run dev` — expected behaviour)*
- [x] If current filter would hide the new row, filter switches to All after accepted submit *(verifiable via `npm run dev`)*
- [ ] Backend returns 4xx/5xx → "Could not submit URL" panel shown with status-specific friendly message + `Technical detail: <message>` in muted text; no row inserted; button re-enables *(requires live backend)*
  - 401 → "Your session expired. Please sign in again."
  - 403 → "You do not have permission to add documents."
  - 404 → "The URL ingestion endpoint is not available yet. Please try again after the backend URL ingestion API is deployed." (no internal module names exposed to users)
  - 429 → "Too many requests. Please try again in a minute."
  - 5xx → "The document service is having trouble. Please try again later."
- [x] Network error / CORS block / "Failed to fetch" → "Could not reach the document service. Check backend availability or CORS." + technical detail *(verifiable via `npm run dev` with backend stopped or CORS misconfigured)*
- [x] No direct n8n request appears in browser Network tab — `documents/page.tsx` does not import `n8nIngestionApi` *(verifiable by reading source)*
- [x] Document table does NOT refresh from backend after submit — optimistic row does not survive page refresh; `GET /admin/documents` polling remains pending *(verifiable — expected behaviour)*

**File upload — all criteria blocked (Phase 3):**
- [ ] Upload a PDF ≤ 25 MB → row appears immediately with `pending` badge (no page refresh)
- [ ] Upload a file > 25 MB → rejected client-side; no network request fires
- [ ] Upload a `.exe` or other disallowed type → rejected client-side with error message
- [ ] XHR progress bar advances during upload; does not jump straight to 100 %

## Documents Page — Status & Polling

> **StatusBadge — shared component (UI only)**: `StatusBadge` is now a shared presentation component at
> `src/components/admin/StatusBadge.tsx`. This was a UI extraction only — no API integration occurred.
> Both the list page (`documents/page.tsx`) and the detail page (`documents/[id]/page.tsx`) still
> render hardcoded mock data. Verified via `npm run typecheck` + screenshot; no automated test runner
> is installed. All criteria below remain unchecked and require Phase 3 live-stack wiring.

- [ ] `pending` → `processing` → `completed` transitions happen without page refresh
- [ ] `completed` row shows correct chunk count returned by backend (not a hardcoded value)
- [ ] `failed` row shows red X badge; `error_message` shown inline under the badge
- [ ] Polling stops once all visible rows are in a terminal state
- [ ] Storage quota bar reflects current usage; turns amber at 80 %, red at 95 %

## Documents Page — Ingestion Pipeline Stepper

> **Mock state**: stepper is always-visible beneath each row. Expand/collapse toggle is a future phase.
> Update these criteria to "clicking a row expands the stepper" once the toggle is implemented.

- [ ] `processing` row stepper shows correct active stage spinning; prior stages filled green
- [ ] `failed` row stepper shows red marker on the failed stage and `error_message` beneath
- [ ] `completed` row stepper shows all stages filled green + chunk count + indexed timestamp
- [ ] Stepper labels match exactly: uploaded → validated → parsed/OCR → chunked → embedded → stored
- [ ] No label implies the frontend performs parsing, chunking, embedding, or storage

## Documents Page — Table Controls

> **Mock filter (already verifiable)**: client-side filter over mock data — testable via `npm run dev` without a live stack.
> **API filter (requires live stack)**: re-fetches `GET /admin/documents?status=` on each selection.
> Update the filter criteria below to remove the mock note once backend wiring is done.
>
> **Actions column — current mock state**: "Detail" link is navigable (routes to the placeholder
> detail page) but always shows hardcoded mock data regardless of which row was clicked.
> "Delete" and "Retry" are not yet implemented; completed/failed rows show only `Detail`, while pending/processing rows show `—`.

- [ ] Filter by `failed` (mock: client-side) → table shows only failed documents; other statuses hidden
- [ ] Filter by `failed` (live stack) → `GET /admin/documents?status=failed` fires; only failed rows returned from backend
- [ ] Pagination: navigating to page 2 loads the next 20 rows
- [ ] Delete → confirmation dialog appears → confirm → row removed → success toast
- [ ] Delete → cancel → row remains; no API call fired
- [ ] Empty state renders when no documents exist

## Document Detail Page

> **Placeholder state**: The "Detail" link in the table now navigates to `/admin/documents/[id]`,
> but the detail page always renders hardcoded mock data (a `failed` document) regardless of which
> row was clicked — `params.id` from the URL is displayed in the amber notice only.
> The red failed-state alert is always visible — this does **not** count as passing that criterion.
> The Delete button is disabled. All criteria below require Phase 4 backend wiring
> (`GET /admin/documents/{id}`, `DELETE /admin/documents/{id}`) and `ConfirmDialog` implementation.

- [ ] Title, type, status badge, chunk count, upload timestamp, and source path all render (live data from `GET /admin/documents/{id}`)
- [ ] `failed` status: red alert box with `error_message` is visible above the delete button (live data)
- [ ] Delete → confirmation dialog → `DELETE /admin/documents/{id}` fires → redirect to `/admin/documents` → success toast

## Users Page

> **`GET /admin/users` + `POST /auth/register` wired; RBAC UX guard active; deactivate pending.**
> Users page is `admin` and `super_admin` only. `role === 'user'` sees "Access restricted" state;
> `GET /admin/users` is NOT called; no table, no Invite button, no drawer rendered.
> Admin sidebar hides the Users nav item for `role === 'user'` (UX only — backend enforces RBAC).
> This is a frontend UX guard only; backend must independently reject unauthorized requests.
> Role is sourced from the `POST /auth/login` response; `GET /auth/me` wiring is still pending.
>
> For `admin`/`super_admin`: Users page calls `GET /admin/users` on mount via `listUsersApi()`.
> Invite drawer calls `POST /auth/register` via `createUserApi()` with `{ email, password, tenant_id, role }`.
> Bearer token attached automatically by `apiClient` (no hardcoded JWT; no direct DB access).
> `tenant_id` sourced from `authContext.user.tenant_id` — not a form field.
> `phone_number` visible but disabled — NOT sent to backend (absent from `RegisterRequest`).
> Password sent to backend only; cleared after success; frontend never stores passwords; backend owns hashing.
> On success: returned `UserOut` prepended to table; drawer closes; form cleared.
> On create failure: inline red panel in drawer; drawer stays open.
> On list fetch failure: inline red panel above table; no silent fallback to mock data.
> Backend must enforce: unique-email, password hashing, tenant-scope 403, Slack onboarding lookup.
> `GET /auth/me` for backend-verified role refresh remains pending.
> No automated frontend test runner; verification is typecheck + browser check against live stack.
>
> **Registration vs login**: No self-service signup in the admin portal. First-time users are
> admin-provisioned via this drawer; all users (first-time and returning) authenticate at `/login`.
>
> **Contract** (`RegisterRequest = { email, password, tenant_id, role? }`):
> `phone_number` absent (blocker for that field). `tenant_id` from admin JWT. 409 for duplicate
> email not in `openapi.yaml` (duplicate handling is best-effort). Backend owns: unique-email
> enforcement, password hashing, tenant-scope 403 guard, Slack onboarding lookup.

- [x] "Invite user" button is present on the Users page *(verifiable via `npm run dev`)*
- [x] Clicking "Invite user" opens a right-side slide-over drawer *(verifiable via `npm run dev`)*
- [x] Drawer shows email, role, tenant_id (read-only), password, and phone_number (disabled/blocked) fields *(verifiable via `npm run dev`)*
- [x] Submit button is disabled; amber blocker notice is visible in drawer *(verifiable via `npm run dev`)*
- [x] Logged-in user's own row has no Deactivate action; shows "—" instead *(verifiable via `npm run dev` when logged in)*
- [x] Email search input filters rows by case-insensitive email substring *(client-side over fetched data — verifiable via `npm run dev` + live backend)*
- [x] Role filter buttons (All / Super Admin / Admin / User) filter table; active button is indigo *(client-side over fetched data — verifiable via `npm run dev` + live backend)*
- [x] Empty state "No users match the current filters." renders when filters produce no results *(verifiable via `npm run dev`)*
- [x] phone_number drawer badge is amber "Required by team · Schema pending" *(verifiable via `npm run dev`)*
- [x] Invite drawer shows no "M1" or "M2" internal module names in user-facing copy *(verifiable by reading source)*
- [x] Users page sends `GET /admin/users` on mount *(requires live backend — verifiable via browser DevTools Network tab)*
- [x] `GET /admin/users` request includes `Authorization: Bearer <token>` header *(verifiable via browser DevTools)*
- [x] Backend users render in the table with correct role pills, active badge, join date *(requires live backend)*
- [x] List fetch failure shows inline red "Could not load users" panel with friendly message + `Technical detail:` in muted text; no silent fallback to mock data *(verifiable via `npm run dev` with backend stopped)*
- [x] Loading skeleton (3 rows, pulse animation) shown while `GET /admin/users` is in flight *(verifiable via `npm run dev` with network throttled)*
- [x] All users in the tenant are listed with correct role pill colors (indigo/blue/slate) *(requires live backend)*
- [x] Create user drawer sends `POST /auth/register` with `{ email, password, tenant_id, role }` *(requires live backend — verifiable via browser DevTools Network tab)*
- [x] `POST /auth/register` request includes `Authorization: Bearer <token>` header; token attached by `apiClient`, no hardcoded value *(verifiable via browser DevTools)*
- [x] Request body does NOT include `phone_number` — field visible in drawer but never submitted *(verifiable by reading source)*
- [x] `tenant_id` in request body is sourced from `authContext.user.tenant_id`; not a form field *(verifiable by reading source)*
- [x] Successful `POST /auth/register` response (201 `UserOut`) prepended to user table at top *(requires live backend)*
- [x] Password field cleared after successful create; frontend does not store passwords *(requires live backend)*
- [x] Drawer closes and form fields reset after successful create *(requires live backend)*
- [x] `POST /auth/register` failure keeps drawer open and shows inline red error panel with status-specific message + `Technical detail:` in muted text *(verifiable via `npm run dev` with backend returning error)*
  - 400/422 → "Please check the user details and try again."
  - 401 → "Your session expired. Please sign in again."
  - 403 → "You do not have permission to create users."
  - 409 or "already exists" in detail → "A user with this email already exists."
  - 429 → "Too many requests. Please try again in a minute."
  - 5xx → "The user service is having trouble. Please try again later."
  - network/CORS → "Could not reach the user service. Check backend availability or CORS."
- [x] Submit button ("Create user") disabled until email, password (≥8 chars), and `tenant_id` are present; disabled while request in flight *(verifiable via `npm run dev`)*
- [x] phone_number field remains visible but disabled ("Required by team · Schema pending"); never sent to backend *(verifiable via `npm run dev`)*
- [ ] Deactivate user → `ConfirmDialog` → `PATCH /admin/users/{id}` → row updates *(not yet implemented)*

**Users RBAC UX guard** (frontend UX only — backend must independently enforce):
- [x] Admin sidebar does NOT show "Users" nav item when logged in as `role === 'user'` *(requires live backend — verifiable via browser DevTools + role: user account)*
- [x] Navigating directly to `/admin/users` as `role === 'user'` shows "Access restricted" heading and "User management is available only to admins." message *(requires live backend)*
- [x] "Access restricted" page includes "Go to Chat" link to `/chat/new` *(verifiable via `npm run dev` by mocking role)*
- [x] `GET /admin/users` is NOT called when `role === 'user'` — no Network request visible in browser DevTools *(requires live backend)*
- [x] No users table, no search/filter, no Invite user button, and no drawer render for `role === 'user'` *(verifiable by reading source)*
- [x] `admin` role sees the full users table, search/filter, and Invite user button *(requires live backend)*
- [x] `super_admin` role sees the full users table, search/filter, and Invite user button *(requires live backend)*
- [x] Create-user action (`POST /auth/register`) is only reachable by `admin`/`super_admin` — drawer not rendered for `user` role *(verifiable by reading source)*
- [x] Role is sourced from `POST /auth/login` response user object; `GET /auth/me` wiring for backend-verified role refresh remains pending *(expected behavior)*
- [ ] Backend independently rejects `GET /admin/users` and `POST /auth/register` for `role === 'user'` *(backend RBAC — not yet verified; frontend guard is UX only)*

## Chat Navigation

> **M8 adds navigation access only. Chat UI is M9-owned.**
> Admin sidebar includes a "Chat" nav item linking to `/chat/new`.
> Active state matches `/chat/*` via `matchPrefix: '/chat'`.
> Users page does not embed chat — no iframe, no chat window.
> Per-user chat history view in the Users page is future work / API pending.
> No automated frontend test runner; verification is typecheck + browser check.

- [x] Admin sidebar shows a "Chat" nav item with chat-bubble icon *(verifiable via `npm run dev`)*
- [x] Clicking "Chat" in sidebar navigates to `/chat/new` *(verifiable via `npm run dev`)*
- [x] Chat nav item is active (indigo highlight) when on `/chat/new` or any `/chat/*` path *(verifiable via `npm run dev`)*
- [x] Login as `user` role with no `next` param → redirected to `/chat/new` after success *(requires live backend)*
- [x] Login as `admin` or `super_admin` with no `next` param → redirected to `/admin/documents` *(requires live backend)*
- [x] Login with safe `next` param → redirected to `next` regardless of role *(requires live backend)*
- [x] Users page does not embed a chat window or iframe *(verifiable by reading source)*
- [ ] Per-user conversation history in Users page *(future work — chat history API not yet defined)*

## Tenants Page

> **Requires Phase 6 auth wiring.** The current placeholder renders no 403 state — any user
> can reach the page. These criteria cannot pass until `AuthGuard` and role checks are implemented.

- [ ] `admin` role sees a 403 message, not a blank page or unhandled error
- [ ] `super_admin` sees the full tenant list
- [ ] Create Tenant modal → submit → new row appears in table
- [ ] Edit Tenant modal → fields pre-populated → save → row updates
- [ ] Deactivate → confirmation dialog → confirm → tenant marked inactive in table

## Settings Page

> **Requires Phase 7 backend wiring.** Channel status icons and tenant info fields are
> currently hardcoded placeholders. These criteria cannot pass until tenant data and channel
> config are fetched from the backend.

- [ ] Tenant name, slug (read-only), and plan badge render correctly for the logged-in tenant
- [ ] Channel status icons reflect backend configuration (grey = not configured)

## Polish
- [ ] Dark mode toggle switches theme; preference persists across page navigations
- [ ] Initial page load shows a skeleton, not a blank flash
- [ ] Killing the backend mid-session → error toast with the `detail` message from the response
- [ ] All buttons and links reachable and activatable by keyboard alone
- [ ] Sidebar hamburger appears at 375 px; all nav links are accessible
