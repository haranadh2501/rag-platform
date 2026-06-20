"""M4 Slack webhook tests.

Hit the real FastAPI app over ASGI against a live Postgres (same pattern as
test_auth.py). Fast-path tests (signature, challenge, bot, missing-field, mock
pipeline) need no M4 schema. End-to-end tests that touch slack_workspace_map /
processed_requests are skipped if migration 0002 hasn't been applied.

    docker compose run --rm -v "$PWD":/repo -w /repo backend pytest tests/test_m4_slack.py -v

NOTE: tests/ is M10-owned — this file is additive; coordinate sign-off with M10.
"""
import hashlib
import hmac
import json
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

from app.bots import slack  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Tenant, User  # noqa: E402
from app.services import message_service, pipeline_client  # noqa: E402

pytestmark = pytest.mark.asyncio

SIGNING_SECRET = "test-signing-secret"


async def _db_available() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _m4_schema_present() -> bool:
    async with engine.connect() as conn:
        wsm = (await conn.execute(text("SELECT to_regclass('slack_workspace_map')"))).scalar()
        preq = (await conn.execute(text("SELECT to_regclass('processed_requests')"))).scalar()
    return wsm is not None and preq is not None


@pytest_asyncio.fixture(autouse=True)
async def _db_lifecycle(monkeypatch):
    if not await _db_available():
        pytest.skip("Postgres not reachable — start it with `docker compose up -d postgres`")
    monkeypatch.setattr(settings, "SLACK_SIGNING_SECRET", SIGNING_SECRET)
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _signed(payload: dict, secret: str = SIGNING_SECRET, ts: str = "1700000000"):
    raw = json.dumps(payload).encode()
    base = b"v0:" + ts.encode() + b":" + raw
    digest = hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    headers = {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": f"v0={digest}",
        "Content-Type": "application/json",
    }
    return raw, headers


# ── Fast-path tests (no M4 schema needed) ────────────────────────────────────

async def test_invalid_signature_403(client):
    raw, headers = _signed({"type": "event_callback"}, secret="wrong-secret")
    r = await client.post("/webhooks/slack/events", content=raw, headers=headers)
    assert r.status_code == 403


async def test_url_verification_echoes_challenge(client):
    raw, headers = _signed({"type": "url_verification", "challenge": "abc123"})
    r = await client.post("/webhooks/slack/events", content=raw, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"challenge": "abc123"}


