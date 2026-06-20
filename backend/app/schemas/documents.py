"""Pydantic schemas for document endpoints. Owner: M3.

Shapes match specs/openapi.yaml DocumentOut, DocumentList, UrlIngestRequest.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    source_type: str                    # pdf | docx | txt | url
    source_url: str | None
    status: str                         # pending | processing | completed | failed
    chunk_count: int
    error_message: str | None
    created_at: datetime


class DocumentList(BaseModel):
    documents: list[DocumentOut]
    total: int


class UrlIngestRequest(BaseModel):
    url: str = Field(description="Publicly reachable URL to ingest")
    title: str | None = None
