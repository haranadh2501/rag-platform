"""M12 WhatsApp webhook tests.

Hit the real FastAPI app over ASGI against a live Postgres (same pattern as
test_m4_slack.py). Tests verify Twilio form parsing, deduplication, identity
resolution via whatsapp_tenant_map, and Twilio REST API delivery.

    docker compose run --rm -v "$PWD":/repo -w /repo backend pytest tests/test_m12_whatsapp.py -v

NOTE: tests/ is M10-owned — this file is additive; coordinate sign-off with M10.
"""
import os
import sys
import uuid
from unittest.mock import Mock, AsyncMock

import pytest
import pytest_asyncio

_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.bots import whatsapp  # noqa: E402
from app.bots.tenant_map import get_tenant_for_phone, register_phone_for_tenant  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Tenant, User  # noqa: E402
from app.services import message_service, pipeline_client  # noqa: E402

pytestmark = pytest.mark.asyncio

TEST_PHONE = "whatsapp:+9198765"
TEST_AUTH_TOKEN = "test-twilio-token"


async def _db_available() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _m12_schema_present() -> bool:
    async with engine.connect() as conn:
        wtm = (await conn.execute(text("SELECT to_regclass('whatsapp_tenant_map')"))).scalar()
        preq = (await conn.execute(text("SELECT to_regclass('processed_requests')"))).scalar()
    return wtm is not None and preq is not None


@pytest_asyncio.fixture(autouse=True)
async def _db_lifecycle(monkeypatch):
    if not await _db_available():
        pytest.skip("Postgres not reachable — start it with `docker compose up -d postgres`")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", TEST_AUTH_TOKEN)
    monkeypatch.setattr(settings, "APP_ENV", "development")  # Skip signature validation
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _twilio_form(message_sid: str, phone: str, body: str, num_media: int = 0) -> dict:
    """Build Twilio webhook form data."""
    form = {
        "MessageSid": message_sid,
        "From": phone,
        "Body": body,
        "NumMedia": str(num_media),
    }
    if num_media > 0:
        form["MediaUrl0"] = "https://api.twilio.com/2010-04-01/Accounts/test/Media/ME123"
        form["MediaContentType0"] = "image/png"
    return form


# ── Fast-path tests (no M12 schema needed) ────────────────────────────────────

async def test_twilio_signature_validation(client, monkeypatch):
    """Invalid signature → 403 when not in development mode."""
    monkeypatch.setattr(settings, "APP_ENV", "production")
    # Mock RequestValidator to return False
    from twilio.request_validator import RequestValidator
    mock_validator = Mock()
    mock_validator.validate.return_value = False
    monkeypatch.setattr("app.api.webhooks.RequestValidator", lambda token: mock_validator)

    form = _twilio_form("SM123", TEST_PHONE, "hello")
    r = await client.post("/webhooks/whatsapp", data=form)
    assert r.status_code == 403
    assert "Invalid Twilio signature" in r.json()["detail"]


