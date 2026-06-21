"""
Chat API routes.
- `POST /chat/query` — web adapter over the unified message service (Owner: M4).
- conversation CRUD — Owner: M3.
"""
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import ChatMessage, Conversation, User
from app.schemas.chat import ChatMessageOut, ConversationDetail, ConversationOut
from app.services import message_service, pipeline_client
from app.services.types import MessageContext

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatQueryRequest(BaseModel):
    """Matches openapi.yaml ChatQueryRequest."""
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
    except pipeline_client.PipelineError as exc:
        logger.error("PipelineError detail: %s", exc)
        return JSONResponse(status_code=502, content={
            "answer": message_service.FALLBACK_MESSAGE,
            "sources": [],
            "follow_up_questions": [],
            "debug_error": str(exc),
        })


# ══════════════════════════════════════════
# CONVERSATION CRUD  (M3)
# ══════════════════════════════════════════

@router.get("/conversations", summary="List conversations for current user")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Conversation, func.count(ChatMessage.id).label("msg_count"))
        .outerjoin(ChatMessage, ChatMessage.conversation_id == Conversation.id)
        .where(Conversation.user_id == current_user.id)
        .group_by(Conversation.id)
        .order_by(Conversation.created_at.desc())
    )).all()

    return {
        "conversations": [
            ConversationOut(
                id=conv.id,
                title=conv.title,
                channel=conv.channel,
                created_at=conv.created_at,
                message_count=count or 0,
            )
            for conv, count in rows
        ]
    }


@router.get("/conversations/{conversation_id}", summary="Get conversation with messages")
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = (await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )).scalar_one_or_none()

    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    messages = (await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
    )).scalars().all()

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        channel=conv.channel,
        created_at=conv.created_at,
        message_count=len(messages),
        messages=[ChatMessageOut.model_validate(m) for m in messages],
    )


@router.delete("/conversations/{conversation_id}", status_code=204, summary="Delete conversation")
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = (await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )).scalar_one_or_none()

    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(conv)
    await db.commit()
