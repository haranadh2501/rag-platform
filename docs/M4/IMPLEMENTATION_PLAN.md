# M4 Implementation Plan — Unified Message Service (Slack slice + shared core)

**Status:** Implemented (Slack slice + shared core); web wiring handed off to M3
**Author:** Tushar | **Date:** 2026-06-18
**Source spec:** [`specs/SPEC_M4_MESSAGE_SERVICE.md`](../../specs/SPEC_M4_MESSAGE_SERVICE.md)
**Scope of this doc:** How M4 will be built **without modifying any file owned by another module.**

> ⚠️ This file lives under `docs/` which is **M11-owned**. It is an additive new file
> (no edits to M11's existing docs). Flag it for M11 awareness in the PR.

---

## 1. Guiding Principle

M4 ships a **self-contained Slack vertical** plus a **channel-agnostic `process_message()`
core** that M3 wires into the web path later. M4 does **not** edit any file owned by
another module. Anything that would touch M2 / M3 / M7 is isolated as a **handoff**, not
an edit.

---

## 2. Resolved Design Decisions

These four were confirmed before planning (they override the spec text where it conflicts):

| # | Decision | Effect |
|---|---|---|
| 1 | Slack path = **`POST /webhooks/slack/events`** | Matches `openapi.yaml` + existing route. Spec text saying `/webhooks/slack` is stale. |
| 2 | Response shape = **follow `openapi.yaml`** | `SourceChunk = {document_id, title, chunk_text, page_number, score}`; response keeps `conversation_id`/`faithfulness`/`metadata`. Spec's `{title,url,chunk_id}` is dropped. |
| 3 | **Raw SQL** for new tables | No ORM changes to `models.py`; access `slack_workspace_map` / `processed_requests` / `slack_user_id` via raw SQL. |

---

## 3. Files M4 Will Touch

| File | Action | Owner | Notes |
|---|---|---|---|
| `backend/app/services/types.py` | **New** | unowned | `MessageContext` dataclass |
| `backend/app/services/pipeline_client.py` | **New** | unowned | httpx POST to pipeline; reads `PIPELINE_URL` via `os.getenv` |
| `backend/app/services/message_service.py` | **New** | unowned | `process_message(ctx, db)` — steps 2–8 |
| `backend/app/api/webhooks.py` | Modify | **M4** | implement `/webhooks/slack/events` + add `/webhooks/mock/pipeline` |
| `backend/app/bots/slack.py` | Modify | **M4** | `post_reply()` / `post_text()` via `chat.postMessage` |
| `backend/app/api/chat.py` | Modify | **M4** | web adapter `POST /chat/query`: JWT → `MessageContext` → `process_message` → return. `ChatQueryRequest` defined inline (no `schemas/chat.py` exists). Conversation-CRUD stubs left for M3. |

### Already available — no edit required
- `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` already exist in `config.py` → read via `settings`.
- `httpx==0.27.0` and `slack-sdk==3.27.2` already in `requirements.txt`.
- `get_db` (async session) and `AsyncSessionLocal` already exist in `core/database.py`.
- Migration `0002_m4_messaging.py` already defines all required schema.

---

## 4. Explicitly NOT Touched (Handoffs)

| Need | Owner | M4 workaround / handoff |
|---|---|---|
| Router registration / `main.py` | M2 | **Avoid** by hosting the mock under the already-registered `/webhooks` router → `POST /webhooks/mock/pipeline`. |
| `PIPELINE_URL`, `PIPELINE_TIMEOUT_SECONDS` in `config.py` | M2 | Read via `os.getenv` in `pipeline_client.py` (Settings has `extra="ignore"`, so `.env` entries are tolerated). |
| `slack_*` / `processed_requests` ORM models | M2 | **Raw SQL** — no `models.py` change. |
| DB schema (migration `0002` vs `init.sql` drift) | M7 | **Flag, don't fix.** Precondition: deploy runs `alembic upgrade head`. See Risk #1. |
| `.env.example` keys | M1 | Document the two new vars in the PR description for M1 to add. |

---

## 5. Component Design

### 5.1 `types.py` — `MessageContext`
Dataclass per spec §4:
`request_id, user_id, tenant_id, source, query, conversation_id, slack_channel, slack_thread_ts`.

### 5.2 `pipeline_client.py`
- `async def call_pipeline(payload: dict) -> dict`
- `PIPELINE_URL = os.getenv("PIPELINE_URL", "http://localhost:8000/webhooks/mock/pipeline")`
- timeout from `os.getenv("PIPELINE_TIMEOUT_SECONDS", "120")`
- Returns parsed dict on 2xx; raises `PipelineError` on timeout / non-2xx.
- Response contract = **openapi `ChatQueryResponse`** shape (decision #2).

### 5.3 `message_service.py` — `async def process_message(ctx, db) -> dict`
Channel-agnostic; raises typed exceptions so each adapter maps them appropriately.

| Step | Action |
|---|---|
| 2 | Resolve identity — Slack: raw-SQL JOIN `slack_workspace_map` + `users`; web: already on `ctx`. |
| 3 | Find/create conversation (raw SQL). Web `conversation_id` ownership mismatch → raise `ConversationOwnershipError`. |
| 4 | Reset (`/new` `/reset` `/clear`) → delete + recreate + return confirmation, STOP. Partial matches (`/newer`) do not trigger. |
| 5 | Load last 10 (raw SQL `ORDER BY created_at DESC LIMIT 10`, reverse to oldest-first). |
| 6 | `pipeline_client.call_pipeline(...)`; on failure raise `PipelineError`. |
| 7 | Delivery — `source=="slack"` → `slack.post_reply(...)`; `"web"` → return payload (no side-effect). |
| 8 | Save user + assistant in one transaction (raw SQL), **only on success**. |

Returns the response dict (web uses it; Slack ignores the return).

**Typed exceptions:** `ConversationOwnershipError` → web 403; `PipelineError` → web 502 / Slack fallback message; identity failures → Slack logs & stops (already ACKed).

### 5.4 `webhooks.py` (M4) — `/webhooks/slack/events`
Fast path, in order:
1. Read **raw body bytes**; verify HMAC-SHA256 against `settings.SLACK_SIGNING_SECRET` → **403** on fail.
2. `type == "url_verification"` → echo `challenge`, stop.
3. `event.bot_id` set → **200** no-op (loop prevention).
4. Dedup: `INSERT INTO processed_requests (request_id) VALUES (:event_id) ON CONFLICT DO NOTHING`; `rowcount == 0` → duplicate → **200**, stop.
5. Validate `event_id` / `event.user` / `event.text` present → missing → **200** + log warning (don't trigger Slack retry).
6. Extract `event.channel`, `event.ts` for threading.
7. **Return 200 immediately**, then `BackgroundTask(_run)`.

`_run`:
- Opens its **own `AsyncSessionLocal`** (the request's `get_db` session is closed after the response is sent).
- Builds `MessageContext`, calls `process_message`.
- Catches `PipelineError` / identity errors → posts fallback via `slack.post_text` or logs.

Also adds `POST /mock/pipeline` (→ `/webhooks/mock/pipeline`) returning the canned
openapi-shaped response (mirror `chat.py` `MOCK_RESPONSE`).

Leaves `/whatsapp` and `/n8n/ingestion-status` stubs **untouched**.

### 5.5 `bots/slack.py` (M4)
- `async def post_reply(channel, thread_ts, answer, sources)` and `post_text(channel, thread_ts, text)`.
- Calls `chat.postMessage` (httpx + `settings.SLACK_BOT_TOKEN`).
- Block Kit: answer section + sources context block, **capped at 3 sources**.

---

## 6. Processing Flow (M4-owned portion)

```
Slack POST /webhooks/slack/events
  → HMAC verify (403) → url_verification echo → bot_id skip (200)
  → dedup INSERT (dup → 200) → field check (missing → 200+log)
  → 200 ACK  ──────────────────────────────────────────────┐
                                                            │ BackgroundTask
                          ┌─────────────────────────────────▼─────────────────┐
                          │ process_message(ctx, db=fresh AsyncSessionLocal)   │
                          │  2 resolve identity (raw SQL JOIN)                 │
                          │  3 find/create conversation (raw SQL)              │
                          │  4 reset? → recreate + confirm, STOP               │
                          │  5 load last 10 (raw SQL)                          │
                          │  6 pipeline_client.call_pipeline()                 │
                          │  7 slack.post_reply(channel, thread_ts, ...)       │
                          │  8 save user+assistant (1 txn) — success only      │
                          └────────────────────────────────────────────────────┘
```

---

## 7. Web Path — implemented in M4 (`POST /chat/query`)

The web adapter now lives in `chat.py` (moved into M4 scope per the updated spec). It
authenticates via the JWT dependency, builds a web `MessageContext`, delegates to
`process_message`, and returns the response inline:

```python
@router.post("/query")
async def chat_query(payload: ChatQueryRequest,
                     current_user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    ctx = MessageContext(request_id=str(uuid4()), source="web", query=payload.query,
                         user_id=current_user.id, tenant_id=current_user.tenant_id,
                         conversation_id=payload.conversation_id)
    try:
        return await process_message(ctx, db)
    except ConversationOwnershipError:      # → 403
        raise HTTPException(403, "conversation_id belongs to another user")
    except PipelineError:                   # → 502 + fallback body
        return JSONResponse(502, {"answer": FALLBACK_MESSAGE, "sources": [], "follow_up_questions": []})
```

- **401** (invalid/expired JWT) — enforced by `get_current_user`.
- **422** (missing/empty query) — enforced by the inline `ChatQueryRequest` schema.
- Conversation-CRUD endpoints (`/chat/conversations*`) remain **M3** stubs — untouched.

---

## 8. Testing

`tests/` is **M10-owned**. M4 adds two **new** additive files (no edits to
`conftest.py` / `test_auth.py`), flagged for M10 sign-off in the PR:

**`tests/test_m4_slack.py`** (Slack):
- HMAC pass / fail (403)
- `url_verification` challenge echo
- `bot_id` event → 200 no-op
- missing required fields → 200 no-op
- mock pipeline endpoint returns a valid shape
- happy path → threaded reply posted + 2 messages saved (needs migration 0002)
- reset command → conversation recreated, pipeline NOT called, nothing saved
- duplicate `event_id` → delivered once

**`tests/test_m4_chat.py`** (web):
- missing query → 422
- no auth → 401
- happy path → 200 with `conversation_id` + 2 messages saved
- foreign `conversation_id` → 403

---

## 9. Environment Variables (read via `os.getenv`, documented for M1)

| Variable | Default | Notes |
|---|---|---|
| `PIPELINE_URL` | `http://localhost:8000/webhooks/mock/pipeline` | real n8n URL in prod |
| `PIPELINE_TIMEOUT_SECONDS` | `120` | HTTP timeout |

`SLACK_SIGNING_SECRET` / `SLACK_BOT_TOKEN` already exist in `config.py` — no change.

---

## 10. Risks (surface in PR — not fixed by M4)

1. **🔴 `init.sql` vs migration `0002` drift** — if the DB is seeded from `database/init.sql`,
   the tables M4's raw SQL needs (`slack_workspace_map`, `processed_requests`, `slack_user_id`,
   `UNIQUE(user_id, channel)`) won't exist. **Hard precondition: run `alembic upgrade head`.**
   Owner: M7 to reconcile `init.sql`.
2. **Mock path divergence** — spec says `/mock/pipeline`; M4 ships `/webhooks/mock/pipeline`
   to avoid editing `main.py`. If the bare path is required, that's an M2 router-registration PR.
3. **`chat.py` shared with M3** — M4 owns `POST /chat/query`; M3 owns the conversation-CRUD
   stubs in the same file. Both edit `chat.py`, so coordinate merges to avoid conflicts.
4. **Spec text drift** — `SPEC_M4_MESSAGE_SERVICE.md` still shows `/webhooks/slack` and
   `{title,url,chunk_id}` sources and says "no schema changes." Implementation follows the
   §2 decisions (`/webhooks/slack/events`, openapi response shape, migration 0002) instead.

---

## 11. Build Order

1. `types.py` (`MessageContext`)
2. `pipeline_client.py` + `/webhooks/mock/pipeline` route → unblocks local testing
3. `message_service.py` (steps 2–8, raw SQL)
4. `bots/slack.py` (`post_reply` / `post_text`)
5. `webhooks.py` `/slack/events` fast path + BackgroundTask wiring
6. `chat.py` `POST /chat/query` web adapter (inline `ChatQueryRequest`)
7. `tests/test_m4_slack.py` + `tests/test_m4_chat.py` (coordinate with M10)
8. PR with handoff notes for M1 (env), M2 (optional mock path), M3 (chat.py merge), M7 (schema)
