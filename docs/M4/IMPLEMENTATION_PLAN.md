# M4 Implementation Plan — Unified Message Service (Web + Slack)

**Author:** Tushar | **Date:** 2026-06-17 | **Branch:** `feature/M4_webhook`  
**Spec:** `specs/MODULE_SPEC_M4.md`

---

## What This Plan Covers

Eight build phases that turn the M4 spec into working code. Each phase has a clear goal, exact files to touch, specific function signatures, and a done-check. Complete phases in order — later phases depend on earlier ones.

---

## Codebase Baseline (What Already Exists)

Before writing a single line, understand the current state:

| File | Current State | M4 Action |
|---|---|---|
| `backend/app/api/webhooks.py` | Stub — Slack handler returns `{"ok": True}` | Implement fully |
| `backend/app/bots/slack.py` | Stub — `handle_app_mention` logs and returns | Implement delivery |
| `backend/app/services/n8n_client.py` | Has `retrieve()` but wrong payload shape and 60s timeout | Update payload + timeout |
| `backend/app/api/chat.py` | Stub owned by M3 | Coordinate with M3 to wire M4 services |
| `backend/app/models/models.py` | `Conversation` missing `is_active`, `last_message_at`, `team_id`, `external_id`; no `ProcessedRequest` or `SlackWorkspaceMap` | Add via migration |
| `backend/app/services/context_builder.py` | Does not exist | Create |
| `backend/app/services/conversation_router.py` | Does not exist | Create |
| `backend/app/services/message_handler.py` | Does not exist | Create |

---

## Phase 0 — Database Migration & ORM

**Goal:** Get the schema M4 depends on into the DB before writing any service code.

### 0.1 — Add ORM Models

Edit `backend/app/models/models.py`:

**Add to `Conversation` class:**
```python
is_active      = Column(Boolean, default=True, nullable=False)
last_message_at = Column(DateTime, nullable=True)
team_id        = Column(String(64), nullable=True)   # Slack workspace ID; None for Web
external_id    = Column(String(255), nullable=True)  # slack_user_id / phone; None for Web
```

**Add new `ProcessedRequest` model** (dedup table):
```python
class ProcessedRequest(Base):
    __tablename__ = "processed_requests"
    request_id  = Column(String(255), primary_key=True)
    received_at = Column(DateTime, default=datetime.utcnow)
```

**Add new `SlackWorkspaceMap` model** (team_id → tenant_id):
```python
class SlackWorkspaceMap(Base):
    __tablename__ = "slack_workspace_map"
    team_id   = Column(String(64), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 0.2 — Write the Alembic Migration

Create `backend/alembic/versions/xxxx_m4_conversations.py`. Replace `xxxx` with the generated revision ID.

```python
"""M4: add is_active, last_message_at, team_id, external_id to conversations;
   add processed_requests and slack_workspace_map tables."""

