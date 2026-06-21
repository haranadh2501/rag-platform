"""Mock pipeline endpoint — returns a canned RAG response for development.

Replaces a real n8n retrieval workflow. Set PIPELINE_URL=http://localhost:8000/mock/pipeline
in .env to use this during local development.
Owner: M4.
"""
import logging
from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter()

MOCK_RESPONSE = {
    "answer": (
        "This is a sample response from the mock pipeline. "
        "In production, this will be a grounded answer from the RAG engine "
        "with source citations. [Sample Document, p.12]"
    ),
    "sources": [
        {
            "title": "Sample Product Manual",
            "url": "https://example.com/docs/manual",
            "chunk_id": "chunk-001",
        }
    ],
    "follow_up_questions": [
        "Can you explain this in more detail?",
        "What are the next steps?",
        "Who should I contact for further help?",
    ],
}


@router.post("/pipeline", summary="Mock RAG pipeline (dev only)")
async def mock_pipeline(request: Request):
    """Accepts any pipeline payload and returns a canned success response."""
    body = await request.json()
    logger.info("[MOCK] Pipeline called with query: %.100s", body.get("query", "")[:100])
    return MOCK_RESPONSE
