# SPEC — Ephemeral Session Webhooks (WhatsApp)

**Owner**: M4 | **Branch**: `feature/ephemeral_integration_trial`

## Overview

Add an opt-in ephemeral document analysis mode to WhatsApp. Users send `/ephemeral_ingest` to enter a session where they can upload documents, have them indexed via n8n, and ask grounded Q&A against only those documents. Outside this mode, everything continues through the existing normal retrieval pipeline.

### Scope

- **WhatsApp only** — Slack and web chat are not affected.
- **Additive** — no changes to `message_service.py`, `pipeline_client.py`, or any existing Slack/web flow.
- **Multi-document** — users can upload multiple files per session (one n8n ingest API call per file, sent sequentially).
- **File size cap** — 9 MB per file. Enforced **server-side in FastAPI** before base64 encoding. The n8n endpoint accepts up to 10 MB but FastAPI enforces 9 MB as the operational limit.

---

## n8n Endpoints (External — Hosted on Railway)

Base URL: `https://n8n-production-c637.up.railway.app`

All endpoints are scoped by `tenant_id` + `conversation_id` (called `n8n_session_id` internally to avoid confusion with our DB `conversation_id`).

### 1. Ingest — `POST /webhook/ingest-ephemeral-wf`

Upload a document as base64. Accepted types: pdf, png, jpg/jpeg, txt. FastAPI enforces a 9 MB file size cap before calling this endpoint.

**Request:**
```json
{
  "conversation_id": "<N8N_SESSION_UUID>",
  "tenant_id": "<TENANT_UUID>",
  "source_name": "user-upload.pdf",
  "file_base64": "<BASE64_OF_FILE_BYTES>",
  "ttl_seconds": 3600
}
```

**Success 200:**
```json
{
  "status": "completed",
  "conversation_id": "...",
  "chunk_count": 8,
  "used_ocr": true,
  "expires_at": "2026-06-20T...Z"
}
```

**Failure:** 422 (validation) / 5xx (runtime)
```json
{
  "status": "failed",
  "phase": "...",
  "node": "...",
  "statusCode": 422,
  "error": "..."
}
```

**Timeout handling**: FastAPI applies a **300-second (5-minute) timeout** to each ingest call using `asyncio.wait_for`. If the call times out, send the user: `"⏳ Processing timed out for [source_name]. Please try again with a smaller file."` and revert session status (see State Machine).

**Retry**: Retry once on 5xx before marking as failed.

### 2. Retrieve — `POST /webhook/retrieve-ephemeral`

Grounded answer over only that session's uploaded docs.

**Request:**
```json
{
  "query": "What is the refund window?",
  "tenant_id": "<TENANT_UUID>",
  "conversation_id": "<N8N_SESSION_UUID>",
  "max_chunks": 5,
  "conversation_history": [
    {"role": "user", "content": "earlier question"},
    {"role": "assistant", "content": "earlier answer"}
  ]
}
```

- `max_chunks` optional (default 5, range 1–20).
- `conversation_history` — last 10 messages loaded from `chat_messages` DB table for this session's `conversation_id`, oldest-first. Same pattern as `message_service._load_history`. FastAPI always sends the full history; n8n does not maintain history server-side.

**Success 200:**
```json
{
  "answer": "The refund window is 30 days ... [1].",
  "sources": [
    {
      "chunk_text": "...",
      "source_name": "refund-policy.txt",
      "chunk_index": 0,
      "score": 0.94
    }
  ],
  "follow_up_questions": [],
  "faithfulness": null,
  "requires_clarification": false,
  "conversation_id": "<N8N_SESSION_UUID>",
  "metadata": {
    "model": "deepseek-v4-flash",
    "chunks_retrieved": 1
  }
}
```

Empty session → 200, `sources: []`, answer: "I couldn't find any documents in this session…"

### 3. Purge — `POST /webhook/purge-ephemeral`

Wipe session data immediately. TTL auto-purges hourly as backstop.

**Request:**
```json
{
  "conversation_id": "<N8N_SESSION_UUID>",
  "tenant_id": "<TENANT_UUID>"
}
```

