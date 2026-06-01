"""Pydantic v2 schemas for the Auth API.

Owner: M2. Shapes must match `specs/openapi.yaml` (LoginRequest, LoginResponse,
RegisterRequest, UserOut) exactly — that file is the contract.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    tenant_id: uuid.UUID
    role: Literal["admin", "user"] = "user"


class UserOut(BaseModel):
    # from_attributes lets us return ORM `User` objects directly.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: str
    tenant_id: uuid.UUID
    is_active: bool
    created_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
