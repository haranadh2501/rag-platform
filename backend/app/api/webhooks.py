"""
Webhook routes — WhatsApp (Twilio), Slack Events, n8n callbacks.
Owner: M4 — implement route bodies.
"""
import hashlib
import hmac
import json
import logging
import re
from uuid import UUID

import uuid as _uuid

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
)
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.request_validator import RequestValidator

from app.bots import slack, teams, whatsapp
from app.bots.slack import SlackAPIError, SlackUserNotFoundError
from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.dependencies import require_role
from app.models.models import Document, User
from app.schemas.webhook import SlackOnboardRequest, SlackOnboardResponse
from app.services import ephemeral_service, file_validator, message_service, n8n_client, pipeline_client
from app.services.types import MessageContext

logger = logging.getLogger(__name__)

router = APIRouter()


def _twiml_ack() -> str:
    """Empty TwiML response — we reply via Twilio REST API in the background task."""
    return '<?xml version="1.0"?><Response></Response>'


async def _handle_whatsapp_media(
    media_url: str,
    media_type: str,
    from_number: str,
    conversation_id: UUID
) -> None:
    """Download, validate, and ingest ephemeral media from WhatsApp."""
    try:
        # Download with Twilio auth
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(
                media_url,
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            )
            resp.raise_for_status()
            content = resp.content

        # Validate
        extension = media_type.split('/')[-1] if '/' in media_type else 'bin'
        validated = file_validator.validate_upload(
            filename=f"whatsapp_upload.{extension}",
            content=content,
            declared_mime=media_type,
            max_bytes=settings.MAX_WHATSAPP_UPLOAD_BYTES,
        )

        # Send to n8n ephemeral ingestion
        await n8n_client.ingest_ephemeral(
            validated.content,
            str(conversation_id),
            validated.mime_type
        )
        await whatsapp.post_text(
            from_number,
            "Indexed ✓ — ask me anything about this file for the next 60 minutes."
        )
    except HTTPException as exc:
        await whatsapp.post_text(from_number, f"File upload failed: {exc.detail}")
    except Exception as exc:
        logger.exception("WhatsApp media processing failed: %s", exc)
        await whatsapp.post_text(from_number, "Sorry, failed to process your file.")


async def _process_whatsapp_message(
    message_sid: str,
    from_number: str,
    query: str,
    media_url: str | None = None,
    media_type: str | None = None,
) -> None:
    """Background task — runs with its own DB session.

    Branches on ephemeral session state before falling through to the
    existing normal pipeline. The normal pipeline path is unchanged.
    """
    async with AsyncSessionLocal() as db:
        ctx = MessageContext(
            request_id=message_sid,
            source="whatsapp",
            query=query or ".",
            whatsapp_from=from_number,
        )
        try:
            await message_service._resolve_identity(ctx, db)

            session = await ephemeral_service.get_active_session(ctx.user_id, db)
            query_lower = (query or "").strip().lower()

            # ── Ephemeral commands ────────────────────────────────────────────
            if query_lower == "/askdoc":
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
                    # Purge ephemeral session silently, then confirm reset
                    await ephemeral_service.end_session(ctx, db, session, silent=True)
                    await whatsapp.post_text(from_number, message_service.RESET_CONFIRMATION)
                    return
                # No active session — normal reset flow
                await message_service._find_or_create_conversation(ctx, db)
                await message_service._handle_reset(ctx, db)
                return

            # ── Ephemeral mode active ─────────────────────────────────────────
            if session:
                if media_url and media_type:
                    await ephemeral_service.handle_upload(ctx, db, session, media_url, media_type)
                else:
                    await ephemeral_service.handle_query(ctx, db, session)
                return

            # ── Normal mode (unchanged) ───────────────────────────────────────
            if media_url and media_type:
                await whatsapp.post_text(from_number,
                    "📎 File uploads require ephemeral mode. Send /ephemeral_ingest first.")
                return

            await whatsapp.post_text(from_number, "🤔 Thinking...")
            await message_service._find_or_create_conversation(ctx, db)
            await message_service.process_message(ctx, db)

        except message_service.IdentityResolutionError:
            await whatsapp.post_text(from_number,
                "This number isn't registered. Please ask your admin to add you.")
        except pipeline_client.PipelineError:
            await whatsapp.post_text(from_number, message_service.FALLBACK_MESSAGE)
        except Exception:  # noqa: BLE001 — never let a bg task crash silently
            logger.exception("WhatsApp processing failed (sid=%s)", message_sid)


