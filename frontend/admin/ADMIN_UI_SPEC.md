# ADMIN_UI_SPEC.md — Admin Portal

> Owner: M8 · Files: `frontend/src/app/admin/` · `frontend/src/components/admin/`
> Stack: Next.js 14 · TypeScript · TailwindCSS · JWT (stateless Bearer token; `access_token` returned by `POST /auth/login`; stored in `localStorage` by `authContext`; hydrated on app load)
> Full platform context: `frontend/UI_SPEC.md`

---

## Routes

| Path | Page | Role |
|---|---|---|
| `/admin` | Redirects to `/admin/documents` | admin, super_admin |
| `/admin/documents` | Document list + upload | admin, super_admin |
| `/admin/documents/[id]` | Document detail + delete | admin, super_admin |
| `/admin/users` | User list + invite | admin, super_admin |
| `/admin/tenants` | Tenant list + manage | super_admin only |
| `/admin/settings` | Tenant info + channel status | admin, super_admin |

All routes are protected by `AuthGuard`. Unauthenticated requests redirect to `/login?next=<path>`. `super_admin`-only routes return a 403 page for `admin` role — do not hide the nav item; show it disabled with a lock icon.

---

## Shared Layout

```
┌──────────┬──────────────────────────────────────────────┐
│          │  Header: <Tenant Name>   [User ▾]  [Logout]  │
│ Sidebar  ├──────────────────────────────────────────────┤
│          │                                              │
│ Documents│  [Page content]                              │
│ Users    │                                              │
│ Tenants 🔒│                                              │
│ Settings │                                              │
│ Chat ───►│  (links to /chat/new; Chat UI is M9-owned)  │
│          │                                              │
│ Knowledge│                                              │
│ Base ───►│                                              │
└──────────┴──────────────────────────────────────────────┘
```

- Sidebar width: 240 px. Collapses to hamburger on < 768 px.
- Active nav item: `indigo-600` left border + background tint.
- **Chat nav item**: links to `/chat/new`; active state matches `/chat/*`; chat-bubble icon. M8 adds this navigation access point only — Chat UI is M9-owned. Users page does not embed chat.
- Sidebar bottom shows a "Knowledge Base" descriptor footer.

**Login redirect behavior (role-aware):**
- Safe `?next=<path>` param present → redirect to `next` (all roles).
- No safe `next` + `role === 'user'` → redirect to `/chat/new`.
- No safe `next` + `role === 'admin'` or `'super_admin'` → redirect to `/admin/documents`.

---

## Status Badge Colors

| Status | Tailwind | Icon |
|---|---|---|
| `pending` | `slate-400` | Filled dot |
| `processing` | `blue-500` | Spinning circle |
| `completed` | `emerald-500` | Filled dot |
| `failed` | `red-500` | X mark + `error_message` shown inline under the badge (list/table); dedicated red alert block above delete button (detail page) |

Poll `GET /admin/documents` every 5 s for rows in `pending` or `processing` state. Stop polling when all rows reach a terminal state.

---

## Documents Page (`/admin/documents`)

### Upload Area (top of page) — two tabs

**Upload File tab**
```
┌─────────────────────────────────────────────────────┐
│  📁  Drag & drop PDF, DOCX, or TXT                  │
│      or  [Browse files]                             │
│      Max 25 MB · 20 uploads/hour                    │
└─────────────────────────────────────────────────────┘
```
- Client-side MIME + size validation before sending. Reject > 25 MB immediately.
- Use `XMLHttpRequest` (not `fetch`) to stream upload progress as a progress bar per file.
- On submit: `POST /admin/documents/upload` (multipart). New row appears at table top with `pending` status.

**Add by URL tab** — required URL field + required Title field → sends `POST /admin/documents/url` to backend through `apiClient` via `src/lib/documentApi.ts`. "Add source" disabled when URL is invalid, title is empty, or a request is in flight. Bearer token attached automatically by `apiClient` from the in-memory store; no hardcoded JWT or backend URL.

