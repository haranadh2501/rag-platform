# MODULE_SPEC_M8 — Frontend: Admin Portal

**Owner**: Member 8 | **Track**: Frontend | **Branch**: `feat/admin-ui`

> **Implementation source of truth**: `frontend/admin/ADMIN_UI_SPEC.md`.
> This spec file gives the high-level overview; all page layouts, component contracts,
> API call shapes, and acceptance criteria live in `frontend/admin/ADMIN_UI_SPEC.md`.
> When this file and `ADMIN_UI_SPEC.md` conflict, `ADMIN_UI_SPEC.md` wins.

## Role
Next.js admin dashboard: login, document upload, document management, user management, tenant settings.

## Day-by-Day Deliverables
| Day | Deliverable | Done? |
|---|---|---|
| 1 | Set up Next.js 14 + TailwindCSS + project structure. Branch. | ☐ |
| 2 | API client (`src/lib/apiClient.ts`) — manual fetch wrapper implemented; codegen skipped (see API Client Setup note below) | ☑ |
| 2 | `authContext.tsx` done — localStorage hydration, login/logout, AuthProvider wraps layout | ☑ |
| 2 | Login page (`/login`) placeholder — inputs + disabled button; `POST /auth/login` wiring pending | ☑ |
| 2 | Wire login page to `POST /auth/login` → `authContext.login(token, user)` → redirect `/admin` | ☑ |
| 2 | `AuthGuard` shell — redirects to `/login?next=<path>` when no localStorage token; localStorage-only check; no role checks | ☑ |
| 2 | Admin layout: sidebar (Documents, Users, Tenants) + header | ☐ |
| 2 | Document upload page: drag-drop + URL input form | ☐ |
| 3 | Document list page: table with status badges (pending/processing/completed/failed) | ☐ |
| 3 | Document detail page: metadata, chunk count, delete button | ☐ |
| 4 | Wire login flow: `POST /auth/login` via `authApi.ts` → `localStorage` + `setAuthToken()` → redirect (Auth.json contract; login page only) | ☑ |
| 4 | Wire URL ingestion: Add by URL tab → `n8nIngestionApi.ts` → n8n webhook (demo mode); `NEXT_PUBLIC_N8N_INGEST_WEBHOOK_URL` + `NEXT_PUBLIC_DEMO_TENANT_ID` in `.env.example`; accepted-state UX with optimistic pending→processing local demo transition. **Superseded by backend API wiring below.** | ☑ |
| 4 | Wire Add by URL to backend API: `src/lib/documentApi.ts` → `ingestDocumentUrlApi({ url, title? })` → `apiRequest<DocumentOut>('POST', '/admin/documents/url', body)`; Bearer token attached automatically by `apiClient`; no direct browser → n8n call; `n8nIngestionApi.ts` no longer imported in `documents/page.tsx` (kept for reference); backend owns JWT validation, tenant isolation, and n8n trigger; response 202 `DocumentOut` fields populate the optimistic row; if backend returns `pending`, local 1500 ms `setTimeout` advances row to `processing` for demo feedback (NOT correlated with actual n8n progress); completed status requires real `GET /admin/documents` data; `GET /admin/documents` polling/list refresh remains pending | ☑ |
| 4 | URL ingestion error UX polish: `classifyUrlError(err)` in `page.tsx` maps `ApiError.status` to friendly messages (401/403/404/429/5xx) and maps network/CORS `TypeError` to "could not reach service"; all paths include `Technical detail: <message>` in muted sub-text; `urlError` state is now `{ message, detail } \| null`; no optimistic row inserted on failure; button re-enables; `aria-live="assertive"` preserved; `ApiError` imported from `apiClient.ts`; direct n8n browser call not in UI path; backend/CORS availability can block URL ingestion | ☑ |
| 4 | Wire document pages to real backend (`GET /admin/documents`, file upload, detail, delete) — separate from URL ingest wiring | ☐ |
| 5 | User management page: `GET /admin/users` + `POST /auth/register` wired; deactivate pending | ☑ |
| 5 | Chat nav item in Admin sidebar → `/chat/new`; active on `/chat/*`; login redirects `user` role to `/chat/new` | ☑ |
| 5 | Polish: loading states, error handling, toast notifications | ☐ |
| 6 | Responsive design, final UI review | ☐ |

