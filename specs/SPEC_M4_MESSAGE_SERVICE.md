# SPEC_M4_MESSAGE_SERVICE — Unified Message Service (Web + Slack)

**Status:** Active — Source of Truth for M4 implementation
**Author:** Tushar | **Date:** 2026-06-18
**Updated:** 2026-06-18 — Web adapter (`chat.py`) moved from M3 handoff into M4 scope; now implemented.

---

## 1. Scope

**In scope:**
- Web + Slack message handling
- Web: synchronous — answer returned in the HTTP response
- Slack: ACK 200 immediately, process in BackgroundTask, reply via `chat.postMessage`
- Conversation lifecycle: auto-find/create for (user_id, source), reset via `/new` `/reset` `/clear`
- History: last 10 messages passed to pipeline as context
- Mock pipeline endpoint for development (real n8n URL plugged in later via env var)
- Slack user onboarding: look up user by email in workspace, return Slack member ID; error if not found

**Out of scope:** WhatsApp, MCP, streaming, file uploads in chat, rolling summaries

---

## 2. Processing Flow

```
Request
  │
  ├─ Step 1: Validate minimal fields (request_id, user identifier, source, query)
  │           → Invalid: reject (401/403/422)
  │           → Valid:   [Slack: return 200 ACK, start BackgroundTask]
  │                      [Web:   continue inline]
  │
  ├─ Step 2: Resolve identity → (user_id, tenant_id, source)
  │
  ├─ Step 3: Find or create conversation for (user_id, source)
  │
  ├─ Step 4: Check reset command (/new, /reset, /clear)
  │           → Yes: delete conversation + messages, create new, reply confirmation, STOP
  │
  ├─ Step 5: Load last 10 messages for conversation_id
  │
  ├─ Step 6: Call pipeline (mock for now)
  │           → Failure: deliver error message, do NOT save, STOP
  │
  ├─ Step 7: Deliver response to user
  │           → Web:   return in HTTP response
  │           → Slack: chat.postMessage in thread (channel + thread_ts from Step 1)
  │
  └─ Step 8: Save user query + assistant response to chat_messages
```

---

## 3. Step Details

### Step 1 — Receive & Validate (fast path — no heavy DB work)

**Web (`POST /chat/query`):**
- Validate JWT → extract `user_id`, `tenant_id`
- Validate `query` present in request body
- Generate `request_id` = UUID. `source` = `"web"`.
- Invalid JWT → `401`. Missing query → `422`.
- Proceed inline (no background task).

**Slack (`POST /webhooks/slack`):**
- Read raw body bytes, verify HMAC-SHA256 (`X-Slack-Signature` + `SLACK_SIGNING_SECRET`)
- Invalid signature → `403`
- `type == "url_verification"` → echo `challenge`, stop
- `event.bot_id` set → `200`, stop (prevent reply loops)
- Dedup: `INSERT INTO processed_requests (request_id) VALUES (event_id) ON CONFLICT DO NOTHING`
  - `rowcount == 0` → duplicate → `200`, stop