> **Backend wiring** (`src/lib/documentApi.ts → ingestDocumentUrlApi() → apiRequest<DocumentOut>()`):
> Request body: `{ url: string, title: string }` (UI now requires both fields; `UrlIngestRequest`
> in openapi.yaml marks `title` optional at the schema level — frontend applies a stricter UX
> requirement, not a contract change). Backend validates the JWT, enforces tenant isolation, and
> triggers the n8n ingestion pipeline server-side. No direct browser → n8n call; no webhook URL in
> the browser bundle. Response: 202 `DocumentOut` — `id`, `tenant_id`, `title`, `source_type`,
> `source_url`, `status` (`"pending"`), `chunk_count`, `error_message`, `created_at` all come from
> the backend.
>
> **Accepted-state UX** (implemented): while the request is in flight, "Add source" button shows
> a spinner + "Submitting…" (disabled). On 202 response: "Request accepted" inline panel
> (`aria-live="polite"`) — "We have started ingesting this URL. It may take a few minutes before
> it appears as searchable knowledge." URL and title fields cleared. The returned `DocumentOut` is
> prepended to the table as an optimistic row (status always `pending` per the contract — never
> claimed as `completed`) while the page triggers a real refetch of `GET /admin/documents?page=1&per_page=<perPage>`
> (preferred over relying solely on the optimistic row, since the list API is already wired); once
> that refetch returns a persisted row with the same `id`, the optimistic copy is dropped. If the
> current filter would hide the new row, filter auto-switches to All on submit. On failure: "Could
> not submit URL" panel (`aria-live="assertive"`); no optimistic row inserted; button re-enables.
> Friendly message is status-specific via `classifyUrlError()` in `page.tsx`: 400 → "check the URL
> and title"; 401 → "session expired"; 403 → "no permission"; 404 → "Add by URL endpoint not
> available yet"; 409 → "document may already exist"; 422 → "URL or title invalid"; 429 → "too many
> requests"; 5xx → "service trouble"; network/CORS/no-response (`TypeError`) → "Could not reach the
> document service. Check backend availability or CORS." All cases include
> `Technical detail: <original message>` in muted sub-text. Direct n8n browser call is not part of
> the UI path; backend/CORS availability can block URL ingestion.
>
> **Optimistic row does not survive page refresh.** Row never auto-completes; completed status
> requires real backend data from `GET /admin/documents`. `n8nIngestionApi.ts` is kept for
> reference but is no longer imported by `documents/page.tsx`.

### Storage Quota Bar
```
Storage used:  ████████░░░░░░░  420 MB of 1 GB
```
Amber at 80 %, red at 95 %. Sourced from tenant metadata.

### Document Table

| # | Title | Type | Status | Chunks | Uploaded | Actions |
|---|---|---|---|---|---|---|
| 1 | Product Manual | PDF | ● Completed | 142 | 2 min ago | Detail · Delete |
| 2 | IT SOP Guide | DOCX | ⟳ Processing… | — | 30 s ago | — |
| 3 | Quick Start | URL | ● Pending | — | just now | — |
| 4 | Old Policy | TXT | ✕ Failed | — | 1 day ago | Retry · Delete |

> **List wiring (implemented)**: `documents/page.tsx` calls `listDocumentsApi({ page, perPage })`
> (`src/lib/documentApi.ts` → `apiRequest<DocumentList>('GET', '/admin/documents?page=&per_page=')`)
> on mount and whenever `page` or `perPage` changes. Bearer token is attached automatically by
> `apiClient` — no hardcoded JWT, no direct database access. The table renders backend-returned
> `DocumentOut[]` instead of mock data; there is no silent fallback to mock data on failure. While
> a request is in flight, the table body shows 5 pulsing skeleton rows. On failure, a red inline
> error panel appears above the table with a status-specific friendly message and
> `Technical detail: <message>` in muted text (401/403/404/429/5xx/network mapped by
> `classifyListError()`); the table area below keeps whatever was last successfully fetched (empty
> on a first-load failure).

