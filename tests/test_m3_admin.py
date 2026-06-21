"""M3 admin document & tenant endpoint tests.

Integration tests — require a live Postgres.
Skip automatically if Postgres is unreachable.

    docker compose run --rm backend pytest tests/test_m3_admin.py -v

Also covers POST /webhooks/n8n/ingestion-status (part of the document lifecycle).
External services (n8n_client, storage) are monkeypatched so no network I/O occurs.
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

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Document, Tenant, UploadAudit, User  # noqa: E402
from app.services import n8n_client, storage  # noqa: E402

pytestmark = pytest.mark.asyncio

_PDF_BYTES = b"%PDF-1.4 " + b"x" * 100
_DOCX_BYTES = b"PK\x03\x04" + b"x" * 100


# ── helpers ──────────────────────────────────────────────────────────────────

async def _db_available() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _mock_store(filename: str, content: bytes) -> str:
    return f"/mock/uploads/{uuid.uuid4().hex}_{filename}"


async def _mock_ingest(document_id, tenant_id, source_url, source_type, title):
    return {"status": "mock_started"}


async def _mock_ingest_raises(document_id, tenant_id, source_url, source_type, title):
    raise RuntimeError("n8n unavailable")


async def _async_noop(*args, **kwargs):
    return None


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


# ── tenant + user fixtures ────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_user():
    """Tenant + admin user + bearer token. Cleaned up after each test."""
    slug = f"m3adm-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        tenant = Tenant(name=f"M3 Admin Tenant {slug}", slug=slug)
        db.add(tenant)
        await db.flush()
        user = User(
            tenant_id=tenant.id,
            email=f"admin-{uuid.uuid4().hex[:8]}@m3test.example",
            hashed_password=get_password_hash("testpassword"),
            role="admin",
        )
        db.add(user)
        await db.commit()
        tenant_id, user_id = tenant.id, user.id

    token = create_access_token({"sub": str(user_id)})
    yield {"token": token, "user_id": user_id, "tenant_id": tenant_id}

    async with AsyncSessionLocal() as db:
        await db.execute(
            text("DELETE FROM upload_audit WHERE tenant_id = :t"), {"t": tenant_id}
        )
        await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant_id})
        await db.commit()


@pytest_asyncio.fixture
async def super_admin_user():
    """Tenant + super_admin user + bearer token. Cleaned up after each test."""
    slug = f"m3sa-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        tenant = Tenant(name=f"SA Tenant {slug}", slug=slug)
        db.add(tenant)
        await db.flush()
        user = User(
            tenant_id=tenant.id,
            email=f"sa-{uuid.uuid4().hex[:8]}@m3test.example",
            hashed_password=get_password_hash("testpassword"),
            role="super_admin",
        )
        db.add(user)
        await db.commit()
        tenant_id, user_id = tenant.id, user.id

    token = create_access_token({"sub": str(user_id)})
    yield {"token": token, "user_id": user_id, "tenant_id": tenant_id}

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant_id})
        await db.commit()


@pytest_asyncio.fixture
async def doc_in_db(admin_user):
    """A Document row (status=pending, fake file_path) for admin_user's tenant."""
    async with AsyncSessionLocal() as db:
        doc = Document(
            id=uuid.uuid4(),
            tenant_id=admin_user["tenant_id"],
            uploaded_by=admin_user["user_id"],
            title="Test Document",
            source_type="pdf",
            file_path="/fake/uploads/test.pdf",
            status="pending",
        )
        db.add(doc)
        await db.commit()
        doc_id = doc.id

    yield {"id": doc_id, "file_path": "/fake/uploads/test.pdf"}

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM documents WHERE id = :d"), {"d": doc_id})
        await db.commit()


# ═══════════════════════════════════════════
# GET /admin/documents
# ═══════════════════════════════════════════