@router.post("/whatsapp", summary="Twilio WhatsApp incoming message")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Verify → ACK 200 fast; heavy work runs in a BackgroundTask."""
    raw = await request.body()

    # Verify Twilio signature (skip in development mode)
    if settings.APP_ENV != "development":
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        form_data = {k: v for k, v in (await request.form()).items()}
        url = str(request.url)
        signature = request.headers.get("X-Twilio-Signature", "")
        if not validator.validate(url, form_data, signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # Parse form data
    form = await request.form()
    message_body = form.get("Body", "").strip()
    from_number = form.get("From", "")        # "whatsapp:+919876543210"
    message_sid = form.get("MessageSid", "")   # Dedup key
    num_media = int(form.get("NumMedia", "0"))
    media_url = form.get("MediaUrl0", "") if num_media > 0 else None
    media_type = form.get("MediaContentType0", "") if num_media > 0 else None

    # Dedup on MessageSid (same pattern as Slack event_id)
    if message_sid:
        result = await db.execute(
            text("INSERT INTO processed_requests (request_id) VALUES (:rid) ON CONFLICT DO NOTHING"),
            {"rid": message_sid}
        )
        await db.commit()
        if result.rowcount == 0:
            return Response(content=_twiml_ack(), media_type="application/xml")

    # Build MessageContext and fire background task
    if not message_body and num_media == 0:
        return Response(content=_twiml_ack(), media_type="application/xml")

    if not message_sid or not from_number:
        logger.warning(
            "WhatsApp webhook missing required fields: message_sid=%s from_number=%s",
            message_sid, from_number,
        )
        return Response(content=_twiml_ack(), media_type="application/xml")

    # Fire background task with media info
    background_tasks.add_task(
        _process_whatsapp_message,
        message_sid,
        from_number,
        message_body,
        media_url,
        media_type
    )

    # ACK immediately with empty TwiML
    return Response(content=_twiml_ack(), media_type="application/xml")


# ── Microsoft Teams (Bot Framework) ──────────────────────────────────────────
_TEAMS_OPENID_CONFIG = "https://login.botframework.com/v1/.well-known/openidconfiguration"
_TEAMS_ISSUER = "https://api.botframework.com"
_TEAMS_FILE_DOWNLOAD = "application/vnd.microsoft.teams.file.download.info"
_EXT_MIME = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}

# Cached Bot Framework signing keys: list of JWK dicts.
_teams_jwks_cache: list[dict] | None = None


async def _teams_signing_keys() -> list[dict]:
    """Fetch (and cache) the Bot Framework JWKS used to sign inbound activities."""
    global _teams_jwks_cache
    if _teams_jwks_cache is not None:
        return _teams_jwks_cache
    async with httpx.AsyncClient(timeout=10.0) as client:
        config = (await client.get(_TEAMS_OPENID_CONFIG)).json()
        jwks = (await client.get(config["jwks_uri"])).json()
    _teams_jwks_cache = jwks.get("keys", [])
    return _teams_jwks_cache


async def _verify_teams_token(request: Request) -> bool:
    """Validate the Bot Framework JWT in the Authorization header.

    Skipped in development (mirrors the WhatsApp/Twilio dev bypass). In other
    environments the token must be RS256-signed by the Bot Connector, issued by
    api.botframework.com, and scoped to our MICROSOFT_APP_ID.
    """
    if settings.APP_ENV == "development":
        return True

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return False
    token = header[len("Bearer "):]

    try:
        kid = jwt.get_unverified_header(token).get("kid")
        key = next((k for k in await _teams_signing_keys() if k.get("kid") == kid), None)
        if key is None:
            return False
        jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.MICROSOFT_APP_ID,
            issuer=_TEAMS_ISSUER,
        )
        return True
    except Exception as exc:  # noqa: BLE001 — any failure is a rejected request
        logger.warning("Teams token validation failed: %s", exc)
        return False


def _strip_mentions(raw_text: str) -> str:
    """Remove Teams ``<at>Bot</at>`` mentions (incl. inner name) and HTML tags."""
    text_ = re.sub(r"<at\b[^>]*>.*?</at>", "", raw_text or "", flags=re.DOTALL)
    text_ = re.sub(r"<[^>]+>", "", text_)            # any remaining stray tags
    return re.sub(r"\s+", " ", text_).strip()         # collapse whitespace


def _extract_teams_attachment(attachments: list) -> dict | None:
    """Return {url, mime, filename} for the first supported attachment, else None."""
    for att in attachments:
        content_type = att.get("contentType", "")
        if content_type == _TEAMS_FILE_DOWNLOAD:
            content = att.get("content") or {}
            url = content.get("downloadUrl")
            if not url:
                continue
            name = att.get("name") or "teams_upload"
            ext = (content.get("fileType") or name.rsplit(".", 1)[-1] or "bin").lower()
            return {
                "url": url,
                "mime": _EXT_MIME.get(ext, "application/octet-stream"),
                "filename": name,
            }
        if content_type.startswith("image/"):
            url = att.get("contentUrl")
            if not url:
                continue
            return {
                "url": url,
                "mime": content_type,
                "filename": att.get("name") or f"teams_upload.{content_type.split('/')[-1]}",
            }
    return None


async def _handle_teams_media(
    media: dict,
    service_url: str,
    teams_conversation_id: str,
    conversation_id: UUID,
) -> None:
    """Download, validate, and ingest ephemeral media from Teams."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(media["url"])
            resp.raise_for_status()
            content = resp.content

        validated = file_validator.validate_upload(
            filename=media["filename"],
            content=content,
            declared_mime=media["mime"],
            max_bytes=settings.MAX_TEAMS_UPLOAD_BYTES,
        )

        await n8n_client.ingest_ephemeral(
            validated.content,
            str(conversation_id),
            validated.mime_type,
        )
        await teams.post_text(
            service_url,
            teams_conversation_id,
            "Indexed ✓ — ask me anything about this file for the next 60 minutes.",
        )
    except HTTPException as exc:
        await teams.post_text(service_url, teams_conversation_id, f"File upload failed: {exc.detail}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Teams media processing failed: %s", exc)
        await teams.post_text(service_url, teams_conversation_id, "Sorry, failed to process your file.")


