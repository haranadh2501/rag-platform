"""Pydantic schemas for the Chat API.

Owner: M3/M4. Shapes must match specs/openapi.yaml exactly.
"""
from pydantic import BaseModel, Field


class ChatQueryRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=4000,
        examples=["What is the refund policy?"],
    )
    conversation_id: str | None = Field(
        default=None,
        description="Omit to start a new conversation; pass existing ID to continue.",
        examples=["00000000-0000-0000-0000-000000000099"],
    )
