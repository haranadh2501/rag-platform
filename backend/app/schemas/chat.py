"""Pydantic schemas for conversation endpoints. Owner: M3.

Shapes match specs/openapi.yaml ConversationOut, ChatMessageOut.

Note: faithfulness and requires_clarification are written by the pipeline
when available. faithfulness is nullable; requires_clarification defaults
to False via the DB column default — both are read directly from ORM.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str                           # user | assistant
    content: str
    sources: list[dict]
    faithfulness: float | None
    requires_clarification: bool
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    channel: str
    created_at: datetime
    message_count: int                  # computed — not an ORM column


class ConversationDetail(ConversationOut):
    messages: list[ChatMessageOut]