## Files Owned
- `frontend/src/app/admin/`
- `frontend/src/components/admin/`

## Key Pages
```
/login                → login form (shared route — not under /admin)
/admin/documents      → document list with upload button
/admin/documents/[id] → document detail
/admin/users          → user list + invite
/admin/tenants        → tenant list (super_admin only)
/admin/settings       → tenant settings
```

## API Client Setup

> **Implemented as a manual fetch wrapper** — codegen was skipped.
> `src/lib/apiClient.ts` exports `apiRequest<T>()`, `ApiError`, `setAuthToken`, and `getAuthToken`.
> The codegen command below is the original plan; it can still be run to generate typed stubs from
> the OpenAPI spec, but the manual client is the active implementation and should not be overwritten.

```bash
# Original codegen plan (not executed — manual client used instead):
npx openapi-typescript-codegen \
  --input ../specs/openapi.yaml \
  --output src/lib/api \
  --client axios
```

## Registration Endpoint

> **Endpoint confirmed** (Auth.json + openapi.yaml): `POST /auth/register` (Auth.json) and
> `POST /admin/users/invite` (openapi.yaml) both exist and share `RegisterRequest`:
> `{ email, password, tenant_id, role? }`. Both are **admin-gated** (require Bearer token) —
> not a public self-service signup. Use `POST /admin/users/invite` from the admin portal.
>
> **First-time vs returning user**: There is no registration page for end users. First-time users
> are provisioned by admins via the Invite User drawer. All users (first-time and returning)
> authenticate at `/login`.
>
> **Backend-owned rules** (frontend must not replicate these):
> - Unique email enforcement — backend rejects duplicates
> - Password hashing — frontend never stores or transmits a hashed password; sends plaintext over TLS; backend hashes on receipt
> - Tenant-scope guard — 403 if caller passes a `tenant_id` that does not match their own (non-`super_admin`)
> - Slack onboarding lookup by email — backend responsibility; not a frontend concern
>
> **Implementation blockers** (must be resolved with M1/M2 before Phase 5 wiring):
> 1. `phone_number` not in `RegisterRequest` → raise with M1 to update `openapi.yaml`
> 2. 409 response for duplicate email not defined in `openapi.yaml` → raise with M1/M2
> 3. `password` required by schema but absent from current drawer UX spec → confirm auto-generate vs. form field with M2

## Auth Context

> **Auth strategy resolved**: stateless `Authorization: Bearer` on every request.
> `POST /auth/login` returns `access_token` in the JSON body; `authContext` stores it in
> `localStorage` (key: `access_token`) and calls `setAuthToken()` from `src/lib/apiClient.ts`.
> On app load `authContext` reads `localStorage` and hydrates the token. No httpOnly cookie
> or Next.js `/api/auth/callback` proxy needed.

```typescript
// src/lib/authContext.tsx  (IMPLEMENTED)
// On login: POST /auth/login → localStorage.setItem('access_token', token)
//           + localStorage.setItem('user_context', JSON.stringify(user)) → setAuthToken(token)
// On mount: hydrates token + UserOut from localStorage; JSON.parse failure discards user silently
// Provides useAuth() hook: { token, user: UserOut | null, isAuthenticated, isHydrated, login(token, user), logout }
// On logout (authContext.logout): removes 'access_token' + 'user_context' → setAuthToken(null)
//   NOTE: redirect is NOT done inside logout() — caller (AdminShellLayout.handleLogout) owns redirect.
// Logout flow (AdminShellLayout, admin/layout.tsx):
//   1. logoutApi() → POST /auth/logout with Bearer token (from apiClient in-memory store; no hardcoded JWT)
//   2. try/catch/finally → authContext.logout() + router.replace('/login') always execute
//   3. Backend logout failure (network/401/5xx) does NOT prevent local auth clear or redirect
// On 401: apiClient throws ApiError(401); authContext/AuthGuard handles redirect to /login (TODO)
// Admin header: avatar initial from user.email, role badge from user.role, tenant pill from user.tenant_id
//               + "Sign out" button wired to handleLogout (disabled + spinner while in-flight)
// User data sourced from POST /auth/login response; NOT verified against backend on each request.
// GET /auth/me wiring is a pending phase. Role guards and Tenants 403 are pending.
```

