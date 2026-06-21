"""Microsoft Teams delivery (M14) — Bot Framework Connector integration.

Mirrors ``bots/whatsapp.py``. Teams replies are sent *proactively* via the Bot
Connector REST API (``{serviceUrl}/v3/conversations/{id}/activities``), authed
with an AAD client-credentials token — the same ACK-fast-then-reply pattern the
WhatsApp bot uses with Twilio's REST API.

Owner: M14 — implement send helpers and token acquisition.
"""
import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Teams activities cap text well above WhatsApp's 1600; keep a safe ceiling.
_MAX_TEAMS_LENGTH = 28_000
_MAX_SOURCES = 3
_BOTFRAMEWORK_SCOPE = "https://api.botframework.com/.default"

# In-process access-token cache: (token, expires_at_epoch).
_token_cache: tuple[str, float] | None = None


def _token_url() -> str:
    """AAD token endpoint — single-tenant if configured, else multi-tenant."""
    tenant = settings.MICROSOFT_APP_TENANT_ID or "botframework.com"
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"


async def _get_access_token() -> str:
    """Fetch (and cache) a Bot Connector access token via client credentials."""
    global _token_cache
    now = time.time()
    if _token_cache and _token_cache[1] > now + 60:
        return _token_cache[0]

    data = {
        "grant_type": "client_credentials",
        "client_id": settings.MICROSOFT_APP_ID,
        "client_secret": settings.MICROSOFT_APP_PASSWORD,
        "scope": _BOTFRAMEWORK_SCOPE,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(_token_url(), data=data)
        resp.raise_for_status()
        payload = resp.json()

    token = payload["access_token"]
    expires_in = int(payload.get("expires_in", 3600))
    _token_cache = (token, now + expires_in)
    return token


async def post_text(service_url: str, conversation_id: str, text: str) -> None:
    """Send a plain text message (for "🤔 Thinking..." or error messages)."""
    await _send_activity(service_url, conversation_id, text[:_MAX_TEAMS_LENGTH])


async def post_reply(
    service_url: str, conversation_id: str, answer: str, sources: list
) -> None:
    """Send an answer with a Markdown sources footer (capped at 3)."""
    formatted_text = answer
    if sources:
        source_lines = []
        for src in sources[:_MAX_SOURCES]:
            title = src.get("title", "source")
            page = src.get("page_number")
            source_lines.append(f"{title} p.{page}" if page else title)
        formatted_text += f"\n\n**📚 Sources:** {', '.join(source_lines)}"

    await _send_activity(service_url, conversation_id, formatted_text[:_MAX_TEAMS_LENGTH])


async def _send_activity(service_url: str, conversation_id: str, text: str) -> None:
    """POST a message activity to the Bot Connector for *conversation_id*."""
    if not service_url or not conversation_id:
        logger.error("Teams send skipped: missing service_url/conversation_id")
        return

    url = f"{service_url.rstrip('/')}/v3/conversations/{conversation_id}/activities"
    body = {"type": "message", "textFormat": "markdown", "text": text}
    try:
        token = await _get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code >= 400:
                logger.error(
                    "Teams send failed: %s %s", resp.status_code, resp.text[:500]
                )
    except Exception as exc:  # noqa: BLE001 — delivery failures must not crash the bg task
        logger.error("Teams connector request failed: %s", exc)
