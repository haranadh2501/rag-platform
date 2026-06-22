---
name: chat-ui-phase
description: >-
  Guide and validate work on the Chat Portal (M9). Loads module context,
  checks current implementation state against the spec, and produces or
  reviews chat-only frontend code. Use when building or reviewing anything
  under frontend/src/app/chat/ or frontend/src/components/chat/.
allowed-tools: >-
  Read, Edit, Write, Bash(npm run typecheck:*), Bash(npm run lint:*),
  Bash(npm run build:*), Bash(rg:*), Bash(find:*), Bash(grep:*)
---

# chat-ui-phase

Focused skill for the Chat Portal module (M9). Keeps work inside module
boundaries and ensures every change is consistent with the spec and the
existing API contract.

## 1. Load context (always do this first)

Read these before writing or reviewing any code:

1. `specs/MODULE_SPEC_M9.md` — deliverables, acceptance criteria, key pages
2. `frontend/chat/types/chat.ts` — TypeScript types; do not redefine inline
3. `frontend/src/lib/chat/chatApi.ts` — API client; extend, don't duplicate
4. `frontend/UI_WORK_SUMMARY.md` (M9 section) — what's already implemented vs. known gaps

## 2. Scope guard

Before making any change, verify the target file path starts with:
- `frontend/src/app/chat/`
- `frontend/src/components/chat/`
- `frontend/chat/types/chat.ts` (canonical type contract — import from here)
- `frontend/src/lib/chat/chatApi.ts` (extend; don't duplicate request logic elsewhere)
- `frontend/src/lib/` (shared utilities only — do not add chat-specific logic there)

If a requested change requires modifying `specs/openapi.yaml` or any
`backend/` file, **stop** and tell the user to raise it with M1 or the
relevant backend owner. Do not make cross-module edits.

## 3. Implementation rules

- **No RAG logic.** Retrieval, grounding, and generation run in n8n/backend.
  The frontend only calls `POST /chat/query` and renders what comes back.
- **There is no `POST /chat/conversations`.** A new conversation is created
  implicitly by the backend when `conversation_id` is omitted/`null` on
  `POST /chat/query` — never add or call that endpoint.
- **`/chat/new` is frontend-only until the first message.** Its "New
  conversation / Draft" sidebar row is local state; it must never be
  persisted or trigger a backend call before the user sends a message.
- **Keep grounding UI intact.** `CitationsPanel`, `FaithfulnessBadge`,
  `ClarificationBanner`, and `FollowUpChips` all render fields already on
  `ChatQueryResponse`/`ChatMessageOut` — don't remove or stub them out while
  touching adjacent code.
- **Preserve responsive and theme behavior.** Mobile sidebar collapse and
  `ChatThemeProvider`/`ChatThemeToggle` (chat-scoped dark mode) are already
  implemented — don't regress them as a side effect of an unrelated change.
- **Types come from `frontend/chat/types/chat.ts`.** Import `ChatMessageOut`,
  `ConversationOut`, `SourceChunk`, etc. from there. Add new types there first
  if needed — don't duplicate them elsewhere.
- **`useSearchParams()` needs a `<Suspense>` boundary.** Any new use of it
  under `frontend/src/app/chat/` must be wrapped (or rely on an existing
  ancestor `<Suspense>`) or `next build` will fail.

## 4. After each phase

1. Run `npm run typecheck` — fix all TypeScript errors before marking done.
2. Run `npm run build` if the Node version allows it (Next 14.2 requires
   Node ≥18.17 for `build`/`dev`/`lint`; if the installed version is older,
   say so plainly instead of claiming a check that didn't run).
3. Check the relevant row in `specs/MODULE_SPEC_M9.md`'s acceptance criteria.
4. Report root cause (for bugfixes), files changed, checks actually run, and
   remaining gaps — don't claim a live browser/manual check happened unless
   it really did.

## 5. Hard rules

- **Never edit** `frontend/src/app/admin/`, `frontend/src/components/admin/`,
  `frontend/src/app/onboarding/`, or `backend/` — those belong to M8, M13, and
  the backend team.
- **Never touch** `n8n-workflows/`, Slack/WhatsApp bot code, auth, or the
  database unless the user explicitly asks.
- **Never push** — commits are always the user's explicit step.
- **Never embed secrets** — API base URL comes from `NEXT_PUBLIC_API_URL`,
  not hardcoded.
