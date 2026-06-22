"""Ephemeral session state machine for WhatsApp document analysis.

Handles the full lifecycle: session creation, file upload/ingest, grounded
Q&A over uploaded docs, and session teardown. All DB writes use raw SQL
(matching message_service.py conventions). No changes to the normal pipeline.
"""
import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bots import whatsapp
from app.core.config import settings
from app.models.models import EphemeralSession
from app.services import file_validator, n8n_client
from app.services.types import MessageContext

logger = logging.getLogger(__name__)

_INGEST_TIMEOUT_SECONDS = 300.0   # 5 minutes


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ext_from_mime(mime_type: str) -> str:
    _MAP = {
        "application/pdf": "pdf",
        "image/png": "png",
        "image/jpeg": "jpg",
        "text/plain": "txt",
    }
    return _MAP.get(mime_type, mime_type.split("/")[-1])


# ── Public API ────────────────────────────────────────────────────────────────

async def get_active_session(user_id: UUID, db: AsyncSession) -> EphemeralSession | None:
    """Return the active ephemeral_sessions row for this user, or None."""
    row = (await db.execute(
        text("SELECT * FROM ephemeral_sessions WHERE user_id = :uid LIMIT 1"),
        {"uid": user_id},
    )).mappings().first()
    if row is None:
        return None
    session = EphemeralSession()
    for key, val in row.items():
        setattr(session, key, val)
    return session


async def start_session(ctx: MessageContext, db: AsyncSession) -> None:
    """Create conversation + ephemeral_sessions row. Reply to user."""
    # uq_conversations_user_channel prevents two whatsapp rows per user.
    # Repurpose the existing conversation (clearing its prior messages) rather
    # than failing. The cascade on end_session will clean it up.
    conversation_id = (await db.execute(text("""
        INSERT INTO conversations (tenant_id, user_id, channel, title)
        VALUES (:tid, :uid, 'whatsapp', 'Ephemeral Session')
        ON CONFLICT (user_id, channel)
        DO UPDATE SET title = 'Ephemeral Session'
        RETURNING id
    """), {"tid": ctx.tenant_id, "uid": ctx.user_id})).scalar_one()

    # Clear any prior messages from this conversation slot
    await db.execute(text(
        "DELETE FROM chat_messages WHERE conversation_id = :cid"
    ), {"cid": conversation_id})

    n8n_session_id = uuid.uuid4()

    await db.execute(text("""
        INSERT INTO ephemeral_sessions
            (tenant_id, user_id, conversation_id, n8n_session_id, status)
        VALUES
            (:tid, :uid, :cid, :n8n_sid, 'awaiting_document')
    """), {
        "tid": ctx.tenant_id,
        "uid": ctx.user_id,
        "cid": conversation_id,
        "n8n_sid": n8n_session_id,
    })
    await db.commit()

    await whatsapp.post_text(
        ctx.whatsapp_from,
        "📎 Ephemeral session started. Upload a document (PDF, image, or text file, max 9 MB).",
    )


