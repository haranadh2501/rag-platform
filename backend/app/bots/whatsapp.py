"""
WhatsApp bot logic — Twilio integration.
Owner: M12 — implement handle_whatsapp_message and helper functions.
"""
import logging

import httpx
from twilio.rest import Client

from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_WHATSAPP_LENGTH = 1600
_MAX_SOURCES = 3


def twiml_reply(message: str) -> str:
    """Format a TwiML XML response for WhatsApp."""
    message = message[:1600]  # WhatsApp character limit
    escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<?xml version="1.0"?><Response><Message>{escaped}</Message></Response>'


async def post_text(to: str, text: str) -> None:
    """Send a plain text message (for "🤔 Thinking..." or error messages)."""
    text = text[:_MAX_WHATSAPP_LENGTH]
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=to,
            body=text
        )
    except Exception as exc:
        logger.error("Twilio messages.create failed: %s", exc)


async def post_reply(to: str, answer: str, sources: list) -> None:
    """Send answer + sources via Twilio REST API (not TwiML)."""
    # Format: answer text + "\n\n📚 Sources: Title p.N, Title p.N"
    formatted_text = answer
    if sources:
        source_lines = []
        for src in sources[:_MAX_SOURCES]:
            title = src.get("title", "source")
            page = src.get("page_number")
            if page:
                source_lines.append(f"{title} p.{page}")
            else:
                source_lines.append(title)
        formatted_text += f"\n\n📚 Sources: {', '.join(source_lines)}"

    # Truncate to 1600 chars (WhatsApp limit)
    formatted_text = formatted_text[:_MAX_WHATSAPP_LENGTH]

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=to,
            body=formatted_text
        )
    except Exception as exc:
        logger.error("Twilio messages.create failed: %s", exc)
