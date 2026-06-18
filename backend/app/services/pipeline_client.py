"""HTTP client for the RAG pipeline (M4).

POSTs to `PIPELINE_URL` (the mock endpoint in dev, the real n8n URL in prod) and
returns the parsed response. Config is read via `os.getenv` so this module stays
self-contained and does not require changes to `app.core.config` (M2-owned).
"""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

PIPELINE_URL = os.getenv(
    "PIPELINE_URL", "http://localhost:8000/webhooks/mock/pipeline"
)
PIPELINE_TIMEOUT_SECONDS = float(os.getenv("PIPELINE_TIMEOUT_SECONDS", "120"))


class PipelineError(Exception):
    """Raised when the pipeline call fails, times out, or returns non-2xx."""


async def call_pipeline(payload: dict) -> dict:
    """POST `payload` to the pipeline and return the parsed JSON response.

    Raises `PipelineError` on timeout, transport error, non-2xx, or bad JSON.
    """
    try:
        async with httpx.AsyncClient(timeout=PIPELINE_TIMEOUT_SECONDS) as client:
            resp = await client.post(PIPELINE_URL, json=payload)
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.exception("Pipeline call to %s failed", PIPELINE_URL)
        raise PipelineError(str(exc)) from exc