async def _process_teams_message(
    activity_id: str,
    service_url: str,
    teams_conversation_id: str,
    teams_tenant_id: str,
    teams_user_id: str,
    query: str,
    media: dict | None = None,
) -> None:
    """Background task — runs Steps 2-8 with its own DB session."""
    async with AsyncSessionLocal() as db:
        ctx = MessageContext(
            request_id=activity_id,
            source="teams",
            query=query or ".",  # Placeholder if only media
            teams_service_url=service_url,
            teams_conversation_id=teams_conversation_id,
            teams_tenant_id=teams_tenant_id,
            teams_user_id=teams_user_id,
        )
        try:
            # Resolve identity and find/create conversation first
            await message_service._resolve_identity(ctx, db)
            await message_service._find_or_create_conversation(ctx, db)

            # Handle media upload if present
            if media is not None:
                await _handle_teams_media(
                    media, service_url, teams_conversation_id, ctx.conversation_id
                )
                if query:
                    await teams.post_text(service_url, teams_conversation_id, "🤔 Thinking...")
                    await message_service.process_message(ctx, db)
            elif query:
                await teams.post_text(service_url, teams_conversation_id, "🤔 Thinking...")
                await message_service.process_message(ctx, db)

        except message_service.IdentityResolutionError:
            await teams.post_text(
                service_url,
                teams_conversation_id,
                "This Microsoft Teams organization isn't registered. "
                "Please ask your admin to add it.",
            )
        except pipeline_client.PipelineError:
            await teams.post_text(service_url, teams_conversation_id, message_service.FALLBACK_MESSAGE)
        except Exception:  # noqa: BLE001 — never let a bg task crash silently
            logger.exception("Teams processing failed (activity=%s)", activity_id)


@router.post("/teams", summary="Microsoft Teams Bot Framework activity")
async def teams_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Verify → ACK 200 fast; heavy work runs in a BackgroundTask."""
    raw = await request.body()

    if not await _verify_teams_token(request):
        raise HTTPException(status_code=403, detail="Invalid Teams bot token")

    body = json.loads(raw)

    # Only handle user messages — ignore conversationUpdate, typing, etc.
    if body.get("type") != "message":
        return {"status": "ignored"}

    activity_id = body.get("id")
    query = _strip_mentions(body.get("text") or "")
    service_url = body.get("serviceUrl")
    conversation = body.get("conversation") or {}
    teams_conversation_id = conversation.get("id")
    from_ = body.get("from") or {}
    teams_user_id = from_.get("id")
    channel_data = body.get("channelData") or {}
    teams_tenant_id = (channel_data.get("tenant") or {}).get("id")
    media = _extract_teams_attachment(body.get("attachments") or [])

    # Dedup on activity id (same pattern as Slack event_id / Twilio MessageSid)
    if activity_id:
        result = await db.execute(
            text("INSERT INTO processed_requests (request_id) VALUES (:rid) ON CONFLICT DO NOTHING"),
            {"rid": activity_id},
        )
        await db.commit()
        if result.rowcount == 0:
            return {"status": "duplicate"}

    if not query and media is None:
        return {"status": "empty"}

    if not activity_id or not service_url or not teams_conversation_id \
            or not teams_user_id or not teams_tenant_id:
        logger.warning(
            "Teams activity missing required fields: activity_id=%s tenant=%s user=%s",
            activity_id, teams_tenant_id, teams_user_id,
        )
        return {"status": "ignored"}

    background_tasks.add_task(
        _process_teams_message,
        activity_id,
        service_url,
        teams_conversation_id,
        teams_tenant_id,
        teams_user_id,
        query,
        media,
    )
    return {"status": "ok"}


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


class _IngestionStatusBody(BaseModel):
    document_id: _uuid.UUID
    status: str                         # completed | failed
    chunk_count: int | None = None
    error_message: str | None = None
    callback_token: str | None = None


@router.post("/n8n/ingestion-status", summary="n8n ingestion pipeline callback")
async def n8n_ingestion_callback(
    body: _IngestionStatusBody,
    db: AsyncSession = Depends(get_db),
):
    if body.callback_token != settings.N8N_CALLBACK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid callback token")

    doc = await db.get(Document, body.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = body.status
    doc.chunk_count = body.chunk_count or 0
    doc.error_message = body.error_message
    await db.commit()

    logger.info("Ingestion status updated: document=%s status=%s chunks=%s",
                body.document_id, body.status, body.chunk_count)
    return {"ok": True}