- Validate required fields present: `event_id`, `event.user`, `event.text`
  - Missing → `200` + log warning (don't trigger Slack retry)
- Extract reply-back details: `event.channel`, `event.ts` (for threading)
- **Return `200` immediately.** Remaining steps run in `BackgroundTask`.

### Step 2 — Resolve Identity

- **Web:** Already resolved from JWT. `user_id` + `tenant_id` are ready.
- **Slack:**
  - Resolve tenant: `SELECT tenant_id FROM slack_workspace_map WHERE team_id = ?`
  - Resolve user: `SELECT id FROM users WHERE slack_user_id = ? AND tenant_id = ?`
  - Can be combined into a single JOIN query to minimize DB calls.
  - Failure (workspace or user not found) → log error, stop processing (already ACKed).

### Step 3 — Find or Create Conversation

- `SELECT id FROM conversations WHERE user_id = ? AND channel = ?`
- Row exists → use its `id` as `conversation_id`
- No row → `INSERT INTO conversations (tenant_id, user_id, channel) RETURNING id`
- `UNIQUE(user_id, channel)` constraint guarantees one active conversation per user per source.
- **Web with `conversation_id` in request body:** validate the row's `user_id` matches → `403` if mismatch.

### Step 4 — Check Reset Command (short-circuit)

- Normalize: `query.strip().lower()`
- Match against: `{"/new", "/reset", "/clear"}`
- If match:
  - `DELETE FROM conversations WHERE user_id = ? AND channel = ?`
    - `ON DELETE CASCADE` on `chat_messages.conversation_id` auto-removes all history
  - `INSERT INTO conversations (tenant_id, user_id, channel) RETURNING id`
  - Deliver reply: "Conversation reset ✓"
  - **STOP** — do not call pipeline, do not save to history.
- Partial matches (e.g., `/newer`) do NOT trigger reset.

### Step 5 — Load History and Format History

```sql
SELECT role, content FROM chat_messages
WHERE conversation_id = ?
ORDER BY created_at DESC
LIMIT 10
```
- Reverse result to oldest-first.
- Format as a plain-text block to be prepended to the current query:

Context:
user: <message>
assistant: <message>
...

User Query: <current query>

- If no history exists, send only `User Query: <current query>` (no Context block).


### Step 6 — Call Pipeline

- `POST` to `PIPELINE_URL` env var (defaults to mock endpoint during dev):
{
  "query": "Context:\nuser: What is RAG?\nassistant: RAG stands for...\n\nUser Query: Can you give an example?"
}


```
- The `query` field contains the full formatted context string (history + current message).
- Plain text only — no JSON nesting, no role arrays.


- Expected response:
```json
{
  "answer": "...",
  "model_used": "..."
}

```
- - `sources` and `follow_up_questions` are not returned by n8n; the gateway defaults both to `[]` before responding to the client.
- Timeout: `PIPELINE_TIMEOUT_SECONDS` = 120
- On timeout or non-2xx → deliver fallback error to user, do NOT save to history, log error.
- History formatting is the gateway's responsibility — n8n receives a single pre-composed string.
- Cap history at last 10 messages (HISTORY_LIMIT) to avoid oversized payloads.


### Step 7 — Deliver Response

**Web:** Return inline in HTTP 200:
```json
{
  "request_id": "...",
  "conversation_id": "...",
  "answer": "...",
  "sources": [...],
  "follow_up_questions": [...]
}
```

**Slack:** `chat.postMessage` to the channel in a thread:
- `channel` = stored from Step 1 (`event.channel`)
- `thread_ts` = stored from Step 1 (`event.ts`)
- Format with Block Kit: answer section + sources context block (cap 3 sources)

### Step 8 — Save to History (single transaction, after delivery)

```sql
BEGIN;
INSERT INTO chat_messages (conversation_id, role, content, sources)
  VALUES (?, 'user', ?, '[]');
INSERT INTO chat_messages (conversation_id, role, content, sources)
  VALUES (?, 'assistant', ?, ?::jsonb);
COMMIT;
```
- Only on pipeline success + successful delivery.
- On pipeline failure: nothing saved.

---

## 4. MessageContext (shared data carrier)

All channel adapters normalize their payload into this before processing:

```python
@dataclass
class MessageContext:
    request_id:      str            # UUID (web) | event_id (Slack)
    user_id:         UUID           # resolved internal user ID
    tenant_id:       UUID           # from JWT (web) | slack_workspace_map (Slack)
    source:          str            # "web" | "slack"
    query:           str            # message text
    conversation_id: UUID | None    # set in Step 3
    # Slack reply-back (None for web)
    slack_channel:   str | None
    slack_thread_ts: str | None
```

---

## 5. Endpoint Contracts

### Web — `POST /chat/query`

**Request:**
```json
{ "query": "What is the refund policy?", "conversation_id": "..." }
```
`conversation_id` is optional — omit to auto-find/create.

**Headers:** `Authorization: Bearer <JWT>`

**200 Response:**
```json
{
  "request_id": "...",
  "conversation_id": "...",
  "answer": "...",
  "sources": [{"title": "...", "url": "...", "chunk_id": "..."}],
  "follow_up_questions": ["..."]
}
```

**Errors:**
- `401` — invalid/expired JWT
- `403` — conversation_id belongs to another user
- `422` — missing query
- `502` — pipeline failure (return fallback: `{"answer": "Sorry, something went wrong — please try again.", "sources": [], "follow_up_questions": []}`)

### Slack — `POST /webhooks/slack`

- Invalid HMAC → `403`
- `url_verification` → `{"challenge": "..."}`
- `bot_id` set → `200` no-op
- Duplicate `event_id` → `200` no-op
- Valid message → `200` ACK immediately; answer delivered async via `chat.postMessage` in thread

### Mock Pipeline — `POST /mock/pipeline`

Accepts any valid pipeline payload, always returns a canned success response.
Used during development. Replaced by real n8n URL in production via `PIPELINE_URL` env var.

### Slack Onboard — `POST /webhooks/slack/onboard`

Looks up a user by email in the connected Slack workspace and returns their Slack member ID.
Intended for admin use to link a platform user to their Slack identity before they interact via bot.

**Headers:** `Authorization: Bearer <JWT>` (admin only)

**Request:**
```json
{ "email": "user@example.com" }
```

**200 Response:**
```json
{
  "slack_user_id": "U0123456789",
  "email": "user@example.com"
}
```

**Errors:**
- `401` — invalid/expired JWT
- `403` — caller is not an admin
- `404` — email not found in the Slack workspace (user must accept a Slack invite first)
- `409` — user already has a `slack_user_id` set in the platform users table
- `503` — Slack API unreachable or returned an unexpected error

**Implementation notes:**
- Calls `users.lookupByEmail` Slack API with `SLACK_BOT_TOKEN`
- On success, `UPDATE users SET slack_user_id = ? WHERE email = ? AND tenant_id = ?`
- The tenant is derived from the admin's JWT (`tenant_id` claim)
- Do NOT create a new user row — only link an existing platform user to their Slack identity

---

## 6. Database

### Decision: Existing tables are sufficient — no schema changes needed.

**`conversations`** — one row per (user_id, channel)

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | auto-generated |
| tenant_id | UUID FK → tenants | NOT NULL |
| user_id | UUID FK → users | NOT NULL |
| channel | VARCHAR(50) | `"web"` \| `"slack"` |
| title | VARCHAR(500) | nullable, unused for now |
| created_at | TIMESTAMPTZ | auto |

Constraint: `UNIQUE(user_id, channel)` — enforces one conversation per user per source.

**`chat_messages`** — append-only message log

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | auto-generated |
| conversation_id | UUID FK → conversations | `ON DELETE CASCADE` |
| role | VARCHAR(20) | `"user"` \| `"assistant"` |
| content | TEXT | message text |
| sources | JSON | `[]` default |
| created_at | TIMESTAMPTZ | auto |

**`processed_requests`** — Slack dedup

| Column | Type | Notes |
|---|---|---|
| request_id | VARCHAR(255) PK | Slack event_id |
| received_at | TIMESTAMPTZ | auto |

**`slack_workspace_map`** — Slack team_id → tenant_id mapping
**`users`** — has `slack_user_id` column for Slack identity resolution

### DB Query Count (per request)

| Step | Web | Slack |
|---|---|---|
| Dedup | — | 1 INSERT ON CONFLICT |
| Resolve identity | 0 (from JWT) | 1 SELECT (JOIN workspace+user) |
| Find/create conversation | 1 SELECT (+1 INSERT if new) | 1 SELECT (+1 INSERT if new) |
| Load history | 1 SELECT | 1 SELECT |
| Save messages | 2 INSERTs (1 txn) | 2 INSERTs (1 txn) |
| **Total (normal msg)** | **3–4** | **5–6** |

---

## 7. Files

| File | Action | Responsibility |
|---|---|---|
| `backend/app/services/types.py` | Modify | Simplified `MessageContext` dataclass |
| `backend/app/services/message_service.py` | **New** | All processing logic: resolve identity, conversation CRUD, reset, load history, call pipeline, deliver, save. Single entry point: `process_message(ctx)` |
| `backend/app/services/pipeline_client.py` | **New** | HTTP client: POST to `PIPELINE_URL`. Returns parsed response or raises on failure/timeout. |
| `backend/app/api/chat.py` | Modify | **M4** — Web adapter: JWT → build context → call `process_message` → return response. (Was M3 handoff; moved into M4 scope.) |
| `backend/app/api/webhooks.py` | Modify | Slack adapter: HMAC + dedup + ACK → dispatch `process_message` as BackgroundTask |
| `backend/app/api/mock_pipeline.py` | **New** | `POST /mock/pipeline` — canned response endpoint |
| `backend/app/bots/slack.py` | Modify | `post_reply()` + `post_text()` — Slack delivery via `chat.postMessage` |
| `backend/app/schemas/chat.py` | Keep | `ChatQueryRequest` — no changes |
| `backend/app/models/models.py` | Keep | No changes |
| `backend/app/main.py` | Modify | Register mock_pipeline router |
| `backend/app/api/webhooks.py` | Modify | Add `POST /webhooks/slack/onboard` — Slack email lookup via `users.lookupByEmail`, update `users.slack_user_id` |
### Files to remove (replaced by `message_service.py`)

| File | Reason |
|---|---|
| `backend/app/services/context_builder.py` | Logic moves into `message_service.py` |
| `backend/app/services/conversation_router.py` | Logic moves into `message_service.py` |
| `backend/app/services/message_handler.py` | Logic moves into `message_service.py` |
| `backend/app/services/n8n_client.py` | Replaced by `pipeline_client.py` |

---

## 8. Environment Variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SLACK_SIGNING_SECRET` | Yes (Slack) | `""` | HMAC verification |
| `SLACK_BOT_TOKEN` | Yes (Slack) | `""` | chat.postMessage |
| `PIPELINE_URL` | No | `http://localhost:8000/mock/pipeline` | Mock in dev; set to `https://n8n-production-c637.up.railway.app/webhook/retrieve` in prod |
| `PIPELINE_TIMEOUT_SECONDS` | No | `120` | HTTP timeout for pipeline calls |

---

## 9. Mock Pipeline Response

`POST /mock/pipeline` always returns:

```json
{
  "answer": "This is a sample response from the mock pipeline. In production, this will be a grounded answer from the RAG engine with source citations. [Sample Document, p.12]",
  "sources": [
    {
      "title": "Sample Product Manual",
      "url": "https://example.com/docs/manual",
      "chunk_id": "chunk-001"
    }
  ],
  "follow_up_questions": [
    "Can you explain this in more detail?",
    "What are the next steps?",
    "Who should I contact for further help?"
  ]
}
```

---

## 10. Acceptance Criteria

1. Web normal message → `POST /chat/query` returns 200 with answer; conversation auto-created if new
2. Web continue conversation → same user, no `conversation_id` → reuses existing (user_id, "web") conversation
3. Web foreign `conversation_id` → `403`, nothing created or saved
4. Web reset → query = `/new` → old conversation + messages deleted, new one created, confirmation returned, pipeline NOT called
5. Slack normal message → ACKs 200 within 3s; answer posted in thread via `chat.postMessage`
6. Slack duplicate `event_id` → 200 no-op, no duplicate processing
7. Slack reset → `/new` → old conversation deleted, new one created, confirmation posted in thread, pipeline NOT called
8. Slack bot message → event with `bot_id` → 200 no-op
9. Slack invalid signature → `403`
10. Pipeline failure/timeout → error message delivered to user, nothing saved to `chat_messages`
11. History → pipeline receives last 10 messages as context
12. Mock pipeline → `POST /mock/pipeline` returns valid sample response
13. Invalid/expired JWT on web → `401`, nothing downstream runs
14. Slack onboard known email → `200` with `slack_user_id` returned; `users.slack_user_id` updated in DB
15. Slack onboard unknown email → `404`, nothing written to DB
16. Slack onboard duplicate (user already has `slack_user_id`) → `409`, no update performed
17. Slack onboard non-admin caller → `403`