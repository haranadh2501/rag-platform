"""Unified message service (M4).

Channel-agnostic processing core. A single entry point — `process_message(ctx, db)` —
runs Steps 2–8 of the flow (identity → conversation → reset → history → pipeline →
deliver → save). Adapters (Slack webhook, web chat) build a `MessageContext` and call it.

New tables (`slack_workspace_map`, `processed_requests`) and the `users.slack_user_id`
column are accessed via raw SQL — no ORM model changes (see migration 0002_m4_messaging).
"""
import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bots import slack
from app.services import pipeline_client
from app.services.types import MessageContext

logger = logging.getLogger(__name__)

RESET_COMMANDS = {"/new", "/reset", "/clear"}
HISTORY_LIMIT = 10
RESET_CONFIRMATION = "Conversation reset ✓"
FALLBACK_MESSAGE = "Sorry, something went wrong — please try again."


class ConversationOwnershipError(Exception):
    """Web: the supplied conversation_id belongs to another user (→ 403)."""


class IdentityResolutionError(Exception):
    """Slack: workspace or user could not be mapped to a tenant/user."""


async def process_message(ctx: MessageContext, db: AsyncSession) -> dict:
    """Process one inbound message end-to-end and return the response payload.

    For Slack the answer is also delivered via `chat.postMessage`; the returned
    dict is what the web adapter returns to its HTTP caller.
    """
    await _resolve_identity(ctx, db)                      # Step 2
    await _find_or_create_conversation(ctx, db)           # Step 3

    if ctx.query.strip().lower() in RESET_COMMANDS:        # Step 4
        return await _handle_reset(ctx, db)

    history = await _load_history(ctx, db)                 # Step 5

    response = await pipeline_client.call_pipeline({       # Step 6 (raises PipelineError)
        "request_id": ctx.request_id,
        "tenant_id": str(ctx.tenant_id),
        "conversation_id": str(ctx.conversation_id),
        "current_message": ctx.query,
        "history": history,
    })
    answer = response.get("answer", "")
    sources = response.get("sources", []) or []

    if ctx.source == "slack":                              # Step 7
        await slack.post_reply(ctx.slack_channel, ctx.slack_thread_ts, answer, sources)

    await _save_messages(ctx, db, ctx.query, answer, sources)  # Step 8

    response["conversation_id"] = str(ctx.conversation_id)
    response.setdefault("request_id", ctx.request_id)
    return response


async def _resolve_identity(ctx: MessageContext, db: AsyncSession) -> None:
    """Step 2 — web is already resolved from JWT; Slack maps team + user via raw SQL."""
    if ctx.source != "slack":
        return
    row = (await db.execute(text("""
        SELECT u.id AS user_id, m.tenant_id AS tenant_id
        FROM slack_workspace_map m
        JOIN users u
          ON u.tenant_id = m.tenant_id
         AND u.slack_user_id = :slack_user_id
        WHERE m.team_id = :team_id
    """), {"team_id": ctx.slack_team_id, "slack_user_id": ctx.slack_user_id})).first()
    if row is None:
        raise IdentityResolutionError(
            f"No tenant/user for team_id={ctx.slack_team_id} slack_user_id={ctx.slack_user_id}"
        )
    ctx.user_id = row.user_id
    ctx.tenant_id = row.tenant_id


async def _find_or_create_conversation(ctx: MessageContext, db: AsyncSession) -> None:
    """Step 3 — one conversation per (user_id, channel); validate web ownership."""
    # Web with an explicit conversation_id: it must belong to this user.
    if ctx.source == "web" and ctx.conversation_id is not None:
        row = (await db.execute(
            text("SELECT user_id FROM conversations WHERE id = :cid"),
            {"cid": ctx.conversation_id},
        )).first()
        if row is None or row.user_id != ctx.user_id:
            raise ConversationOwnershipError(str(ctx.conversation_id))
        return

    row = (await db.execute(
        text("SELECT id FROM conversations WHERE user_id = :uid AND channel = :ch"),
        {"uid": ctx.user_id, "ch": ctx.source},
    )).first()
    if row is not None:
        ctx.conversation_id = row.id
        return

    ctx.conversation_id = (await db.execute(
        text("""INSERT INTO conversations (tenant_id, user_id, channel)
                VALUES (:tid, :uid, :ch) RETURNING id"""),
        {"tid": ctx.tenant_id, "uid": ctx.user_id, "ch": ctx.source},
    )).scalar_one()
    await db.commit()


async def _handle_reset(ctx: MessageContext, db: AsyncSession) -> dict:
    """Step 4 — delete conversation (+messages via cascade), recreate, confirm, STOP."""
    await db.execute(
        text("DELETE FROM conversations WHERE user_id = :uid AND channel = :ch"),
        {"uid": ctx.user_id, "ch": ctx.source},
    )
    ctx.conversation_id = (await db.execute(
        text("""INSERT INTO conversations (tenant_id, user_id, channel)
                VALUES (:tid, :uid, :ch) RETURNING id"""),
        {"tid": ctx.tenant_id, "uid": ctx.user_id, "ch": ctx.source},
    )).scalar_one()
    await db.commit()

    if ctx.source == "slack":
        await slack.post_text(ctx.slack_channel, ctx.slack_thread_ts, RESET_CONFIRMATION)

    return {
        "request_id": ctx.request_id,
        "conversation_id": str(ctx.conversation_id),
        "answer": RESET_CONFIRMATION,
        "sources": [],
        "follow_up_questions": [],
    }


async def _load_history(ctx: MessageContext, db: AsyncSession) -> list[dict]:
    """Step 5 — last 10 messages, oldest-first."""
    rows = (await db.execute(text("""
        SELECT role, content FROM chat_messages
        WHERE conversation_id = :cid
        ORDER BY created_at DESC
        LIMIT :lim
    """), {"cid": ctx.conversation_id, "lim": HISTORY_LIMIT})).all()
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


async def _save_messages(
    ctx: MessageContext, db: AsyncSession, query: str, answer: str, sources: list
) -> None:
    """Step 8 — persist user + assistant rows in a single transaction."""
    await db.execute(text("""
        INSERT INTO chat_messages (conversation_id, role, content, sources)
        VALUES (:cid, 'user', :content, CAST(:sources AS JSONB))
    """), {"cid": ctx.conversation_id, "content": query, "sources": "[]"})
    await db.execute(text("""
        INSERT INTO chat_messages (conversation_id, role, content, sources)
        VALUES (:cid, 'assistant', :content, CAST(:sources AS JSONB))
    """), {"cid": ctx.conversation_id, "content": answer, "sources": json.dumps(sources)})
    await db.commit()
