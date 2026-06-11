# ADMIN_UI_SPEC.md — Admin Portal

> Owner: M8 · Files: `frontend/src/app/admin/` · `frontend/src/components/admin/`
> Stack: Next.js 14 · TypeScript · TailwindCSS · JWT (httpOnly cookie)
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
│          │                                              │
│ Knowledge│                                              │
│ Base ───►│                                              │
└──────────┴──────────────────────────────────────────────┘
```

- Sidebar width: 240 px. Collapses to hamburger on < 768 px.
- Active nav item: `indigo-600` left border + background tint.
- Sidebar bottom shows a "Knowledge Base" descriptor footer (static text — no Chat nav link).

---

## Status Badge Colors

| Status | Tailwind | Icon |
|---|---|---|
| `pending` | `slate-400` | Filled dot |
| `processing` | `blue-500` | Spinning circle |
| `completed` | `emerald-500` | Filled dot |
| `failed` | `red-500` | X mark + tooltip with `error_message` |

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

**Add by URL tab** — URL field + optional Title → `POST /admin/documents/url` (JSON). Same optimistic row behavior.

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

- Filter bar: all / pending / processing / completed / failed — calls `GET /admin/documents?status=`.
- Pagination: 20 rows/page (`GET /admin/documents?page=&per_page=20`).
- "Chunks" column shows `—` while not yet `completed`.
- Actions column: "Detail" → `/admin/documents/[id]`. "Delete" opens `ConfirmDialog`. "Retry" re-posts the same document to upload endpoint.
- Empty state: illustration + "Upload your first document" CTA.

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

### User Table

| Email | Role | Active | Joined | Actions |
|---|---|---|---|---|
| admin@acme.com | Admin | ✓ | 2026-06-01 | — |
| user@acme.com | User | ✓ | 2026-06-01 | Deactivate |

Role pills: `super_admin` = indigo · `admin` = blue · `user` = slate.
Current user row has no actions (cannot self-deactivate).

### Invite User (slide-over drawer)
```
  Email:  [____________________]
  Role:   [User ▾]
  [Send Invite]
```
Calls `POST /admin/users/invite`. On success: new row inserted at top of table, drawer closes, success toast fires.

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
| List documents | `GET /admin/documents?status=&page=&per_page=` |
| Upload file | `POST /admin/documents/upload` (multipart) |
| Ingest URL | `POST /admin/documents/url` |
| Document detail | `GET /admin/documents/{id}` |
| Delete document | `DELETE /admin/documents/{id}` |
| List users | `GET /admin/users` |
| Invite user | `POST /admin/users/invite` |
| List tenants | `GET /admin/tenants` |
| Create tenant | `POST /admin/tenants` |
| Edit tenant | `PATCH /admin/tenants/{id}` |

All requests send `Authorization: Bearer <token>`. 401 → logout + redirect to `/login`. 429 → toast: "Upload limit reached (20/hour). Try again later."

---

## Error States

| Scenario | Treatment |
|---|---|
| No documents yet | Empty state illustration + "Upload your first document" CTA |
| `status: failed` in table | Red badge, `error_message` in tooltip, "Retry" action |
| `status: failed` on detail page | Red alert box with `error_message` above delete button |
| Storage at 95 %+ | Quota bar turns red; upload button shows warning tooltip |
| 403 on Tenants page | Full-page "Access restricted — super_admin only" message |
| Network error on any action | Error toast with the response `detail` field |
