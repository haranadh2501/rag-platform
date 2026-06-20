"""Tests for POST /webhooks/slack/onboard (M4).

Requires a live Postgres with migration 0002 applied and a seeded admin user.
Skipped automatically when the DB is not reachable.

    docker compose run --rm -v "$PWD":/repo -w /repo backend pytest tests/test_m4_slack_onboard.py -v
"""
import os
import sys
import uuid

import pytest
import pytest_asyncio

_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.bots import slack as slack_bot  # noqa: E402
from app.bots.slack import SlackAPIError, SlackUserNotFoundError  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Tenant, User  # noqa: E402

pytestmark = pytest.mark.asyncio


async def _db_available() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest_asyncio.fixture(autouse=True)
async def _require_db():
    if not await _db_available():
        pytest.skip("Postgres not reachable — start it with `docker compose up -d postgres`")
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def tenant_and_users():
    """Create one admin and one plain user in a fresh tenant; tear down after."""
    slug = f"onboard-test-{uuid.uuid4().hex[:8]}"
    user_email = f"plain-{uuid.uuid4().hex[:8]}@example.com"
    admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"

    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="Onboard Test", slug=slug)
        db.add(tenant)
        await db.flush()

        admin = User(
            tenant_id=tenant.id,
            email=admin_email,
            hashed_password="x",
            role="admin",
        )
        plain = User(
            tenant_id=tenant.id,
            email=user_email,
            hashed_password="x",
            role="user",
        )
        db.add(admin)
        db.add(plain)
        await db.flush()
        await db.commit()
        tenant_id = tenant.id
        admin_id = admin.id
        plain_id = plain.id

    admin_token = create_access_token({"sub": str(admin_id)})
    plain_token = create_access_token({"sub": str(plain_id)})

    yield {
        "tenant_id": tenant_id,
        "admin_id": admin_id,
        "plain_id": plain_id,
        "user_email": user_email,
        "admin_token": admin_token,
        "plain_token": plain_token,
    }

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM users WHERE tenant_id = :t"), {"t": tenant_id})
        await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant_id})
        await db.commit()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Happy path ────────────────────────────────────────────────────────────────

async def test_onboard_known_email_links_user(client, tenant_and_users, monkeypatch):
    slack_uid = f"U{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(slack_bot, "lookup_user_by_email", lambda e: _return(slack_uid))

    r = await client.post(
        "/webhooks/slack/onboard",
        json={"email": tenant_and_users["user_email"]},
        headers=_auth(tenant_and_users["admin_token"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["slack_user_id"] == slack_uid
    assert body["email"] == tenant_and_users["user_email"]

    # Verify DB was actually updated.
    async with AsyncSessionLocal() as db:
        row = (await db.execute(
            text("SELECT slack_user_id FROM users WHERE id = :uid"),
            {"uid": tenant_and_users["plain_id"]},
        )).mappings().first()
    assert row["slack_user_id"] == slack_uid


# ── Error cases ───────────────────────────────────────────────────────────────

async def test_onboard_unknown_email_404(client, tenant_and_users, monkeypatch):
    monkeypatch.setattr(slack_bot, "lookup_user_by_email",
                        lambda e: _raise(SlackUserNotFoundError(e)))

    r = await client.post(
        "/webhooks/slack/onboard",
        json={"email": tenant_and_users["user_email"]},
        headers=_auth(tenant_and_users["admin_token"]),
    )
    assert r.status_code == 404
    assert "workspace" in r.json()["detail"].lower()


async def test_onboard_already_linked_409(client, tenant_and_users, monkeypatch):
    existing_sid = f"U{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE users SET slack_user_id = :sid WHERE id = :uid"),
            {"sid": existing_sid, "uid": tenant_and_users["plain_id"]},
        )
        await db.commit()

    monkeypatch.setattr(slack_bot, "lookup_user_by_email", lambda e: _return(existing_sid))

    r = await client.post(
        "/webhooks/slack/onboard",
        json={"email": tenant_and_users["user_email"]},
        headers=_auth(tenant_and_users["admin_token"]),
    )
    assert r.status_code == 409

    # Clean up for fixture teardown.
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE users SET slack_user_id = NULL WHERE id = :uid"),
            {"uid": tenant_and_users["plain_id"]},
        )
        await db.commit()


async def test_onboard_slack_api_down_503(client, tenant_and_users, monkeypatch):
    monkeypatch.setattr(slack_bot, "lookup_user_by_email",
                        lambda e: _raise(SlackAPIError("connection refused")))

    r = await client.post(
        "/webhooks/slack/onboard",
        json={"email": tenant_and_users["user_email"]},
        headers=_auth(tenant_and_users["admin_token"]),
    )
    assert r.status_code == 503


async def test_onboard_non_admin_403(client, tenant_and_users, monkeypatch):
    monkeypatch.setattr(slack_bot, "lookup_user_by_email", lambda e: _return("U_never_called"))

    r = await client.post(
        "/webhooks/slack/onboard",
        json={"email": tenant_and_users["user_email"]},
        headers=_auth(tenant_and_users["plain_token"]),
    )
    assert r.status_code == 403


async def test_onboard_no_auth_401(client, tenant_and_users):
    r = await client.post(
        "/webhooks/slack/onboard",
        json={"email": tenant_and_users["user_email"]},
    )
    assert r.status_code == 401


# ── Async helpers for monkeypatching coroutines ───────────────────────────────

async def _return(value):
    return value


async def _raise(exc: Exception):
    raise exc
