"""M4 web chat tests — POST /chat/query.

Hit the real FastAPI app over ASGI against a live Postgres (same pattern as
test_auth.py). The web path needs only base tables (users/conversations/
chat_messages), so no migration-0002 guard is required.

    docker compose run --rm -v "$PWD":/repo -w /repo backend pytest tests/test_m4_chat.py -v

NOTE: tests/ is M10-owned — this file is additive; coordinate sign-off with M10.
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

from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Tenant, User  # noqa: E402
from app.services import pipeline_client  # noqa: E402

pytestmark = pytest.mark.asyncio


async def _db_available() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest_asyncio.fixture(autouse=True)
async def _db_lifecycle():
    if not await _db_available():
        pytest.skip("Postgres not reachable — start it with `docker compose up -d postgres`")
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def web_user():
    """A tenant + user + bearer token; cleaned up after."""
    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="Web Test", slug=f"test-{uuid.uuid4().hex[:8]}")
        db.add(tenant)
        await db.flush()
        user = User(
            tenant_id=tenant.id,
            email=f"web-{uuid.uuid4().hex[:8]}@example.com",
            hashed_password=get_password_hash("supersecret123"),
            role="user",
        )
        db.add(user)
        await db.commit()
        tenant_id, user_id = tenant.id, user.id

    token = create_access_token({"sub": str(user_id)})
    yield {"token": token, "user_id": user_id, "tenant_id": tenant_id}

    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            DELETE FROM chat_messages WHERE conversation_id IN
              (SELECT id FROM conversations WHERE user_id = :u)
        """), {"u": user_id})
        await db.execute(text("DELETE FROM conversations WHERE user_id = :u"), {"u": user_id})
        await db.execute(text("DELETE FROM users WHERE tenant_id = :t"), {"t": tenant_id})
        await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant_id})
        await db.commit()


async def _count_messages(user_id) -> int:
    async with AsyncSessionLocal() as db:
        return (await db.execute(text("""
            SELECT count(*) FROM chat_messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.user_id = :u
        """), {"u": user_id})).scalar()


async def test_missing_query_422(client, web_user):
    r = await client.post("/chat/query", json={},
                          headers={"Authorization": f"Bearer {web_user['token']}"})
    assert r.status_code == 422


async def test_no_auth_401(client):
    r = await client.post("/chat/query", json={"query": "hello"})
    assert r.status_code == 401


async def test_happy_path_returns_answer_and_saves(client, web_user, monkeypatch):
    monkeypatch.setattr(pipeline_client, "call_pipeline", _mock_pipeline)
    r = await client.post("/chat/query", json={"query": "What is the refund policy?"},
                          headers={"Authorization": f"Bearer {web_user['token']}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"] == "mock answer"
    assert body["conversation_id"]
    assert await _count_messages(web_user["user_id"]) == 2


async def test_foreign_conversation_id_403(client, web_user, monkeypatch):
    monkeypatch.setattr(pipeline_client, "call_pipeline", _mock_pipeline)
    # A conversation owned by a different user in the same tenant.
    async with AsyncSessionLocal() as db:
        other = User(
            tenant_id=web_user["tenant_id"],
            email=f"other-{uuid.uuid4().hex[:8]}@example.com",
            hashed_password="x",
            role="user",
        )
        db.add(other)
        await db.flush()
        foreign_conv = (await db.execute(text("""
            INSERT INTO conversations (tenant_id, user_id, channel)
            VALUES (:t, :u, 'web') RETURNING id
        """), {"t": web_user["tenant_id"], "u": other.id})).scalar_one()
        await db.commit()
        other_id = other.id

    r = await client.post(
        "/chat/query",
        json={"query": "hello", "conversation_id": str(foreign_conv)},
        headers={"Authorization": f"Bearer {web_user['token']}"},
    )
    assert r.status_code == 403

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM conversations WHERE id = :c"), {"c": foreign_conv})
        await db.execute(text("DELETE FROM users WHERE id = :u"), {"u": other_id})
        await db.commit()


async def _mock_pipeline(payload):
    return {"answer": "mock answer", "sources": [], "follow_up_questions": []}
