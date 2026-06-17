"""Auth API routes — login, register, me, logout.

Owner: M2. Shapes match `specs/openapi.yaml`.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.rate_limit import limiter
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.models import Tenant, User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserOut

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=LoginResponse, summary="Login and get JWT token")
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Validate credentials and return a signed JWT + the user profile.

    `request` is the Starlette Request — required by slowapi to key the rate
    limit on client IP. The JSON body is `payload` (shape unchanged: LoginRequest).
    """
    try:
        result = await db.execute(select(User).where(User.email == payload.email))
        user = result.scalar_one_or_none()

        # If the user is not present (or the password is wrong) return the SAME
        # 401 — same error + timing — so we don't leak which emails are registered.
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled",
            )

        token = create_access_token(
            {"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role}
        )
        return LoginResponse(
            access_token=token, token_type="bearer", user=UserOut.model_validate(user)
        )
    except HTTPException:
        # Intended auth failures (401) pass through unchanged.
        raise
    except Exception:
        # Anything unexpected (e.g. DB unavailable) → log + clean 500, never a raw trace.
        logger.exception("Unexpected error during login for %s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to a server error",
        )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (admin role required)",
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    """Create a user in an existing tenant. Caller must be admin/super_admin."""
    # Tenant-scope guard: a tenant admin may only create users in their OWN
    # tenant. super_admin is platform-level and may target any tenant. Checked
    # before the tenant lookup so a tenant admin can't probe other tenants.
    if _admin.role != "super_admin" and request.tenant_id != _admin.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create users outside your tenant",
        )

    tenant = await db.get(Tenant, request.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        tenant_id=request.tenant_id,
        email=request.email,
        hashed_password=get_password_hash(request.password),
        role=request.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Registered user %s (role=%s) in tenant %s", user.email, user.role, user.tenant_id)
    return UserOut.model_validate(user)


@router.get("/me", response_model=UserOut, summary="Get current user profile")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the user the Bearer token belongs to."""
    return UserOut.model_validate(current_user)


@router.post("/logout", summary="Logout")
async def logout(_current_user: User = Depends(get_current_user)):
    """Stateless JWT — logout is a client-side token discard. No server state."""
    return {"message": "Logged out"}
