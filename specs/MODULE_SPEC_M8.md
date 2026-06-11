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
| 2 | Login page + JWT auth context (cookie storage) | ☐ |
| 2 | Admin layout: sidebar (Documents, Users, Tenants) + header | ☐ |
| 2 | Document upload page: drag-drop + URL input form | ☐ |
| 3 | Document list page: table with status badges (pending/processing/completed/failed) | ☐ |
| 3 | Document detail page: metadata, chunk count, delete button | ☐ |
| 4 | Wire to real backend: login flow + protected routes + real data | ☐ |
| 5 | User management page: list users, invite form | ☐ |
| 5 | Polish: loading states, error handling, toast notifications | ☐ |
| 6 | Responsive design, final UI review | ☐ |

## Files Owned
- `frontend/src/app/admin/`
- `frontend/src/components/admin/`

## Key Pages
```
/admin/login          → login form
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

## Auth Context

> **Open question — auth storage mechanism unresolved.** `CLAUDE.md` says "read from httpOnly
> cookie", but httpOnly cookies are inaccessible to JavaScript; `Authorization: Bearer` requires a
> JS-readable token. `openapi.yaml` `LoginResponse` returns `access_token` in the JSON body.
> The `/api/auth/callback` route pattern below is one possible approach but was never agreed on.
> Confirm with M1/M2 before implementing `authContext.tsx`.

```typescript
// src/lib/authContext.tsx  (not yet implemented — pending auth storage decision)
// Will call setAuthToken(token) from apiClient.ts on login
// Provide useAuth() hook: { user, role, login, logout }
// Redirect to /login (path TBD) if not authenticated
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
- [ ] Invite user form posts to `POST /admin/users/invite`
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
5. `app/login/page.tsx`: email+password form → POST /auth/login → store token → redirect /admin.
6. `app/admin/layout.tsx`: sidebar (Documents, Users, Tenants, Settings) + AuthGuard HOC redirecting to /login if no token.

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
