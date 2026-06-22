"""M3 conversation CRUD tests — GET and DELETE /chat/conversations*.

Integration tests — require a live Postgres.
Skip automatically if Postgres is unreachable.

    docker compose run --rm backend pytest tests/test_m3_conversations.py -v

NOTE: POST /chat/query is already tested in tests/test_m4_chat.py — not duplicated here.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta

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
from app.models.models import ChatMessage, Conversation, Tenant, User  # noqa: E402

pytestmark = pytest.mark.asyncio


# ── helpers ───────────────────────────────────────────────────────────────────

async def _db_available() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ── session-level DB guard ────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def _db_lifecycle():
    if not await _db_available():
        pytest.skip("Postgres not reachable — start it with `docker compose up -d postgres`")
    yield
    await engine.dispose()


# ── HTTP client ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── user fixture ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def conv_user():
    """Tenant + regular user + bearer token. Cleaned up after each test."""
    slug = f"m3cv-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        tenant = Tenant(name=f"Conv Tenant {slug}", slug=slug)
        db.add(tenant)
        await db.flush()
        user = User(
            tenant_id=tenant.id,
            email=f"user-{uuid.uuid4().hex[:8]}@m3conv.example",
            hashed_password=get_password_hash("testpassword"),
            role="user",
        )
        db.add(user)
        await db.commit()
        tenant_id, user_id = tenant.id, user.id

    token = create_access_token({"sub": str(user_id)})
    yield {"token": token, "user_id": user_id, "tenant_id": tenant_id}

    async with AsyncSessionLocal() as db:
        await db.execute(
            text("""
                DELETE FROM chat_messages
                WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id = :u)
            """),
            {"u": user_id},
        )
        await db.execute(
            text("DELETE FROM conversations WHERE user_id = :u"), {"u": user_id}
        )
        await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant_id})
        await db.commit()


@pytest_asyncio.fixture
async def conv_with_messages(conv_user):
    """A Conversation with 2 messages (user then assistant) owned by conv_user."""
    async with AsyncSessionLocal() as db:
        conv = Conversation(
            id=uuid.uuid4(),
            tenant_id=conv_user["tenant_id"],
            user_id=conv_user["user_id"],
            title="Test Conversation",
            channel="web",
        )
        db.add(conv)
        await db.flush()

        msg1 = ChatMessage(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role="user",
            content="Hello",
            sources=[],
            requires_clarification=False,
            created_at=datetime.utcnow() - timedelta(seconds=10),
        )
        msg2 = ChatMessage(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role="assistant",
            content="Hi there!",
            sources=[],
            requires_clarification=False,
            created_at=datetime.utcnow(),
        )
        db.add(msg1)
        db.add(msg2)
        await db.commit()
        conv_id = conv.id

    yield {"id": conv_id}
    # conv_user teardown cascades through: deletes chat_messages then conversations


# ═══════════════════════════════════════════
# GET /chat/conversations
# ═══════════════════════════════════════════

async def test_list_conversations_empty(client, conv_user):
    r = await client.get(
        "/chat/conversations",
        headers={"Authorization": f"Bearer {conv_user['token']}"},
    )
    assert r.status_code == 200
    assert r.json()["conversations"] == []


async def test_list_conversations_own_only(client, conv_user, conv_with_messages):
    # Create a second user in the same tenant with their own conversation
    async with AsyncSessionLocal() as db:
        other = User(
            tenant_id=conv_user["tenant_id"],
            email=f"other-{uuid.uuid4().hex[:8]}@m3conv.example",
            hashed_password="x",
            role="user",
        )
        db.add(other)
        await db.flush()
        other_conv = Conversation(
            id=uuid.uuid4(),
            tenant_id=conv_user["tenant_id"],
            user_id=other.id,
            channel="web",
        )
        db.add(other_conv)
        await db.commit()
        other_user_id, other_conv_id = other.id, other_conv.id

    try:
        r = await client.get(
            "/chat/conversations",
            headers={"Authorization": f"Bearer {conv_user['token']}"},
        )
        assert r.status_code == 200
        ids = [c["id"] for c in r.json()["conversations"]]
        assert str(conv_with_messages["id"]) in ids
        assert str(other_conv_id) not in ids
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("DELETE FROM conversations WHERE id = :c"), {"c": other_conv_id}
            )
            await db.execute(
                text("DELETE FROM users WHERE id = :u"), {"u": other_user_id}
            )
            await db.commit()


async def test_list_conversations_message_count(client, conv_user, conv_with_messages):
    r = await client.get(
        "/chat/conversations",
        headers={"Authorization": f"Bearer {conv_user['token']}"},
    )
    assert r.status_code == 200
    convs = r.json()["conversations"]
    our_conv = next(c for c in convs if c["id"] == str(conv_with_messages["id"]))
    assert our_conv["message_count"] == 2


async def test_list_conversations_unauthenticated_401(client):
    r = await client.get("/chat/conversations")
    assert r.status_code == 401


# ═══════════════════════════════════════════
# GET /chat/conversations/{id}
# ═══════════════════════════════════════════

async def test_get_conversation_200(client, conv_user, conv_with_messages):
    r = await client.get(
        f"/chat/conversations/{conv_with_messages['id']}",
        headers={"Authorization": f"Bearer {conv_user['token']}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(conv_with_messages["id"])
    assert body["title"] == "Test Conversation"
    assert len(body["messages"]) == 2


async def test_get_conversation_messages_chronological(client, conv_user, conv_with_messages):
    r = await client.get(
        f"/chat/conversations/{conv_with_messages['id']}",
        headers={"Authorization": f"Bearer {conv_user['token']}"},
    )
    assert r.status_code == 200
    messages = r.json()["messages"]
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


async def test_get_conversation_404(client, conv_user):
    r = await client.get(
        f"/chat/conversations/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {conv_user['token']}"},
    )
    assert r.status_code == 404


async def test_get_conversation_403(client, conv_user):
    async with AsyncSessionLocal() as db:
        other = User(
            tenant_id=conv_user["tenant_id"],
            email=f"foreign-{uuid.uuid4().hex[:8]}@m3conv.example",
            hashed_password="x",
            role="user",
        )
        db.add(other)
        await db.flush()
        foreign_conv = Conversation(
            id=uuid.uuid4(),
            tenant_id=conv_user["tenant_id"],
            user_id=other.id,
            channel="web",
        )
        db.add(foreign_conv)
        await db.commit()
        other_user_id, foreign_conv_id = other.id, foreign_conv.id

    try:
        r = await client.get(
            f"/chat/conversations/{foreign_conv_id}",
            headers={"Authorization": f"Bearer {conv_user['token']}"},
        )
        assert r.status_code == 403
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("DELETE FROM conversations WHERE id = :c"), {"c": foreign_conv_id}
            )
            await db.execute(
                text("DELETE FROM users WHERE id = :u"), {"u": other_user_id}
            )
            await db.commit()


async def test_get_conversation_message_count_matches(client, conv_user, conv_with_messages):
    r = await client.get(
        f"/chat/conversations/{conv_with_messages['id']}",
        headers={"Authorization": f"Bearer {conv_user['token']}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["message_count"] == len(body["messages"])


# ═══════════════════════════════════════════
# DELETE /chat/conversations/{id}
# ═══════════════════════════════════════════

async def test_delete_conversation_204(client, conv_user, conv_with_messages):
    r = await client.delete(
        f"/chat/conversations/{conv_with_messages['id']}",
        headers={"Authorization": f"Bearer {conv_user['token']}"},
    )
    assert r.status_code == 204

    r2 = await client.get(
        f"/chat/conversations/{conv_with_messages['id']}",
        headers={"Authorization": f"Bearer {conv_user['token']}"},
    )
    assert r2.status_code == 404


async def test_delete_conversation_404(client, conv_user):
    r = await client.delete(
        f"/chat/conversations/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {conv_user['token']}"},
    )
    assert r.status_code == 404


async def test_delete_conversation_403(client, conv_user):
    async with AsyncSessionLocal() as db:
        other = User(
            tenant_id=conv_user["tenant_id"],
            email=f"del403-{uuid.uuid4().hex[:8]}@m3conv.example",
            hashed_password="x",
            role="user",
        )
        db.add(other)
        await db.flush()
        foreign_conv = Conversation(
            id=uuid.uuid4(),
            tenant_id=conv_user["tenant_id"],
            user_id=other.id,
            channel="web",
        )
        db.add(foreign_conv)
        await db.commit()
        other_user_id, foreign_conv_id = other.id, foreign_conv.id

    try:
        r = await client.delete(
            f"/chat/conversations/{foreign_conv_id}",
            headers={"Authorization": f"Bearer {conv_user['token']}"},
        )
        assert r.status_code == 403
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("DELETE FROM conversations WHERE id = :c"), {"c": foreign_conv_id}
            )
            await db.execute(
                text("DELETE FROM users WHERE id = :u"), {"u": other_user_id}
            )
            await db.commit()


async def test_delete_conversation_cascade(client, conv_user, conv_with_messages):
    conv_id = conv_with_messages["id"]

    await client.delete(
        f"/chat/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {conv_user['token']}"},
    )

    async with AsyncSessionLocal() as db:
        count = (
            await db.execute(
                text("SELECT count(*) FROM chat_messages WHERE conversation_id = :c"),
                {"c": conv_id},
            )
        ).scalar()
    assert count == 0
