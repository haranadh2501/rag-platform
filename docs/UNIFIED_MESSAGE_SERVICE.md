# Unified Message Service — Design Document

**Status:** Draft  
**Author:** Tushar  
**Date:** 2026-06-10  
**Scope:** All 4 input channels → single processing service

---

## Problem Statement

The platform accepts queries from 4 channels: Website, WhatsApp, Slack, and MCP. Without a unified design:

- Each channel duplicates auth, conversation lookup, and RAG call logic
- Conversation history can leak or get misrouted between users
- No consistent way to reset a conversation
- Behaviour diverges silently as each channel evolves independently

This document defines a single service that all 4 channels connect to.

---

## High-Level Flow (Summary)

1. **Receive** — Get inputs from the 4 sources and respond back with 200 status
2. **Authorise** — Check if the user is authorised or not
3. **Identify** — Get the user ID (common across all sources) and their last `conversation_id` on the basis of source
4. **Reset check** — If the message is `/new`, `/restart`, or `/clear`, create a new `conversation_id`
5. **Load history** — Get the last 5–10 messages / conversation history, if not a new conversation
6. **Call n8n** — Send `user_id`, `conversation_id`, `request_id`, history, and `current_message`
7. **Save query** — Save `current_message` to the DB
8. **Route reply** — After receiving the response from n8n, check that `request_id` and `conversation_id` match, then send it back to the user on the same conversation and source
9. **Save response** — Save the response in the DB

> See **End-to-End Request Flow** below for the detailed, corrected version of each step (dedup, validation order, tenant scoping, atomic writes, sync vs async delivery).

---

## Advantages Over the Original Spec Flow

The module specs (M3/M4/M12) describe a per-channel, fully-synchronous flow. This design improves on it:

**Reliability**
- Handles webhook retries: Slack retries after 3s, Twilio after ~15s — real RAG latency (rerank + LLM + self-check + fallback retry) will exceed both. Dedup (Step 0) + immediate ACK prevent duplicate processing; the spec flow would process the same message twice.
- No orphaned messages: user + assistant messages saved in one transaction *after* n8n succeeds. Spec flow leaves a dangling user message in DB when n8n fails, corrupting the next history load.
- Failure path defined: user always gets a reply (answer or fallback), never silence + bare 502.

**One implementation instead of four**
- Single `message_handler.py` replaces duplicated load-history → retrieve → save loops in M3 (web), M12 (WhatsApp), M4 (Slack), MCP.
- Resolves spec inconsistency: M3 says last 5 messages, M6 says last 10 — now one `HISTORY_WINDOW` constant for all channels.
- A bug fixed once is fixed everywhere; a new channel (e.g. Teams) is just a thin adapter.

**Conversation lifecycle (absent from specs)**
- `/new` reset — spec had no way for a WhatsApp/Slack user to ever start a fresh conversation.
- `is_active` + `last_message_at` give a clean definition of "current conversation".
- Leak-proofing is an explicit invariant: every lookup scoped to `(tenant_id, identity, channel, is_active)`.

**Better answers, bounded cost**
- Query rewriting from history before embedding — "what about damaged items?" retrieves junk if embedded literally (spec flow). Biggest multi-turn RAG quality win.
- Rolling summary (Phase 2) keeps long-conversation context at a fixed token budget.

**Right pattern per channel**
- Sync where sync is fine (Web/MCP — no polling/WebSocket infra needed).
- Async only where forced (WhatsApp/Slack webhook timeouts).
- One-line upgrade path to Redis Streams when BackgroundTasks limits start to matter — the architecture doesn't change.

---

## End-to-End Request Flow

**Step 0 — Deduplication:** Slack retries webhooks if not ACKed within 3 seconds; Twilio retries too. Skip messages already processed.
- Extract `request_id` from the channel (Twilio `MessageSid`, Slack `event_id`, JSON-RPC `id`; generate UUID for Web)
- If `request_id` already seen → return 200 immediately, do not process
- Track seen IDs via unique constraint in DB (or Redis SETNX later)