- Filter bar: all / pending / processing / completed / failed.
  - **Current state**: client-side filter over the currently fetched page of backend documents; no
    additional network request fired per filter click. Status filtering is applied to the page
    already in memory until backend `?status=` filtering is wired in a later phase.
  - **Future**: calls `GET /admin/documents?status=<value>` and re-fetches from backend.
- Pagination: client-side controls (Previous / Next / per-page selector) drive the backend's
  paginated `GET /admin/documents?page=&per_page=` response. Default `page=1`, `perPage=20`;
  optional per-page selector offers 10/20/50 and resets `page` to 1 on change. Range text shows
  `"<start>-<end> of <total>"`; page text shows `"Page <page> of <totalPages>"`. Previous is
  disabled on page 1; Next is disabled once `page * perPage >= total`.
- "Chunks" column shows `—` while not yet `completed`.
- Actions column: "Detail" → `/admin/documents/[id]` for `completed`/`failed` rows (unchanged).
  "Delete" and "Retry" remain unwired/pending.
- Add by URL remains a separate flow from the list fetch: a successful submit still prepends a
  local optimistic row labelled as a status preview; it is not claimed as persisted until
  `GET /admin/documents` returns a document with the same `id` (at which point the optimistic
  copy is dropped in favor of the persisted row).
- 5 s polling for in-progress rows and auto-refresh remain pending (not implemented in this phase).
- Empty state: "No documents." row when the fetched page (filtered) has no rows. The richer
  illustration + "Upload your first document" CTA remains a future enhancement.

---

## Ingestion Pipeline Visibility

n8n executes all backend processing (parse, OCR, chunk, embed, store). The frontend **only displays** status reported by the backend — it must never imply it performs any of these steps itself.

Each document row shows a stage stepper derived from `DocumentOut.status`, `error_message`, and `chunk_count`.

> **Current mock state**: the stepper is always-visible beneath each row (no expand/collapse toggle). Expand/collapse interaction is a future phase enhancement.



```
uploaded → validated → parsed/OCR → chunked → embedded → stored
  ●──────────●──────────⟳──────────○──────────○──────────○
                         running
```

- **In progress**: spinning icon on the active stage; filled dots for completed stages; empty dots for future stages.
- **Failed**: active stage marker turns red; display "Failed at: &lt;stage&gt; — &lt;error_message&gt;" beneath the stepper.
- **Completed**: all dots filled green; display "&lt;chunk_count&gt; chunks · indexed &lt;created_at&gt;" beneath the stepper.

---

## Document Detail Page (`/admin/documents/[id]`)

```
┌──────────────────────────────────────────────────┐
│  ← Back to Documents                             │
│                                                  │
│  Product Manual                                  │
│  Type: PDF   Status: ● Completed   Chunks: 142   │
│  Uploaded: 2026-06-01 10:30                      │
│  Source: /uploads/product-manual.pdf             │
│                                                  │
│                           [Delete Document]      │
└──────────────────────────────────────────────────┘
```

- Fetched via `GET /admin/documents/{document_id}`.
- Delete button opens `ConfirmDialog`: "This will remove all N chunks from the knowledge base." On confirm: `DELETE /admin/documents/{document_id}` → redirect to `/admin/documents` with success toast.
- If `status === 'failed'`: show `error_message` in a red alert box above the delete button.

---

## Users Page (`/admin/users`)

