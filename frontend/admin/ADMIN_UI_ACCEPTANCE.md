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
> persistence depends on n8n writing to the backend DB. `GET /admin/documents` list API wiring is
> implemented — see "Documents Page — List & Pagination" below. File upload disabled. No automated test runner.

**Add by URL — verifiable via `npm run dev` + live backend:**
- [x] Invalid URL (e.g. `not-a-url`) → "Add source" button disabled; no network request *(verifiable via `npm run dev`)*
- [x] Partially typed URL → inline "Must be a valid http:// or https:// URL" error shown *(verifiable via `npm run dev`)*
- [x] Empty Title with a valid URL → "Add source" button stays disabled; "Required." hint shown; no network request *(verifiable via `npm run dev`)*
- [x] Submit URL + title → clicking "Add source" sends `POST /admin/documents/url` with `{ url, title }` through `apiClient` (`ingestDocumentUrlApi()`); no hardcoded JWT or backend URL *(requires live backend + `.env.local` `NEXT_PUBLIC_API_URL` — verifiable via browser DevTools Network tab)*
- [x] Form shows loading state while submitting — spinner + "Submitting…"; button disabled for the duration of the request *(verifiable via `npm run dev`)*
- [x] Request includes `Authorization: Bearer <token>` header attached automatically by `apiClient`; no direct n8n request appears in browser Network tab *(requires live backend + browser DevTools Network)*
- [x] Successful response (202 `DocumentOut`, `status: "pending"`) shows a `pending` document — never claimed as `completed` — and "Request accepted" panel appears; URL and title fields cleared *(requires live backend)*
- [ ] Invalid/expired token → backend returns 401 → "Your session expired. Please sign in again." shown in error panel; no row inserted *(requires live backend)*
- [x] Accepted URL appears as a row at the top of the document table using backend-returned `id`, `title`, `source_type`, `status`, `created_at`, while a refetch of `GET /admin/documents?page=1&per_page=<perPage>` runs in the background and replaces it with the persisted row once it resolves *(verifiable via `npm run dev` with mock response)*
- [x] If backend returns `pending`, row shows stage-0 pipeline stepper; after ~1500 ms the (still-optimistic) row advances locally to Processing if the refetch has not yet resolved *(verifiable via `npm run dev`)*
- [x] Optimistic row labelled "Status preview — live updates require GET /admin/documents polling." only while pending/processing, and only until the refetch dedupes it against the persisted row *(verifiable via `npm run dev`)*
- [x] Row does not claim completion unless backend returned `completed` status *(verifiable via `npm run dev` — expected behaviour)*
- [x] If current filter would hide the new row, filter switches to All after accepted submit *(verifiable via `npm run dev`)*
- [ ] Friendly error panel/message appears on API failure with status-specific copy + `Technical detail: <message>` in muted text; no row inserted; button re-enables *(requires live backend)*
  - 400 → "Please check the URL and title."
  - 401 → "Your session expired. Please sign in again."
  - 403 → "You do not have permission to add documents."
  - 404 → "The Add by URL endpoint is not available yet."
  - 409 → "This document may already exist."
  - 422 → "The submitted URL or title is invalid."
  - 429 → "Too many requests. Please try again in a minute."
  - 5xx → "The document service is having trouble. Please try again later."
- [x] Network error / CORS block / "Failed to fetch" → "Could not reach the document service. Check backend availability or CORS." + technical detail *(verifiable via `npm run dev` with backend stopped or CORS misconfigured)*
- [x] No direct n8n request appears in browser Network tab — `documents/page.tsx` does not import `n8nIngestionApi` *(verifiable by reading source)*
- [x] No JWT or backend URL is hardcoded anywhere in `documentApi.ts` or `page.tsx` — token comes from `apiClient`'s in-memory store, base URL comes from `NEXT_PUBLIC_API_URL` *(verifiable by reading source)*
- [x] After a successful submit, the page sets `page` to 1 and triggers a refetch of `GET /admin/documents?page=1&per_page=<perPage>` rather than relying only on the local optimistic row *(verifiable via `npm run dev` + live backend, browser DevTools Network tab)*