**Success 200:**
```json
{
  "status": "purged",
  "conversation_id": "...",
  "deleted_count": 3
}
```

Idempotent — `deleted_count: 0` is fine.

### Operational Notes

- **Isolation**: server-side filtering by `tenant_id` + `conversation_id`. Wrong tenant → 0 results.
- **Errors**: structured — check `statusCode` (422 = bad input, 5xx = server) and `phase`/`error`.
- **Burst**: rapid ingests can transiently 500 → retry once on 5xx.
- **Purge auth**: currently unauthenticated; `token` field will be added later.
- **No MOCK_N8N path** — ephemeral endpoints always call the real n8n URLs. The existing `MOCK_N8N` flag only gates the standard ingest/retrieve pipeline and is not used here.

---

## State Machine

A WhatsApp user is always in one of two modes:

| Mode | Condition | Pipeline |
|------|-----------|----------|
| **Normal** (default) | No active `ephemeral_sessions` row | `pipeline_client.call_pipeline()` |
| **Ephemeral** | Active `ephemeral_sessions` row exists | n8n ephemeral endpoints |

### Ephemeral Sub-States

```
NORMAL MODE
  │
  ├─ /ephemeral_ingest ──────────────→ AWAITING_DOCUMENT
  │                                        │
  │                                        ├─ file upload ──→ INGESTING ──(n8n 200)──→ READY
  │                                        │                       │                      │
  │                                        │             timeout/5xx fail          ┌──────┤
  │                                        │           (doc_count==0 → AWAITING)   │      │
  │                                        │           (doc_count >0 → READY)      │   upload more
  │                                        │                                        │      │
  │                                        │                               INGESTING ←────┘
  │                                        │
  │                                        ├─ text query ──→ "📎 Upload a document first."
  │                                        │
  │                                        └─ /end_session ──→ purge ──→ NORMAL MODE
  │
  ├─ /end_session (no session) ──→ "No active session."
  │
  ├─ /reset | /new | /clear (ephemeral active) ──→ purge + conversation delete ──→ NORMAL MODE
  │
  ├─ file upload (no session) ──→ "📎 Use /ephemeral_ingest to analyze uploaded documents."
  │
  └─ text query (no session) ──→ existing pipeline (UNCHANGED)
```

### Status Transitions

| From | Event | To |
|------|-------|----|
| — | `/ephemeral_ingest` | `awaiting_document` |
| `awaiting_document` | file upload received | `ingesting` |
| `ready` | file upload received | `ingesting` |
| `ingesting` | n8n 200 OK | `ready` |
| `ingesting` | n8n 5xx (after 1 retry) OR timeout (`doc_count > 0`) | `ready` |
| `ingesting` | n8n 5xx (after 1 retry) OR timeout (`doc_count == 0`) | `awaiting_document` |
| any | `/end_session` or `/reset` | row deleted |

### User-Facing Messages

| Trigger | Response |
|---------|----------|
| `/ephemeral_ingest` (no active session) | "📎 Ephemeral session started. Upload a document (PDF, image, or text file, max 9 MB)." |
| `/ephemeral_ingest` (session already active) | "⚠️ You already have an active ephemeral session. Send /end_session to exit first." |
| File upload (awaiting_document or ready) | *starts ingestion* |
| File upload success | "✅ Document indexed ({chunk_count} chunks, {doc_count} total docs). Ask me anything!" |
| File upload error (too large) | "⚠️ File too large (max 9 MB). Please send a smaller file." |
| File upload error (n8n 5xx after retry) | "❌ Failed to process [source_name]. Please try again." |
| File upload timeout | "⏳ Processing timed out for [source_name]. Please try again with a smaller file." |
| Text query (awaiting_document) | "📎 No documents uploaded yet. Please upload a file first." |
| Text query (ingesting) | "⏳ Still processing your document. Please wait a moment." |
| Text query (ready) | *calls retrieve-ephemeral, returns answer* |
| `/end_session` (active session) | *purges n8n session* → "Session ended ✓ — back to normal mode." |
| `/end_session` (no session) | "No active ephemeral session." |
| `/reset` (active session) | *purges n8n session + deletes conversation* → "Conversation reset ✓" |
| File upload (no session) | "📎 File uploads require ephemeral mode. Send /ephemeral_ingest first." |

