"""Core types shared across all M4 services.

Every channel adapter (Web, Slack) normalises its payload into MessageContext
before any processing. Import from here — never redefine these elsewhere.
"""
import uuid
from dataclasses import dataclass, field
from enum import Enum


class ChannelType(str, Enum):
    WEB   = "WEB"
    SLACK = "SLACK"


@dataclass
class MessageContext:
    request_id:        str               # event_id (Slack) | generated UUID (Web)
    source:            ChannelType       # WEB | SLACK
    user_id:           uuid.UUID         # resolved from JWT (Web) or slack_user_id lookup (Slack)
    tenant_id:         uuid.UUID         # scopes the n8n RAG query to the right knowledge base
    external_identity: str               # email (Web) | slack_user_id (Slack)
    team_id:           str | None        # Slack workspace ID; None for Web
    raw_query:         str               # message text
    reset_requested:   bool              # True if raw_query is /new /restart /clear (Slack)
    conversation_id:   uuid.UUID | None = field(default=None)   # set by find_or_create_conversation
    _slack_event:      dict             = field(default_factory=dict, repr=False)  # channel + ts for threading
