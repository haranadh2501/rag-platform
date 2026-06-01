"""Auth dependencies injected into protected routes.

Owner: M2.

    from app.core.dependencies import get_current_user, require_role

    @router.get("/me")
    async def me(user: User = Depends(get_current_user)): ...

    @router.post("/register")
    async def register(_: User = Depends(require_role("admin"))): ...

`super_admin` always passes `require_role`.
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.models import User

# tokenUrl is used by Swagger's "Authorize" button; the real token is minted by
# POST /auth/login (JSON body, per the OpenAPI contract).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the Bearer JWT and load the active user it points to."""
    payload = decode_token(token)
    if not payload:
        raise _CREDENTIALS_EXC

    sub = payload.get("sub")
    if not sub:
        raise _CREDENTIALS_EXC
    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError):
        raise _CREDENTIALS_EXC

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXC
    return user


def require_role(*allowed_roles: str):
    """Dependency factory: allow only the given roles (super_admin always passes)."""

    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role != "super_admin" and user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _checker