---

## Database Schema

### Existing Cascade Chain (verified)

```
conversations (id)
  ├─ chat_messages.conversation_id  → ON DELETE CASCADE  ✓
  └─ ephemeral_sessions.conversation_id → ON DELETE CASCADE  ✓
```

**Delete strategy for `end_session` and `/reset`**:
Delete the `conversations` row. This single delete cascades to:
1. All `chat_messages` for that conversation (via `chat_messages.conversation_id ON DELETE CASCADE`).
2. The `ephemeral_sessions` row itself (via `ephemeral_sessions.conversation_id ON DELETE CASCADE`).

Never delete `ephemeral_sessions` first — that leaves an orphan conversation. Always delete the conversation row and let the DB handle the rest.

### New Table: `ephemeral_sessions`

```sql
CREATE TABLE ephemeral_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    n8n_session_id  UUID NOT NULL,
    status          VARCHAR(30) NOT NULL DEFAULT 'awaiting_document',
    total_chunks    INTEGER NOT NULL DEFAULT 0,
    doc_count       INTEGER NOT NULL DEFAULT 0,
    expires_at      TIMESTAMPTZ,               -- NULL until first successful ingest; set from n8n response
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fast lookup: one active session per user
CREATE INDEX idx_ephemeral_sessions_user ON ephemeral_sessions (user_id);

-- Enforce one session per user at the DB level (application logic alone is insufficient)
CREATE UNIQUE INDEX idx_ephemeral_sessions_one_per_user ON ephemeral_sessions (user_id);
```

**`expires_at`**: Stays `NULL` until the first successful ingest call. On first success, set it from `n8n_response["expires_at"]`. On subsequent ingests, update it if the new value is later. This field is informational — n8n's own TTL is the authoritative expiry; `expires_at` here is for display/audit only and does not affect other tables or services.

**Lifecycle**: Row is created on `/ephemeral_ingest`, deleted (via conversation cascade) on `/end_session` or `/reset`. At most one row per `user_id` at any time — enforced by both the `UNIQUE INDEX` and application logic.

---

## Conversation History

History in ephemeral sessions is stored in and retrieved from the same `chat_messages` table used by the normal pipeline. Each retrieve call follows this exact pattern (matching `message_service._load_history` and `_save_messages`):

**Loading history** (before calling retrieve-ephemeral):
```python
rows = (await db.execute(text("""
    SELECT role, content FROM chat_messages
    WHERE conversation_id = :cid
    ORDER BY created_at DESC
    LIMIT 10
"""), {"cid": ctx.conversation_id})).all()
history = [{"role": r.role, "content": r.content} for r in reversed(rows)]
```

**Saving messages** (after receiving answer from retrieve-ephemeral):
```python
# User message — explicit timestamp avoids same-transaction collision
await db.execute(text("""
    INSERT INTO chat_messages (conversation_id, role, content, sources, created_at)
    VALUES (:cid, 'user', :content, CAST(:sources AS JSONB), :ts)
"""), {"cid": ctx.conversation_id, "content": query, "sources": "[]", "ts": datetime.now(timezone.utc)})

# Assistant message with sources from n8n
await db.execute(text("""
    INSERT INTO chat_messages (conversation_id, role, content, sources, created_at)
    VALUES (:cid, 'assistant', :content, CAST(:sources AS JSONB), :ts)
"""), {"cid": ctx.conversation_id, "content": answer, "sources": json.dumps(sources), "ts": datetime.now(timezone.utc)})
await db.commit()
```

History is scoped to the ephemeral `conversation_id`. When the session ends and the conversation is deleted, all history is deleted with it via cascade.

---

## File Changes

### Step 1: Config — `backend/app/core/config.py`

Add 4 new settings:

```python
# ── n8n Ephemeral (WhatsApp) ──────────────────────────────────
N8N_EPHEMERAL_INGEST_WF_URL: str = "https://n8n-production-c637.up.railway.app/webhook/ingest-ephemeral-wf"
N8N_EPHEMERAL_RETRIEVE_URL: str = "https://n8n-production-c637.up.railway.app/webhook/retrieve-ephemeral"
N8N_EPHEMERAL_PURGE_URL: str = "https://n8n-production-c637.up.railway.app/webhook/purge-ephemeral"
MAX_WHATSAPP_EPHEMERAL_UPLOAD_BYTES: int = 9_437_184   # 9 MB hard cap
```

