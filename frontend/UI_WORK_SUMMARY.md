# UI Work Summary

Plain-language snapshot of what's actually implemented in the Admin Portal (M8) and
Chat Portal (M9) frontends, and what's still missing. Source of truth for details
remains `specs/MODULE_SPEC_M8.md` / `specs/MODULE_SPEC_M9.md` and the code itself.

No live browser/screenshot verification has been performed for any item below unless
explicitly stated otherwise — checks so far are `tsc --noEmit`, ESLint/build where the
Node version allowed it, and direct code review.

## M8 — Admin Portal

### Completed
- Auth: `POST /auth/login` wired, token in `localStorage` + in-memory `apiClient` store;
  `AuthGuard` redirects to `/login?next=<path>` when no token (no role check yet).
- Admin shell: sidebar + header layout, nav for Documents / Users / Tenants / Settings,
  Chat link to `/chat/new`.
- Users page: `GET /admin/users` list + `POST /auth/register` wired. Deactivate not wired.
- Documents list: `GET /admin/documents` with real pagination, status filters, loading
  and error states. No mock fallback.
- Add by URL: `POST /admin/documents/url` wired, with field validation and status-specific
  error messages.
- Document detail: `GET /admin/documents/{id}` wired, all fields rendered, in-progress and
  failed states shown. Delete button present but not wired.
- File upload: `POST /admin/documents/upload` wired via `XMLHttpRequest` (not `fetch`) for
  real progress, drag-and-drop, client-side type (`.pdf`/`.docx`/`.txt`) and 25 MB checks
  before sending, status-specific error messages.
- Documents page is mobile responsive: table becomes stacked cards below `md:`, the
  pipeline stepper has a compact vertical variant, upload/pagination controls stack on
  narrow screens.
- Status rendering: `StatusBadge` color-codes pending/processing/completed/failed;
  `PipelineStepper` shows ingestion stage.

### Known gaps
- Delete, retry, and 5-second status polling are not implemented — a completed
  transition currently needs a manual page refresh to show.
- Tenants and Settings pages are static placeholders (hardcoded "wired in Phase 6/7"
  text) — not connected to any backend endpoint.
- Toast notifications and a role-based 403 view for `/admin/tenants` are not implemented.
- Two backend issues found in an earlier audit, not yet fixed (owned by M3, not this
  frontend): `source_type` is hardcoded to `"url"` in `admin.py` regardless of actual
  MIME type, and an `"image"` source_type exists in the backend mapping but not in the
  OpenAPI/frontend enum.

## M9 — Chat Portal

### Completed
- `/chat` redirects to `/chat/new`.
- `/chat/new`: blank draft conversation; first message calls `POST /chat/query` with
  `conversation_id: null`. There is no `POST /chat/conversations` endpoint and nothing
  calls one.
- `/chat/[conversationId]`: loads history via `GET /chat/conversations/{id}`, then same
  send/retry behavior as `/chat/new`.
- Sidebar (`ConversationList`): lists conversations from `GET /chat/conversations`,
  highlights the active one, delete wired to `DELETE /chat/conversations/{id}`.
- Temporary draft row: while on `/chat/new` with no real conversation yet, the sidebar
  shows a "New conversation / Draft" row at the top, styled active. Pure client state —
  never sent to the backend.
- New Chat reset fix: clicking "New Chat" while already on `/chat/new` was a no-op
  (same-URL navigations don't fire). Fixed with a `?reset=N` query param in that case,
  used as a React `key` to force the draft to remount empty.
- Both `/chat/new` and `/chat/[conversationId]` wrap their `useSearchParams()`-dependent
  tree in `<Suspense fallback={null}>`, required by Next.js for production builds.
- Message list with Markdown rendering (`react-markdown` + `rehype-highlight`); code
  blocks and links are styled.
- Citations panel: collapsible per assistant message — source title, page number, score,
  chunk excerpt.
- Faithfulness badge: color-coded from `ChatQueryResponse.faithfulness`
  (grounded ≥0.85, partially grounded 0.7–0.85, low confidence <0.7).
- Clarification banner shown when `requires_clarification` is true.
- Follow-up chips: up to 3 clickable suggestions from `follow_up_questions`; clicking
  one sends it as the next query.
- Typing indicator with rotating status text; error state with a Retry button.
- Mobile: sidebar collapses behind a hamburger toggle below `md:`.
- Light/dark theme: `ChatThemeProvider` + `ChatThemeToggle`, scoped to the chat UI only
  (applies a `dark` class to a wrapper `div`, not `<html>`), persisted in `localStorage`.

### Known gaps
- No app-wide dark mode — only the Chat UI has a theme toggle; Admin UI has none.
- `next build` / `next dev` / `next lint` could not be run in the environment this work
  was done in (Node 18.16 installed, Next 14.2 requires ≥18.17), so the Suspense build
  fix is unverified end-to-end beyond following Next's documented pattern.
- The chat `vitest` suite also cannot run in that same environment (unrelated
  Node/`rolldown` incompatibility) — existing chat component tests were checked by
  reading, not executing.
- Conversation title generation is backend-owned; the frontend only displays whatever
  `title` comes back (falls back to "Untitled conversation").
- No search across conversations.