async def handle_upload(
    ctx: MessageContext,
    db: AsyncSession,
    session: EphemeralSession,
    media_url: str,
    media_type: str,
) -> None:
    """Download file from Twilio → validate → base64 → ingest into n8n → update session."""
    source_name = f"upload.{_ext_from_mime(media_type)}"

    # ── Download with Twilio Basic Auth ──────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                media_url,
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            )
            resp.raise_for_status()
            content = resp.content
    except Exception as exc:
        logger.error("Twilio media download failed: %s", exc)
        await whatsapp.post_text(ctx.whatsapp_from, "❌ Failed to download your file. Please try again.")
        return

    # ── Validate size and MIME ────────────────────────────────────────────────
    try:
        validated = file_validator.validate_upload(
            filename=source_name,
            content=content,
            declared_mime=media_type,
            max_bytes=settings.MAX_WHATSAPP_EPHEMERAL_UPLOAD_BYTES,
        )
    except HTTPException as exc:
        if exc.status_code == 413:
            await whatsapp.post_text(ctx.whatsapp_from, "⚠️ File too large (max 9 MB). Please send a smaller file.")
        else:
            await whatsapp.post_text(ctx.whatsapp_from, f"❌ File rejected: {exc.detail}")
        return

    file_base64 = base64.b64encode(validated.content).decode()

    # ── Set status to ingesting ───────────────────────────────────────────────
    await db.execute(
        text("UPDATE ephemeral_sessions SET status = 'ingesting' WHERE id = :sid"),
        {"sid": session.id},
    )
    await db.commit()

    # ── Call n8n with 5-minute timeout ───────────────────────────────────────
    try:
        result = await asyncio.wait_for(
            n8n_client.ingest_ephemeral_base64(
                tenant_id=str(session.tenant_id),
                n8n_session_id=str(session.n8n_session_id),
                source_name=source_name,
                file_base64=file_base64,
            ),
            timeout=_INGEST_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.error("n8n ephemeral ingest timed out for session=%s file=%s", session.id, source_name)
        await _revert_ingest_status(session, db)
        await whatsapp.post_text(
            ctx.whatsapp_from,
            f"⏳ Processing timed out for {source_name}. Please try again with a smaller file.",
        )
        return
    except Exception as exc:
        logger.error("n8n ephemeral ingest failed for session=%s: %s", session.id, exc)
        await _revert_ingest_status(session, db)
        await whatsapp.post_text(ctx.whatsapp_from, f"❌ Failed to process {source_name}. Please try again.")
        return

    # ── Atomic update: chunks + doc_count + expires_at ───────────────────────
    chunk_count = result.get("chunk_count", 0)
    expires_at_str = result.get("expires_at")
    expires_at = None
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        except ValueError:
            pass

    row = (await db.execute(text("""
        UPDATE ephemeral_sessions
        SET total_chunks = total_chunks + :chunk_delta,
            doc_count    = doc_count + 1,
            status       = 'ready',
            expires_at   = COALESCE(expires_at, :exp)
        WHERE id = :sid
        RETURNING doc_count
    """), {"chunk_delta": chunk_count, "exp": expires_at, "sid": session.id})).first()
    await db.commit()

    doc_count = row[0] if row else session.doc_count + 1
    await whatsapp.post_text(
        ctx.whatsapp_from,
        f"✅ Document indexed ({chunk_count} chunks, {doc_count} total docs). Ask me anything!",
    )


async def handle_query(
    ctx: MessageContext,
    db: AsyncSession,
    session: EphemeralSession,
) -> None:
    """Route text query: guard on status, load history, call retrieve-ephemeral, save messages."""
    if session.status == "ingesting":
        await whatsapp.post_text(ctx.whatsapp_from, "⏳ Still processing your document. Please wait a moment.")
        return
    if session.status == "awaiting_document":
        await whatsapp.post_text(ctx.whatsapp_from, "📎 No documents uploaded yet. Please upload a file first.")
        return

    # ── Load last 10 messages from chat_messages (oldest-first) ──────────────
    rows = (await db.execute(text("""
        SELECT role, content FROM chat_messages
        WHERE conversation_id = :cid
        ORDER BY created_at DESC
        LIMIT 10
    """), {"cid": session.conversation_id})).all()
    history = [{"role": r.role, "content": r.content} for r in reversed(rows)]

    # ── Call n8n retrieve-ephemeral ───────────────────────────────────────────
    try:
        result = await n8n_client.retrieve_ephemeral(
            query=ctx.query,
            tenant_id=str(session.tenant_id),
            n8n_session_id=str(session.n8n_session_id),
            conversation_history=history,
        )
    except Exception as exc:
        logger.error("n8n ephemeral retrieve failed for session=%s: %s", session.id, exc)
        await whatsapp.post_text(ctx.whatsapp_from, "❌ Failed to get an answer. Please try again.")
        return

    answer = result.get("answer", "")
    sources: list = result.get("sources", [])

    # ── Persist user + assistant messages ─────────────────────────────────────
    now = datetime.now(timezone.utc)
    await db.execute(text("""
        INSERT INTO chat_messages (conversation_id, role, content, sources, created_at)
        VALUES (:cid, 'user', :content, CAST(:sources AS JSONB), :ts)
    """), {"cid": session.conversation_id, "content": ctx.query, "sources": "[]", "ts": now})
    await db.execute(text("""
        INSERT INTO chat_messages (conversation_id, role, content, sources, created_at)
        VALUES (:cid, 'assistant', :content, CAST(:sources AS JSONB), :ts)
    """), {"cid": session.conversation_id, "content": answer, "sources": json.dumps(sources), "ts": now})
    await db.commit()

    await whatsapp.post_reply(ctx.whatsapp_from, answer, sources)


async def end_session(
    ctx: MessageContext,
    db: AsyncSession,
    session: EphemeralSession,
    silent: bool = False,
) -> None:
    """Purge n8n session, delete conversation (cascades to chat_messages + ephemeral_sessions row)."""
    # Purge n8n — log and continue even if it fails (TTL handles cleanup as backstop)
    try:
        await n8n_client.purge_ephemeral(
            tenant_id=str(session.tenant_id),
            n8n_session_id=str(session.n8n_session_id),
        )
    except Exception as exc:
        logger.error("n8n purge failed for session=%s (continuing with local delete): %s", session.id, exc)

    # Delete conversation — cascades to chat_messages AND ephemeral_sessions
    await db.execute(
        text("DELETE FROM conversations WHERE id = :cid"),
        {"cid": session.conversation_id},
    )
    await db.commit()

    if not silent:
        await whatsapp.post_text(ctx.whatsapp_from, "Session ended ✓ — back to normal mode.")


# ── Private helpers ───────────────────────────────────────────────────────────

async def _revert_ingest_status(session: EphemeralSession, db: AsyncSession) -> None:
    """Revert status after ingest failure: ready if prior docs exist, else awaiting_document."""
    revert_to = "ready" if session.doc_count > 0 else "awaiting_document"
    await db.execute(
        text("UPDATE ephemeral_sessions SET status = :s WHERE id = :sid"),
        {"s": revert_to, "sid": session.id},
    )
    await db.commit()