**File upload — all criteria blocked (Phase 3):**
- [ ] Upload a PDF ≤ 25 MB → row appears immediately with `pending` badge (no page refresh)
- [ ] Upload a file > 25 MB → rejected client-side; no network request fires
- [ ] Upload a `.exe` or other disallowed type → rejected client-side with error message
- [ ] XHR progress bar advances during upload; does not jump straight to 100 %

## Documents Page — List & Pagination

> **`GET /admin/documents` list + pagination wired.** `documents/page.tsx` calls
> `listDocumentsApi({ page, perPage })` (`src/lib/documentApi.ts` →
> `apiRequest<DocumentList>('GET', '/admin/documents?page=&per_page=')`) on mount and whenever
> `page` or `perPage` changes. Bearer token is attached automatically by `apiClient` — no
> hardcoded JWT, no direct database access. The table renders backend-returned `DocumentOut[]`;
> the mock document array was removed; there is no silent fallback to mock data on failure.
> Loading: a 5-row pulsing skeleton replaces the table body while the request is in flight.
> Failure: an inline red panel above the table shows a status-specific friendly message
> (`classifyListError()`: 401/403/404/429/5xx/network) plus `Technical detail: <message>` in
> muted text. Pagination is implemented as client-side controls (Previous/Next, "Page X of Y",
> an optional 10/20/50 per-page `<select>`) driving the backend's paginated response; default
> `page=1`, `perPage=20`; changing the per-page selector resets `page` to 1 and refetches. Status
> filters apply to the currently fetched page only — backend `?status=` filtering remains a future
> enhancement. 5 s polling/auto-refresh for in-progress rows remains pending. File upload remains
> disabled. Document detail, delete, and retry remain pending. No automated test runner;
> verification is typecheck + browser check against a live stack.

- [x] Documents page sends `GET /admin/documents?page=1&per_page=20` on initial mount *(requires live backend — verifiable via browser DevTools Network tab)*
- [x] Request includes `Authorization: Bearer <token>` header; token attached by `apiClient`, no hardcoded value *(verifiable via browser DevTools)*
- [x] Backend documents render in the table with correct title/type/status/chunks/uploaded values *(requires live backend)*
- [x] Loading skeleton (5 rows, pulse animation) shown while `GET /admin/documents` is in flight *(verifiable via `npm run dev` with network throttled)*
- [x] API failure shows inline red "Could not load documents" panel with friendly message + `Technical detail:` in muted text; no silent fallback to mock data *(verifiable via `npm run dev` with backend stopped)*
- [x] Previous button is disabled on page 1 *(requires live backend)*
- [x] Next button is disabled once `page * perPage >= total` (last page) *(requires live backend)*
- [x] Changing the per-page selector resets to page 1 and refetches *(requires live backend)*
- [x] Status filters apply to the currently fetched page (client-side over the page already in memory) *(requires live backend)*

## Documents Page — Status & Polling

> **StatusBadge — shared component**: `StatusBadge` is a shared presentation component at
> `src/components/admin/StatusBadge.tsx`, used by both the list page (now wired to
> `GET /admin/documents` — see "List & Pagination" above) and the detail page
> (`documents/[id]/page.tsx`, which still renders hardcoded mock data). Verified via
> `npm run typecheck` + screenshot; no automated test runner is installed. Criteria below require
> 5 s polling (not yet implemented) and remain unchecked.

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

