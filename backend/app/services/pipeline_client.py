"""HTTP client for the RAG pipeline (M4).

POSTs to `PIPELINE_URL` (the n8n production URL in prod, mock in dev) and
returns the parsed response.

Uses httpx sync client in asyncio.to_thread — the async client returns empty
bodies for some external endpoints when running inside uvicorn's event loop.
"""
import asyncio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

PIPELINE_URL = settings.PIPELINE_URL
PIPELINE_TIMEOUT_SECONDS = settings.PIPELINE_TIMEOUT_SECONDS


class PipelineError(Exception):
    """Raised when the pipeline call fails, times out, or returns non-2xx."""


def _sync_call(payload: dict) -> dict:
    """Synchronous HTTP POST via requests — runs in a thread pool."""
    import requests
    logger.info("Pipeline calling %s", PIPELINE_URL)
    resp = requests.post(PIPELINE_URL, json=payload, timeout=PIPELINE_TIMEOUT_SECONDS)
    logger.info("Pipeline response status=%s len=%s", resp.status_code, len(resp.content))
    resp.raise_for_status()
    return resp.json()


async def call_pipeline(payload: dict) -> dict:
    """POST `payload` to the pipeline and return the parsed JSON response.

    Raises `PipelineError` on timeout, transport error, non-2xx, or bad JSON.
    """
    try:
        return await asyncio.to_thread(_sync_call, payload)
    except Exception as exc:
        logger.exception("Pipeline call to %s failed", PIPELINE_URL)
        raise PipelineError(str(exc)) from exc
