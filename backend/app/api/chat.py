"""
Chat API routes.
- `POST /chat/query` — web adapter over the unified message service (Owner: M4).
- conversation CRUD — Owner: M3 (stubs below).
"""
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import User
from app.services import message_service, pipeline_client
from app.services.types import MessageContext

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatQueryRequest(BaseModel):
    """Matches openapi.yaml ChatQueryRequest. Defined inline — no schemas/chat.py exists."""
    query: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    max_chunks: int = Field(default=5, ge=1, le=20)


@router.post("/query", summary="Send a query — returns grounded answer with citations")
async def chat_query(
    payload: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Build a web MessageContext from the JWT, delegate to process_message, return inline.

    401 (invalid JWT) and 422 (missing query) are enforced by the dependency/schema.
    """
    ctx = MessageContext(
        request_id=str(uuid4()),
        source="web",
        query=payload.query,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        conversation_id=payload.conversation_id,
    )
    try:
        return await message_service.process_message(ctx, db)
    except message_service.ConversationOwnershipError:
        raise HTTPException(status_code=403, detail="conversation_id belongs to another user")
    except pipeline_client.PipelineError:
        return JSONResponse(status_code=502, content={
            "answer": message_service.FALLBACK_MESSAGE,
            "sources": [],
            "follow_up_questions": [],
        })


@router.get("/conversations", summary="List conversations")
async def list_conversations():
    """M3: Return conversations for current user."""
    raise HTTPException(status_code=501, detail="M3: implement conversation list")


@router.get("/conversations/{conversation_id}", summary="Get conversation with messages")
async def get_conversation(conversation_id: str):
    """M3: Return conversation + all messages."""
    raise HTTPException(status_code=501, detail="M3: implement get conversation")


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str):
    """M3: Delete conversation and all messages."""
    raise HTTPException(status_code=501, detail="M3: implement delete conversation")