> **Current state — `GET /admin/users` + `POST /auth/register` wired; deactivate pending.**
> `listUsersApi()` → `GET /admin/users`; `createUserApi(input)` → `POST /auth/register`.
> Both in `src/lib/userApi.ts`; Bearer token attached automatically by `apiClient` (no hardcoded
> JWT; no direct DB access from frontend; backend persists user in DB).
> `tenant_id` sourced from `authContext.user.tenant_id`; never a form field.
> `phone_number` visible in drawer but disabled and never sent — absent from `RegisterRequest`.
> Password sent to backend only; cleared after success; backend owns hashing.
> On success: returned `UserOut` prepended to table; drawer closes; form cleared.
> On create failure: inline red error panel in drawer; `classifyCreateError()` maps all status codes.
> Duplicate handling is best-effort — 409 not documented in `openapi.yaml`; frontend also checks
> "already exists"/"duplicate" keywords in `detail` for 400/422 responses.
> Slack onboarding is backend-owned; no frontend action.
> Deactivate remains pending.

### User Table

| Email | Role | Active | Joined | Actions |
|---|---|---|---|---|
| admin@example.com | Super Admin | ✓ | 15 Jan 2026 | — (current user) |
| alice@acme.com | Admin | ✓ | 10 Feb 2026 | Deactivate (disabled) |
| bob@acme.com | User | ✓ | 20 Mar 2026 | Deactivate (disabled) |
| charlie@acme.com | User | Inactive | 5 Apr 2026 | Deactivate (disabled) |

Role pills: `super_admin` = indigo · `admin` = blue · `user` = slate.
Current logged-in user's row: emerald "You" badge on email cell; Actions shows "—" (cannot self-deactivate).
All other rows: disabled "Deactivate" button, `title="API pending — wired in Phase 5 once blockers are resolved"`.
Empty state: "No users match the current filters." when search/filter produce no results.

**Filters (client-side over mock data):**
- Email search input: case-insensitive substring match on `user.email`.
- Role filter buttons: All / Super Admin / Admin / User; active button indigo-filled.
- Mock data notice above table references `GET /admin/users` (Phase 5).

### Invite User (slide-over drawer)

Fields (in order): email, phone_number (disabled — amber "Required by team · Schema pending"),
role (admin/user), tenant_id (read-only — shows `currentUser?.tenant_id` or fallback text),
password/temp-password.

Amber blocker notice inline (no "M1"/"M2" internal module names in user-facing copy).
Submit button: "Send invite — API pending" (disabled). Footer: `POST /admin/users/invite` wired in Phase 5.

```
  Email:         [____________________]
  Phone number:  [disabled — Required by team · Schema pending]
  Role:          [User ▾]
  Tenant:        [<tenant_id from JWT — read-only>]
  Password:      [••••••••]
  [Send invite — API pending]  ← disabled
```

Calls `POST /admin/users/invite` (Phase 5, blocked). On success: new row inserted at top of table, drawer closes, success toast fires.

> **Registration vs login**: There is no public self-service registration page in the admin portal.
> First-time users are provisioned by admins via this drawer; all users (first-time and returning)
> authenticate at `/login`. The admin portal does not display a "Create account" link.
>
> **Contract** (Auth.json + openapi.yaml): `POST /admin/users/invite` and `POST /auth/register` share
> the same `RegisterRequest` schema — `{ email, password, tenant_id, role? }`. Use
> `POST /admin/users/invite` for admin-portal provisioning. `tenant_id` is derived from the caller's
> JWT — not a drawer form field.
>
> **Implementation gaps — raise with the backend team before wiring Phase 5:**
> 1. **Password field**: `RegisterRequest` requires `password`; confirm whether backend auto-generates
>    a temporary password (not currently documented in openapi.yaml) or the drawer must add a field.
> 2. **`phone_number` blocker**: `RegisterRequest` has no `phone_number` field. Any requirement to
>    collect phone number in the invite form is blocked until `openapi.yaml` is updated.
> 3. **Duplicate-user 409**: No 409 response is defined for `/admin/users/invite` in `openapi.yaml`.
>    Backend must enforce unique email; frontend will surface the `detail` field from the error
>    response. Document the 409 shape before implementing inline error handling.
> 4. **No plaintext passwords**: frontend must never store or log passwords; backend owns hashing.
> 5. **Tenant-scope guard**: a non-`super_admin` caller passing a different `tenant_id` receives 403
>    (documented in Auth.json cross-tenant test). Frontend derives `tenant_id` from JWT, so this
>    guard is for backend enforcement only — no frontend deduplication needed.

