# ADMIN_UI_ACCEPTANCE.md — Admin Portal Acceptance Criteria

> Test against a live stack: `docker compose up -d` + backend (`uvicorn`) + frontend (`npm run dev`).
> Seed: `python -m app.scripts.seed_admin` creates `admin@example.com / changeme`.
>
> **No automated test runner is installed** (`package.json` has no jest/vitest/playwright/cypress).
> Current verification approach: `npm run typecheck` + `npm run lint` + `npm run build` + screenshot/manual review.
> End-to-end criteria below require a live stack and are not automatically tested.

## Auth & Route Guards

> **Login wired; AuthProvider at root; AuthGuard active; document pages still mock.**
> `POST /auth/login` is wired in `src/app/login/page.tsx` via `src/lib/authApi.ts` (contract: Auth.json + openapi.yaml). On success the page calls `useAuth().login(access_token)` — `authContext` is the single place that writes `localStorage` and updates the in-memory apiClient store; no direct `localStorage` writes exist outside `authContext`. `AuthProvider` now lives in root `layout.tsx` (wraps all routes, including `/login`). `AuthGuard` redirects `/admin/*` to `/login?next=<path>` when no token is in `localStorage`. Token is **not verified against the backend** on each request — localStorage presence only. Role checks and the Tenants 403 state are not implemented. `apiClient.ts` 401 → redirect remains a TODO. All document, user, tenant, and settings pages remain mock/placeholder. No automated test runner; verification is typecheck + lint + build + browser check.

- [x] `/admin/documents` without token → redirects to `/login?next=/admin/documents` *(manual browser check — AuthGuard shell active)*
- [ ] Login as `admin` role → lands on `/admin/documents` *(requires live backend)*
- [ ] Login as `user` role → `/admin/*` is inaccessible (redirect or 403) *(requires role checks — not yet implemented)*
- [ ] `/admin/tenants` as `admin` role → shows 403 state, not blank page or JS error *(requires role checks — not yet implemented)*

## Login Page (`/login`)

> **Wired — manual browser checks required for live-stack criteria.**
> `src/app/login/page.tsx` calls `POST /auth/login` via `src/lib/authApi.ts`. On success:
> calls `useAuth().login(access_token)` — `authContext` writes `localStorage` and updates the
> apiClient in-memory store (single write point); redirects to `?next` path (if safe) or
> `/admin/documents`. On 401: inline "Invalid email or password" error; no token stored. Button
> disabled until both fields are non-empty; `aria-live` error region for screen readers.
> Auth contract sourced from Auth.json (Postman) and confirmed against `specs/openapi.yaml`.
> No automated test runner; verification is typecheck + lint + build + browser check against live stack.

- [x] Valid credentials → `POST /auth/login` → `access_token` in `localStorage` → redirect *(manual browser check with live backend)*
- [x] Invalid credentials → inline "Invalid email or password" error; no redirect; no token stored *(manual browser check)*
- [x] Empty form → Sign in button disabled; no API call fires *(verifiable via `npm run dev`)*

## Documents Page — Upload
- [ ] Upload a PDF ≤ 25 MB → row appears immediately with `pending` badge (no page refresh)
- [ ] Upload a file > 25 MB → rejected client-side; no network request fires
- [ ] Upload a `.exe` or other disallowed type → rejected client-side with error message
- [ ] XHR progress bar advances during upload; does not jump straight to 100 %
- [ ] "Add by URL" tab → submits to `POST /admin/documents/url`; new `pending` row appears

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
- [ ] All users in the tenant are listed with correct role pill colors (indigo/blue/slate)
- [ ] Logged-in user's own row has no Deactivate action
- [ ] Invite user: valid email + role → `POST /admin/users/invite` → new row appears at top → drawer closes
- [ ] Invite user: invalid email format → inline validation error; no API call

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
