"""message_handler.py — unified message handler for Web and Slack.

Entry point: handle_message(ctx).
- Web:   runs inline; returns response dict
- Slack: runs as BackgroundTask; returns None; delivers reply via chat.postMessage

The entire body is wrapped in try/except — any unhandled exception logs the full
traceback and delivers the fallback reply. This function must never silently terminate.
Owner: M4.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.services.types import MessageContext, ChannelType
from app.services.conversation_router import find_or_create_conversation
from app.services import n8n_client
from app.models.models import ChatMessage

logger = logging.getLogger(__name__)

HISTORY_WINDOW    = 10
MAX_HISTORY_CHARS = 5000
FALLBACK_REPLY    = "Sorry, something went wrong — please try again."


async def handle_message(ctx: MessageContext) -> dict | None:
    """Unified handler. Web returns a dict; Slack returns None after posting to channel."""
    async with AsyncSessionLocal() as db:
        try:
            return await _run(ctx, db)
        except Exception:
            logger.error("handle_message failed for request_id=%s", ctx.request_id, exc_info=True)
            await _deliver_error(ctx, FALLBACK_REPLY)
            return None


async def _run(ctx: MessageContext, db: AsyncSession) -> dict | None:
    # Step 1 — Slack only: find/create conversation (deferred from sync webhook path)
    if ctx.source == ChannelType.SLACK:
        async with db.begin():
            ctx.conversation_id = await find_or_create_conversation(ctx, db)

    # Step 2 — Load history with character budget
    history = await _load_history(ctx.conversation_id, db)

    # Step 3 — Call n8n (120s timeout; TimeoutException propagates to outer try/except)
    n8n_resp = await n8n_client.retrieve(
        request_id      = ctx.request_id,
        tenant_id       = str(ctx.tenant_id),
        conversation_id = str(ctx.conversation_id),
        current_message = ctx.raw_query,
        history         = history,
    )

    answer  = n8n_resp.get("answer", FALLBACK_REPLY)
    sources = n8n_resp.get("sources", [])

    # Step 4 — Persist (on n8n success only). db may have an autobegin transaction
    # started by _load_history; using db.add() + commit() works whether or not
    # autobegin is active (avoids "A transaction is already begun" from begin()).
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
    await db.commit()

    # Step 5 — Deliver reply
    if ctx.source == ChannelType.SLACK:
        from app.bots.slack import post_reply
        await post_reply(ctx, answer, sources)
        return None

    return {
        "request_id":          ctx.request_id,
        "conversation_id":     str(ctx.conversation_id),
        "answer":              answer,
        "sources":             sources,
        "follow_up_questions": n8n_resp.get("follow_up_questions", []),
    }


async def _load_history(conversation_id, db: AsyncSession) -> list[dict]:
    """Load last HISTORY_WINDOW messages and trim to MAX_HISTORY_CHARS budget."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(HISTORY_WINDOW)
    )
    rows = list(reversed(result.scalars().all()))   # oldest-first for n8n

    # Drop oldest until total chars fit in budget
    while rows:
        if sum(len(r.content) for r in rows) <= MAX_HISTORY_CHARS:
            break
        rows.pop(0)

    return [{"role": r.role, "content": r.content} for r in rows]


async def _deliver_error(ctx: MessageContext, message: str) -> None:
    """Best-effort error reply. Logs but never raises if delivery itself fails."""
    try:
        if ctx.source == ChannelType.SLACK:
            from app.bots.slack import post_reply
            await post_reply(ctx, message, sources=[])
    except Exception:
        logger.error(
            "handle_message: secondary failure sending error reply for request_id=%s",
            ctx.request_id,
            exc_info=True,
        )