**Step 1 — Validate auth / signature:** Reject forged or unauthorized requests *before* ACKing. Validation is fast (<5 ms) and fits inside any webhook timeout.
- WhatsApp: Twilio HMAC via `X-Twilio-Signature` + `TWILIO_AUTH_TOKEN`
- Slack: HMAC-SHA256 via `X-Slack-Signature` + signing secret
- Web: JWT signature + expiry
- MCP: API key lookup (`X-MCP-API-Key`)
- Invalid → 401/403, nothing downstream runs

**Step 2 — Build MessageContext:** Normalize the channel-specific payload into the one shared envelope all later layers use.
- Resolve `user_id` (JWT claims / phone → user / slack ID → user / API key → user)
- Resolve `tenant_id` — **critical: decides which knowledge base n8n queries** (JWT claims, `whatsapp_tenant_map`, `slack_workspace_map`, API key record)
- Set `source`, `external_identity`, `raw_query`, `request_id`, `reset_requested`, optional `conversation_id` / media

**Step 3 — Handle `/new` command (short-circuit):** A reset is a command, not a query — it never reaches n8n.
- If `raw_query` is `/new`, `/restart`, or `/clear`: UPDATE old conversation SET `is_active = false`
- CREATE new conversation row (`is_active = true`)
- Reply "New conversation started ✓" directly and STOP

**Step 4 — Find or create conversation:** One router function for all channels; every lookup scoped to at least `(tenant_id, identity)` so conversations can never leak.
- Web/MCP with `conversation_id`: validate it belongs to `(user_id, tenant_id)`, use it
- Web/MCP without: create new
- WhatsApp/Slack: find row WHERE `(tenant_id, external_id, channel, is_active = true)`; create if none

**Step 5 — ACK (channel-dependent):** Only bot channels have hard webhook timeouts; Web/MCP stay synchronous.
- WhatsApp/Slack: return 200 now, continue in a FastAPI BackgroundTask
- Web/MCP: skip this step — run the handler inline and return the answer in the same HTTP response

**Step 6 — Load context:** Postgres is the memory; the LLM API is stateless.
- Load last 10 messages (`HISTORY_WINDOW`, same constant for all channels) for `conversation_id`
- Load `conversations.summary` (rolling summary of older turns, if any)

**Step 7 — Call n8n:** All LLM work (query rewriting, retrieval, generation, summarization) lives here, per CLAUDE.md.
- POST `{request_id, tenant_id, conversation_id, current_message, history, summary}`
- n8n rewrites the query using history → embeds → retrieves chunks → generates grounded answer
- If summary threshold crossed, n8n also returns `new_summary`

**Step 8 — Persist (one transaction):** Atomic write after success — saving the user message before the n8n call would leave an orphaned message if n8n fails.
- On success: INSERT user message + assistant message, UPDATE `summary`, `last_message_at`, `message_count`
- On failure: do NOT save, send fallback reply ("Sorry, something went wrong — please try again"), log the error

**Step 9 — Deliver reply:** Channel-specific formatting on the way out.
- WhatsApp: Twilio REST API `messages.create()`, truncate 1600 chars
- Slack: `chat.postMessage` in thread, Block Kit
- Web/MCP: returned directly in the HTTP response from Step 5's inline run

---

## Architecture Overview

```
Website   ─────┐
WhatsApp  ─────┤──→  Channel Adapter  ──→  Auth + Context Builder
Slack     ─────┤                                    │
MCP       ─────┘                                    ▼
                                         Conversation Router
                                                    │
                                                    ▼
                                    ┌───────────────────────────┐
                                    │   Unified Message Handler  │
                                    │   (FastAPI BackgroundTask) │
                                    │                           │
                                    │   1. Load history         │
                                    │   2. Call n8n RAG         │
                                    │   3. Save messages        │
                                    │   4. Send reply via       │
                                    │      channel API          │
                                    └───────────────────────────┘
```

