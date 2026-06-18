---
name: admin-ui-phase
description: >-
  Guide and validate work on the Admin Portal (M8). Loads module context,
  checks current implementation state against the spec, and produces or
  reviews admin-only frontend code. Use when building or reviewing anything
  under frontend/src/app/admin/ or frontend/src/components/admin/.
allowed-tools: >-
  Read, Edit, Write, Bash(npm run typecheck:*), Bash(npm run lint:*),
  Bash(npm run build:*), Bash(rg:*), Bash(find:*), Bash(grep:*)
---

# admin-ui-phase

Focused skill for the Admin Portal module (M8). Keeps work inside module
boundaries and ensures every change is consistent with the spec and
acceptance criteria.

## 1. Load context (always do this first)

Read these files before writing or reviewing any code:

1. `frontend/admin/CLAUDE.md` — module boundaries, rules, API base URL
2. `frontend/admin/ADMIN_UI_SPEC.md` — layouts, pages, component list, API calls
3. `frontend/admin/types/admin.ts` — TypeScript types; do not redefine inline
4. `frontend/admin/ADMIN_UI_PLAN.md` — find the first unchecked phase and work there

## 2. Scope guard

Before making any change, verify the target file path starts with:
- `frontend/src/app/admin/`
- `frontend/src/components/admin/`
- `frontend/admin/types/admin.ts` (the canonical type contract — import from here)
- `frontend/src/lib/` (shared utilities only — do not add admin-specific logic there)

If a requested change requires modifying `specs/openapi.yaml` or any
`backend/` file, **stop** and tell the user to raise it with M1 or the
relevant backend owner. Do not make cross-module edits.

## 3. Implementation rules

- **No RAG logic.** Parse, chunk, embed, and store run inside n8n. The
  frontend only polls `GET /admin/documents` and displays what the backend
  reports. Never simulate stage transitions on the client.
- **No `fetch` for file uploads.** Use `XMLHttpRequest` to get progress events.
- **Destructive actions require `ConfirmDialog`** before the API call fires:
  delete document, deactivate user, deactivate tenant.
- **`/admin/tenants` is `super_admin` only.** Render a 403 state for `admin`
  role — do not hide the nav item.
- **401 handling is global.** Clear the JWT cookie and redirect to
  `/login?next=<current-path>`. Handle this once in `apiClient.ts`, not per-call.
- **Types come from `frontend/admin/types/admin.ts`.** Import `DocumentOut`, `UserOut`, etc.
  from that file. If a new type is needed, add it there first. Do not duplicate types elsewhere.

## 4. After each phase

1. Run `npm run typecheck` — fix all TypeScript errors before marking done.
2. Run `npm run lint` — fix all ESLint errors.
3. Check the relevant acceptance criteria in `frontend/admin/ADMIN_UI_ACCEPTANCE.md`.
4. Mark completed tasks in `frontend/admin/ADMIN_UI_PLAN.md` with `[x]`.

## 5. Hard rules

- **Never edit** `frontend/src/app/chat/`, `frontend/src/app/onboarding/`,
  or `backend/` — those belong to M9, M13, and the backend team.
- **Never push** — commits are always the user's explicit step.
- **Never embed secrets** — API base URL goes in `NEXT_PUBLIC_API_URL`, not
  hardcoded.