## Document Status Badge Colors
```typescript
const statusColors = {
  pending: 'slate',      // slate-400 — filled dot
  processing: 'blue',    // blue-500 — spinning circle
  completed: 'emerald',  // emerald-500 — filled dot
  failed: 'red',         // red-500 — X mark + error_message
}
```

## Acceptance Criteria
- [ ] Login with `admin@example.com` (seed data) works
- [ ] Upload PDF → status shows `processing` → updates to `completed`
- [ ] Document list paginated with real data from backend
- [ ] Delete document removes it from list
- [ ] Invite user form posts to `POST /admin/users/invite` *(blocked — see Registration Endpoint note below)*
- [ ] Unauthorized access redirects to login
- [ ] Loading spinners during API calls
- [ ] Error toast on API failure


---
<!-- AUTO-APPENDED:SKILLS-V1 -->
## Skills Required
- **Must-have:** Next.js 14 App Router, TypeScript, TailwindCSS, React hooks, JWT in localStorage/cookies, file upload UX, drag-and-drop.
- **Nice-to-have:** SWR or TanStack Query, shadcn/ui, optimistic updates, openapi-typescript codegen.

## Detailed Step-by-Step Plan
### Day 1 — Scaffold
1. `cd frontend && npm install`. Confirm `npm run dev` opens http://localhost:3000.
2. Generate API client: `npx openapi-typescript ../specs/openapi.yaml -o src/types/api.ts`.
3. Branch `feat/admin-ui`.
4. Create `src/lib/api.ts`: `fetch` wrapper that auto-attaches `Bearer `.

### Day 2 — Auth Pages
5. `app/login/page.tsx`: placeholder created (inputs + disabled button). Full wiring pending:
   POST /auth/login → `authContext.login(token)` (stores in `localStorage` + calls `setAuthToken`) → redirect to `/admin/documents`.
6. `app/admin/layout.tsx`: sidebar done. `AuthGuard` shell done — redirects to `/login?next=<path>`
   when no localStorage token; no role checks yet. Role-based guards require `GET /auth/me` (see step 5 above).

### Day 3 — Document Upload + List
7. `app/admin/documents/page.tsx`: drag-drop zone (use `react-dropzone`) → multipart POST /admin/documents/upload → optimistic row insert.
8. Status badges: pending (slate-400) / processing (blue-500 spinner) / completed (emerald-500) / failed (red-500 X). Poll every 5 sec for pending/processing rows.
9. Add second tab "Add by URL" → JSON POST /admin/documents/url.

### Day 4 — Users + Tenants Mgmt
10. `app/admin/users/page.tsx`: table of users, role dropdown (super_admin/admin/user), invite-user modal.
11. `app/admin/tenants/page.tsx`: list tenants, create/edit modal, show usage (storage_used_bytes / 1 GB cap).

### Day 5 — Settings + Polish
12. `app/admin/settings/page.tsx`: API keys section (masked, copy button), rate-limit display.
13. Dark mode toggle (TailwindCSS `dark:` classes + `next-themes`).
14. Mobile responsive review.

### Day 6 — Deploy + Tests
15. Push to `main` → Vercel auto-deploys (M7 set this up).
16. Cypress or Playwright smoke test: login → upload → see document in list.

> **Current state — no test runner installed.** `package.json` has no jest/vitest/playwright/cypress.
> Verification is `npm run typecheck` + `npm run lint` + `npm run build` + screenshot/manual review.
> Install a test runner before implementing step 16.

## Learning Resources
- Next.js App Router: https://nextjs.org/docs/app
- TailwindCSS: https://tailwindcss.com/docs/installation
- openapi-typescript: https://github.com/drwpow/openapi-typescript
- shadcn/ui: https://ui.shadcn.com