**WhatsApp/Slack return HTTP 200 immediately** (hard webhook timeouts) and process in a background task. **Web/MCP run synchronously** — no timeout pressure, answer returned in the same HTTP response.

---

## What Each Channel Sends Us

| Field | Website | WhatsApp | Slack | MCP |
|---|---|---|---|---|
| User identity | JWT token | Phone number (`From`) | Slack user ID (`event.user`) | API Key (`X-MCP-API-Key`) |
| Organisation / Tenant | Inside JWT | Lookup via `whatsapp_tenant_map` | Lookup via `slack_workspace_map` | Lookup via API key record |
| Message text | JSON body `query` | Form field `Body` | `event.text` | JSON-RPC `params.query` |
| Conversation ID | JSON body (optional) | None — derived from phone | None — derived from user + workspace | `params.conversation_id` (optional) |
| Request ID | Not provided — we generate | Twilio `MessageSid` | Slack `event_id` | JSON-RPC `id` |
| File / Media | Multipart upload | `MediaUrl0` + `MediaContentType0` | `files` array in event | Base64 or URL in params |
| Reset signal | No `conversation_id` sent | User types `/new` | User types `/new` | No `conversation_id` sent |
| Verification | JWT signature | Twilio HMAC (`X-Twilio-Signature`) | Slack HMAC (`X-Slack-Signature`) | API key itself |

---

## Layer 1 — Channel Adapters

Each adapter is a thin normalizer. Its only job: extract raw fields from the channel-specific format and pass them forward. No business logic here.

**Files:**
- `backend/app/api/chat.py` — Web adapter
- `backend/app/api/webhooks.py` — WhatsApp + Slack adapters
- `backend/app/mcp/server.py` — MCP adapter

---

## Layer 2 — Auth + Context Builder

All 4 adapters call one function that validates the incoming identity and produces a `MessageContext` object.

```python
@dataclass
class MessageContext:
    request_id: str        # UUID — generated here if not provided by channel
    source: ChannelType    # WEB | WHATSAPP | SLACK | MCP
    user_id: UUID          # internal UUID resolved from identity signal
    username: str          # display name
    tenant_id: UUID        # which org's knowledge base to query
    org_id: UUID           # parent organisation
    tenant_access: list    # list of tenant UUIDs this user can query
    external_identity: str # raw phone number / slack user ID / email
    raw_query: str         # the message text
    reset_requested: bool  # True if user sent /new
    conversation_id: UUID  # None here — resolved in Layer 3
    media_url: str | None  # file attachment if present
```

**Auth resolution per channel:**

| Channel | How tenant_id is resolved |
|---|---|
| Web | Decoded from JWT claims |
| WhatsApp | `SELECT tenant_id FROM whatsapp_tenant_map WHERE phone_number = $1` |
| Slack | `SELECT tenant_id FROM slack_workspace_map WHERE team_id = $1` |
| MCP | `SELECT tenant_id FROM api_keys WHERE key_hash = $1` |

If auth fails → reject immediately with appropriate error. Nothing downstream runs.

**Reset detection (WhatsApp + Slack only):**

```
if raw_query.strip().lower() in ["/new", "reset", "new chat"]:
    reset_requested = True
    raw_query = ""  # or prompt user for their first message
```

---

## Layer 3 — Conversation Router

One function handles all conversation lifecycle for all channels.

```
find_or_create_conversation(ctx: MessageContext) → UUID
```

**Decision logic:**

```
if reset_requested:
    → UPDATE old conversation SET is_active = false
    → CREATE new conversation row (is_active = true), return new UUID

elif source == WEB or source == MCP:
    if conversation_id provided:
        → VALIDATE it belongs to (user_id, tenant_id), use it
    else:
        → CREATE new conversation

elif source == WHATSAPP:
    → FIND conversation WHERE (tenant_id, external_identity=phone, is_active = true)
    → if none exists: CREATE new

elif source == SLACK:
    → FIND conversation WHERE (tenant_id, external_identity=slack_user_id, team_id, is_active = true)
    → if none exists: CREATE new
```

