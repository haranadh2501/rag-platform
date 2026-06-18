"""Slack delivery (M4).

Posts answers back to Slack via the Web API `chat.postMessage`, threaded under the
originating message. `SLACK_BOT_TOKEN` is read from settings (already defined in config).
"""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
_LOOKUP_EMAIL_URL = "https://slack.com/api/users.lookupByEmail"
_MAX_SOURCES = 3


class SlackUserNotFoundError(Exception):
    """Raised when the email is not in the Slack workspace."""


class SlackAPIError(Exception):
    """Raised when the Slack API returns ok=false for a non-lookup reason."""


async def post_text(channel: str, thread_ts: str | None, text: str) -> None:
    """Post a plain text message in-thread."""
    await _post({"channel": channel, "thread_ts": thread_ts, "text": text})


async def post_reply(
    channel: str, thread_ts: str | None, answer: str, sources: list
) -> None:
    """Post an answer with a Block Kit sources context block (capped at 3)."""
    blocks: list[dict] = [
        {"type": "section", "text": {"type": "mrkdwn", "text": answer}}
    ]
    if sources:
        lines = [f"• {s.get('title', 'source')}" for s in sources[:_MAX_SOURCES]]
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "\n".join(lines)}],
        })
    await _post({
        "channel": channel,
        "thread_ts": thread_ts,
        "text": answer,        # fallback for notifications / clients without blocks
        "blocks": blocks,
    })


async def lookup_user_by_email(email: str) -> str:
    """Return the Slack member ID for *email*.

    Raises SlackUserNotFoundError if the email is not in the workspace.
    Raises SlackAPIError for any other Slack error or transport failure.
    """
    headers = {"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_LOOKUP_EMAIL_URL, params={"email": email}, headers=headers)
        data = resp.json()
    except httpx.HTTPError as exc:
        raise SlackAPIError(f"Transport error: {exc}") from exc

    if not data.get("ok"):
        error = data.get("error", "unknown_error")
        if error == "users_not_found":
            raise SlackUserNotFoundError(email)
        raise SlackAPIError(error)

    return data["user"]["id"]


async def _post(payload: dict) -> None:
    headers = {
        "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_POST_MESSAGE_URL, json=payload, headers=headers)
            data = resp.json()
        if not data.get("ok"):
            logger.error("Slack chat.postMessage failed: %s", data.get("error"))
    except httpx.HTTPError as exc:
        logger.error("Slack chat.postMessage transport error: %s", exc)
