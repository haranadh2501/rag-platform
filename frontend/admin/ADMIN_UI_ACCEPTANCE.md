# ADMIN_UI_ACCEPTANCE.md — Admin Portal Acceptance Criteria

> Test against a live stack: `docker compose up -d` + backend (`uvicorn`) + frontend (`npm run dev`).
> Seed: `python -m app.scripts.seed_admin` creates `admin@example.com / changeme`.
>
> **No automated test runner is installed** (`package.json` has no jest/vitest/playwright/cypress).
> Current verification approach: `npm run typecheck` + `npm run lint` + `npm run build` + screenshot/manual review.
> End-to-end criteria below require a live stack and are not automatically tested.

## Auth & Route Guards
- [ ] `/admin/documents` without token → redirects to `/login?next=/admin/documents`
- [ ] Login as `admin` role → lands on `/admin/documents`
- [ ] Login as `user` role → `/admin/*` is inaccessible (redirect or 403)
- [ ] `/admin/tenants` as `admin` role → shows 403 state, not blank page or JS error

## Documents Page — Upload
- [ ] Upload a PDF ≤ 25 MB → row appears immediately with `pending` badge (no page refresh)
- [ ] Upload a file > 25 MB → rejected client-side; no network request fires
- [ ] Upload a `.exe` or other disallowed type → rejected client-side with error message
- [ ] XHR progress bar advances during upload; does not jump straight to 100 %
- [ ] "Add by URL" tab → submits to `POST /admin/documents/url`; new `pending` row appears

## Documents Page — Status & Polling
- [ ] `pending` → `processing` → `completed` transitions happen without page refresh
- [ ] `completed` row shows correct chunk count returned by backend (not a hardcoded value)
- [ ] `failed` row shows red X badge; `error_message` visible in tooltip
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

- [ ] Filter by `failed` (mock: client-side) → table shows only failed documents; other statuses hidden
- [ ] Filter by `failed` (live stack) → `GET /admin/documents?status=failed` fires; only failed rows returned from backend
- [ ] Pagination: navigating to page 2 loads the next 20 rows
- [ ] Delete → confirmation dialog appears → confirm → row removed → success toast
- [ ] Delete → cancel → row remains; no API call fired
- [ ] Empty state renders when no documents exist

## Document Detail Page
- [ ] Title, type, status badge, chunk count, upload timestamp, and source path all render
- [ ] `failed` status: red alert box with `error_message` is visible above the delete button
- [ ] Delete → confirmation → `DELETE /admin/documents/{id}` fires → redirect to `/admin/documents` → success toast

## Users Page
- [ ] All users in the tenant are listed with correct role pill colors (indigo/blue/slate)
- [ ] Logged-in user's own row has no Deactivate action
- [ ] Invite user: valid email + role → `POST /admin/users/invite` → new row appears at top → drawer closes
- [ ] Invite user: invalid email format → inline validation error; no API call

## Tenants Page
- [ ] `admin` role sees a 403 message, not a blank page or unhandled error
- [ ] `super_admin` sees the full tenant list
- [ ] Create Tenant modal → submit → new row appears in table
- [ ] Edit Tenant modal → fields pre-populated → save → row updates
- [ ] Deactivate → confirmation dialog → confirm → tenant marked inactive in table

## Settings Page
- [ ] Tenant name, slug (read-only), and plan badge render correctly for the logged-in tenant
- [ ] Channel status icons reflect backend configuration (grey = not configured)

## Polish
- [ ] Dark mode toggle switches theme; preference persists across page navigations
- [ ] Initial page load shows a skeleton, not a blank flash
- [ ] Killing the backend mid-session → error toast with the `detail` message from the response
- [ ] All buttons and links reachable and activatable by keyboard alone
- [ ] Sidebar hamburger appears at 375 px; all nav links are accessible