Note: The existing `MAX_WHATSAPP_UPLOAD_BYTES` (10 MB) governs the old ephemeral flow in `_handle_whatsapp_media`. The new `MAX_WHATSAPP_EPHEMERAL_UPLOAD_BYTES` (9 MB) governs this feature independently.

### Step 2: Model — `backend/app/models/models.py`

Add `EphemeralSession` ORM model:

```python
class EphemeralSession(Base):
    __tablename__ = "ephemeral_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    n8n_session_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(30), nullable=False, default="awaiting_document")
    total_chunks = Column(Integer, nullable=False, default=0)
    doc_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)   # NULL until first ingest
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
```

Use `datetime.now(timezone.utc)` — `datetime.utcnow()` is deprecated in Python 3.12.

### Step 3: Migration — `backend/alembic/versions/0004_ephemeral_sessions.py`

Revision ID: `0004_ephemeral_sessions` | Revises: `0003_uuid_defaults`

Standard Alembic migration creating `ephemeral_sessions` table + both indexes (lookup index + unique index on `user_id`).

### Step 4: n8n Client — `backend/app/services/n8n_client.py`

Add 3 new functions (no MOCK_N8N branch — these always call the real URLs):

```python
async def ingest_ephemeral_base64(
    tenant_id: str,
    n8n_session_id: str,
    source_name: str,
    file_base64: str,
    ttl_seconds: int = 3600,
) -> dict:
    """POST base64-encoded file to n8n ephemeral ingest workflow.

    Retries once on 5xx. Caller is responsible for applying a 300-second
    asyncio.wait_for timeout and handling asyncio.TimeoutError.
    """

async def retrieve_ephemeral(
    query: str,
    tenant_id: str,
    n8n_session_id: str,
    conversation_history: list[dict] | None = None,
    max_chunks: int = 5,
) -> dict:
    """POST query to n8n ephemeral retrieve endpoint.

    conversation_history is loaded from chat_messages by the caller (ephemeral_service)
    and passed here as a list of {"role": ..., "content": ...} dicts, oldest-first.
    """

async def purge_ephemeral(
    tenant_id: str,
    n8n_session_id: str,
) -> dict:
    """POST to n8n ephemeral purge to wipe session data immediately."""
```

### Step 5: Ephemeral Service — `backend/app/services/ephemeral_service.py` (NEW)

Core state-machine logic. All functions receive a `MessageContext` (from `app.services.types`) and `AsyncSession`.

```python
async def get_active_session(user_id: UUID, db: AsyncSession) -> EphemeralSession | None:
    """Return the active ephemeral_sessions row for this user, or None."""

async def start_session(ctx: MessageContext, db: AsyncSession) -> None:
    """Create conversation (channel='whatsapp', title='Ephemeral Session') +
    ephemeral_sessions row. n8n_session_id is a freshly minted uuid4 — NOT
    the same as conversation_id. Reply to user via WhatsApp.
    """

async def handle_upload(
    ctx: MessageContext,
    db: AsyncSession,
    session: EphemeralSession,
    media_url: str,
    media_type: str,
) -> None:
    """Download file from Twilio (with Twilio Basic Auth) → validate ≤9MB →
    base64 encode → set status='ingesting' → call n8n ingest_ephemeral_base64
    with a 300-second asyncio.wait_for timeout → on success: atomically
    update total_chunks and doc_count, set expires_at → reply to user.

    On 5xx (after 1 retry) or timeout: revert status to 'ready' if doc_count > 0,
    else revert to 'awaiting_document'. Send appropriate error/timeout message
    including the original source_name (filename).
    """

async def handle_query(
    ctx: MessageContext,
    db: AsyncSession,
    session: EphemeralSession,
) -> None:
    """Guard on session status ('ingesting' → busy message, 'awaiting_document'
    → no docs message). For 'ready': load chat_messages history (last 10,
    oldest-first) → call n8n retrieve_ephemeral → persist user+assistant
    messages to chat_messages → reply to user via WhatsApp.
    """

async def end_session(
    ctx: MessageContext,
    db: AsyncSession,
    session: EphemeralSession,
) -> None:
    """Call n8n purge_ephemeral (log error but continue if n8n is down) →
    DELETE conversation row (cascades to chat_messages + ephemeral_sessions) →
    reply to user.
    """
```