**Isolation guarantee:** Every lookup is scoped to at minimum `(tenant_id, user_identity)`. A WhatsApp user cannot land in a Web user's conversation — the identity types are different columns.

Old conversations are never deleted on reset — only a new row is created. Full audit history is preserved.

---

## Layer 4 — Unified Message Handler

**This is the core service.** Lives at `backend/app/services/message_handler.py`.  
All 4 channel adapters import and call this single function.

```
handle_message(ctx: MessageContext) → None
```

Steps:
1. Load last 10 messages from `chat_messages` + `conversations.summary` for `conversation_id`
2. Call `n8n_client.retrieve(query, tenant_id, history, summary)`
3. Save user message + assistant response to `chat_messages` (one transaction)
4. If n8n returned an updated `new_summary`, save it to `conversations.summary`
5. Call channel-specific delivery function with the response

### FastAPI BackgroundTasks (Option C)

Every channel route returns HTTP 200 immediately and fires this handler as a background task:

```python
@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    ctx = await build_context(request)          # Layer 2
    ctx.conversation_id = await find_or_create_conversation(ctx)  # Layer 3
    background_tasks.add_task(handle_message, ctx)  # Layer 4 async
    return Response(content=twiml_ack(), media_type="application/xml")  # 200 immediately
```

This pattern is the same across all 4 channel routes.

---

## Layer 5 — Response Formatters

After the handler has a response, it calls the channel-specific delivery function:

| Channel | Delivery method | Format |
|---|---|---|
| Web | Same HTTP response (synchronous) | JSON — answer + sources + follow_up_questions |
| WhatsApp | Twilio REST API `messages.create()` | Plain text, max 1600 chars |
| Slack | `chat.postMessage` in thread | Slack Block Kit |
| MCP | Same JSON-RPC response (synchronous) | `{ result: { answer, sources } }` |

Web and MCP run inline — no polling or WebSocket needed. Only the bot channels (with hard webhook timeouts) use the ACK-then-push pattern.

---

## Conversation History Strategy

**Approach: Sliding window (Phase 1) + rolling summary (Phase 2).**
Postgres is the single source of truth — LLM APIs are stateless and retain nothing between calls; we are the memory.

### Phase 1 — Sliding Window

Every message is stored in `chat_messages`. On each request, load the last 10 turns scoped strictly to `conversation_id`:

```sql
SELECT role, content FROM chat_messages
WHERE conversation_id = $1
ORDER BY created_at DESC
LIMIT 10
```

Passed to n8n as `conversation_history` array. **One `HISTORY_WINDOW = 10` constant in the unified handler — identical for all 4 channels** (resolves the M3 "last 10" vs M12 "last 5" spec inconsistency).

### Phase 2 — Rolling Summary

When a conversation exceeds ~10 turns, older context is compressed into a 2–3 sentence summary stored on `conversations.summary`. Context sent to the LLM = `summary + last N messages` — bounded token cost regardless of conversation length.

### Division of Responsibility (per CLAUDE.md: no LLM calls in FastAPI)

| FastAPI (`message_handler.py`) | n8n (retrieval pipeline) |
|---|---|
| Store user + assistant messages | Query rewriting using history (LLM) |
| Load last N messages | Generate answer with history + summary in prompt (LLM) |
| Load / save `conversations.summary` | Generate updated summary when threshold crossed (LLM) |
| Send `{query, tenant_id, history, summary}` to n8n | Return `{answer, sources, new_summary?}` |

**Why this split:** state lives in one place (Postgres, owned by the backend); n8n stays stateless (data in, data out — easy to test and re-import); all LLM calls and token spend stay in one layer.

### Per-Request Flow