async def test_missing_fields_returns_empty_twiml(client):
    """Missing MessageSid or From → 200 + empty TwiML."""
    r = await client.post("/webhooks/whatsapp", data={"Body": "hello"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/xml"
    assert "<Response></Response>" in r.text


async def test_empty_message_returns_empty_twiml(client):
    """No Body and no NumMedia → 200 + empty TwiML."""
    form = _twilio_form("SM123", TEST_PHONE, "")
    r = await client.post("/webhooks/whatsapp", data=form)
    assert r.status_code == 200
    assert "<Response></Response>" in r.text


async def test_twiml_truncation(monkeypatch):
    """Messages > 1600 chars are truncated."""
    long_message = "A" * 2000
    sources = [{"title": "Doc", "page_number": 1}]

    captured_body = []

    # Mock Twilio client at the module level where it's imported
    mock_client = Mock()
    mock_messages = Mock()

    def mock_create(**kwargs):
        captured_body.append(kwargs["body"])
        return Mock()

    mock_messages.create = mock_create
    mock_client.messages = mock_messages

    def mock_client_factory(*args, **kwargs):
        return mock_client

    # Patch in the whatsapp module where Client is used
    import app.bots.whatsapp as whatsapp_module
    monkeypatch.setattr(whatsapp_module, "Client", mock_client_factory)

    await whatsapp.post_reply(TEST_PHONE, long_message, sources)

    # Verify the call was made with truncated content
    assert len(captured_body) == 1, f"Expected 1 call, got {len(captured_body)}"
    assert len(captured_body[0]) <= 1600, f"Message length {len(captured_body[0])} exceeds 1600"


# ── End-to-end tests (need migration 0002 + M12 schema) ─────────────────────

@pytest_asyncio.fixture
async def whatsapp_user():
    if not await _m12_schema_present():
        pytest.skip("M12 schema absent — run `alembic upgrade head` (migration 0002 + M12 tables)")

    slug = f"test-{uuid.uuid4().hex[:8]}"
    phone = f"whatsapp:+91{uuid.uuid4().hex[:8]}"  # Max 20 chars: "whatsapp:+91xxxxxxxx" = 19 chars

    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="WhatsApp Test", slug=slug)
        db.add(tenant)
        await db.flush()

        # Register phone in whatsapp_tenant_map
        await db.execute(
            text("INSERT INTO whatsapp_tenant_map (phone_number, tenant_id) VALUES (:phone, :tid)"),
            {"phone": phone, "tid": tenant.id},
        )

        # Create user with phone_number
        user = User(
            tenant_id=tenant.id,
            email=f"wa-{uuid.uuid4().hex[:8]}@whatsapp.local",
            hashed_password="whatsapp-no-login",
            role="user",
        )
        db.add(user)
        await db.flush()

        await db.execute(
            text("UPDATE users SET phone_number = :phone WHERE id = :uid"),
            {"phone": phone, "uid": user.id}
        )
        await db.commit()

        tenant_id, user_id = tenant.id, user.id

    yield {"phone": phone, "tenant_id": tenant_id, "user_id": user_id}

    async with AsyncSessionLocal() as db:
        # Delete in order: conversations (child) → users (child) → tenant (parent)
        await db.execute(text("DELETE FROM conversations WHERE user_id = :u"), {"u": user_id})
        await db.execute(text("DELETE FROM whatsapp_tenant_map WHERE phone_number = :p"), {"p": phone})
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


async def test_whatsapp_text_flow(client, whatsapp_user, monkeypatch):
    """Happy path: POST form → background task → Twilio REST reply → messages saved."""
    posted = []

    async def mock_post_text(to, text):
        posted.append(("text", to, text))

    async def mock_post_reply(to, answer, sources):
        posted.append(("reply", to, answer))

    monkeypatch.setattr(whatsapp, "post_text", mock_post_text)
    monkeypatch.setattr(whatsapp, "post_reply", mock_post_reply)
    monkeypatch.setattr(pipeline_client, "call_pipeline", _mock_pipeline)

    form = _twilio_form(f"SM{uuid.uuid4().hex[:8]}", whatsapp_user["phone"], "hello")
    r = await client.post("/webhooks/whatsapp", data=form)

    assert r.status_code == 200
    assert "<Response></Response>" in r.text

    # Background task completes — check if messages were posted
    import asyncio
    await asyncio.sleep(0.1)  # Give background task time to complete

    assert len(posted) >= 1  # At least "Thinking..." message
    assert await _count_messages(whatsapp_user["user_id"]) == 2  # user + assistant


async def test_whatsapp_dedup(client, whatsapp_user, monkeypatch):
    """Same MessageSid twice → second is ignored."""
    calls = []

    async def mock_post_text(to, text):
        calls.append(1)

    async def mock_post_reply(to, answer, sources):
        calls.append(1)

    monkeypatch.setattr(whatsapp, "post_text", mock_post_text)
    monkeypatch.setattr(whatsapp, "post_reply", mock_post_reply)
    monkeypatch.setattr(pipeline_client, "call_pipeline", _mock_pipeline)

    message_sid = f"SM{uuid.uuid4().hex[:8]}"
    form = _twilio_form(message_sid, whatsapp_user["phone"], "hello")

    await client.post("/webhooks/whatsapp", data=form)
    await client.post("/webhooks/whatsapp", data=form)  # Duplicate

    import asyncio
    await asyncio.sleep(0.1)

    # Should only process once
    assert len(calls) <= 2  # Thinking + Reply from first call only

    # Clean up
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM processed_requests WHERE request_id = :r"), {"r": message_sid})
        await db.commit()


async def test_whatsapp_unknown_phone(client, monkeypatch):
    """Unregistered phone → 'not registered' reply."""
    if not await _m12_schema_present():
        pytest.skip("M12 schema absent")

    replies = []

    async def mock_post_text(to, text):
        replies.append(text)

    monkeypatch.setattr(whatsapp, "post_text", mock_post_text)
    monkeypatch.setattr(pipeline_client, "call_pipeline", _mock_pipeline)

    unknown_phone = f"whatsapp:+91{uuid.uuid4().hex[:8]}"
    form = _twilio_form(f"SM{uuid.uuid4().hex[:8]}", unknown_phone, "hello")
    r = await client.post("/webhooks/whatsapp", data=form)

    assert r.status_code == 200

    import asyncio
    await asyncio.sleep(0.2)  # Give more time for background task

    # Should have received "registered" (either "not registered" or "isn't registered")
    assert len(replies) > 0, f"Expected replies but got none"
    assert any("registered" in reply.lower() for reply in replies), f"Got replies: {replies}"


async def test_whatsapp_reset(client, whatsapp_user, monkeypatch):
    """Send /new → conversation reset → confirmation message."""
    texts = []

    async def mock_post_text(to, text):
        texts.append(text)

    monkeypatch.setattr(whatsapp, "post_text", mock_post_text)
    monkeypatch.setattr(pipeline_client, "call_pipeline", _fail_pipeline)  # Must NOT be called

    form = _twilio_form(f"SM{uuid.uuid4().hex[:8]}", whatsapp_user["phone"], "/new")
    r = await client.post("/webhooks/whatsapp", data=form)

    assert r.status_code == 200

    import asyncio
    await asyncio.sleep(0.1)

    assert message_service.RESET_CONFIRMATION in texts
    assert await _count_messages(whatsapp_user["user_id"]) == 0  # Reset saves nothing


async def test_tenant_map_lookup():
    """get_tenant_for_phone returns tenant_id for registered phone."""
    if not await _m12_schema_present():
        pytest.skip("M12 schema absent")

    slug = f"test-{uuid.uuid4().hex[:8]}"
    phone = f"whatsapp:+91{uuid.uuid4().hex[:8]}"

    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="Lookup Test", slug=slug)
        db.add(tenant)
        await db.flush()

        await db.execute(
            text("INSERT INTO whatsapp_tenant_map (phone_number, tenant_id) VALUES (:phone, :tid)"),
            {"phone": phone, "tid": tenant.id}
        )
        await db.commit()

        # Test lookup
        result = await get_tenant_for_phone(phone, db)
        assert result == tenant.id

        # Test unknown phone
        unknown = await get_tenant_for_phone("whatsapp:+910000000000", db)
        assert unknown is None

        # Cleanup
        await db.execute(text("DELETE FROM whatsapp_tenant_map WHERE phone_number = :p"), {"p": phone})
        await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant.id})
        await db.commit()


async def test_tenant_map_register():
    """register_phone_for_tenant inserts and handles conflicts."""
    if not await _m12_schema_present():
        pytest.skip("M12 schema absent")

    slug = f"test-{uuid.uuid4().hex[:8]}"
    phone = f"whatsapp:+91{uuid.uuid4().hex[:8]}"

    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="Register Test", slug=slug)
        db.add(tenant)
        await db.flush()
        await db.commit()

        # Register phone
        await register_phone_for_tenant(phone, tenant.id, db)

        # Verify
        result = await get_tenant_for_phone(phone, db)
        assert result == tenant.id

        # Re-register (should not error due to ON CONFLICT DO NOTHING)
        await register_phone_for_tenant(phone, tenant.id, db)

        # Cleanup
        await db.execute(text("DELETE FROM whatsapp_tenant_map WHERE phone_number = :p"), {"p": phone})
        await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant.id})
        await db.commit()


# ── Test helpers ──────────────────────────────────────────────────────────────

async def _mock_pipeline(payload):
    return {"answer": "mock answer", "sources": [], "follow_up_questions": []}


async def _fail_pipeline(payload):
    raise AssertionError("pipeline must not be called on reset")