#### Twilio Media Download

When downloading a file from Twilio's `MediaUrl`, authenticate using HTTP Basic Auth:

```python
async with httpx.AsyncClient(timeout=30.0) as client:
    resp = await client.get(
        media_url,
        auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    )
    resp.raise_for_status()
    content = resp.content   # raw bytes
```

This matches the existing pattern in `_handle_whatsapp_media` in `webhooks.py`.

#### Atomic Chunk Count Update

Always use an atomic SQL increment — never fetch, add, then set:

```python
await db.execute(text("""
    UPDATE ephemeral_sessions
    SET total_chunks = total_chunks + :chunk_delta,
        doc_count    = doc_count + 1,
        status       = 'ready',
        expires_at   = COALESCE(expires_at, :exp)
    WHERE id = :sid
"""), {
    "chunk_delta": chunk_count,
    "exp": expires_at_from_n8n,
    "sid": session.id,
})
await db.commit()
```

`COALESCE(expires_at, :exp)` preserves any existing `expires_at` from a prior ingest and sets it only on the first success. `doc_count + 1` is also atomic for the same reason.

### Step 6: Webhook Routing — `backend/app/api/webhooks.py`

Modify `_process_whatsapp_message` to branch on ephemeral state. `RESET_COMMANDS` is already defined in `message_service` as `{"/new", "/reset", "/clear"}` — import it from there.

```python
async def _process_whatsapp_message(message_sid, from_number, query, media_url, media_type):
    async with AsyncSessionLocal() as db:
        ctx = MessageContext(request_id=message_sid, source="whatsapp",
                             query=query or ".", whatsapp_from=from_number)

        await message_service._resolve_identity(ctx, db)

        session = await ephemeral_service.get_active_session(ctx.user_id, db)
        query_lower = (query or "").strip().lower()

        # ── Command routing ──
        if query_lower == "/ephemeral_ingest":
            if session:
                await whatsapp.post_text(from_number,
                    "⚠️ Already in ephemeral mode. /end_session to exit first.")
            else:
                await ephemeral_service.start_session(ctx, db)
            return

        if query_lower == "/end_session":
            if session:
                await ephemeral_service.end_session(ctx, db, session)
            else:
                await whatsapp.post_text(from_number, "No active ephemeral session.")
            return

        if query_lower in message_service.RESET_COMMANDS:
            if session:
                await ephemeral_service.end_session(ctx, db, session)
                return
            # No active session — fall through to existing reset logic
            await message_service._find_or_create_conversation(ctx, db)
            await message_service._handle_reset(ctx, db)
            return

        # ── Ephemeral mode active ──
        if session:
            if media_url and media_type:
                await ephemeral_service.handle_upload(ctx, db, session, media_url, media_type)
            else:
                await ephemeral_service.handle_query(ctx, db, session)
            return

        # ── Normal mode ──
        if media_url and media_type:
            await whatsapp.post_text(from_number,
                "📎 File uploads require ephemeral mode. Send /ephemeral_ingest first.")
            return

        # Existing flow unchanged
        await whatsapp.post_text(from_number, "🤔 Thinking...")
        await message_service._find_or_create_conversation(ctx, db)
        await message_service.process_message(ctx, db)
```

### Step 7: Environment Variables — `.env` and `.env.example`

```env
# ── n8n Ephemeral Endpoints ──
N8N_EPHEMERAL_INGEST_WF_URL=https://n8n-production-c637.up.railway.app/webhook/ingest-ephemeral-wf
N8N_EPHEMERAL_RETRIEVE_URL=https://n8n-production-c637.up.railway.app/webhook/retrieve-ephemeral
N8N_EPHEMERAL_PURGE_URL=https://n8n-production-c637.up.railway.app/webhook/purge-ephemeral
MAX_WHATSAPP_EPHEMERAL_UPLOAD_BYTES=9437184
```

