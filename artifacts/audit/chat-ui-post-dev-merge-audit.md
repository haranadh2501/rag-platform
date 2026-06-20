# Chat UI — Post Dev-Merge Audit

**Date:** 2026-06-18
**Branch:** `feat/chat-ui`
**Scope:** Read-only. No files edited. No previous audit found at `artifacts/audit/chat-ui-exhaustive-audit.md` — `artifacts/audit/` was empty, so this is the first audit on record for this module.

## 1. Current frontend structure (post Admin-UI merge)

```
frontend/
├── package.json                          # next 14.2, react 18.3, tailwind 3.4 — no markdown/zustand deps yet
├── tailwind.config.ts                     # darkMode: 'class' (configured, unused so far)
├── tsconfig.json                          # paths: "@/*" → src/*, "@admin-types" → admin/types/admin
├── admin/                                 # SIBLING to src/ — M8's canonical types + specs, outside src/
│   ├── types/admin.ts                     # canonical TS types for admin, source of truth = openapi.yaml
│   ├── ADMIN_UI_SPEC.md / _PLAN.md / _ACCEPTANCE.md
│   └── CLAUDE.md                          # module-scoped rules, explicitly excludes chat/onboarding/backend
└── src/
    ├── app/
    │   ├── layout.tsx                     # root layout, wraps children in <AuthProvider>
    │   ├── page.tsx, globals.css
    │   ├── login/page.tsx                 # working login form, real POST /auth/login
    │   ├── admin/...                      # fully built (M8): layout, documents, users, tenants, settings
    │   └── chat/
    │       ├── new/                       # EMPTY — no page.tsx
    │       └── [conversationId]/          # EMPTY — no page.tsx
    ├── components/
    │   ├── admin/ (AuthGuard.tsx, StatusBadge.tsx)
    │   └── chat/                          # EMPTY — no files
    ├── lib/
    │   ├── apiClient.ts                   # shared fetch wrapper, Bearer token, ApiError class
    │   ├── authApi.ts, authContext.tsx    # shared, working
    │   └── chat/                          # EMPTY — placeholder dir
    └── __tests__/                         # EMPTY — no test framework installed
```

**Conclusion:** Admin UI (M8) is fully built and merged. Chat UI (M9) directories exist only as empty placeholders — zero chat code has been written yet.

## 2. Available scripts

From `frontend/package.json`:
| Script | Command |
|---|---|
| `dev` | `next dev` |
| `build` | `next build` |
| `lint` | `next lint` |
| `typecheck` | `tsc --noEmit` |

**No `test` script, no test runner in devDependencies** (no jest/vitest/RTL). CLAUDE.md requires "minimum 1 test per PR" — this is currently unsatisfiable for frontend without first adding a test framework. Flagging as a blocker (see §7).

## 3. Styling conventions established by Admin UI