---

## Tenants Page (`/admin/tenants`) — super_admin only

| Tenant | Slug | Plan | Active | Created | Actions |
|---|---|---|---|---|---|
| Acme Corp | acme-corp | Free | ✓ | 2026-06-01 | Edit |
| Beta Co | beta-co | Pro | ✓ | 2026-05-30 | Edit · Deactivate |

- "Create Tenant" button → modal with Company Name, Slug, Plan → `POST /admin/tenants`.
- Edit → modal → `PATCH /admin/tenants/{id}` (name, plan, is_active).
- Deactivate → `ConfirmDialog` first → `PATCH` with `is_active: false`. Deactivated tenants' users cannot log in.
- `GET /admin/tenants` — super_admin JWT required; 403 returned for lesser roles.

---

## Settings Page (`/admin/settings`)

- Tenant info card: name, slug (read-only), plan badge.
- Channel status row: Web ✓ · WhatsApp (grey if unconfigured) · Slack (grey if unconfigured).
- Rate limits: "20 uploads / hour per tenant" as informational text.
- No editable fields in MVP beyond what PATCH /admin/tenants supports.

---

## Component List

| Component | Responsibility |
|---|---|
| `AdminLayout` | Sidebar + header shell, `AuthGuard` wrapper |
| `AuthGuard` | Redirects to `/login?next=<path>` when no localStorage token; spinner while hydrating |
| `StatusBadge` | Renders all four ingestion states with correct color and icon |
| `DocumentTable` | Paginated list with filter bar and 5 s polling |
| `DocumentUploadPanel` | Tabbed drag-drop / URL form with progress bar |
| `StorageQuotaBar` | Tenant storage progress bar with color thresholds |
| `UserTable` | User list with role pills |
| `InviteUserDrawer` | Slide-over invite form |
| `TenantTable` | Tenant list (super_admin guard) |
| `TenantModal` | Create / edit tenant form |
| `ConfirmDialog` | Reusable confirmation modal for all destructive actions |

---

## API Calls Summary

| Action | Method + Endpoint |
|---|---|
| **Auth** | |
| Login | `POST /auth/login` → `{ access_token, token_type, user }` |
| Current user + role | `GET /auth/me` → `UserOut` (needed for role-based guards + header) |
| Logout | `POST /auth/logout` (blacklists JWT server-side) |
| **Documents** | |
| List documents | `GET /admin/documents?status=&page=&per_page=` |
| Upload file | `POST /admin/documents/upload` (multipart) |
| Ingest URL | `POST /admin/documents/url` |
| Document detail | `GET /admin/documents/{id}` |
| Delete document | `DELETE /admin/documents/{id}` |
| **Users** | |
| List users | `GET /admin/users` |
| Invite / register user | `POST /admin/users/invite` → `RegisterRequest { email, password, tenant_id, role? }` → `UserOut` (201); also at `POST /auth/register` (Auth.json, same schema, admin-gated). No `phone_number` in schema (blocker). No 409 for duplicate email documented (blocker). |
| **Tenants** | |
| List tenants | `GET /admin/tenants` |
| Create tenant | `POST /admin/tenants` |
| Edit tenant | `PATCH /admin/tenants/{id}` |

All requests send `Authorization: Bearer <token>`. 401 → logout + redirect to `/login`. 429 → toast: "Upload limit reached (20/hour). Try again later."

