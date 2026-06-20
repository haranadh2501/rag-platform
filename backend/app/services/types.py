"""Shared data carrier for the unified message service (M4).

All channel adapters normalize their payload into a `MessageContext` before
handing it to `message_service.process_message`.
"""
from dataclasses import dataclass
from uuid import UUID


@dataclass
class MessageContext:
    request_id: str                       # UUID (web) | event_id (Slack)
    source: str                           # "web" | "slack"
    query: str                            # message text
    # Resolved in Step 2 — present on entry for web, filled in for Slack.
    user_id: UUID | None = None           # internal user ID
    tenant_id: UUID | None = None         # from JWT (web) | slack_workspace_map (Slack)
    conversation_id: UUID | None = None   # set in Step 3
    # Slack reply-back + raw identity (None for web)
    slack_channel: str | None = None
    slack_thread_ts: str | None = None
    slack_team_id: str | None = None      # Slack team_id → tenant resolution
    slack_user_id: str | None = None      # Slack user id → internal user resolution