async def test_bot_message_noop(client):
    raw, headers = _signed({
        "type": "event_callback",
        "event_id": f"Ev{uuid.uuid4().hex[:8]}",
        "event": {"bot_id": "B123", "text": "ignored", "user": "U1", "channel": "C1", "ts": "1.1"},
    })
    r = await client.post("/webhooks/slack/events", content=raw, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_missing_fields_noop(client):
    # No event_id → dedup skipped → field validation returns 200 without touching M4 tables.
    raw, headers = _signed({"type": "event_callback", "event": {"channel": "C1", "ts": "1.1"}})
    r = await client.post("/webhooks/slack/events", content=raw, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_mock_pipeline_endpoint(client):
    r = await client.post("/webhooks/mock/pipeline", json={"current_message": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert isinstance(body["sources"], list)
    assert isinstance(body["follow_up_questions"], list)


# ── End-to-end tests (need migration 0002 + monkeypatched Slack/pipeline) ─────

@pytest_asyncio.fixture
async def slack_user():
    if not await _m4_schema_present():
        pytest.skip("M4 schema absent — run `alembic upgrade head` (migration 0002)")
    slug = f"test-{uuid.uuid4().hex[:8]}"
    team_id = f"T{uuid.uuid4().hex[:8]}"
    slack_uid = f"U{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="Slack Test", slug=slug)
        db.add(tenant)
        await db.flush()
        user = User(
            tenant_id=tenant.id,
            email=f"slack-{uuid.uuid4().hex[:8]}@example.com",
            hashed_password="x",
            role="user",
            slack_user_id=slack_uid,
        )
        db.add(user)
        await db.flush()
        await db.execute(
            text("INSERT INTO slack_workspace_map (team_id, tenant_id) VALUES (:t, :ten)"),
            {"t": team_id, "ten": tenant.id},
        )
        await db.commit()
        tenant_id, user_id = tenant.id, user.id

    yield {"team_id": team_id, "slack_user_id": slack_uid, "tenant_id": tenant_id, "user_id": user_id}

    async with AsyncSessionLocal() as db:
        # Delete in order: conversations (child) → users (child) → tenant (parent)
        await db.execute(text("DELETE FROM conversations WHERE user_id = :u"), {"u": user_id})
        await db.execute(text("DELETE FROM slack_workspace_map WHERE team_id = :t"), {"t": team_id})
        # Drop conversations (cascades to chat_messages) before users: conversations.user_id
        # has no ON DELETE CASCADE, so deleting users first violates the FK.
        await db.execute(text("DELETE FROM conversations WHERE tenant_id = :t"), {"t": tenant_id})
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


async def test_slack_happy_path_posts_reply_and_saves(client, slack_user, monkeypatch):
    posted = []
    monkeypatch.setattr(slack, "post_reply",
                        lambda ch, ts, ans, src: posted.append((ch, ans)) or _noop())
    monkeypatch.setattr(pipeline_client, "call_pipeline", _mock_pipeline)

    raw, headers = _signed({
        "type": "event_callback",
        "event_id": f"Ev{uuid.uuid4().hex[:8]}",
        "team_id": slack_user["team_id"],
        "event": {"user": slack_user["slack_user_id"], "text": "hello", "channel": "C1", "ts": "1.1"},
    })
    r = await client.post("/webhooks/slack/events", content=raw, headers=headers)
    assert r.status_code == 200
    assert posted, "expected a threaded reply"
    assert await _count_messages(slack_user["user_id"]) == 2  # user + assistant


async def test_slack_reset_recreates_without_pipeline(client, slack_user, monkeypatch):
    texts = []
    monkeypatch.setattr(slack, "post_text",
                        lambda ch, ts, t: texts.append(t) or _noop())
    monkeypatch.setattr(pipeline_client, "call_pipeline", _fail_pipeline)  # must NOT be called

    raw, headers = _signed({
        "type": "event_callback",
        "event_id": f"Ev{uuid.uuid4().hex[:8]}",
        "team_id": slack_user["team_id"],
        "event": {"user": slack_user["slack_user_id"], "text": "/new", "channel": "C1", "ts": "1.1"},
    })
    r = await client.post("/webhooks/slack/events", content=raw, headers=headers)
    assert r.status_code == 200
    assert texts == [message_service.RESET_CONFIRMATION]
    assert await _count_messages(slack_user["user_id"]) == 0  # reset saves nothing


async def test_slack_duplicate_event_id_noop(client, slack_user, monkeypatch):
    calls = []
    monkeypatch.setattr(slack, "post_reply", lambda *a: calls.append(1) or _noop())
    monkeypatch.setattr(pipeline_client, "call_pipeline", _mock_pipeline)

    event_id = f"Ev{uuid.uuid4().hex[:8]}"
    payload = {
        "type": "event_callback",
        "event_id": event_id,
        "team_id": slack_user["team_id"],
        "event": {"user": slack_user["slack_user_id"], "text": "hello", "channel": "C1", "ts": "1.1"},
    }
    raw, headers = _signed(payload)
    await client.post("/webhooks/slack/events", content=raw, headers=headers)
    raw, headers = _signed(payload)
    await client.post("/webhooks/slack/events", content=raw, headers=headers)
    assert len(calls) == 1  # second delivery deduped

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM processed_requests WHERE request_id = :r"), {"r": event_id})
        await db.commit()


async def _noop():
    return None


async def _mock_pipeline(payload):
    return {"answer": "mock answer", "sources": [], "follow_up_questions": []}


async def _fail_pipeline(payload):
    raise AssertionError("pipeline must not be called on reset")
