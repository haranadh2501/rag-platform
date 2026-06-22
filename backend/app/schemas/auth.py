"""Pydantic v2 schemas for the Auth API.

Owner: M2. Shapes must match `specs/openapi.yaml` (LoginRequest, LoginResponse,
RegisterRequest, UserOut) exactly — that file is the contract.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["admin@iisc-demo.com"])
    password: str = Field(min_length=8, examples=["changeme-strong-password"])


class RegisterRequest(BaseModel):
    email: EmailStr = Field(examples=["analyst@iisc-demo.com"])
    password: str = Field(min_length=8, examples=["a-strong-password"])
    tenant_id: uuid.UUID = Field(examples=["83d5f2cf-e28a-48fa-8092-367735a99c1d"])
    role: Literal["admin", "user"] = "user"


class UserOut(BaseModel):
    # from_attributes lets us return ORM `User` objects directly.
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "1d73fb60-cb7f-4463-ae57-33336e3a350c",
                "email": "admin@iisc-demo.com",
                "role": "super_admin",
                "tenant_id": "83d5f2cf-e28a-48fa-8092-367735a99c1d",
                "is_active": True,
                "created_at": "2026-06-01T04:26:15.423433Z",
            }
        },
    )

    id: uuid.UUID
    # Plain str (not EmailStr): synthetic identities like "wa-…@whatsapp.local"
    # are stored for bot users, and the reserved .local TLD fails RFC email
    # validation. Output schemas serialize stored values; they don't re-validate.
    email: str
    role: str
    tenant_id: uuid.UUID
    is_active: bool
    created_at: datetime


class LoginResponse(BaseModel):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = "bearer"
    user: UserOut


class UserList(BaseModel):
    """Response for GET /admin/users — users in the current tenant + count."""
    users: list[UserOut]
    total: int
