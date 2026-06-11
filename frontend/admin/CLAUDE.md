# CLAUDE.md — Admin Portal (M8)

> Read this before touching any file under `frontend/src/app/admin/` or `frontend/src/components/admin/`.

## Scope

This module is the Admin Portal only. Do not edit Chat UI, Onboarding, or any backend file.

## Files You Own

- `frontend/src/app/admin/` — Next.js App Router pages
- `frontend/src/components/admin/` — Admin-specific React components
- `frontend/admin/types/admin.ts` — canonical TypeScript types for this module; imported via the `@admin-types` path alias

## Files You Must Not Touch

| Path | Owner |
|---|---|
| `frontend/src/app/chat/`, `frontend/src/components/chat/` | M9 |
| `frontend/src/app/onboarding/` | M13 |
| `backend/` | M2/M3/M4 |
| `specs/openapi.yaml` | M1 — raise a PR to change |

## Read First

1. `frontend/admin/ADMIN_UI_SPEC.md` — layouts, pages, components, API calls
2. `frontend/admin/types/admin.ts` — all TypeScript types; do not redefine them inline
3. `specs/openapi.yaml` — the API contract; request/response shapes must match exactly

## Key Rules

- All API calls attach `Authorization: Bearer <token>` read from the httpOnly cookie.
- A `401` response clears the token and redirects to `/login?next=<current-path>`.
- Parse, chunk, embed, and store are executed by n8n — never call, simulate, or imply these from the frontend.
- Ingestion progress is displayed from `DocumentOut.status`, `error_message`, and `chunk_count` polled via `GET /admin/documents` every 5 s. Stop polling when all visible rows reach `completed` or `failed`.
- Every destructive action (delete document, deactivate tenant or user) requires a `ConfirmDialog` before the API call fires.
- `/admin/tenants` must render a 403 state for the `admin` role — do not hide the nav item; show it disabled with a lock icon.
- File uploads use `XMLHttpRequest` (not `fetch`) to expose upload progress events.

## API Base URL

`process.env.NEXT_PUBLIC_API_URL` (default: `http://localhost:8000`)