- **TailwindCSS utility classes only** — no CSS modules, no component library, no `clsx`/`cva`. Conditional classes built as `[...].join(' ')`.
- **Palette:** slate = neutrals/surfaces, `indigo-600` (`brand-primary` #4f46e5) = primary/active/accent, `emerald` = success, `red` = error/destructive, `blue` = in-progress.
- **Icons:** inline heroicons-style SVGs (outline, `strokeWidth=1.5`), no icon package dependency.
- **Layout:** fixed sidebar, collapses to overlay drawer below `md:` (768px) breakpoint — directly reusable pattern for Chat's sidebar + sources drawer.
- **Loading spinner:** small ring via `animate-spin` + two-tone border trick (`AuthGuard.tsx`).
- **Status badges:** colored dot/text per state (`StatusBadge.tsx`) — direct precedent for `FaithfulnessBadge.tsx` (green/amber/red).
- **Types convention:** canonical types live *outside* `src/`, in a sibling `frontend/<module>/types/<module>.ts`, aliased via a `tsconfig.json` path (`@admin-types`), with a comment marking it the single source of truth derived from `openapi.yaml`. M9 has no equivalent yet — no `@chat-types` alias exists.
- **Dark mode:** `darkMode: 'class'` is configured in `tailwind.config.ts` but **nothing uses it yet** — no `dark:` classes anywhere, no theme toggle, no `ThemeProvider`. M9 would be the first module to actually implement dark mode end-to-end.
- **Per-module `CLAUDE.md`:** `frontend/admin/CLAUDE.md` scopes M8 and explicitly forbids touching `frontend/src/app/chat/` or `frontend/src/components/chat/`. No equivalent `frontend/chat/CLAUDE.md` exists yet for M9.

## 4. Does `frontend/src/app/chat/` exist?

Yes, but empty except two placeholder subdirectories with no files inside: `chat/new/` and `chat/[conversationId]/`. No `chat/page.tsx` redirect file either.

## 5. Does `frontend/src/components/chat/` exist?

Yes, directory exists, zero files.

## 6. Reusable shared layout/theme/components

| Asset | Reusable as-is? | Notes |
|---|---|---|
| `AuthProvider` (root `layout.tsx`) | Yes | Already wraps whole app; chat pages get auth state for free. |
| `src/lib/apiClient.ts`, `authContext.tsx` | Yes | Not module-owned by M8 in the ownership table — shared infra. |
| Tailwind theme/config | Yes | No changes needed; same indigo/slate palette applies. |
| `components/admin/AuthGuard.tsx` | **No, must duplicate** | Lives under `components/admin/`, owned by M8 per CLAUDE.md module table — M9 cannot edit it. Logic is generic (checks `isAuthenticated`/`isHydrated`) so create an equivalent `components/chat/ChatAuthGuard.tsx` (or similarly named) reusing the same pattern. |
| Shared `Button`/`Input`/`Spinner` kit | N/A — doesn't exist | Admin UI inlines Tailwind per-component; no shared kit was extracted. Chat UI should follow the same inline convention rather than inventing a new shared-component layer. |
| `@admin-types` pattern | Mirror, don't reuse | Create parallel `frontend/chat/types/chat.ts` + add `"@chat-types": ["./chat/types/chat"]` to `tsconfig.json` `paths`. `tsconfig.json` isn't in the module ownership table, so this edit is low-risk, but it is a shared file — keep the diff to just adding the one path entry. |

## 7. Remaining Chat UI blockers

No prior audit file existed to diff against — this section reports current-state blockers found directly.

1. **No test framework installed** (no script, no jest/vitest in `devDependencies`). Need at minimum one test per PR per CLAUDE.md Git Rules — blocks satisfying that rule until a runner is added.
2. **No `@chat-types` alias / no canonical chat types file** — must be created before writing typed API calls (mirrors what M8 did for `@admin-types`).
3. **No `frontend/chat/CLAUDE.md`** — doesn't block coding, but M8 has one; worth adding for consistency/scoping once implementation starts.
4. **Dark mode has no existing implementation to extend** — M9 acceptance criteria require it, but there's no `ThemeProvider`/toggle anywhere in the codebase to build on; this is new infra, not a reuse.

No blocker is a hard stop — all are resolvable inside M9's own owned files.

## 8. Is `POST /chat/conversations` still absent from `openapi.yaml`?

**Yes, confirmed still absent.** Only these chat paths exist in `specs/openapi.yaml`:
- `GET /chat/conversations` — list conversations
- `GET /chat/conversations/{conversation_id}` — get one, with embedded messages
- `DELETE /chat/conversations/{conversation_id}`
- `POST /chat/query`

There is **no endpoint to explicitly create a conversation**. This contradicts `MODULE_SPEC_M9.md` step 11, which describes `"New chat" → POST /chat/conversations → redirect`.

**Resolution (no spec change needed):** `ChatQueryRequest.conversation_id` is nullable, and `ChatQueryResponse` always returns a `conversation_id`. The intended flow is: a "new chat" is purely client-side (blank composer, no id); on first send, call `POST /chat/query` with `conversation_id: null`; the backend/n8n creates the conversation and returns its new id in the response, at which point the UI routes to `/chat/[conversation_id]`. The `MODULE_SPEC_M9.md` plan is stale on this point — `openapi.yaml` is the source of truth per `CLAUDE.md` ("ALL endpoints must match `specs/openapi.yaml` exactly").

## 9. Does `GET /chat/conversations/{id}` include embedded messages?

**Yes.** Its response schema is `allOf [ConversationOut, { messages: ChatMessageOut[] }]` — a single GET returns the conversation header (`id`, `title`, `channel`, `created_at`, `message_count`) plus the full `messages` array in one call.

This also contradicts `MODULE_SPEC_M9.md` step 6, which references a separate `GET /chat/conversations/{id}/messages` endpoint — that path does not exist in `openapi.yaml`. Use `GET /chat/conversations/{id}` only.

## 10. Exact fields for `POST /chat/query` (source: `specs/openapi.yaml`)

**Request — `ChatQueryRequest`:**
| Field | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | 1–2000 chars |
| `conversation_id` | string (uuid) \| null | no | omit/null → new conversation |
| `max_chunks` | integer | no | default 5, min 1, max 20 |

**Response — `ChatQueryResponse`:**
| Field | Type | Notes |
|---|---|---|
| `answer` | string | |
| `sources` | `SourceChunk[]` | `document_id`, `title`, `chunk_text`, `page_number` (nullable int), `score` (float) |
| `follow_up_questions` | string[] | |
| `conversation_id` | string (uuid) | always present, even for new conversations |
| `faithfulness` | float 0–1 | self-check score; <0.7 triggers Pro-model retry server-side |
| `requires_clarification` | boolean | default false |
| `metadata` | object | `model`, `retrieval_time_ms` (int), `chunks_retrieved` (int) |

**Important divergence:** `MODULE_SPEC_M9.md`'s "Mock Data Shape (from M3)" omits `faithfulness` and `requires_clarification` — both exist in `openapi.yaml` and are required by the module's own acceptance criteria (faithfulness badge, clarification banner). Treat `openapi.yaml` as ground truth, not the module spec's mock shape.

**Related — `ChatMessageOut`** (used inside the embedded `messages` array from §9): `id`, `role` (`user`\|`assistant`), `content`, `sources` (`SourceChunk[]`), `faithfulness` (nullable float), `requires_clarification` (boolean, default false), `created_at`.

## Bonus finding — backend is testable now

`backend/app/api/chat.py` exists and is wired into `app/main.py` (`/chat` router included). `.env.example` sets `MOCK_N8N=true`. This means Chat UI can be developed and manually verified against a **real running backend in mock mode** rather than needing hand-rolled frontend fixtures — prefer this over building a separate mock layer.

---

## Report

### What changed after the Admin UI merge
- `frontend/` now has a fully built Admin Portal (M8): layout, auth guard, documents/users/tenants/settings pages, shared `apiClient`/`authContext`/`authApi`, working login page, Tailwind theme, and a sibling `frontend/admin/` directory holding canonical types (`@admin-types`) and module docs.
- Root layout already wraps everything in `<AuthProvider>`, so auth state is available app-wide without any chat-side setup.
- `frontend/src/app/chat/`, `frontend/src/components/chat/`, and `frontend/src/lib/chat/` exist only as empty placeholder directories — no chat code has landed yet.
- Backend `/chat` router is live and mockable (`MOCK_N8N=true`), so the gateway side is ready to integrate against immediately.

### What Chat UI files should be created
- `frontend/chat/types/chat.ts` (+ `@chat-types` tsconfig path) — `ChatQueryRequest`, `ChatQueryResponse`, `SourceChunk`, `ConversationOut`, `ChatMessageOut`, mirroring `openapi.yaml` exactly (including `faithfulness`/`requires_clarification`, which the module spec's mock shape omits).
- `frontend/src/lib/chat/chatApi.ts` — thin wrappers over `apiRequest` for `POST /chat/query`, `GET /chat/conversations`, `GET /chat/conversations/{id}`, `DELETE /chat/conversations/{id}`.
- `frontend/src/app/chat/page.tsx` — redirect to `/chat/new`.
- `frontend/src/app/chat/new/page.tsx` — blank composer, no `conversation_id` yet.
- `frontend/src/app/chat/[conversationId]/page.tsx` — loads via `GET /chat/conversations/{id}`, renders history + composer.
- `frontend/src/components/chat/ChatLayout.tsx`, `Sidebar.tsx` (or `ConversationList.tsx`), `MessageList.tsx`, `MessageBubble.tsx` (renders Markdown), `CitationsPanel.tsx`/`CitationCard.tsx`, `FollowUpChips.tsx`, `MessageInput.tsx`, `TypingIndicator.tsx`, `FaithfulnessBadge.tsx`.
- `frontend/src/components/chat/ChatAuthGuard.tsx` — own copy of the admin guard logic (cannot import from `components/admin/` per ownership rules).
- `frontend/chat/CLAUDE.md` — module scope doc, mirroring `frontend/admin/CLAUDE.md`'s pattern.

### Existing frontend conventions that must be reused
- Tailwind-only styling, inline utility classes, no component library, slate/indigo/emerald/red palette.
- `[...].join(' ')` pattern for conditional classes; inline heroicons-style SVGs; `md:` breakpoint for mobile/desktop split; spinner-via-`animate-spin` pattern; badge-via-colored-text pattern (`StatusBadge.tsx` → `FaithfulnessBadge.tsx`).
- `apiClient.apiRequest<T>()` for all HTTP calls — never raw `fetch` in components.
- Canonical-types-outside-`src` + path-alias convention (`@admin-types` → mirror as `@chat-types`).
- `openapi.yaml` as the single source of truth over any module-spec mock shapes that have drifted (confirmed drift in §10).

### Whether implementation can start
**Yes.** No blocking dependency remains: Admin UI merge didn't touch anything M9 needs differently, the backend `/chat` endpoints exist and are mockable, and the only "blockers" found (§7) are things M9 creates itself (types file, alias, test runner) rather than waiting on another module or an OpenAPI change.

### Next implementation plan (≤25 bullets, not yet executed)
1. Add `react-markdown`, `rehype-highlight`, `rehype-raw` to `frontend/package.json` dependencies.
2. Add a lightweight test runner (vitest + @testing-library/react) since none exists, to satisfy "1 test per PR."
3. Create `frontend/chat/types/chat.ts` with `ChatQueryRequest`, `ChatQueryResponse`, `SourceChunk`, `ConversationOut`, `ChatMessageOut` exactly matching `openapi.yaml` (include `faithfulness`, `requires_clarification`).
4. Add `"@chat-types": ["./chat/types/chat"]` to `tsconfig.json` `paths`.
5. Create `frontend/chat/CLAUDE.md` scoping M9 to `frontend/src/app/chat/`, `frontend/src/components/chat/`, `frontend/chat/types/chat.ts`.
6. Create `frontend/src/lib/chat/chatApi.ts`: `sendQuery()`, `listConversations()`, `getConversation()`, `deleteConversation()`, all via `apiRequest`.
7. Create `frontend/src/components/chat/ChatAuthGuard.tsx` (duplicate of admin's guard logic, own copy).
8. Build `frontend/src/components/chat/MessageBubble.tsx` — user (right, indigo) vs assistant (left, slate surface) bubble, Markdown rendering via `react-markdown`.
9. Build `FaithfulnessBadge.tsx` — green ≥0.85 / amber 0.7–0.85 / red <0.7, tooltip "self-check score."
10. Build `CitationsPanel.tsx`/`CitationCard.tsx` — collapsible, shows title/page/excerpt/score per `SourceChunk`.
11. Build `FollowUpChips.tsx` — renders `follow_up_questions`, click → sends as next query.
12. Build `MessageInput.tsx` — textarea + send button, Cmd+Enter submit, disabled while loading.
13. Build `TypingIndicator.tsx` — 3 bouncing dots, shown while awaiting `POST /chat/query`.
14. Build `MessageList.tsx` — scrollable history, autoscroll to bottom on new message.
15. Build `Sidebar.tsx`/`ConversationList.tsx` — `GET /chat/conversations`, highlight active conversation, "New chat" link to `/chat/new`.
16. Build `ChatLayout.tsx` — sidebar + main area wrapper, mobile-responsive drawer (mirror admin's `md:` breakpoint pattern).
17. Create `frontend/src/app/chat/page.tsx` — redirect to `/chat/new`.
18. Create `frontend/src/app/chat/new/page.tsx` — blank conversation; on first send, `POST /chat/query` with `conversation_id: null`, then route to `/chat/[returned id]`.
19. Create `frontend/src/app/chat/[conversationId]/page.tsx` — `GET /chat/conversations/{id}` for history, append on each new `POST /chat/query`.
20. Wire `requires_clarification` → warning banner + red badge override.
21. Add dark mode: a `ThemeProvider`/toggle (new infra — nothing to extend) plus `dark:` Tailwind variants across chat components only.
22. Verify mobile responsiveness at 375px (drawer → full-screen, per acceptance criteria).
23. Manually verify end-to-end against the real backend with `MOCK_N8N=true` (no need for hand-rolled fixtures).
24. Write at least one test (e.g., `MessageBubble` renders Markdown, or `chatApi.sendQuery` request shape) once the runner is added.
25. Run `npm run lint`, `npm run typecheck`, `npm run build` before opening the PR; confirm no edits landed outside `frontend/src/app/chat/`, `frontend/src/components/chat/`, `frontend/src/lib/chat/`, `frontend/chat/`.