> **Client-side filter over the fetched page (current state)**: filter buttons apply to the
> documents already returned by the current `GET /admin/documents` page — no additional network
> request fires per filter click. See "List & Pagination" above for the fetch/pagination wiring.
> **API filter (future enhancement)**: re-fetches `GET /admin/documents?status=` on each selection.
> Update the filter criteria below to remove this note once backend `?status=` filtering is wired.
>
> **Actions column — current state**: "Detail" link is navigable and opens the now-wired detail
> page at `/admin/documents/{document_id}`, which fetches the real document by id (see "Document
> Detail Page" below). "Delete" and "Retry" are not yet implemented; completed/failed rows show
> only `Detail`, while pending/processing rows show `—`.

- [x] Filter by `failed` (client-side over fetched page) → table shows only failed documents; other statuses hidden *(requires live backend)*
- [ ] Filter by `failed` (backend `?status=`) → `GET /admin/documents?status=failed` fires; only failed rows returned from backend *(future enhancement — not yet wired)*
- [x] Pagination: navigating to page 2 loads the next page of rows from the backend — see "List & Pagination" above *(requires live backend)*
- [ ] Delete → confirmation dialog appears → confirm → row removed → success toast
- [ ] Delete → cancel → row remains; no API call fired
- [ ] Empty state renders when no documents exist

## Document Detail Page

> **`GET /admin/documents/{document_id}` wired.** `getDocumentApi(documentId)` in
> `src/lib/documentApi.ts` calls `apiRequest<DocumentOut>('GET', '/admin/documents/{document_id}')`
> through `apiClient` — Bearer token attached automatically; no hardcoded JWT or backend URL.
> `src/app/admin/documents/[id]/page.tsx` fetches on mount/route param via `useEffect`; shows a
> pulsing skeleton while loading; on failure shows an inline red panel with a status-specific
> friendly message (`classifyDetailError()`: 400/401/403/404/429/5xx/network) plus
> `Technical detail: <message>` in muted text — no mock fallback. On success renders `title`,
> `status` (via `StatusBadge`), `source_type`, `source_url` (a real link only when non-null; `—`
> when `null` — never a clickable link for a null value), `chunk_count` (`—` unless `completed`),
> `error_message` (red alert when `failed`), `created_at`, `id`, and `tenant_id` (shown for admin
> debugging). `pending`/`processing` show a blue "still in progress" notice instead of claiming
> completion. The Delete button remains disabled — `ConfirmDialog` and `DELETE` wiring remain
> pending. No automated test runner; verification is typecheck + browser check against a live stack.

- [x] Clicking "Detail" on the list page opens `/admin/documents/{document_id}` *(verifiable via `npm run dev`)*
- [x] Detail page sends `GET /admin/documents/{document_id}` on mount/route param load *(requires live backend — verifiable via browser DevTools Network tab)*
- [x] Request includes `Authorization: Bearer <token>` header attached automatically by `apiClient`; no hardcoded JWT or backend URL *(verifiable via browser DevTools / by reading source)*
- [x] Title, type, status badge, chunk count, upload timestamp, source, id, and tenant id all render with live data from `GET /admin/documents/{document_id}` *(requires live backend)*
- [x] `pending` status shows the blue "ingestion still in progress" notice *(requires live backend)*
- [x] `failed` status shows the red alert box with `error_message` above the delete button *(requires live backend)*
- [x] `completed` status shows the real `chunk_count` from the backend *(requires live backend)*
- [x] `source_url: null` renders as `—`, never as a clickable link; a non-null `source_url` renders as a real link *(requires live backend)*
- [x] API failure (e.g. 404 for an unknown id) shows the inline red "Could not load document" panel with friendly message + `Technical detail:` in muted text *(verifiable via `npm run dev` with backend stopped, or by visiting an unknown id with a live backend)*
- [ ] Delete → confirmation dialog → `DELETE /admin/documents/{id}` fires → redirect to `/admin/documents` → success toast *(not yet implemented)*

## Users Page

> **`GET /admin/users` wired + `POST /auth/register` create-user wired; deactivate remains pending.**
> Users page calls `GET /admin/users` via `listUsersApi()` on mount; renders backend `UserOut[]` in table.
> Invite drawer calls `POST /auth/register` via `createUserApi()` with `{ email, password, tenant_id, role }`.
> Bearer token attached automatically by `apiClient` (no hardcoded JWT; no direct DB access).
> `tenant_id` sourced from `authContext.user.tenant_id` — not a form field.
> `phone_number` is visible in drawer but disabled and NOT sent to backend (absent from `RegisterRequest`).
> Password sent to backend only; cleared after successful create; frontend never stores passwords; backend owns hashing.
> On success: returned `UserOut` prepended to table; drawer closes; form fields cleared.
> On create failure: inline red panel in drawer; drawer stays open.
> On list fetch failure: inline red panel above table; no silent fallback to mock data.
> Duplicate-user error handling relies on backend returning 409 or "already exists" in `detail`
> (409 not yet documented in `openapi.yaml`; error classification handles it opportunistically).
> Slack onboarding lookup is backend-owned; no frontend action.
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
