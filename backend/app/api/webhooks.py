"""Webhook routes — WhatsApp (Twilio), Slack Events, n8n callbacks.
Owner: M4.
"""
import hashlib
import hmac
import json
import logging
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import ProcessedRequest
from app.services.context_builder import build_slack_context
from app.services.conversation_router import reset_conversation
from app.services.message_handler import handle_message

router = APIRouter()
logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _verify_slack_signature(headers: dict, body: bytes) -> None:
    """Raise HTTPException 403 if Slack HMAC does not match or timestamp is stale."""
    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")

    try:
        ts_int = int(timestamp)
    except (ValueError, TypeError):
        raise HTTPException(status_code=403, detail="Missing or invalid timestamp header")

    # Reject replays older than 5 minutes
    if abs(time.time() - ts_int) > 300:
        raise HTTPException(status_code=403, detail="Request timestamp too old")

    sig_base = f"v0:{timestamp}:".encode() + body
    expected = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        sig_base,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")


# ── Slack Events ─────────────────────────────────────────────────────────────

@router.post("/slack/events", summary="Slack Events API webhook")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    # Must read raw bytes BEFORE any other body access — body is a one-shot stream
    body = await request.body()

    # Step 1 — HMAC verification (fast; raises 403 if invalid)
    _verify_slack_signature(dict(request.headers), body)

    payload = json.loads(body)

    # URL verification handshake (one-time, during Slack app setup)
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}

    event = payload.get("event", {})

    # Ignore events from bots to prevent reply loops
    if event.get("bot_id"):
        return Response(status_code=200)

    event_id = payload.get("event_id", "")

    # Step 2 — Dedup: insert-on-conflict; rowcount 0 means already processed
    async with AsyncSessionLocal() as db:
        stmt = (
            pg_insert(ProcessedRequest)
            .values(request_id=event_id)
            .on_conflict_do_nothing()
        )
        result = await db.execute(stmt)
        await db.commit()

    if result.rowcount == 0:
        return Response(status_code=200)   # duplicate event_id — already handled

    # Step 3 — Build MessageContext (resolve workspace + user)
    try:
        async with AsyncSessionLocal() as db:
            ctx = await build_slack_context(payload, db)
    except (ValueError, LookupError) as exc:
        logger.warning("Slack context build failed: %s", exc)
        return Response(status_code=200)   # ACK Slack; do not trigger a retry

    # Step 4 — Reset command short-circuit (never touches n8n)
    if ctx.reset_requested:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                await reset_conversation(ctx, db)
        from app.bots.slack import post_text
        await post_text(
            channel   = event.get("channel", ""),
            thread_ts = event.get("ts", ""),
            text      = "New conversation started ✓",
        )
        return Response(status_code=200)

    # Step 5 — ACK immediately; conversation lookup + n8n + delivery run in background
    background_tasks.add_task(handle_message, ctx)
    return Response(status_code=200)


# ── WhatsApp (Twilio) ─────────────────────────────────────────────────────────

@router.post("/whatsapp", summary="Twilio WhatsApp incoming message")
async def whatsapp_webhook(request: Request):
    """
    M4: Implement:
    1. Validate Twilio signature (Day 5)
    2. Parse form: Body (message text), From (phone number)
    3. Lookup tenant from phone number (M12's tenant_map)
    4. Call chat_query_internal(body, tenant_id)
    5. Return TwiML XML response
    """
    form = await request.form()
    message_body = form.get("Body", "")
    from_number = form.get("From", "")
    # M4: implement real logic
    twiml = (
        f'<?xml version="1.0"?><Response>'
        f'<Message>M4: implement WhatsApp handler. Received: {message_body[:50]}</Message>'
        f'</Response>'
    )
    return Response(content=twiml, media_type="application/xml")


# ── n8n ingestion callback ────────────────────────────────────────────────────

@router.post("/n8n/ingestion-status", summary="n8n ingestion pipeline callback")
async def n8n_ingestion_callback(request: Request):
    """
    M4: Implement:
    1. Parse: {document_id, status, chunk_count, error_message}
    2. UPDATE documents SET status=?, chunk_count=? WHERE id=?
    3. Return 200
    """
    body = await request.json()
    document_id = body.get("document_id")
    status = body.get("status")
    # M4/M3: update document status in DB
    return {"message": f"Status update received: document_id={document_id} status={status}"}