> **Auth + user context + logout wired; URL ingestion wired (demo mode) with accepted-state UX; document list/detail/file-upload remain mock.**
> `POST /auth/login` wired in `src/app/login/page.tsx` via `src/lib/authApi.ts`.
> Login calls `useAuth().login(access_token, user)` — `authContext` stores both `access_token` and
> the full `UserOut` (`user_context` key) in `localStorage`. Admin header shows live data from that
> context: email initial (avatar), role badge, `tenant_id` prefix, and a "Sign out" button.
> `POST /auth/logout` wired via `logoutApi()` in `src/lib/authApi.ts`; header button calls
> `apiRequest<{ message?: string }>('POST', '/auth/logout')` with the current Bearer token
> (from apiClient in-memory store — no hardcoded JWT). On success or failure, `authContext.logout()`
> clears both localStorage keys and the in-memory store, then `router.replace('/login')` redirects.
> Local auth is always cleared even if the backend logout request fails.
> Add by URL now calls `POST /admin/documents/url` via `src/lib/documentApi.ts` →
> `apiRequest<DocumentOut>('POST', '/admin/documents/url', { url, title? })`. Bearer token
> attached automatically by `apiClient`; backend owns JWT validation, tenant isolation, and
> n8n trigger. No direct browser → n8n call; `n8nIngestionApi.ts` no longer imported in
> `documents/page.tsx` (file kept for reference). Response 202 `DocumentOut` fields populate
> the optimistic row directly (real `id`, `title`, `status`, etc.). Accepted-state UX is
> implemented: spinner + "Submitting…" while in-flight; "Request accepted" panel on 202;
> optimistic row starts with backend status; if `pending`, local 1500 ms timer advances to
> `processing` for demo feedback (NOT correlated with n8n progress); "Could not submit URL"
> panel on failure with status-specific friendly message + technical detail; no row inserted on
> failure; direct n8n browser call is not part of the UI path; backend/CORS availability can
> block URL ingestion.
> Row never auto-completes; completed status requires real data from `GET /admin/documents`.
> **`GET /admin/documents` list wiring (implemented)**: `listDocumentsApi({ page, perPage })` in
> `src/lib/documentApi.ts` calls `apiRequest<DocumentList>('GET', '/admin/documents?page=&per_page=')`.
> Bearer token attached automatically by `apiClient`. `documents/page.tsx` fetches on mount and on
> every `page`/`perPage` change; renders backend `DocumentOut[]` (no mock fallback); shows a 5-row
> pulsing skeleton while loading; shows a red inline error panel with friendly message +
> `Technical detail:` on failure. Pagination is implemented as client-side controls (Previous/Next,
> page-of-total display, optional 10/20/50 per-page selector that resets to page 1) driving the
> backend's paginated response. Status filters apply to the currently fetched page only — backend
> `?status=` filtering is a future enhancement. 5 s polling/auto-refresh for in-progress rows
> remains pending. File upload remains disabled. Document detail, delete, and retry remain pending.
> No automated test runner; verified via typecheck + browser check against live backend.
> User data is localStorage-sourced only — `GET /auth/me` wiring pending.
> `AuthGuard` protects `/admin/*` by localStorage token presence (no backend verification per request).
> Document detail, file upload, delete, retry, and all user/tenant/settings pages remain
> mock/placeholder. `401 → logout + redirect` in `apiClient.ts` remains a TODO. `GET /auth/me`,
> role guards, and Tenants 403 remain pending.
> No automated test runner; verified via typecheck + browser check.

---

## Error States

| Scenario | Treatment |
|---|---|
| No documents yet | Empty state illustration + "Upload your first document" CTA |
| `status: failed` in table | Red badge, `error_message` shown inline under the badge, "Retry" action |
| `status: failed` on detail page | Red alert box with `error_message` above delete button |
| Storage at 95 %+ | Quota bar turns red; upload button shows warning tooltip |
| 403 on Tenants page | Full-page "Access restricted — super_admin only" message |
| Network error on any action | Error toast with the response `detail` field |
