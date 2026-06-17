# MODULE_SPEC_M4 — Unified Message Service (Web + Slack)

**Status:** Draft | **Author:** Tushar | **Date:** 2026-06-17

---

## 1. Scope

**In scope:**
- Single message handler shared by Web and Slack
- Web: synchronous — answer in the same HTTP response
- Slack: ACK within 3s, deliver reply via `chat.postMessage` in a background task
- Conversation lifecycle: create, continue, reset (`/new`)
- History: last 10 messages (sliding window)

**Out of scope (deferred):** WhatsApp, MCP, streaming responses, Redis Streams worker, rolling summary

---

## 2. Architecture

```
Website ───┐
           ├──→ build_context() → find_or_create_conversation() → handle_message()
Slack   ───┘
```

- **Web:** all steps run inline; JSON answer returned in the same HTTP response
- **Slack:** auth + dedup + context run inline; ACK 200 immediately; `handle_message` runs in `BackgroundTask`

---

## 3. MessageContext

Every channel normalizes its payload into this before any processing:

```python
@dataclass
class MessageContext:
    request_id: str               # event_id (Slack) | generated UUID (Web)
    source: ChannelType           # WEB | SLACK
    user_id: UUID                 # from JWT (Web) | looked up from Slack user ID
    tenant_id: UUID               # from JWT (Web) | slack_workspace_map[team_id]
    external_identity: str        # email (Web) | slack_user_id (Slack)
    team_id: str | None           # Slack workspace ID; None for Web
    raw_query: str                # message text
    reset_requested: bool         # True only for Slack /new /restart /clear
    conversation_id: UUID | None  # filled in by find_or_create_conversation()
```

---

## 4. End-to-End Request Flow

**Step 0 — Deduplication:** Slack retries webhooks if not ACKed within 3 seconds. Skip already-processed messages.
- Extract `request_id`: Slack `event_id`; generate UUID for Web
- If `request_id` already in `processed_requests` → return `200` immediately, do not process
- Track via unique constraint in the DB (insert-on-conflict, not a prior SELECT)

**Step 1 — Validate auth / signature:** Reject forged or unauthorized requests before ACKing. Validation is fast (<5 ms) and fits inside any webhook timeout.
- Slack: HMAC-SHA256 via `X-Slack-Signature` + signing secret; also handle `url_verification` challenge; ignore events where `bot_id` is set (prevents reply loops)
- Web: JWT signature + expiry
- Invalid → `401`/`403`, nothing downstream runs

**Step 2 — Build MessageContext:** Normalize the channel payload into the shared envelope all later steps use.
- Resolve `user_id` (JWT claims for Web; Slack user ID → internal user for Slack)
- Resolve `tenant_id` — decides which knowledge base n8n queries (JWT claims for Web; `slack_workspace_map[team_id]` for Slack)
- Set `source`, `external_identity`, `raw_query`, `request_id`, `reset_requested`, optional `conversation_id`

**Step 3 — Handle reset command (short-circuit):** A reset is a command, not a query — it never reaches n8n.
- Normalize before matching: `raw_query.strip().lower()`
- Recognized reset commands: `/new`, `/restart`, `/clear`
- If the normalized query matches any of the above: mark old conversation `is_active = false`, create new row (`is_active = true`), reply "New conversation started ✓", and STOP
- Variations like `/New`, `/new `, `/ new` all match after normalization; partial strings (e.g. `/newer`) do not

**Step 4 — Find or create conversation:** Every lookup scoped to at least `(tenant_id, identity)` so conversations can never leak across users.
- Web with `conversation_id`: validate it belongs to `(user_id, tenant_id)`, use it; mismatch → `403`
- Web without `conversation_id`: create new
- **Slack: deferred — runs at the start of `handle_message()` inside the BackgroundTask, not in the synchronous request path.** This keeps the Slack sync path to HMAC verify + dedup only, safely inside the 3s window.

**Step 5 — ACK (Slack only):** Slack has a hard 3s webhook timeout; Web stays synchronous.
- Slack: return `200` immediately after dedup — no conversation DB work happens before this
- Web: skip this step — run the handler inline and return the answer in the same HTTP response

**Step 6 — Load context:**
- Load last 10 messages for `conversation_id`, oldest-first
- If total character count across all loaded messages exceeds `MAX_HISTORY_CHARS = 5000`, drop the oldest messages until under the limit
- Send the trimmed list as `history` to n8n

**Step 7 — Call n8n:** All LLM work (query rewriting, retrieval, generation) lives in n8n, per CLAUDE.md.
- POST `{ request_id, tenant_id, conversation_id, current_message, history }`
- n8n rewrites the query using history → embeds → retrieves chunks → generates grounded answer

**Step 8 — Persist (one transaction):** Atomic write after success only — saving before the n8n call would leave an orphaned message if n8n fails.
- On success: INSERT user message + assistant message; UPDATE `last_message_at`
- On failure: do NOT save; send fallback reply ("Sorry, something went wrong — please try again"); log the error

**Step 9 — Deliver reply:**
- Slack: `chat.postMessage` in thread, Block Kit
- Web: returned directly in the HTTP response from Step 5's inline run

---

## 5. Endpoint Behaviour

**Slack `POST /webhooks/slack`:**
- Read raw body bytes first, then verify HMAC signature — `403` if invalid
- If `type == "url_verification"`, echo the `challenge` and stop
- If `bot_id` is set on the event, return `200` and ignore (prevents reply loops)
- If `event_id` already in `processed_requests`, return `200` and stop (dedup)
- Build `MessageContext`; if reset command detected (normalized `raw_query.strip().lower()`), reset conversation and return `200`
- **Return `200` immediately** — no conversation DB work before this point
- Dispatch `handle_message(ctx)` as a `BackgroundTask`; conversation lookup, n8n call, and reply delivery all happen inside it

