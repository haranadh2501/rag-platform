"""Chat API routes — query (with MOCK_N8N mode), conversations.

Owner: M3 (list/get/delete) · M4 (query endpoint wired here via PR coordination).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import User
from app.schemas.chat import ChatQueryRequest
from app.services.context_builder import build_web_context
from app.services.conversation_router import find_or_create_conversation
from app.services.message_handler import handle_message

router = APIRouter()


@router.post("/query", summary="Send a query — returns grounded answer with citations")
async def chat_query(
    body:         ChatQueryRequest,
    current_user: User           = Depends(get_current_user),
    db:           AsyncSession   = Depends(get_db),
):
    """Web chat endpoint. Runs the full RAG pipeline inline and returns the answer."""
    # Build normalized MessageContext from JWT-authenticated user
    ctx = build_web_context(current_user, body.query, body.conversation_id)

    # Resolve conversation — validates ownership if conversation_id was provided
    try:
        ctx.conversation_id = await find_or_create_conversation(ctx, db)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    # Commit conversation so handle_message's independent session can see it
    await db.commit()

    # Run handler inline (Web is synchronous — blocks until n8n responds)
    result = await handle_message(ctx)

    if result is None:
        raise HTTPException(status_code=502, detail="RAG service unavailable — please try again")

    return result


@router.get("/conversations", summary="List conversations")
async def list_conversations(current_user: User = Depends(get_current_user)):
    """M3: Return conversations for current user."""
    raise HTTPException(status_code=501, detail="M3: implement conversation list")


@router.get("/conversations/{conversation_id}", summary="Get conversation with messages")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    """M3: Return conversation + all messages."""
    raise HTTPException(status_code=501, detail="M3: implement get conversation")


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    """M3: Delete conversation and all messages."""
    raise HTTPException(status_code=501, detail="M3: implement delete conversation")
