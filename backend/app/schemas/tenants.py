"""Pydantic schemas for tenant endpoints. Owner: M3.

Kept separate from M2's schemas/auth.py to allow independent evolution
as multi-tenant admin features are added later.

Shapes match specs/openapi.yaml TenantOut, TenantUpdate.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    created_at: datetime


class TenantUpdate(BaseModel):
    """All fields optional — PATCH semantics, only supplied fields are written."""
    name: str | None = None
    is_active: bool | None = None
    plan: str | None = None