**Web `POST /api/chat`:**
- Verify JWT — `401` if invalid
- Build `MessageContext` from JWT claims
- Find or create conversation
- Run message handler inline and return JSON response

---

## 6. Message Handler Behaviour

Runs identically for both channels. The entire body is wrapped in a top-level `try/except` — any unhandled exception must log the full traceback and deliver the standard error reply to the user. The handler must never silently terminate.

```python
async def handle_message(ctx: MessageContext) -> None:
    try:
        ...
    except Exception:
        log.error("handle_message failed", exc_info=True)
        await deliver_error(ctx, "Sorry, something went wrong — please try again.")
```

**Steps:**

1. **(Slack only)** `find_or_create_conversation(ctx)` — find row WHERE `(tenant_id, external_id, team_id, is_active = true)`; create if none. Sets `ctx.conversation_id`.
2. Load last 10 messages for `conversation_id`, oldest-first. If total character count across all messages exceeds `MAX_HISTORY_CHARS = 5000`, drop the oldest messages until under the limit.
3. POST to n8n (`N8N_TIMEOUT_SECONDS = 120`). A `TimeoutError` or non-2xx response is treated as n8n failure — go to step 5.
4. On n8n success — INSERT user message + assistant reply in one transaction; UPDATE `last_message_at`. Then deliver reply.
5. On n8n failure or timeout — do NOT persist anything; deliver the standard error reply; log the full error with `exc_info=True`.

---

## 7. API Contracts

### Web — `POST /api/chat`

**Request:**
```json
{ "query": "What is the refund policy?", "conversation_id": "..." }
```
`conversation_id` is optional — omit to start a new conversation.

**200 Response:**
```json
{
  "request_id": "...",
  "conversation_id": "...",
  "answer": "...",
  "sources": [{ "title": "...", "url": "...", "chunk_id": "..." }],
  "follow_up_questions": ["..."]
}
```

**Errors:** `401` bad/expired JWT · `403` conversation belongs to another user · `422` missing query · `502` n8n failure (return fallback answer, `sources: []`)

---

### Slack — `POST /webhooks/slack`

- Invalid HMAC signature → `403`
- `url_verification` → `{ "challenge": "..." }`
- Duplicate `event_id` → `200` no-op
- Valid message → `200` immediately; answer delivered by `chat.postMessage` threaded on `thread_ts`

---

### n8n — `POST {N8N_WEBHOOK_URL}`

**Request:**
```json
{
  "request_id": "...",
  "tenant_id": "...",
  "conversation_id": "...",
  "current_message": "...",
  "history": [{ "role": "user", "content": "..." }, { "role": "assistant", "content": "..." }]
}
```

**Response:**
```json
{
  "answer": "...",
  "sources": [{ "title": "...", "url": "...", "chunk_id": "..." }],
  "follow_up_questions": ["..."]
}
```

**Timeout:** `N8N_TIMEOUT_SECONDS = 120`. On timeout, the n8n client raises `TimeoutError`; the message handler treats this identically to an n8n failure (no persist, standard error reply to user, full error logged).

---

## 8. Database Changes (Alembic migration)

```sql
ALTER TABLE conversations ADD COLUMN is_active       BOOLEAN DEFAULT true;
ALTER TABLE conversations ADD COLUMN last_message_at TIMESTAMPTZ;
ALTER TABLE conversations ADD COLUMN team_id         VARCHAR(64);

CREATE INDEX idx_conv_slack ON conversations (tenant_id, external_id, team_id, is_active);
CREATE INDEX idx_conv_web   ON conversations (tenant_id, user_id, is_active);

-- Dedup table for Slack retries
CREATE TABLE processed_requests (
  request_id  VARCHAR(255) PRIMARY KEY,
  received_at TIMESTAMPTZ DEFAULT NOW()
);
```

`chat_messages` needs no changes.

---

## 9. Files

| File | Action |
|---|---|
| `backend/app/api/chat.py` | Modify — Web adapter |
| `backend/app/api/webhooks.py` | Modify — Slack adapter |
| `backend/app/bots/slack.py` | Modify — `chat.postMessage` + Block Kit delivery |
| `backend/app/services/context_builder.py` | **New** — `build_context()` |
| `backend/app/services/conversation_router.py` | **New** — `find_or_create_conversation()` |
| `backend/app/services/message_handler.py` | **New** — `handle_message()` |
| `backend/app/services/n8n_client.py` | **New** — n8n HTTP client |
| `alembic/versions/xxxx_m4_conversations.py` | **New** — migration for §8 |

**Env vars required:** `SLACK_SIGNING_SECRET`, `SLACK_BOT_TOKEN`, `N8N_WEBHOOK_URL`

---

## 10. Acceptance Criteria

1. Web request without `conversation_id` → creates new conversation, returns answer in the same HTTP response
2. Web request with another user's `conversation_id` → `403`, nothing created or persisted
3. Slack message → ACKs `200` within 3s; answer posted in thread via `chat.postMessage`
4. Duplicate Slack `event_id` → `200` no-op, no duplicate DB rows
5. Slack `/new` → marks old conversation `is_active = false`, creates a new one, replies confirmation, does NOT call n8n
6. n8n failure → user message NOT persisted, fallback reply delivered to user
7. Invalid Slack signature → `403`; invalid/expired JWT → `401`; nothing downstream runs in either case