async def test_list_documents_empty(client, admin_user):
    r = await client.get(
        "/admin/documents",
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["documents"] == []
    assert body["total"] == 0


async def test_list_documents_tenant_scoped(client, admin_user, doc_in_db):
    other_slug = f"other-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        other_tenant = Tenant(name="Other", slug=other_slug)
        db.add(other_tenant)
        await db.flush()
        other_doc = Document(
            id=uuid.uuid4(),
            tenant_id=other_tenant.id,
            title="Should not appear",
            source_type="pdf",
            status="pending",
        )
        db.add(other_doc)
        await db.commit()
        other_tenant_id, other_doc_id = other_tenant.id, other_doc.id

    try:
        r = await client.get(
            "/admin/documents",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
        )
        assert r.status_code == 200
        ids = [d["id"] for d in r.json()["documents"]]
        assert str(doc_in_db["id"]) in ids
        assert str(other_doc_id) not in ids
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": other_tenant_id})
            await db.commit()


async def test_list_documents_status_filter(client, admin_user, doc_in_db):
    r = await client.get(
        "/admin/documents?status=pending",
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 200
    docs = r.json()["documents"]
    assert all(d["status"] == "pending" for d in docs)
    assert any(d["id"] == str(doc_in_db["id"]) for d in docs)


async def test_list_documents_pagination(client, admin_user):
    created_ids = []
    async with AsyncSessionLocal() as db:
        for i in range(3):
            doc = Document(
                id=uuid.uuid4(),
                tenant_id=admin_user["tenant_id"],
                title=f"Doc {i}",
                source_type="txt",
                status="pending",
            )
            db.add(doc)
            created_ids.append(doc.id)
        await db.commit()

    try:
        r = await client.get(
            "/admin/documents?page=2&per_page=2",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert len(body["documents"]) == 1
    finally:
        async with AsyncSessionLocal() as db:
            for doc_id in created_ids:
                await db.execute(text("DELETE FROM documents WHERE id = :d"), {"d": doc_id})
            await db.commit()


async def test_list_documents_non_admin_403(client, admin_user):
    async with AsyncSessionLocal() as db:
        plain_user = User(
            tenant_id=admin_user["tenant_id"],
            email=f"plain-{uuid.uuid4().hex[:8]}@m3test.example",
            hashed_password=get_password_hash("pw"),
            role="user",
        )
        db.add(plain_user)
        await db.commit()
        plain_user_id = plain_user.id

    token = create_access_token({"sub": str(plain_user_id)})
    try:
        r = await client.get(
            "/admin/documents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(text("DELETE FROM users WHERE id = :u"), {"u": plain_user_id})
            await db.commit()


# ═══════════════════════════════════════════
# GET /admin/documents/{id}
# ═══════════════════════════════════════════

async def test_get_document_200(client, admin_user, doc_in_db):
    r = await client.get(
        f"/admin/documents/{doc_in_db['id']}",
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(doc_in_db["id"])
    assert body["title"] == "Test Document"
    assert body["status"] == "pending"


async def test_get_document_404(client, admin_user):
    r = await client.get(
        f"/admin/documents/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 404


async def test_get_document_403(client, admin_user):
    other_slug = f"get403-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        other_tenant = Tenant(name="Other403", slug=other_slug)
        db.add(other_tenant)
        await db.flush()
        other_doc = Document(
            id=uuid.uuid4(),
            tenant_id=other_tenant.id,
            title="Foreign doc",
            source_type="pdf",
            status="pending",
        )
        db.add(other_doc)
        await db.commit()
        other_tenant_id, other_doc_id = other_tenant.id, other_doc.id

    try:
        r = await client.get(
            f"/admin/documents/{other_doc_id}",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
        )
        assert r.status_code == 403
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": other_tenant_id})
            await db.commit()


# ═══════════════════════════════════════════
# DELETE /admin/documents/{id}
# ═══════════════════════════════════════════

async def test_delete_document_204(client, admin_user, doc_in_db, monkeypatch):
    monkeypatch.setattr(storage, "delete_upload", _async_noop)

    r = await client.delete(
        f"/admin/documents/{doc_in_db['id']}",
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 204

    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_in_db["id"])
        assert doc is None


async def test_delete_document_404(client, admin_user, monkeypatch):
    monkeypatch.setattr(storage, "delete_upload", _async_noop)

    r = await client.delete(
        f"/admin/documents/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 404


async def test_delete_document_403(client, admin_user, monkeypatch):
    monkeypatch.setattr(storage, "delete_upload", _async_noop)

    other_slug = f"del403-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as db:
        other_tenant = Tenant(name="Del403", slug=other_slug)
        db.add(other_tenant)
        await db.flush()
        other_doc = Document(
            id=uuid.uuid4(),
            tenant_id=other_tenant.id,
            title="Foreign",
            source_type="pdf",
            status="pending",
        )
        db.add(other_doc)
        await db.commit()
        other_tenant_id, other_doc_id = other_tenant.id, other_doc.id

    try:
        r = await client.delete(
            f"/admin/documents/{other_doc_id}",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
        )
        assert r.status_code == 403
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": other_tenant_id})
            await db.commit()


async def test_delete_document_calls_storage_cleanup(client, admin_user, doc_in_db, monkeypatch):
    calls: list[str] = []

    async def _tracking_delete(location: str) -> None:
        calls.append(location)

    monkeypatch.setattr(storage, "delete_upload", _tracking_delete)

    await client.delete(
        f"/admin/documents/{doc_in_db['id']}",
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert calls == [doc_in_db["file_path"]]


# ═══════════════════════════════════════════
# POST /admin/documents/upload
# ═══════════════════════════════════════════

async def test_upload_pdf_202(client, admin_user, monkeypatch):
    monkeypatch.setattr(storage, "store_upload", _mock_store)
    monkeypatch.setattr(n8n_client, "ingest", _mock_ingest)

    r = await client.post(
        "/admin/documents/upload",
        files={"file": ("report.pdf", _PDF_BYTES, "application/pdf")},
        data={"title": "My Report"},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "pending"
    assert body["source_type"] == "pdf"
    assert body["title"] == "My Report"

    doc_id = uuid.UUID(body["id"])
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_id)
        assert doc is not None
        await db.delete(doc)
        await db.commit()


async def test_upload_invalid_mime_415(client, admin_user):
    r = await client.post(
        "/admin/documents/upload",
        files={"file": ("page.html", b"<html>hello</html>", "text/html")},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 415


async def test_upload_wrong_magic_415(client, admin_user):
    r = await client.post(
        "/admin/documents/upload",
        files={"file": ("fake.pdf", _DOCX_BYTES, "application/pdf")},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 415


async def test_upload_rate_limit_429(client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOADS_PER_HOUR", 1)
    monkeypatch.setattr(storage, "store_upload", _mock_store)
    monkeypatch.setattr(n8n_client, "ingest", _mock_ingest)

    async with AsyncSessionLocal() as db:
        db.add(UploadAudit(tenant_id=admin_user["tenant_id"], bytes=100))
        await db.commit()

    r = await client.post(
        "/admin/documents/upload",
        files={"file": ("report.pdf", _PDF_BYTES, "application/pdf")},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 429


async def test_upload_quota_exceeded_413(client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "MAX_BYTES_PER_TENANT", 50)
    monkeypatch.setattr(storage, "store_upload", _mock_store)
    monkeypatch.setattr(n8n_client, "ingest", _mock_ingest)

    async with AsyncSessionLocal() as db:
        db.add(UploadAudit(tenant_id=admin_user["tenant_id"], bytes=50))
        await db.commit()

    r = await client.post(
        "/admin/documents/upload",
        files={"file": ("report.pdf", _PDF_BYTES, "application/pdf")},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 413


async def test_upload_n8n_failure_still_202(client, admin_user, monkeypatch):
    monkeypatch.setattr(storage, "store_upload", _mock_store)
    monkeypatch.setattr(n8n_client, "ingest", _mock_ingest_raises)

    r = await client.post(
        "/admin/documents/upload",
        files={"file": ("report.pdf", _PDF_BYTES, "application/pdf")},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 202

    doc_id = uuid.UUID(r.json()["id"])
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc:
            await db.delete(doc)
            await db.commit()


# ═══════════════════════════════════════════
# POST /admin/documents/url
# ═══════════════════════════════════════════

async def test_ingest_url_202(client, admin_user, monkeypatch):
    monkeypatch.setattr(n8n_client, "ingest", _mock_ingest)

    r = await client.post(
        "/admin/documents/url",
        json={"url": "https://example.com/doc.pdf", "title": "Web Doc"},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["source_type"] == "url"
    assert body["status"] == "pending"

    doc_id = uuid.UUID(body["id"])
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc:
            await db.delete(doc)
            await db.commit()


async def test_ingest_url_n8n_failure_still_202(client, admin_user, monkeypatch):
    monkeypatch.setattr(n8n_client, "ingest", _mock_ingest_raises)

    r = await client.post(
        "/admin/documents/url",
        json={"url": "https://example.com/fallback.pdf"},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 202

    doc_id = uuid.UUID(r.json()["id"])
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc:
            await db.delete(doc)
            await db.commit()


# ═══════════════════════════════════════════
# GET /admin/tenants/{id}
# ═══════════════════════════════════════════

async def test_get_tenant_super_admin_200(client, super_admin_user):
    r = await client.get(
        f"/admin/tenants/{super_admin_user['tenant_id']}",
        headers={"Authorization": f"Bearer {super_admin_user['token']}"},
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(super_admin_user["tenant_id"])


async def test_get_tenant_admin_403(client, admin_user):
    r = await client.get(
        f"/admin/tenants/{admin_user['tenant_id']}",
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 403


async def test_get_tenant_404(client, super_admin_user):
    r = await client.get(
        f"/admin/tenants/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {super_admin_user['token']}"},
    )
    assert r.status_code == 404


# ═══════════════════════════════════════════
# PATCH /admin/tenants/{id}
# ═══════════════════════════════════════════

async def test_update_tenant_name(client, super_admin_user):
    r = await client.patch(
        f"/admin/tenants/{super_admin_user['tenant_id']}",
        json={"name": "Updated Name"},
        headers={"Authorization": f"Bearer {super_admin_user['token']}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Updated Name"
    assert body["is_active"] is True       # other fields unchanged


async def test_update_tenant_partial(client, super_admin_user):
    r = await client.patch(
        f"/admin/tenants/{super_admin_user['tenant_id']}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {super_admin_user['token']}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_active"] is False
    assert body["name"] is not None        # name not reset


async def test_update_tenant_admin_403(client, admin_user):
    r = await client.patch(
        f"/admin/tenants/{admin_user['tenant_id']}",
        json={"name": "Hijack"},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 403


# ═══════════════════════════════════════════
# POST /webhooks/n8n/ingestion-status
# ═══════════════════════════════════════════

async def test_ingestion_callback_completes_document(client, doc_in_db):
    r = await client.post(
        "/webhooks/n8n/ingestion-status",
        json={
            "document_id": str(doc_in_db["id"]),
            "status": "completed",
            "chunk_count": 42,
            "callback_token": settings.N8N_CALLBACK_TOKEN,
        },
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_in_db["id"])
        assert doc.status == "completed"
        assert doc.chunk_count == 42


async def test_ingestion_callback_invalid_token_401(client, doc_in_db):
    r = await client.post(
        "/webhooks/n8n/ingestion-status",
        json={
            "document_id": str(doc_in_db["id"]),
            "status": "completed",
            "callback_token": "definitely-wrong-token",
        },
    )
    assert r.status_code == 401


async def test_ingestion_callback_unknown_doc_404(client):
    r = await client.post(
        "/webhooks/n8n/ingestion-status",
        json={
            "document_id": str(uuid.uuid4()),
            "status": "completed",
            "callback_token": settings.N8N_CALLBACK_TOKEN,
        },
    )
    assert r.status_code == 404


async def test_ingestion_callback_failure_sets_error(client, doc_in_db):
    r = await client.post(
        "/webhooks/n8n/ingestion-status",
        json={
            "document_id": str(doc_in_db["id"]),
            "status": "failed",
            "error_message": "PDF parse error on page 3",
            "callback_token": settings.N8N_CALLBACK_TOKEN,
        },
    )
    assert r.status_code == 200

    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_in_db["id"])
        assert doc.status == "failed"
        assert doc.error_message == "PDF parse error on page 3"


# ═══════════════════════════════════════════
# POST /admin/documents/upload — R2 source_url
# ═══════════════════════════════════════════

async def test_upload_r2_source_url_in_response(client, admin_user, monkeypatch):
    """source_url in the 202 response equals the R2 public URL from store_upload."""
    r2_url = "https://pub-test.r2.dev/abc_report.pdf"

    async def _r2_store(filename: str, content: bytes) -> str:
        return r2_url

    monkeypatch.setattr(storage, "store_upload", _r2_store)
    monkeypatch.setattr(n8n_client, "ingest", _mock_ingest)
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "r2")

    r = await client.post(
        "/admin/documents/upload",
        files={"file": ("report.pdf", _PDF_BYTES, "application/pdf")},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 202
    assert r.json()["source_url"] == r2_url

    doc_id = uuid.UUID(r.json()["id"])
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc:
            await db.delete(doc)
            await db.commit()


async def test_upload_n8n_receives_r2_url_as_source_url(client, admin_user, monkeypatch):
    """n8n ingest background task is called with the R2 public URL as source_url."""
    r2_url = "https://pub-test.r2.dev/uuid_report.pdf"
    captured: list[str] = []

    async def _r2_store(filename: str, content: bytes) -> str:
        return r2_url

    async def _capture_ingest(document_id, tenant_id, source_url, source_type, title):
        captured.append(source_url)

    monkeypatch.setattr(storage, "store_upload", _r2_store)
    monkeypatch.setattr(n8n_client, "ingest", _capture_ingest)
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "r2")

    r = await client.post(
        "/admin/documents/upload",
        files={"file": ("report.pdf", _PDF_BYTES, "application/pdf")},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 202
    assert captured == [r2_url]

    doc_id = uuid.UUID(r.json()["id"])
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc:
            await db.delete(doc)
            await db.commit()


async def test_upload_local_backend_source_url_is_download_endpoint(client, admin_user, monkeypatch):
    """With local backend, n8n source_url is the FastAPI download endpoint URL."""
    captured: list[str] = []

    async def _capture_ingest(document_id, tenant_id, source_url, source_type, title):
        captured.append(source_url)

    monkeypatch.setattr(storage, "store_upload", _mock_store)
    monkeypatch.setattr(n8n_client, "ingest", _capture_ingest)
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")

    r = await client.post(
        "/admin/documents/upload",
        files={"file": ("report.pdf", _PDF_BYTES, "application/pdf")},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 202
    doc_id = r.json()["id"]
    assert len(captured) == 1
    assert captured[0] == f"{settings.APP_BASE_URL}/admin/documents/{doc_id}/download"

    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, uuid.UUID(doc_id))
        if doc:
            await db.delete(doc)
            await db.commit()


# ═══════════════════════════════════════════
# POST /admin/documents/url — n8n source_url
# ═══════════════════════════════════════════

async def test_ingest_url_n8n_receives_original_url_as_source_url(client, admin_user, monkeypatch):
    """n8n ingest is called with source_url equal to the original URL submitted."""
    captured: list[str] = []

    async def _capture_ingest(document_id, tenant_id, source_url, source_type, title):
        captured.append(source_url)

    monkeypatch.setattr(n8n_client, "ingest", _capture_ingest)

    original_url = "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"
    r = await client.post(
        "/admin/documents/url",
        json={"url": original_url, "title": "RAG Wikipedia"},
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert r.status_code == 202
    assert captured == [original_url]

    doc_id = uuid.UUID(r.json()["id"])
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc:
            await db.delete(doc)
            await db.commit()


# ═══════════════════════════════════════════
# GET /admin/documents/{id}/download
# ═══════════════════════════════════════════

@pytest_asyncio.fixture
async def doc_with_file(admin_user, tmp_path):
    """Document row backed by a real file in tmp_path."""
    file = tmp_path / "test_download.pdf"
    file.write_bytes(_PDF_BYTES)

    async with AsyncSessionLocal() as db:
        doc = Document(
            id=uuid.uuid4(),
            tenant_id=admin_user["tenant_id"],
            title="Downloadable Doc",
            source_type="pdf",
            file_path=str(file),
            status="pending",
        )
        db.add(doc)
        await db.commit()
        doc_id = doc.id

    yield {"id": doc_id, "file_path": str(file)}

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM documents WHERE id = :d"), {"d": doc_id})
        await db.commit()


async def test_download_document_200(client, doc_with_file):
    r = await client.get(f"/admin/documents/{doc_with_file['id']}/download")
    assert r.status_code == 200
    assert r.content == _PDF_BYTES
    assert "application/pdf" in r.headers["content-type"]


async def test_download_document_no_file_path_404(client, admin_user):
    """URL-ingested document has no stored file → 404."""
    async with AsyncSessionLocal() as db:
        doc = Document(
            id=uuid.uuid4(),
            tenant_id=admin_user["tenant_id"],
            title="URL Doc",
            source_type="url",
            source_url="https://example.com/doc.pdf",
            file_path=None,
            status="pending",
        )
        db.add(doc)
        await db.commit()
        doc_id = doc.id

    try:
        r = await client.get(f"/admin/documents/{doc_id}/download")
        assert r.status_code == 404
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(text("DELETE FROM documents WHERE id = :d"), {"d": doc_id})
            await db.commit()


async def test_download_document_missing_file_404(client, admin_user):
    """file_path set but file no longer exists on disk → 404."""
    async with AsyncSessionLocal() as db:
        doc = Document(
            id=uuid.uuid4(),
            tenant_id=admin_user["tenant_id"],
            title="Ghost Doc",
            source_type="pdf",
            file_path="/nonexistent/path/ghost.pdf",
            status="pending",
        )
        db.add(doc)
        await db.commit()
        doc_id = doc.id

    try:
        r = await client.get(f"/admin/documents/{doc_id}/download")
        assert r.status_code == 404
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(text("DELETE FROM documents WHERE id = :d"), {"d": doc_id})
            await db.commit()


async def test_download_document_not_found_404(client):
    r = await client.get(f"/admin/documents/{uuid.uuid4()}/download")
    assert r.status_code == 404
