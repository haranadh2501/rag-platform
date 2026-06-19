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
- [ ] Login as `admin` role → lands on `/admin/documents` *(requires live backend)*
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

> **Mock data state — table and drawer complete, API wiring blocked.**
> "Invite user" button opens a right-side slide-over drawer.
> User table shows `MOCK_USERS` (4 users: super_admin, admin, 2 × user; one inactive).
> Email search (contains, case-insensitive) and role filter (All/Super Admin/Admin/User) work client-side.
> Role pills: indigo (super_admin), blue (admin), slate (user).
> Logged-in user's row shows an emerald "You" badge (matched by `useAuth().user?.email`);
> that row has "—" instead of a Deactivate button.
> All other rows have a disabled "Deactivate" button with tooltip "API pending — wired in Phase 5 once blockers are resolved".
> Empty state "No users match the current filters." renders when search/filter produce no rows.
> Mock data notice visible above table.
> Drawer shows: email, phone_number (disabled — amber "Required by team · Schema pending"),
> role (admin/user), tenant_id (read-only; shows `currentUser?.tenant_id` when available),
> password/temp-password, and amber blocker notice.
> Submit button reads "Send invite — API pending"; disabled. No API call fires.
> Verifiable via `npm run dev` without a live stack.
>
> **Registration vs login**: No self-service signup in the admin portal. First-time users are
> admin-provisioned via this drawer; all users (first-time and returning) authenticate at `/login`.
>
> **Contract** (`RegisterRequest = { email, password, tenant_id, role? }`):
> `phone_number` absent (blocker). `tenant_id` from admin JWT. 409 for duplicate email not in
> `openapi.yaml` (blocker). Backend owns: unique-email enforcement, password hashing,
> tenant-scope 403 guard, Slack onboarding lookup. No frontend deduplication.
>
> **All invite-wiring criteria below remain `[ ]`** until three blockers are cleared with the backend team:
> phone_number schema, 409 response definition, password/temp-password behavior.

- [x] "Invite user" button is present on the Users page *(verifiable via `npm run dev`)*
- [x] Clicking "Invite user" opens a right-side slide-over drawer *(verifiable via `npm run dev`)*
- [x] Drawer shows email, role, tenant_id (read-only), password, and phone_number (disabled/blocked) fields *(verifiable via `npm run dev`)*
- [x] Submit button is disabled; amber blocker notice is visible in drawer *(verifiable via `npm run dev`)*
- [x] All users in the tenant are listed with correct role pill colors (indigo/blue/slate) *(mock data — verifiable via `npm run dev`)*
- [x] Logged-in user's own row has no Deactivate action; shows "—" instead *(verifiable via `npm run dev` when logged in)*
- [x] Email search input filters rows by case-insensitive email substring *(mock — verifiable via `npm run dev`)*
- [x] Role filter buttons (All / Super Admin / Admin / User) filter table; active button is indigo *(mock — verifiable via `npm run dev`)*
- [x] Empty state "No users match the current filters." renders when filters produce no results *(verifiable via `npm run dev`)*
- [x] Mock data notice shown above table; references `GET /admin/users` (Phase 5) *(verifiable via `npm run dev`)*
- [x] phone_number drawer badge changed from red "Blocked" to amber "Required by team · Schema pending" *(verifiable via `npm run dev`)*
- [x] Invite drawer shows no "M1" or "M2" internal module names in user-facing copy *(verifiable by reading source)*
- [ ] Invite user: valid email + role → `POST /admin/users/invite` → new row appears at top → drawer closes *(blocked — phone_number schema + 409 + password behavior unresolved)*
- [ ] Invite user: duplicate email → inline "Email already exists" error; no duplicate row created *(blocked — 409 not yet in openapi.yaml)*
- [ ] Invite user: invalid email format → inline validation error; no API call
- [ ] User table wired to `GET /admin/users` — mock data replaced by live backend data *(Phase 5)*

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
