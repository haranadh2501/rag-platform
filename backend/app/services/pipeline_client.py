"""HTTP client for the RAG pipeline (M4).

POSTs to `PIPELINE_URL` (the n8n production URL in prod, mock in dev) and
returns the parsed response.

Uses asyncio.to_thread + httpx.Client (sync) to avoid a Windows ProactorEventLoop
bug where chunked+gzip responses return an empty body inside uvicorn's event loop.
"""
import asyncio
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

PIPELINE_URL = settings.PIPELINE_URL
PIPELINE_TIMEOUT_SECONDS = settings.PIPELINE_TIMEOUT_SECONDS


class PipelineError(Exception):
    """Raised when the pipeline call fails, times out, or returns non-2xx."""


def _sync_call(payload: dict) -> dict:
    """Synchronous HTTP call using urllib — avoids httpx/event-loop issues."""
    import json as jsonlib
    import urllib.request
    data = jsonlib.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        PIPELINE_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=int(PIPELINE_TIMEOUT_SECONDS)) as resp:
        raw = resp.read()
        logger.info("Pipeline raw response: %r", raw[:300])
        return jsonlib.loads(raw.decode("utf-8"))


async def call_pipeline(payload: dict) -> dict:
    """POST `payload` to the pipeline and return the parsed JSON response.

    Raises `PipelineError` on timeout, transport error, non-2xx, or bad JSON.
    """
    try:
        return await asyncio.to_thread(_sync_call, payload)
    except (httpx.HTTPError, ValueError, OSError) as exc:
        logger.exception("Pipeline call to %s failed", PIPELINE_URL)
        raise PipelineError(str(exc)) from exc