---

## What Stays Untouched

| File | Reason |
|------|--------|
| `services/message_service.py` | Normal pipeline — no changes |
| `services/pipeline_client.py` | Only used by normal mode |
| `bots/slack.py` | Slack unaffected |
| `api/chat.py` | Web chat unaffected |
| `models/models.py` (existing models) | No column changes to existing tables |
| `bots/whatsapp.py` | `post_text()` and `post_reply()` reused as-is |

---

## Module Ownership Note

This spec spans M4 (webhooks routing), M2 (Alembic migration `0004_ephemeral_sessions`), and introduces a new `ephemeral_service.py`. The migration must be coordinated with M2 — do not create `0004_ephemeral_sessions.py` without confirming M2 has no concurrent migration in flight.

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| User sends `/ephemeral_ingest` twice | Second call warns: "Already in ephemeral mode" |
| User uploads unsupported file type | `file_validator.validate_upload` (existing, in `services/file_validator.py`) rejects → WhatsApp error message |
| User uploads file > 9 MB | Rejected before base64 encoding → WhatsApp "File too large (max 9 MB)" warning |
| n8n ingest returns 5xx | Retry once; if still fails → error message with filename; revert status (ready if prior docs, else awaiting_document) |
| n8n ingest times out (> 5 min) | asyncio.TimeoutError caught; timeout message with filename; revert status same as above |
| n8n retrieve on empty session | Returns 200 with `sources: []` and "no documents" answer — handled gracefully |
| User sends query while ingesting | "⏳ Still processing…" — no retrieve call made |
| Server restart mid-session | Session persisted in DB — resumes correctly on next message |
| Purge fails (n8n down) | Log error, still DELETE conversation row (n8n TTL auto-purges ephemeral_chunks as backstop) |
| Concurrent file uploads | Each task uses atomic SQL `total_chunks = total_chunks + N` and `doc_count = doc_count + 1`; no lost-update race |
| Second `/ephemeral_ingest` race (two rapid taps) | DB `UNIQUE INDEX` on `user_id` prevents two session rows; second INSERT fails → application catches and replies "already active" |

---

## Testing Checklist

- [ ] `/ephemeral_ingest` creates session + conversation (channel='whatsapp'), returns awaiting_document
- [ ] Second `/ephemeral_ingest` → "Already in ephemeral mode" warning, no duplicate row
- [ ] File upload (≤9 MB, supported type) → n8n ingest → status=ready, total_chunks and doc_count updated atomically
- [ ] File upload (>9 MB) → rejected with "File too large (max 9 MB)" warning, session unchanged
- [ ] File upload (unsupported type) → file_validator rejects → error message, session unchanged
- [ ] n8n 5xx after retry (first doc) → error message with filename, status reverts to awaiting_document
- [ ] n8n 5xx after retry (subsequent doc, doc_count > 0) → error message with filename, status reverts to ready
- [ ] n8n ingest timeout >5 min → timeout message with filename, status reverts correctly
- [ ] Second file upload → atomically increments total_chunks and doc_count, doc_count=2
- [ ] Text query in `ready` state → history loaded from chat_messages → n8n retrieve called with history → answer returned → user+assistant messages persisted
- [ ] Text query history: second query includes first Q&A pair as context
- [ ] Text query in `awaiting_document` → "upload a document first"
- [ ] Text query in `ingesting` → "still processing"
- [ ] `/end_session` → purge called, conversation DELETE cascades to chat_messages + ephemeral_sessions, user back to normal mode
- [ ] `/reset` with active session → purge + conversation DELETE → normal mode, no orphan rows
- [ ] `/reset` without session → normal reset behavior unchanged (existing pipeline)
- [ ] File upload without session → "use /ephemeral_ingest first" warning
- [ ] Normal text query without session → existing pipeline (unchanged)
- [ ] `expires_at` is NULL at session creation; set after first successful ingest; not overwritten on subsequent ingests
- [ ] Twilio media download uses Basic Auth (TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN)
