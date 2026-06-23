"""
n8n HTTP client — called by FastAPI to trigger n8n workflows.
Owner: M3 (uses this). Do not put RAG logic here.
"""
import logging
import httpx
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Mock response for MOCK_N8N=true mode
MOCK_RETRIEVE_RESPONSE = {
    "answer": "Based on the uploaded documentation, here is the answer to your question. "
              "This is a mock response — set MOCK_N8N=false to use real n8n RAG. [Sample Manual, p.12]",
    "sources": [
        {
            "document_id": "00000000-0000-0000-0000-000000000001",
            "title": "Sample Product Manual",
            "chunk_text": "This is a sample chunk from the document that was used to generate the answer.",
            "page_number": 12,
            "score": 0.94,
        }
    ],
    "follow_up_questions": [
        "Can you explain this in more detail?",
        "What are the next steps?",
        "Who should I contact for further help?",
    ],
    "metadata": {
        "model": "gpt-4o-mini",
        "retrieval_time_ms": 1200,
        "chunks_retrieved": 5,
        "mock": True,
    },
}


async def ingest(
    document_id: str,
    tenant_id: str,
    source_url: str,
    source_type: str,
    title: str,
) -> dict:
    """Trigger n8n ingestion workflow."""
    if settings.MOCK_N8N:
        logger.info("[MOCK] Ingestion triggered for %s", document_id)
        return {"status": "mock_started"}

    payload = {
        "document_id": document_id,
        "tenant_id":   tenant_id,
        "source_type": source_type,
        "source_url":  source_url,
        "title":       title,
    }
    logger.info("[n8n ingest] → POST %s", settings.N8N_INGEST_WEBHOOK_URL)
    logger.info("[n8n ingest] → payload: %s", payload)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(settings.N8N_INGEST_WEBHOOK_URL, json=payload)
        logger.info("[n8n ingest] ← status: %s", resp.status_code)
        logger.info("[n8n ingest] ← body: %s", resp.text[:500])
        resp.raise_for_status()
        return resp.json()


async def retrieve(
    query: str,
    tenant_id: str,
    conversation_history: Optional[list] = None,
    max_chunks: int = 5,
) -> dict:
    """Trigger n8n retrieval workflow and return grounded response."""
    if settings.MOCK_N8N:
        logger.info(f"[MOCK] Retrieval for tenant={tenant_id} query='{query[:50]}...'")
        return MOCK_RETRIEVE_RESPONSE

    payload = {
        "query": query,
        "tenant_id": tenant_id,
        "conversation_history": conversation_history or [],
        "max_chunks": max_chunks,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(settings.N8N_RETRIEVE_WEBHOOK_URL, json=payload)
        resp.raise_for_status()
        return resp.json()


async def ingest_ephemeral_base64(
    tenant_id: str,
    n8n_session_id: str,
    source_name: str,
    file_base64: str,
    ttl_seconds: int = 3600,
) -> dict:
    """POST base64-encoded file to n8n ephemeral ingest workflow.

    Retries once on 5xx. Caller wraps this in asyncio.wait_for(timeout=300).
    """
    payload = {
        "conversation_id": n8n_session_id,
        "tenant_id": tenant_id,
        "source_name": source_name,
        "file_base64": file_base64,
        "ttl_seconds": ttl_seconds,
    }
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=310.0) as client:
                resp = await client.post(settings.N8N_EPHEMERAL_INGEST_WF_URL, json=payload)
                if resp.status_code >= 500 and attempt == 0:
                    last_exc = httpx.HTTPStatusError(
                        f"5xx on attempt {attempt}", request=resp.request, response=resp
                    )
                    logger.warning("[n8n ephemeral ingest] 5xx on attempt 0, retrying: %s", resp.text[:200])
                    continue
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            last_exc = exc
    raise last_exc


async def retrieve_ephemeral(
    query: str,
    tenant_id: str,
    n8n_session_id: str,
    conversation_history: list[dict] | None = None,
    max_chunks: int = 5,
) -> dict:
    """POST query to n8n ephemeral retrieve endpoint, scoped to this session's docs."""
    payload = {
        "query": query,
        "tenant_id": tenant_id,
        "conversation_id": n8n_session_id,
        "max_chunks": max_chunks,
        "conversation_history": conversation_history or [],
    }
    logger.info("[ephemeral retrieve] → URL: %s", settings.N8N_EPHEMERAL_RETRIEVE_URL)
    logger.info("[ephemeral retrieve] → payload: %s", payload)
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(settings.N8N_EPHEMERAL_RETRIEVE_URL, json=payload)
        logger.info("[ephemeral retrieve] ← status: %s", resp.status_code)
        logger.info("[ephemeral retrieve] ← body: %s", resp.text[:1000])
        resp.raise_for_status()
        return resp.json()


async def purge_ephemeral(tenant_id: str, n8n_session_id: str) -> dict:
    """POST to n8n ephemeral purge to wipe session data immediately."""
    payload = {"conversation_id": n8n_session_id, "tenant_id": tenant_id}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(settings.N8N_EPHEMERAL_PURGE_URL, json=payload)
        resp.raise_for_status()
        return resp.json()


async def ingest_ephemeral(
    content: bytes,
    conversation_id: str,
    mime_type: str,
) -> dict:
    """Trigger n8n ephemeral ingestion workflow for WhatsApp/chat uploads.

    Files are indexed temporarily (1-hour TTL) and scoped to a conversation_id.
    """
    if settings.MOCK_N8N:
        logger.info(f"[MOCK] Ephemeral ingest for conversation={conversation_id}")
        return {"status": "mock_indexed"}

    # Send multipart form data with the file
    files = {"file": ("upload", content, mime_type)}
    data = {"conversation_id": conversation_id}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            settings.N8N_EPHEMERAL_INGEST_WEBHOOK_URL,
            files=files,
            data=data
        )
        resp.raise_for_status()
        return resp.json()
