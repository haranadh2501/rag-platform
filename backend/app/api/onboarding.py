"""
Customer onboarding API — self-service tenant registration.
Owner: M13
"""
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash
from app.models.models import Tenant, User
from app.schemas.auth import UserOut
from app.schemas.tenants import TenantOut

logger = logging.getLogger(__name__)

router = APIRouter()

RESERVED_SLUGS = {"admin", "api", "www", "app", "auth", "root", "superadmin"}


class OnboardingRegisterRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    company_slug: str = Field(pattern=r'^[a-z0-9-]+$', min_length=2, max_length=100)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)
    plan: Literal["free", "pro"] = "free"


class OnboardingRegisterResponse(BaseModel):
    tenant: TenantOut
    admin_user: UserOut
    access_token: str


@router.post(
    "/register",
    response_model=OnboardingRegisterResponse,
    status_code=201,
    summary="Register new tenant (self-service)",
)
async def register_tenant(
    payload: OnboardingRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — no auth required. Creates tenant + admin user, returns JWT."""
    if payload.company_slug in RESERVED_SLUGS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug is reserved")

    slug_result = await db.execute(select(Tenant).where(Tenant.slug == payload.company_slug))
    if slug_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already taken")

    email_result = await db.execute(select(User).where(User.email == payload.admin_email))
    if email_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    tenant = Tenant(
        name=payload.company_name,
        slug=payload.company_slug,
        plan=payload.plan,
        is_active=True,
    )
    db.add(tenant)
    await db.flush()  # populate tenant.id before creating user

    user = User(
        tenant_id=tenant.id,
        email=payload.admin_email,
        hashed_password=get_password_hash(payload.admin_password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(user)

    token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(tenant.id), "role": user.role}
    )
    logger.info("Onboarded new tenant %s (slug=%s) with admin %s", tenant.name, tenant.slug, user.email)

    return OnboardingRegisterResponse(
        tenant=TenantOut.model_validate(tenant),
        admin_user=UserOut.model_validate(user),
        access_token=token,
    )


@router.get("/check-slug", summary="Check slug availability")
async def check_slug(slug: str, db: AsyncSession = Depends(get_db)):
    """Public endpoint. Returns {available: bool}. Reserved words are unavailable."""
    if slug in RESERVED_SLUGS:
        return {"available": False}
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    return {"available": result.scalar_one_or_none() is None}
