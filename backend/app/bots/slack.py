"""Slack delivery (M4).

Posts answers back to Slack via the Web API `chat.postMessage`, threaded under the
originating message. `SLACK_BOT_TOKEN` is read from settings (already defined in config).
"""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
_MAX_SOURCES = 3


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
