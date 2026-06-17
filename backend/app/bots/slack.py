"""Slack delivery functions — chat.postMessage + Block Kit formatting.

Owner: M4.
Called by message_handler (for answers) and webhooks (for reset confirmation / errors).
"""
import logging
import httpx

from app.core.config import settings
from app.services.types import MessageContext

logger = logging.getLogger(__name__)

SLACK_API = "https://slack.com/api"


async def post_reply(ctx: MessageContext, answer: str, sources: list) -> None:
    """Post a grounded answer in the Slack thread that triggered the request."""
    event     = ctx._slack_event
    channel   = event.get("channel", "")
    thread_ts = event.get("ts", "")

    blocks = _build_blocks(answer, sources)
    await _post_message(channel=channel, thread_ts=thread_ts, text=answer, blocks=blocks)


async def post_text(channel: str, thread_ts: str, text: str) -> None:
    """Post a plain-text message (reset confirmation, error fallback)."""
    await _post_message(channel=channel, thread_ts=thread_ts, text=text, blocks=None)


async def _post_message(
    channel: str, thread_ts: str, text: str, blocks: list | None
) -> None:
    payload: dict = {
        "channel":   channel,
        "thread_ts": thread_ts,
        "text":      text,
    }
    if blocks:
        payload["blocks"] = blocks

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{SLACK_API}/chat.postMessage",
            headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"},
            json=payload,
        )

    data = resp.json()
    if not data.get("ok"):
        logger.error(
            "chat.postMessage failed: error=%s channel=%s",
            data.get("error"), channel,
        )


def _build_blocks(answer: str, sources: list) -> list:
    """Build Slack Block Kit payload: answer section + source context block."""
    blocks: list = [
        {"type": "section", "text": {"type": "mrkdwn", "text": answer}},
    ]
    if sources:
        lines = "\n".join(
            f"• *{s.get('title', 'Source')}*"
            + (f" (p.{s['page_number']})" if s.get("page_number") else "")
            for s in sources[:3]   # cap at 3 in the Slack card
        )
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"*Sources:*\n{lines}"}],
        })
    return blocks