1. FastAPI loads last 10 messages + `conversations.summary`
2. Sends `{query, tenant_id, history, summary}` to the n8n webhook
3. n8n **rewrites the query using history** (e.g. "what about damaged items?" → "what is the refund policy for damaged items?") *before* embedding — critical for follow-up retrieval quality
4. n8n retrieves chunks, generates the grounded answer
5. If `message_count` crossed the summary threshold, n8n makes one extra `gpt-4o-mini` call to update the summary and includes `new_summary` in its response (can run in parallel with answer delivery — user never waits on summarization)
6. FastAPI saves both messages + `new_summary` (if present) in **one transaction** — atomic write prevents an orphaned user message corrupting the next history load

---

## New Conversation

| Channel | How user triggers it |
|---|---|
| Website | Clicks "New Chat" button — client sends request without `conversation_id` |
| MCP | Sends request without `conversation_id` |
| WhatsApp | Types `/new` in chat |
| Slack | Types `/new` in the message |

In all cases the Conversation Router creates a new row. The old conversation stays in the DB untouched.

---

## Required Schema Changes

The current `conversations` table (see `database/init.sql`) is missing fields needed by this design. Add via Alembic migration:

```sql
ALTER TABLE conversations ADD COLUMN is_active       BOOLEAN DEFAULT true;  -- /new marks old convo inactive
ALTER TABLE conversations ADD COLUMN last_message_at TIMESTAMPTZ;           -- find most recent conversation
ALTER TABLE conversations ADD COLUMN summary         TEXT;                  -- Phase 2 rolling summary
ALTER TABLE conversations ADD COLUMN message_count   INTEGER DEFAULT 0;     -- summary threshold check without COUNT(*)

CREATE INDEX idx_conv_active ON conversations (tenant_id, external_id, channel, is_active);

-- Webhook dedup (Step 0): Twilio/Slack retry if not ACKed fast enough
CREATE TABLE processed_requests (
  request_id  VARCHAR(255) PRIMARY KEY,   -- MessageSid / event_id
  received_at TIMESTAMPTZ DEFAULT NOW()   -- purge rows older than 24h via cron
);
```

Without `is_active`, the `/new` command has no clean implementation — the WhatsApp/Slack lookup by `(tenant_id, external_id)` cannot distinguish the old conversation from the new one.

`chat_messages` needs no changes.

---

## Known Limitations of Option C (FastAPI BackgroundTasks)

| Limitation | Impact |
|---|---|
| Tasks live in memory | If server restarts mid-processing, task is lost and user gets no reply |
| No automatic retry | If n8n call fails inside the task, it silently dies |
| No task visibility | Cannot see queued / running / failed tasks |
| Single process | All background tasks share one Uvicorn process |

**Acceptable for:** Development, demos, low-to-medium concurrent users (~50–100).  
**Not acceptable for:** Production with real users where reliability matters.

---

## Upgrade Path (When Option C Is Not Enough)

Replace `background_tasks.add_task(handle_message, ctx)` with a Redis Streams publish call. The handler moves to a standalone worker process. The `MessageContext` object serializes to JSON and is the queue payload. Everything else (layers 1–3 and 5) stays identical.

```
Option C  →  Option A (Redis Streams)
Change: 1 line in each route + add worker process
No change: MessageContext, Conversation Router, Message Handler logic, Response Formatters
```

---

## Files Involved

| File | Role |
|---|---|
| `backend/app/api/chat.py` | Web adapter (M3) |
| `backend/app/api/webhooks.py` | WhatsApp + Slack adapters (M4) |
| `backend/app/mcp/server.py` | MCP adapter (M4) |
| `backend/app/bots/whatsapp.py` | WhatsApp response delivery (M12) |
| `backend/app/bots/slack.py` | Slack response delivery (M4) |
| `backend/app/bots/tenant_map.py` | Phone → tenant lookup (M12) |
| `backend/app/services/message_handler.py` | **Core unified handler — new file** |
| `backend/app/services/conversation_router.py` | **Conversation lifecycle — new file** |
| `backend/app/services/context_builder.py` | **Auth + MessageContext — new file** |
| `database/init.sql` | `conversations` + `chat_messages` tables |
