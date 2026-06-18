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
    file_path: str,
    source_type: str,
    title: str,
) -> dict:
    """Trigger n8n ingestion workflow."""
    if settings.MOCK_N8N:
        logger.info(f"[MOCK] Ingestion triggered for {document_id}")
        return {"status": "mock_started"}

    payload = {
        "document_id": document_id,
        "tenant_id": tenant_id,
        "file_path": file_path,
        "source_type": source_type,
        "title": title,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(settings.N8N_INGEST_WEBHOOK_URL, json=payload)
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
