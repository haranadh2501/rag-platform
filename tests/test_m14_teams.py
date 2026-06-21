"""M14 Microsoft Teams webhook tests.

Hit the real FastAPI app over ASGI against a live Postgres (same pattern as
test_m12_whatsapp.py). Tests verify Bot Framework activity parsing, dedup,
identity resolution via teams_tenant_map, and Connector REST delivery.

    docker compose run --rm -v "$PWD":/repo -w /repo backend pytest tests/test_m14_teams.py -v

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

from app.bots import teams  # noqa: E402
from app.bots.teams_map import get_tenant_for_teams, register_teams_tenant  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Tenant, User  # noqa: E402
from app.services import message_service, pipeline_client  # noqa: E402

pytestmark = pytest.mark.asyncio

SERVICE_URL = "https://smba.trafficmanager.net/test/"
CONVERSATION_ID = "19:conv@thread.tacv2"


async def _db_available() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _m14_schema_present() -> bool:
    async with engine.connect() as conn:
        ttm = (await conn.execute(text("SELECT to_regclass('teams_tenant_map')"))).scalar()
        preq = (await conn.execute(text("SELECT to_regclass('processed_requests')"))).scalar()
    return ttm is not None and preq is not None


@pytest_asyncio.fixture(autouse=True)
async def _db_lifecycle(monkeypatch):
    if not await _db_available():
        pytest.skip("Postgres not reachable — start it with `docker compose up -d postgres`")
    monkeypatch.setattr(settings, "APP_ENV", "development")  # Skip token validation
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _activity(activity_id: str, teams_tenant_id: str, teams_user_id: str,
              text_: str, with_file: bool = False) -> dict:
    """Build a Bot Framework message activity."""
    body = {
        "type": "message",
        "id": activity_id,
        "serviceUrl": SERVICE_URL,
        "channelId": "msteams",
        "from": {"id": teams_user_id, "name": "Test User"},
        "conversation": {"id": CONVERSATION_ID},
        "recipient": {"id": "28:bot", "name": "Bot"},
        "text": text_,
        "channelData": {"tenant": {"id": teams_tenant_id}},
    }
    if with_file:
        body["attachments"] = [{
            "contentType": "application/vnd.microsoft.teams.file.download.info",
            "name": "doc.pdf",
            "content": {"downloadUrl": "https://sharepoint.example/doc.pdf", "fileType": "pdf"},
        }]
    return body


# ── Fast-path tests (no M14 schema needed) ────────────────────────────────────

async def test_token_validation(client, monkeypatch):
    """No Bearer token → 403 when not in development mode."""
    monkeypatch.setattr(settings, "APP_ENV", "production")
    body = _activity("act1", str(uuid.uuid4()), "29:user", "hello")
    r = await client.post("/webhooks/teams", json=body)
    assert r.status_code == 403
    assert "Invalid Teams bot token" in r.json()["detail"]


async def test_non_message_activity_ignored(client):
    """conversationUpdate (bot added) → 200 + ignored."""
    r = await client.post("/webhooks/teams", json={"type": "conversationUpdate", "id": "x"})
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


async def test_empty_message(client):
    """Message with no text and no attachment → 200 + empty."""
    body = _activity(f"act{uuid.uuid4().hex[:8]}", str(uuid.uuid4()), "29:user", "")
    r = await client.post("/webhooks/teams", json=body)
    assert r.status_code == 200
    assert r.json()["status"] == "empty"


async def test_mention_stripped(monkeypatch):
    """<at>Bot</at> mentions are removed before processing."""
    from app.api.webhooks import _strip_mentions
    assert _strip_mentions("<at>RAG Assistant</at> what is onboarding?") == "what is onboarding?"


async def test_reply_truncation(monkeypatch):
    """post_reply caps text and appends a sources footer."""
    captured = []

    async def fake_send(service_url, conversation_id, text_):
        captured.append(text_)

    monkeypatch.setattr(teams, "_send_activity", fake_send)
    await teams.post_reply(SERVICE_URL, CONVERSATION_ID, "answer", [{"title": "Doc", "page_number": 3}])

    assert len(captured) == 1
    assert "Doc p.3" in captured[0]
    assert "📚 Sources" in captured[0]


# ── End-to-end tests (need migration 0004 + M14 schema) ───────────────────────

@pytest_asyncio.fixture
async def teams_user():
    if not await _m14_schema_present():
        pytest.skip("M14 schema absent — run `alembic upgrade head` (migration 0004)")

    slug = f"test-{uuid.uuid4().hex[:8]}"
    teams_tenant_id = str(uuid.uuid4())
    teams_user_id = f"29:{uuid.uuid4().hex}"

    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="Teams Test", slug=slug)
        db.add(tenant)
        await db.flush()

        await db.execute(
            text("INSERT INTO teams_tenant_map (teams_tenant_id, tenant_id) VALUES (:ttid, :tid)"),
            {"ttid": teams_tenant_id, "tid": tenant.id},
        )

        user = User(
            tenant_id=tenant.id,
            email=f"teams-{uuid.uuid4().hex[:8]}@teams.local",
            hashed_password="teams-no-login",
            role="user",
        )
        db.add(user)
        await db.flush()
        await db.execute(
            text("UPDATE users SET teams_user_id = :tuid WHERE id = :uid"),
            {"tuid": teams_user_id, "uid": user.id},
        )
        await db.commit()
        tenant_id, user_id = tenant.id, user.id

    yield {"teams_tenant_id": teams_tenant_id, "teams_user_id": teams_user_id,
           "tenant_id": tenant_id, "user_id": user_id}

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM conversations WHERE user_id = :u"), {"u": user_id})
        await db.execute(text("DELETE FROM teams_tenant_map WHERE teams_tenant_id = :t"), {"t": teams_tenant_id})
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


async def test_teams_text_flow(client, teams_user, monkeypatch):
    """Happy path: POST activity → background task → reply → messages saved."""
    posted = []

    async def mock_post_text(service_url, conversation_id, text_):
        posted.append(("text", text_))

    async def mock_post_reply(service_url, conversation_id, answer, sources):
        posted.append(("reply", answer))

    monkeypatch.setattr(teams, "post_text", mock_post_text)
    monkeypatch.setattr(teams, "post_reply", mock_post_reply)
    monkeypatch.setattr(pipeline_client, "call_pipeline", _mock_pipeline)

    body = _activity(f"act{uuid.uuid4().hex[:8]}", teams_user["teams_tenant_id"],
                     teams_user["teams_user_id"], "hello")
    r = await client.post("/webhooks/teams", json=body)

    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    import asyncio
    await asyncio.sleep(0.1)

    assert len(posted) >= 1  # at least "Thinking..."
    assert await _count_messages(teams_user["user_id"]) == 2  # user + assistant


async def test_teams_dedup(client, teams_user, monkeypatch):
    """Same activity id twice → second is ignored."""
    calls = []

    async def mock_post_text(service_url, conversation_id, text_):
        calls.append(1)

    async def mock_post_reply(service_url, conversation_id, answer, sources):
        calls.append(1)

    monkeypatch.setattr(teams, "post_text", mock_post_text)
    monkeypatch.setattr(teams, "post_reply", mock_post_reply)
    monkeypatch.setattr(pipeline_client, "call_pipeline", _mock_pipeline)

    activity_id = f"act{uuid.uuid4().hex[:8]}"
    body = _activity(activity_id, teams_user["teams_tenant_id"], teams_user["teams_user_id"], "hello")

    r1 = await client.post("/webhooks/teams", json=body)
    r2 = await client.post("/webhooks/teams", json=body)  # duplicate

    assert r1.json()["status"] == "ok"
    assert r2.json()["status"] == "duplicate"

    import asyncio
    await asyncio.sleep(0.1)
    assert len(calls) <= 2  # Thinking + Reply from first call only

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM processed_requests WHERE request_id = :r"), {"r": activity_id})
        await db.commit()


async def test_teams_unknown_tenant(client, monkeypatch):
    """Unregistered Teams org → 'isn't registered' reply."""
    if not await _m14_schema_present():
        pytest.skip("M14 schema absent")

    replies = []

    async def mock_post_text(service_url, conversation_id, text_):
        replies.append(text_)

    monkeypatch.setattr(teams, "post_text", mock_post_text)
    monkeypatch.setattr(pipeline_client, "call_pipeline", _mock_pipeline)

    body = _activity(f"act{uuid.uuid4().hex[:8]}", str(uuid.uuid4()), "29:nobody", "hello")
    r = await client.post("/webhooks/teams", json=body)
    assert r.status_code == 200

    import asyncio
    await asyncio.sleep(0.2)

    assert len(replies) > 0, "Expected replies but got none"
    assert any("registered" in reply.lower() for reply in replies), f"Got replies: {replies}"


