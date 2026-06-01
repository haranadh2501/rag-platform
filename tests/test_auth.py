"""Auth integration tests (M2).

These hit the real FastAPI app over ASGI against a live Postgres (the one from
`docker compose`). They self-seed a throwaway tenant + admin, so they don't
depend on `seed_admin` having run.

Run via a one-off container off the backend image (deps + DB host already set;
mounts the whole repo so tests/ is visible):
    docker compose run --rm -v "$PWD":/repo -w /repo backend pytest tests/test_auth.py -v

Or from the host with the DB up and deps installed:
    cd backend && pip install -r requirements.txt
    DATABASE_URL=postgresql+asyncpg://raguser:changeme@localhost:5432/ragplatform \
        pytest ../tests/test_auth.py -v

If the database can't be reached the whole module is skipped (keeps CI green
until a Postgres service is wired into the workflow).
"""
import os
import sys
import uuid

import pytest
import pytest_asyncio

# Make `app` importable whether pytest runs from repo root or backend/.
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Tenant, User  # noqa: E402

pytestmark = pytest.mark.asyncio

TEST_PASSWORD = "supersecret123"


async def _db_available() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest_asyncio.fixture(autouse=True)
async def _db_lifecycle():
    # pytest-asyncio uses a fresh event loop per test; dispose the app's global
    # engine in teardown (same loop that opened the connections) so the next
    # test starts with an empty pool instead of connections bound to a dead loop.
    if not await _db_available():
        pytest.skip("Postgres not reachable — start it with `docker compose up -d postgres`")
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def admin_user():
    """Create a unique tenant + admin, yield it, then clean up."""
    slug = f"test-{uuid.uuid4().hex[:8]}"
    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="Test Tenant", slug=slug)
        db.add(tenant)
        await db.flush()
        user = User(
            tenant_id=tenant.id,
            email=email,
            hashed_password=get_password_hash(TEST_PASSWORD),
            role="admin",
        )
        db.add(user)
        await db.commit()
        tenant_id, user_id = tenant.id, user.id

    yield {"email": email, "password": TEST_PASSWORD, "tenant_id": str(tenant_id)}

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM users WHERE tenant_id = :t"), {"t": tenant_id})
        await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant_id})
        await db.commit()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_login_success_returns_jwt(client, admin_user):
    r = await client.post("/auth/login", json={"email": admin_user["email"], "password": admin_user["password"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == admin_user["email"]
    assert body["user"]["role"] == "admin"


async def test_login_wrong_password_401(client, admin_user):
    r = await client.post("/auth/login", json={"email": admin_user["email"], "password": "wrongpassword"})
    assert r.status_code == 401


async def test_login_unknown_email_401(client):
    r = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
    assert r.status_code == 401


async def test_me_with_valid_token(client, admin_user):
    login = await client.post("/auth/login", json={"email": admin_user["email"], "password": admin_user["password"]})
    token = login.json()["access_token"]
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == admin_user["email"]


async def test_me_without_token_401(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


async def test_me_with_garbage_token_401(client):
    r = await client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


async def test_register_requires_auth(client, admin_user):
    # No token → rejected (admin role required).
    r = await client.post(
        "/auth/register",
        json={"email": "x@example.com", "password": "password123", "tenant_id": admin_user["tenant_id"]},
    )
    assert r.status_code == 401


async def test_register_as_admin_creates_user(client, admin_user):
    login = await client.post("/auth/login", json={"email": admin_user["email"], "password": admin_user["password"]})
    token = login.json()["access_token"]
    new_email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/auth/register",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": new_email, "password": "password123", "tenant_id": admin_user["tenant_id"], "role": "user"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["email"] == new_email
    assert r.json()["role"] == "user"
