"""
Webhook routes — WhatsApp (Twilio), Slack Events, n8n callbacks.
Owner: M4 — implement route bodies.
"""
import hashlib
import hmac
import json
import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bots import slack
from app.bots.slack import SlackAPIError, SlackUserNotFoundError
from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.dependencies import require_role
from app.models.models import User
from app.schemas.webhook import SlackOnboardRequest, SlackOnboardResponse
from app.services import message_service, pipeline_client
from app.services.types import MessageContext

logger = logging.getLogger(__name__)

router = APIRouter()


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
    twiml = f'<?xml version="1.0"?><Response><Message>M4: implement WhatsApp handler. Received: {message_body[:50]}</Message></Response>'
    return Response(content=twiml, media_type="application/xml")


def _verify_slack_signature(raw_body: bytes, timestamp: str, signature: str) -> bool:
    """HMAC-SHA256 verification per Slack's signing spec."""
    if not timestamp or not signature or not settings.SLACK_SIGNING_SECRET:
        return False
    basestring = b"v0:" + timestamp.encode() + b":" + raw_body
    digest = hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(), basestring, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"v0={digest}", signature)


async def _process_slack_event(
    event_id: str,
    team_id: str | None,
    slack_user_id: str,
    query: str,
    channel: str | None,
    thread_ts: str | None,
) -> None:
    """Background task — runs Steps 2–8 with its own DB session (request session is closed)."""
    async with AsyncSessionLocal() as db:
        ctx = MessageContext(
            request_id=event_id,
            source="slack",
            query=query,
            slack_channel=channel,
            slack_thread_ts=thread_ts,
            slack_team_id=team_id,
            slack_user_id=slack_user_id,
        )
        try:
            await message_service.process_message(ctx, db)
        except pipeline_client.PipelineError:
            await slack.post_text(channel, thread_ts, message_service.FALLBACK_MESSAGE)
        except message_service.IdentityResolutionError as exc:
            logger.error("Slack identity resolution failed: %s", exc)
        except Exception:  # noqa: BLE001 — never let a bg task crash silently
            logger.exception("Slack event processing failed (event_id=%s)", event_id)


@router.post("/slack/events", summary="Slack Events API webhook")
async def slack_events(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Verify → ACK 200 fast; heavy work runs in a BackgroundTask."""
    raw = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    if not _verify_slack_signature(raw, timestamp, signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")

    body = json.loads(raw)

    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}

    event = body.get("event") or {}
    if event.get("bot_id"):                       # prevent reply loops
        return {"ok": True}

    event_id = body.get("event_id")

    # Dedup: first writer wins; a duplicate event_id inserts nothing.
    if event_id:
        result = await db.execute(
            text("INSERT INTO processed_requests (request_id) VALUES (:rid) "
                 "ON CONFLICT DO NOTHING"),
            {"rid": event_id},
        )
        await db.commit()
        if result.rowcount == 0:
            return {"ok": True}                   # duplicate — already handled

    user = event.get("user")
    message_text = event.get("text")
    if not event_id or not user or not message_text:
        logger.warning(
            "Slack event missing required fields: event_id=%s user=%s has_text=%s",
            event_id, user, bool(message_text),
        )
        return {"ok": True}                       # 200 so Slack doesn't retry

    background_tasks.add_task(
        _process_slack_event,
        event_id,
        body.get("team_id"),
        user,
        message_text,
        event.get("channel"),
        event.get("thread_ts") or event.get("ts"),
    )
    return {"ok": True}


# ── Mock pipeline — dev only. Hosted here (already-registered /webhooks router)
#    so no change to main.py is required. PIPELINE_URL defaults to this path. ──
_MOCK_PIPELINE_RESPONSE = {
    "answer": "This is a sample response from the mock pipeline. In production this "
              "will be a grounded answer from the RAG engine. [Sample Manual, p.12]",
    "sources": [
        {
            "document_id": "00000000-0000-0000-0000-000000000001",
            "title": "Sample Product Manual",
            "chunk_text": "Sample relevant excerpt used to generate this answer.",
            "page_number": 12,
            "score": 0.94,
        }
    ],
    "follow_up_questions": [
        "Can you explain this in more detail?",
        "What are the next steps?",
        "Who should I contact for further help?",
    ],
}


@router.post("/mock/pipeline", summary="Mock RAG pipeline (dev only)")
async def mock_pipeline(_request: Request):
    """Canned success response so the message flow can be exercised without n8n."""
    return _MOCK_PIPELINE_RESPONSE


@router.post("/slack/onboard", response_model=SlackOnboardResponse, summary="Link a platform user to their Slack identity")
async def slack_onboard(
    body: SlackOnboardRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Look up *email* in the Slack workspace and write the member ID to the user row.

    - 404 if the email is not a workspace member.
    - 409 if the user already has a slack_user_id set.
    - 503 if the Slack API is unreachable.
    """
    # Fetch member ID from Slack first — fails fast before any DB writes.
    try:
        slack_user_id = await slack.lookup_user_by_email(body.email)
    except SlackUserNotFoundError:
        raise HTTPException(status_code=404, detail="Email not found in Slack workspace")
    except SlackAPIError as exc:
        logger.error("Slack API error during onboard: %s", exc)
        raise HTTPException(status_code=503, detail="Slack API unavailable")

    # Find the platform user scoped to the admin's tenant.
    result = await db.execute(
        text("SELECT id, slack_user_id FROM users WHERE email = :email AND tenant_id = :tid"),
        {"email": body.email, "tid": current_user.tenant_id},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found in this tenant")
    if row["slack_user_id"] is not None:
        raise HTTPException(status_code=409, detail="User already has a Slack identity linked")

    await db.execute(
        text("UPDATE users SET slack_user_id = :sid WHERE id = :uid"),
        {"sid": slack_user_id, "uid": row["id"]},
    )
    await db.commit()
    return SlackOnboardResponse(slack_user_id=slack_user_id, email=body.email)


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
