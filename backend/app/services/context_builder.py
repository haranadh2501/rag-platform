"""context_builder.py — normalize raw channel payloads into MessageContext.

No business logic here — extraction and identity resolution only.
Owner: M4.
"""
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.types import MessageContext, ChannelType
from app.models.models import User, SlackWorkspaceMap

logger = logging.getLogger(__name__)

RESET_COMMANDS = {"/new", "/restart", "/clear"}


async def build_slack_context(payload: dict, db: AsyncSession) -> MessageContext:
    """Build MessageContext from a Slack Events API payload.

    Raises ValueError  — required fields missing from payload.
    Raises LookupError — workspace or user not registered in the platform.
    """
    event     = payload.get("event", {})
    team_id   = payload.get("team_id")
    slack_uid = event.get("user")
    text      = (event.get("text") or "").strip()
    event_id  = payload.get("event_id")

    if not all([team_id, slack_uid, event_id]):
        raise ValueError(
            f"Missing required Slack fields: team_id={team_id!r} "
            f"user={slack_uid!r} event_id={event_id!r}"
        )

    # Resolve tenant from Slack workspace
    result = await db.execute(
        select(SlackWorkspaceMap).where(SlackWorkspaceMap.team_id == team_id)
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise LookupError(
            f"Slack workspace {team_id!r} is not registered to any tenant"
        )

    # Resolve internal user from slack_user_id, scoped to that tenant
    result = await db.execute(
        select(User).where(
            User.tenant_id == mapping.tenant_id,
            User.slack_user_id == slack_uid,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise LookupError(
            f"Slack user {slack_uid!r} not registered in tenant {mapping.tenant_id}"
        )

    return MessageContext(
        request_id        = event_id,
        source            = ChannelType.SLACK,
        user_id           = user.id,
        tenant_id         = mapping.tenant_id,
        external_identity = slack_uid,
        team_id           = team_id,
        raw_query         = text,
        reset_requested   = text.strip().lower() in RESET_COMMANDS,
        conversation_id   = None,   # set by find_or_create_conversation inside handle_message
        _slack_event      = {
            "channel": event.get("channel", ""),
            "ts":      event.get("ts", ""),
        },
    )


def build_web_context(user: "User", query: str, conversation_id: str | None) -> MessageContext:
    """Build MessageContext from an authenticated User ORM object.

    user is the object returned by get_current_user() — already JWT-validated.
    Synchronous: no DB access needed (all data comes from the User object).
    """
    return MessageContext(
        request_id        = str(uuid.uuid4()),
        source            = ChannelType.WEB,
        user_id           = user.id,
        tenant_id         = user.tenant_id,
        external_identity = user.email,
        team_id           = None,
        raw_query         = query,
        reset_requested   = False,
        conversation_id   = uuid.UUID(conversation_id) if conversation_id else None,
    )
