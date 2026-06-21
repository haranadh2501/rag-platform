"""Unified message service (M4).

Channel-agnostic processing core. A single entry point — `process_message(ctx, db)` —
runs Steps 2–8 of the flow (identity → conversation → reset → history → pipeline →
deliver → save). Adapters (Slack webhook, web chat) build a `MessageContext` and call it.

New tables (`slack_workspace_map`, `processed_requests`) and the `users.slack_user_id`
column are accessed via raw SQL — no ORM model changes (see migration 0002_m4_messaging).
"""
import json
import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bots import slack, whatsapp
from app.services import pipeline_client
from app.services.types import MessageContext

logger = logging.getLogger(__name__)

RESET_COMMANDS = {"/new", "/reset", "/clear"}
HISTORY_LIMIT = 10
RESET_CONFIRMATION = "Conversation reset ✓"
FALLBACK_MESSAGE = "Sorry, something went wrong — please try again."

DEFAULT_TITLE = "New Conversation"
TITLE_MAX_LEN = 40
_TITLE_PREFIXES = sorted([
    "what is", "what are", "what's",
    "explain", "can you explain", "could you explain",
    "summarize", "summarise",
    "tell me about", "describe",
    "how do i", "how to", "how does",
], key=len, reverse=True)


def _format_query_with_history(history: list[dict], query: str) -> str:
    """Compose history + current query into the plain-text string n8n expects."""
    if not history:
        return f"User Query: {query}"
    lines = ["Context:"]
    for msg in history:
        lines.append(f"{msg['role']}: {msg['content']}")
    lines.append("")
    lines.append(f"User Query: {query}")
    return "\n".join(lines)


def _derive_title(query: str) -> str:
    """Deterministic short title from a user's first query — no LLM call.

    Strips trailing punctuation and a leading question/instruction phrase
    (e.g. "what is", "summarize"), title-cases the remainder, and caps it at
    TITLE_MAX_LEN chars on a word boundary.
    """
    text_ = query.strip().rstrip("?!.,;: ").strip()
    if not text_:
        return DEFAULT_TITLE

    lowered = text_.lower()
    for prefix in _TITLE_PREFIXES:
        if lowered.startswith(prefix):
            text_ = text_[len(prefix):].strip()
            break

    text_ = text_.rstrip("?!.,;: ").strip()
    if not text_:
        return DEFAULT_TITLE

    title = text_.title()
    if len(title) > TITLE_MAX_LEN:
        title = title[:TITLE_MAX_LEN].rsplit(" ", 1)[0].rstrip() or title[:TITLE_MAX_LEN]
    return title


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

    formatted_query = _format_query_with_history(history, ctx.query)
    response = await pipeline_client.call_pipeline(        # Step 6 (raises PipelineError)
        {"query": formatted_query}
    )
    answer = response.get("answer", "")
    sources: list = []           # n8n does not return sources
    follow_up_questions: list = []  # n8n does not return follow_up_questions

    if ctx.source == "slack":                              # Step 7
        await slack.post_reply(ctx.slack_channel, ctx.slack_thread_ts, answer, sources)
    elif ctx.source == "whatsapp":
        await whatsapp.post_reply(ctx.whatsapp_from, answer, sources)

    await _save_messages(ctx, db, ctx.query, answer, sources)  # Step 8

    return {
        "request_id": ctx.request_id,
        "conversation_id": str(ctx.conversation_id),
        "answer": answer,
        "sources": sources,
        "follow_up_questions": follow_up_questions,
    }


async def _resolve_identity(ctx: MessageContext, db: AsyncSession) -> None:
    """Step 2 — web is already resolved from JWT; Slack maps team + user via raw SQL."""
    if ctx.user_id is not None and ctx.tenant_id is not None:
        return  # already resolved (e.g. WhatsApp pre-resolves before media handling)

    if ctx.source == "slack":
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

    elif ctx.source == "whatsapp":
        # Look up tenant via whatsapp_tenant_map, user via phone_number
        row = (await db.execute(text("""
            SELECT m.tenant_id, u.id AS user_id
            FROM whatsapp_tenant_map m
            LEFT JOIN users u ON u.tenant_id = m.tenant_id AND u.phone_number = :phone
            WHERE m.phone_number = :phone
        """), {"phone": ctx.whatsapp_from})).first()

        if row is None:
            raise IdentityResolutionError(f"Phone {ctx.whatsapp_from} not in whatsapp_tenant_map")

        ctx.tenant_id = row.tenant_id

        if row.user_id is None:
            # Auto-create a "whatsapp" user for this phone in the tenant
            ctx.user_id = (await db.execute(text("""
                INSERT INTO users (tenant_id, email, hashed_password, role, phone_number)
                VALUES (:tid, :email, 'whatsapp-no-login', 'user', :phone)
                RETURNING id
            """), {
                "tid": ctx.tenant_id,
                "email": f"wa-{ctx.whatsapp_from.replace('+','').replace(':','').replace('whatsapp','')}@whatsapp.local",
                "phone": ctx.whatsapp_from,
            })).scalar_one()
            await db.commit()
        else:
            ctx.user_id = row.user_id


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
        text("""INSERT INTO conversations (tenant_id, user_id, channel, title)
                VALUES (:tid, :uid, :ch, :title) RETURNING id"""),
        {"tid": ctx.tenant_id, "uid": ctx.user_id, "ch": ctx.source, "title": _derive_title(ctx.query)},
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
    elif ctx.source == "whatsapp":
        await whatsapp.post_text(ctx.whatsapp_from, RESET_CONFIRMATION)

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
    """Step 8 — persist user + assistant rows in a single transaction.

    created_at is set explicitly rather than left to the column's `now()`
    default: Postgres's `now()` is transaction-scoped, so both rows in this
    same transaction would otherwise get an identical timestamp, making
    _load_history's `ORDER BY created_at` non-deterministic between them.
    """
    await db.execute(text("""
        INSERT INTO chat_messages (conversation_id, role, content, sources, created_at)
        VALUES (:cid, 'user', :content, CAST(:sources AS JSONB), :ts)
    """), {"cid": ctx.conversation_id, "content": query, "sources": "[]", "ts": datetime.utcnow()})
    await db.execute(text("""
        INSERT INTO chat_messages (conversation_id, role, content, sources, created_at)
        VALUES (:cid, 'assistant', :content, CAST(:sources AS JSONB), :ts)
    """), {"cid": ctx.conversation_id, "content": answer, "sources": json.dumps(sources), "ts": datetime.utcnow()})
    await db.commit()
