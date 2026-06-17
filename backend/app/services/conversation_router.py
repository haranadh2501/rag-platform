"""conversation_router.py — conversation lifecycle for all channels.

Schema: UNIQUE(user_id, channel) — one conversation per user per channel at a time.
Reset = hard delete + create fresh (no is_active flag; enforced by the UNIQUE constraint).
Owner: M4.
"""
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.services.types import MessageContext, ChannelType
from app.models.models import Conversation

logger = logging.getLogger(__name__)


async def find_or_create_conversation(ctx: MessageContext, db: AsyncSession) -> uuid.UUID:
    """Return the UUID of the conversation for this request.

    Every lookup is scoped to (user_id, channel) — cross-user access is impossible.

    Web with conversation_id:    validate ownership → return it (PermissionError if mismatch)
    Web without conversation_id: find existing web conversation or create new one
    Slack:                        find existing slack conversation or create new one
    """
    channel = ctx.source.value.lower()

    if ctx.source == ChannelType.WEB and ctx.conversation_id is not None:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id        == ctx.conversation_id,
                Conversation.user_id   == ctx.user_id,
                Conversation.tenant_id == ctx.tenant_id,
            )
        )
        convo = result.scalar_one_or_none()
        if not convo:
            raise PermissionError(
                f"Conversation {ctx.conversation_id} not found for this user"
            )
        return convo.id

    # Find existing conversation for (user_id, channel) or create one
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == ctx.user_id,
            Conversation.channel == channel,
        )
    )
    convo = result.scalar_one_or_none()
    if convo:
        return convo.id

    return await _create_conversation(ctx, db)


async def reset_conversation(ctx: MessageContext, db: AsyncSession) -> uuid.UUID:
    """Hard-delete the current conversation for this (user_id, channel), then create a fresh one.

    Called when reset_requested is True. Chat history is permanently removed.
    The UNIQUE(user_id, channel) constraint makes the hard-delete safe (no orphaned FK rows
    because ChatMessage cascades via ondelete="CASCADE" on conversations.id).
    """
    channel = ctx.source.value.lower()
    await db.execute(
        delete(Conversation).where(
            Conversation.user_id == ctx.user_id,
            Conversation.channel == channel,
        )
    )
    await db.flush()
    return await _create_conversation(ctx, db)


async def _create_conversation(ctx: MessageContext, db: AsyncSession) -> uuid.UUID:
    convo = Conversation(
        tenant_id = ctx.tenant_id,
        user_id   = ctx.user_id,
        channel   = ctx.source.value.lower(),
    )
    db.add(convo)
    await db.flush()   # populate convo.id without committing
    return convo.id