revision = "xxxx_m4"
down_revision = "<previous_revision_id>"

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column("conversations", sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("conversations", sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("conversations", sa.Column("team_id", sa.String(64), nullable=True))
    op.add_column("conversations", sa.Column("external_id", sa.String(255), nullable=True))

    op.create_index("idx_conv_slack", "conversations", ["tenant_id", "external_id", "team_id", "is_active"])
    op.create_index("idx_conv_web",   "conversations", ["tenant_id", "user_id", "is_active"])

    op.create_table(
        "processed_requests",
        sa.Column("request_id",  sa.String(255), primary_key=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "slack_workspace_map",
        sa.Column("team_id",    sa.String(64), primary_key=True),
        sa.Column("tenant_id",  sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table("slack_workspace_map")
    op.drop_table("processed_requests")
    op.drop_index("idx_conv_web",   table_name="conversations")
    op.drop_index("idx_conv_slack", table_name="conversations")
    op.drop_column("conversations", "external_id")
    op.drop_column("conversations", "team_id")
    op.drop_column("conversations", "last_message_at")
    op.drop_column("conversations", "is_active")
```

Run: `alembic upgrade head`

### 0.3 — Done Check

```sql
\d conversations        -- shows is_active, last_message_at, team_id, external_id
\d processed_requests   -- shows request_id, received_at
\d slack_workspace_map  -- shows team_id, tenant_id
```

---

## Phase 1 — Core Types

**Goal:** Define `ChannelType` and `MessageContext` in one place so all other files import from here.

### Create `backend/app/services/types.py`

```python
import uuid
from dataclasses import dataclass, field
from enum import Enum

class ChannelType(str, Enum):
    WEB   = "WEB"
    SLACK = "SLACK"

@dataclass
class MessageContext:
    request_id:        str
    source:            ChannelType
    user_id:           uuid.UUID
    tenant_id:         uuid.UUID
    external_identity: str
    team_id:           str | None
    raw_query:         str
    reset_requested:   bool
    conversation_id:   uuid.UUID | None = field(default=None)
```

**Rules:**
- `conversation_id` starts as `None` for Slack; set inside `handle_message()`.
- `team_id` is `None` for Web.
- `reset_requested` is `True` only if `raw_query.strip().lower()` is one of the reset commands; always `False` for Web in the current sprint.

### Done Check

```python
from app.services.types import MessageContext, ChannelType
```
No import error.

---

## Phase 2 — Update `n8n_client.py`

**Goal:** Update the existing `retrieve()` function to match the spec payload shape and set the correct timeout.

### Edit `backend/app/services/n8n_client.py`

**Replace the `retrieve()` function:**

```python
async def retrieve(
    request_id:   str,
    tenant_id:    str,
    conversation_id: str,
    current_message: str,
    history:      list[dict],          # [{"role": "user"|"assistant", "content": "..."}]
) -> dict:
    """Call n8n retrieval workflow. Returns answer, sources, follow_up_questions."""
    if settings.MOCK_N8N:
        logger.info(f"[MOCK] retrieve tenant={tenant_id} query='{current_message[:50]}'")
        return MOCK_RETRIEVE_RESPONSE

    payload = {
        "request_id":      request_id,
        "tenant_id":       tenant_id,
        "conversation_id": conversation_id,
        "current_message": current_message,
        "history":         history,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:   # N8N_TIMEOUT_SECONDS = 120
        resp = await client.post(settings.N8N_RETRIEVE_WEBHOOK_URL, json=payload)
        resp.raise_for_status()
        return resp.json()
```

**Key changes from existing code:**
- Timeout: `60.0` → `120.0`
- Payload fields renamed to match spec: `query` → `current_message`, `conversation_history` → `history`, added `request_id` and `conversation_id`
- Removed `max_chunks` (n8n controls chunking internally)

**Leave `ingest()` untouched** — it is not part of M4's scope.

### Done Check

- `MOCK_N8N=true` → returns mock response without hitting n8n
- `MOCK_N8N=false`, n8n up → sends correct payload
- `MOCK_N8N=false`, n8n down → raises `httpx.TimeoutException` after 120s

---

## Phase 3 — `context_builder.py`

**Goal:** Normalize a raw channel payload into a `MessageContext`. No business logic here — only extraction and identity resolution.

### Create `backend/app/services/context_builder.py`

```python
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.types import MessageContext, ChannelType
from app.models.models import User, SlackWorkspaceMap
from app.core.security import decode_jwt   # existing helper from M2

logger = logging.getLogger(__name__)

RESET_COMMANDS = {"/new", "/restart", "/clear"}


async def build_slack_context(payload: dict, db: AsyncSession) -> MessageContext:
    """
    Build MessageContext from a Slack Events API payload.
    Raises ValueError if required fields are missing.
    Raises LookupError if the workspace is not mapped to a tenant.
    """
    event      = payload.get("event", {})
    team_id    = payload.get("team_id")
    slack_uid  = event.get("user")
    text       = event.get("text", "").strip()
    event_id   = payload.get("event_id")          # used as request_id

    if not all([team_id, slack_uid, event_id]):
        raise ValueError(f"Missing required Slack fields: team_id={team_id} user={slack_uid} event_id={event_id}")

    # Resolve tenant_id from Slack workspace
    result = await db.execute(
        select(SlackWorkspaceMap).where(SlackWorkspaceMap.team_id == team_id)
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise LookupError(f"Slack workspace {team_id} is not registered to any tenant")

    # Resolve internal user from Slack user ID
    result = await db.execute(
        select(User).where(
            User.tenant_id == mapping.tenant_id,
            User.external_slack_id == slack_uid,    # requires User.external_slack_id column (add in migration if absent)
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise LookupError(f"Slack user {slack_uid} not registered in tenant {mapping.tenant_id}")

    return MessageContext(
        request_id        = event_id,
        source            = ChannelType.SLACK,
        user_id           = user.id,
        tenant_id         = mapping.tenant_id,
        external_identity = slack_uid,
        team_id           = team_id,
        raw_query         = text,
        reset_requested   = text.strip().lower() in RESET_COMMANDS,
        conversation_id   = None,    # filled by find_or_create_conversation inside handle_message
    )


async def build_web_context(jwt_payload: dict, query: str, conversation_id: str | None) -> MessageContext:
    """
    Build MessageContext from a validated JWT and the POST /api/chat request body.
    jwt_payload is the decoded token dict from security.decode_jwt().
    """
    return MessageContext(
        request_id        = str(uuid.uuid4()),
        source            = ChannelType.WEB,
        user_id           = uuid.UUID(jwt_payload["sub"]),
        tenant_id         = uuid.UUID(jwt_payload["tenant_id"]),
        external_identity = jwt_payload.get("email", ""),
        team_id           = None,
        raw_query         = query,
        reset_requested   = False,
        conversation_id   = uuid.UUID(conversation_id) if conversation_id else None,
    )
```

**Important note on `User.external_slack_id`:** Check whether the `User` model already has a column to link a Slack user ID to an internal user. If not, add `external_slack_id = Column(String(255), nullable=True)` to the `User` model and include it in the Alembic migration. Without this, Slack user resolution has no linkage column.

### Done Check

- `build_slack_context()` with a valid payload and registered workspace → returns `MessageContext` with correct `tenant_id` and `user_id`
- Unknown `team_id` → raises `LookupError`
- Missing `event_id` → raises `ValueError`

---

## Phase 4 — `conversation_router.py`

**Goal:** Single function that handles all conversation lifecycle for both channels. Strict tenant isolation enforced on every query path.

### Create `backend/app/services/conversation_router.py`

```python
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.services.types import MessageContext, ChannelType
from app.models.models import Conversation

logger = logging.getLogger(__name__)


async def find_or_create_conversation(ctx: MessageContext, db: AsyncSession) -> uuid.UUID:
    """
    Returns the UUID of the active conversation for this request.
    Every lookup is scoped to (tenant_id, identity) — conversations cannot leak across users.

    Web:   validates existing conversation_id or creates a new one.
    Slack: finds active conversation by (tenant_id, external_id, team_id) or creates one.
    """
    if ctx.source == ChannelType.WEB:
        return await _web_conversation(ctx, db)
    return await _slack_conversation(ctx, db)


async def _web_conversation(ctx: MessageContext, db: AsyncSession) -> uuid.UUID:
    if ctx.conversation_id:
        # Validate ownership — prevent cross-user access
        result = await db.execute(
            select(Conversation).where(
                Conversation.id        == ctx.conversation_id,
                Conversation.user_id   == ctx.user_id,
                Conversation.tenant_id == ctx.tenant_id,
            )
        )
        convo = result.scalar_one_or_none()
        if not convo:
            raise PermissionError(f"Conversation {ctx.conversation_id} not found for this user")
        return convo.id

    # No conversation_id → create new
    return await _create_conversation(ctx, db)


async def _slack_conversation(ctx: MessageContext, db: AsyncSession) -> uuid.UUID:
    result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id    == ctx.tenant_id,
            Conversation.external_id  == ctx.external_identity,
            Conversation.team_id      == ctx.team_id,
            Conversation.is_active    == True,
        )
    )
    convo = result.scalar_one_or_none()
    if convo:
        return convo.id
    return await _create_conversation(ctx, db)


async def _create_conversation(ctx: MessageContext, db: AsyncSession) -> uuid.UUID:
    convo = Conversation(
        tenant_id         = ctx.tenant_id,
        user_id           = ctx.user_id,
        channel           = ctx.source.value.lower(),
        external_id       = ctx.external_identity,
        team_id           = ctx.team_id,
        is_active         = True,
    )
    db.add(convo)
    await db.flush()   # get the ID without committing
    return convo.id


async def reset_conversation(ctx: MessageContext, db: AsyncSession) -> uuid.UUID:
    """
    Called when reset_requested is True.
    Marks all active conversations for this identity as inactive, then creates a new one.
    Never deletes — full history is preserved.
    """
    if ctx.source == ChannelType.SLACK:
        await db.execute(
            update(Conversation)
            .where(
                Conversation.tenant_id   == ctx.tenant_id,
                Conversation.external_id == ctx.external_identity,
                Conversation.team_id     == ctx.team_id,
                Conversation.is_active   == True,
            )
            .values(is_active=False)
        )
    else:
        if ctx.conversation_id:
            await db.execute(
                update(Conversation)
                .where(
                    Conversation.id        == ctx.conversation_id,
                    Conversation.user_id   == ctx.user_id,
                    Conversation.tenant_id == ctx.tenant_id,
                )
                .values(is_active=False)
            )

    await db.flush()
    return await _create_conversation(ctx, db)
```

### Done Check

- Two Slack messages from same user + workspace → same `conversation_id` returned both times
- Slack `/new` → `reset_conversation()` sets old row `is_active=False`, new row created
- Web with another user's `conversation_id` → `PermissionError` raised (caller returns 403)
- Old conversations visible in DB with `is_active=False`

---

## Phase 5 — `message_handler.py`

**Goal:** The core unified handler. Identical entry point for both channels. Wrapped in a top-level try/except that always delivers a reply — even on unhandled exceptions.

### Create `backend/app/services/message_handler.py`

```python
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.types import MessageContext, ChannelType
from app.services.conversation_router import find_or_create_conversation
from app.services import n8n_client
from app.models.models import ChatMessage, Conversation
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

HISTORY_WINDOW    = 10
MAX_HISTORY_CHARS = 5000
FALLBACK_REPLY    = "Sorry, something went wrong — please try again."


async def handle_message(ctx: MessageContext) -> dict | None:
    """
    Unified message handler for Web and Slack.

    - Web:   runs inline; returns {"answer": ..., "sources": ..., "conversation_id": ...}
    - Slack: runs in BackgroundTask; returns None (delivery via chat.postMessage)

    The entire body is wrapped in try/except. Any unhandled exception logs the
    full traceback and delivers the fallback reply. This function must never
    silently terminate.
    """
    async with AsyncSessionLocal() as db:
        try:
            return await _run(ctx, db)
        except Exception:
            logger.error("handle_message failed", exc_info=True)
            await _deliver_error(ctx, FALLBACK_REPLY)
            return None


async def _run(ctx: MessageContext, db: AsyncSession) -> dict | None:
    # Step 1 — Slack only: resolve conversation (deferred from sync path)
    if ctx.source == ChannelType.SLACK:
        ctx.conversation_id = await find_or_create_conversation(ctx, db)

    # Step 2 — Load history with char budget
    history = await _load_history(ctx.conversation_id, db)

    # Step 3 — Call n8n
    n8n_response = await n8n_client.retrieve(
        request_id      = ctx.request_id,
        tenant_id       = str(ctx.tenant_id),
        conversation_id = str(ctx.conversation_id),
        current_message = ctx.raw_query,
        history         = history,
    )

    answer  = n8n_response.get("answer", FALLBACK_REPLY)
    sources = n8n_response.get("sources", [])

    # Step 4 — Persist in one transaction (only on success)
    async with db.begin():
        db.add(ChatMessage(
            conversation_id = ctx.conversation_id,
            role            = "user",
            content         = ctx.raw_query,
            sources         = [],
        ))
        db.add(ChatMessage(
            conversation_id = ctx.conversation_id,
            role            = "assistant",
            content         = answer,
            sources         = sources,
        ))
        await db.execute(
            Conversation.__table__.update()
            .where(Conversation.id == ctx.conversation_id)
            .values(last_message_at=datetime.now(timezone.utc))
        )

    # Step 5 — Deliver reply
    if ctx.source == ChannelType.SLACK:
        from app.bots.slack import post_reply
        await post_reply(ctx, answer, sources)
        return None
    else:
        return {
            "request_id":      ctx.request_id,
            "conversation_id": str(ctx.conversation_id),
            "answer":          answer,
            "sources":         sources,
            "follow_up_questions": n8n_response.get("follow_up_questions", []),
        }


async def _load_history(conversation_id, db: AsyncSession) -> list[dict]:
    """Load last HISTORY_WINDOW messages and trim to MAX_HISTORY_CHARS."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(HISTORY_WINDOW)
    )
    rows = result.scalars().all()
    rows = list(reversed(rows))   # oldest-first for n8n

    # Trim from oldest until total chars fit within budget
    while rows:
        total = sum(len(r.content) for r in rows)
        if total <= MAX_HISTORY_CHARS:
            break
        rows.pop(0)   # drop oldest

    return [{"role": r.role, "content": r.content} for r in rows]


async def _deliver_error(ctx: MessageContext, message: str) -> None:
    """Best-effort error delivery. Logs but does not raise if delivery itself fails."""
    try:
        if ctx.source == ChannelType.SLACK:
            from app.bots.slack import post_reply
            await post_reply(ctx, message, sources=[])
    except Exception:
        logger.error("_deliver_error: secondary failure sending error reply", exc_info=True)
```

### Done Check

- n8n success → both messages in DB, `last_message_at` updated
- n8n `TimeoutException` → nothing persisted, fallback reply sent, error logged with traceback
- Unhandled exception inside `_run` → fallback reply sent, exception logged, function returns `None`

---

## Phase 6 — Slack Adapter

**Goal:** Replace the stub in `webhooks.py` and `slack.py` with the full implementation.

### 6.1 — Edit `backend/app/api/webhooks.py`

Replace the `slack_events` stub with:

```python
import hashlib, hmac, json, logging, time
from fastapi import APIRouter, Request, Response, BackgroundTasks, HTTPException
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.context_builder import build_slack_context
from app.services.conversation_router import reset_conversation
from app.services.message_handler import handle_message
from app.models.models import ProcessedRequest

router = APIRouter()
logger = logging.getLogger(__name__)


def _verify_slack_signature(headers: dict, body: bytes) -> None:
    """Raises HTTPException 403 if HMAC does not match."""
    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")

    # Guard against replay attacks (5-minute window)
    if abs(time.time() - int(timestamp)) > 300:
        raise HTTPException(status_code=403, detail="Request timestamp too old")

    sig_base = f"v0:{timestamp}:".encode() + body
    expected = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        sig_base,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")


@router.post("/slack/events", summary="Slack Events API webhook")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    # Read raw bytes first — must happen before any other body access
    body = await request.body()

    # Step 1: HMAC verification (in-memory, fast)
    _verify_slack_signature(dict(request.headers), body)

    payload = json.loads(body)

    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}

    event = payload.get("event", {})

    # Ignore bot messages (prevents reply loops)
    if event.get("bot_id"):
        return Response(status_code=200)

    event_id = payload.get("event_id", "")

    # Step 0: Dedup — insert-on-conflict; if already seen, return 200 immediately
    async with AsyncSessionLocal() as db:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(ProcessedRequest).values(request_id=event_id).on_conflict_do_nothing()
        result = await db.execute(stmt)
        await db.commit()
        if result.rowcount == 0:
            return Response(status_code=200)   # already processed

    # Step 2: Build MessageContext
    try:
        async with AsyncSessionLocal() as db:
            ctx = await build_slack_context(payload, db)
    except (ValueError, LookupError) as e:
        logger.warning(f"Slack context build failed: {e}")
        return Response(status_code=200)   # ACK Slack; don't retry

    # Step 3: Reset command short-circuit
    if ctx.reset_requested:
        async with AsyncSessionLocal() as db:
            await reset_conversation(ctx, db)
            await db.commit()
        from app.bots.slack import post_text
        await post_text(
            channel   = event.get("channel"),
            thread_ts = event.get("ts"),
            text      = "New conversation started ✓",
        )
        return Response(status_code=200)

    # Step 5: ACK immediately — conversation lookup happens inside handle_message
    background_tasks.add_task(handle_message, ctx)
    return Response(status_code=200)
```

### 6.2 — Edit `backend/app/bots/slack.py`

Replace the stub with proper delivery functions:

```python
import logging
import httpx
from app.core.config import settings
from app.services.types import MessageContext

logger = logging.getLogger(__name__)

SLACK_API = "https://slack.com/api"


async def post_reply(ctx: MessageContext, answer: str, sources: list) -> None:
    """Post answer in thread. Called from handle_message after n8n success."""
    event_data = getattr(ctx, "_slack_event", {})   # attach event dict to ctx before dispatching
    channel   = event_data.get("channel", "")
    thread_ts = event_data.get("ts", "")

    blocks = _build_blocks(answer, sources)
    await _post_message(channel=channel, thread_ts=thread_ts, blocks=blocks, text=answer)


async def post_text(channel: str, thread_ts: str, text: str) -> None:
    """Send a plain-text message (used for reset confirmation and error replies)."""
    await _post_message(channel=channel, thread_ts=thread_ts, text=text, blocks=None)


async def _post_message(channel: str, thread_ts: str, text: str, blocks: list | None) -> None:
    payload = {
        "channel":   channel,
        "thread_ts": thread_ts,
        "text":      text,
    }
    if blocks:
        payload["blocks"] = blocks

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{SLACK_API}/chat.postMessage",
            headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"},
            json=payload,
        )
    data = resp.json()
    if not data.get("ok"):
        logger.error(f"chat.postMessage failed: {data.get('error')} channel={channel}")


def _build_blocks(answer: str, sources: list) -> list:
    """Build Slack Block Kit payload for a grounded RAG answer."""
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": answer}},
    ]
    if sources:
        source_lines = "\n".join(
            f"• *{s.get('title', 'Source')}*" + (f" (p.{s['page_number']})" if s.get("page_number") else "")
            for s in sources[:3]   # cap at 3 sources in the Slack card
        )
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f"*Sources:*\n{source_lines}"}]})
    return blocks
```

**Note on `ctx._slack_event`:** The Slack event dict (containing `channel` and `ts` for threading) must be attached to the `MessageContext` before dispatching the background task. Add `_slack_event: dict = field(default_factory=dict)` to the `MessageContext` dataclass in `types.py`, and populate it in `build_slack_context()`.

### Done Check

- Slack URL verification → `{"challenge": "..."}` returned
- Replay attack (timestamp > 5 min old) → 403
- Wrong signature → 403
- Bot message → 200, no processing
- Duplicate `event_id` → 200, no processing, no DB insert
- Unknown workspace → 200, warning logged
- Valid message → 200 within 3s; answer in Slack thread

---

## Phase 7 — Web Adapter (Coordinate with M3)

**Goal:** Wire M4's shared services into the Web chat endpoint. This file is M3-owned — coordinate via a PR, do not edit unilaterally.

### Changes needed in `backend/app/api/chat.py`

The existing `chat_query` stub needs to be replaced. The PR to M3 must include:

```python
from fastapi import APIRouter, HTTPException, Depends
from app.core.dependencies import get_current_user, get_db
from app.services.context_builder import build_web_context
from app.services.conversation_router import find_or_create_conversation, reset_conversation
from app.services.message_handler import handle_message
from app.schemas.chat import ChatQueryRequest   # define this Pydantic model

@router.post("/query")
async def chat_query(
    body:         ChatQueryRequest,
    current_user: dict = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    ctx = await build_web_context(current_user, body.query, body.conversation_id)

    ctx.conversation_id = await find_or_create_conversation(ctx, db)

    result = await handle_message(ctx)   # runs inline for Web — blocks until n8n responds

    if result is None:
        raise HTTPException(status_code=502, detail="RAG service unavailable")
    return result
```

**Pydantic schema to add** (`backend/app/schemas/chat.py` or similar):
```python
from pydantic import BaseModel

class ChatQueryRequest(BaseModel):
    query:           str
    conversation_id: str | None = None
```

**Coordination checklist:**
- [ ] Raise PR against M3 branch with these changes
- [ ] M3 owner reviews and merges
- [ ] Confirm `get_current_user` returns a dict with `sub` and `tenant_id` keys (check M2's JWT implementation)

---

## Phase 8 — Testing

Test each acceptance criterion from the spec directly. No mocking the DB — use the real Postgres instance.

### Manual Verification Checklist

Run `uvicorn app.main:app --reload --port 8000` with `MOCK_N8N=true` first to verify flow without n8n dependency.

| # | Test | Expected |
|---|---|---|
| 1 | POST `/api/chat` without `conversation_id`, valid JWT | 200, answer returned, new `conversation_id` in response |
| 2 | POST `/api/chat` with another user's `conversation_id` | 403, nothing persisted |
| 3 | POST `/webhooks/slack/events` with valid payload | 200 within 3s; check Slack channel for threaded reply |
| 4 | Re-send same Slack payload (same `event_id`) | 200, no duplicate DB rows in `chat_messages` |
| 5 | Slack message with `text: "/new"` | 200, "New conversation started ✓" in thread, old conversation `is_active=false` |
| 6 | Set `MOCK_N8N=false`, kill n8n, send a message | Fallback reply delivered, nothing persisted, error in logs |
| 7 | POST `/webhooks/slack/events` with wrong signature | 403 |
| 8 | POST `/api/chat` with expired JWT | 401 |
| 9 | Slack `/New` (capital N) | Treated as reset — same as `/new` |
| 10 | Slack `/newer` | NOT treated as reset — goes to n8n as a query |

### Integration Test File

Create `tests/test_m4_slack.py` and `tests/test_m4_web.py` as a minimum to satisfy the "1 test per PR" rule in CLAUDE.md. Cover at minimum:
- Dedup (AC #4)
- Cross-user 403 (AC #2)
- Reset command does not call n8n (AC #5)

---

## Environment Variables Checklist

Before running any of the above, confirm `.env` has:

```bash
SLACK_SIGNING_SECRET=<from Slack app settings → Basic Information → Signing Secret>
SLACK_BOT_TOKEN=<xoxb-... from Slack app settings → OAuth & Permissions>
N8N_RETRIEVE_WEBHOOK_URL=<your n8n retrieval webhook URL>
MOCK_N8N=true          # set false only when n8n is running
```

---

## Build Order Summary

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5  →  Phase 6  →  Phase 7  →  Phase 8
Migration   Types       n8n client  Context      Router       Handler      Slack        Web (M3)     Tests
                                    builder                                adapter      coord
```

Each phase produces a testable artifact before the next one begins. Do not skip Phase 0 — every phase after it assumes the schema columns exist.