async def test_teams_reset(client, teams_user, monkeypatch):
    """Send /new → conversation reset → confirmation message."""
    texts = []

    async def mock_post_text(service_url, conversation_id, text_):
        texts.append(text_)

    monkeypatch.setattr(teams, "post_text", mock_post_text)
    monkeypatch.setattr(pipeline_client, "call_pipeline", _fail_pipeline)  # must NOT be called

    body = _activity(f"act{uuid.uuid4().hex[:8]}", teams_user["teams_tenant_id"],
                     teams_user["teams_user_id"], "/new")
    r = await client.post("/webhooks/teams", json=body)
    assert r.status_code == 200

    import asyncio
    await asyncio.sleep(0.1)

    assert message_service.RESET_CONFIRMATION in texts
    assert await _count_messages(teams_user["user_id"]) == 0


async def test_teams_media_upload_indexed(client, teams_user, monkeypatch):
    """File attachment → download → validate → ephemeral n8n ingest → confirmation."""
    import app.api.webhooks as webhooks_module

    indexed = []

    async def mock_post_text(service_url, conversation_id, text_):
        indexed.append(text_)

    class _FakeResp:
        content = b"fake-pdf-bytes"

        def raise_for_status(self):
            pass

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return _FakeResp()

    ingested = []

    async def mock_ingest_ephemeral(content, conversation_id, mime_type):
        ingested.append((content, conversation_id, mime_type))
        return {"status": "mock_indexed"}

    def mock_validate_upload(*, filename, content, declared_mime=None, max_bytes=None):
        from app.services.file_validator import ValidatedUpload
        return ValidatedUpload(
            filename=filename, content=content,
            mime_type=declared_mime or "application/pdf", size_bytes=len(content),
        )

    monkeypatch.setattr(webhooks_module.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(webhooks_module.file_validator, "validate_upload", mock_validate_upload)
    monkeypatch.setattr(webhooks_module.n8n_client, "ingest_ephemeral", mock_ingest_ephemeral)
    monkeypatch.setattr(teams, "post_text", mock_post_text)
    monkeypatch.setattr(pipeline_client, "call_pipeline", _fail_pipeline)  # file-only must not call pipeline

    body = _activity(f"act{uuid.uuid4().hex[:8]}", teams_user["teams_tenant_id"],
                     teams_user["teams_user_id"], "", with_file=True)
    r = await client.post("/webhooks/teams", json=body)
    assert r.status_code == 200

    import asyncio
    await asyncio.sleep(0.1)

    assert len(ingested) == 1
    assert ingested[0][0] == b"fake-pdf-bytes"
    assert any("Indexed" in t for t in indexed)


async def test_teams_map_lookup():
    """get_tenant_for_teams returns tenant_id for registered org."""
    if not await _m14_schema_present():
        pytest.skip("M14 schema absent")

    slug = f"test-{uuid.uuid4().hex[:8]}"
    teams_tenant_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="Lookup Test", slug=slug)
        db.add(tenant)
        await db.flush()
        await db.execute(
            text("INSERT INTO teams_tenant_map (teams_tenant_id, tenant_id) VALUES (:ttid, :tid)"),
            {"ttid": teams_tenant_id, "tid": tenant.id},
        )
        await db.commit()

        assert await get_tenant_for_teams(teams_tenant_id, db) == tenant.id
        assert await get_tenant_for_teams(str(uuid.uuid4()), db) is None

        await db.execute(text("DELETE FROM teams_tenant_map WHERE teams_tenant_id = :t"), {"t": teams_tenant_id})
        await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant.id})
        await db.commit()


async def test_teams_map_register():
    """register_teams_tenant inserts and handles conflicts."""
    if not await _m14_schema_present():
        pytest.skip("M14 schema absent")

    slug = f"test-{uuid.uuid4().hex[:8]}"
    teams_tenant_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="Register Test", slug=slug)
        db.add(tenant)
        await db.flush()
        await db.commit()

        await register_teams_tenant(teams_tenant_id, tenant.id, db)
        assert await get_tenant_for_teams(teams_tenant_id, db) == tenant.id
        await register_teams_tenant(teams_tenant_id, tenant.id, db)  # ON CONFLICT DO NOTHING

        await db.execute(text("DELETE FROM teams_tenant_map WHERE teams_tenant_id = :t"), {"t": teams_tenant_id})
        await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant.id})
        await db.commit()


# ── Test helpers ──────────────────────────────────────────────────────────────

async def _mock_pipeline(payload):
    return {"answer": "mock answer", "sources": [], "follow_up_questions": []}


async def _fail_pipeline(payload):
    raise AssertionError("pipeline must not be called")
