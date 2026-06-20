"""M3 pure unit tests — no database, no HTTP.

Covers: services/storage.py, services/file_validator.py, and M3 schemas.
All tests are self-contained and run without a Postgres instance.
"""
import os
import sys
import uuid
from datetime import datetime

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from fastapi import HTTPException  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.schemas.chat import ConversationOut  # noqa: E402
from app.schemas.documents import DocumentOut, UrlIngestRequest  # noqa: E402
from app.schemas.tenants import TenantUpdate  # noqa: E402
from app.services import file_validator, storage  # noqa: E402

_PDF_BYTES = b"%PDF-1.4 " + b"x" * 100
_DOCX_BYTES = b"PK\x03\x04" + b"x" * 100


# ═══════════════════════════════════════════
# Storage service — services/storage.py
# ═══════════════════════════════════════════

@pytest.mark.asyncio
async def test_store_upload_local_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")

    content = b"%PDF-1.4 hello world"
    location = await storage.store_upload("test.pdf", content)

    assert location.startswith(str(tmp_path))
    assert os.path.exists(location)
    with open(location, "rb") as f:
        assert f.read() == content


@pytest.mark.asyncio
async def test_store_upload_unknown_backend_raises(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "unknown_cloud")

    with pytest.raises(ValueError, match="Unknown STORAGE_BACKEND"):
        await storage.store_upload("test.pdf", b"data")


@pytest.mark.asyncio
async def test_delete_upload_local_removes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")

    target = tmp_path / "to_delete.bin"
    target.write_bytes(b"content")

    await storage.delete_upload(str(target))

    assert not target.exists()


@pytest.mark.asyncio
async def test_delete_upload_missing_file_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    missing = str(tmp_path / "does_not_exist.bin")

    await storage.delete_upload(missing)   # must not raise


@pytest.mark.asyncio
async def test_delete_upload_unknown_backend_raises(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "unknown_cloud")

    with pytest.raises(ValueError, match="Unknown STORAGE_BACKEND"):
        await storage.delete_upload("/some/path")


# ═══════════════════════════════════════════
# File validator — services/file_validator.py
# ═══════════════════════════════════════════

def test_validate_pdf_valid():
    result = file_validator.validate_upload(
        filename="report.pdf",
        content=_PDF_BYTES,
        declared_mime="application/pdf",
    )
    assert result.mime_type == "application/pdf"
    assert result.size_bytes == len(_PDF_BYTES)
    assert result.filename == "report.pdf"


def test_validate_wrong_magic_raises_415():
    with pytest.raises(HTTPException) as exc_info:
        file_validator.validate_upload(
            filename="fake.pdf",
            content=_DOCX_BYTES,           # DOCX magic bytes
            declared_mime="application/pdf",  # declared as PDF
        )
    assert exc_info.value.status_code == 415


def test_validate_empty_raises_400():
    with pytest.raises(HTTPException) as exc_info:
        file_validator.validate_upload(
            filename="empty.pdf",
            content=b"",
            declared_mime="application/pdf",
        )
    assert exc_info.value.status_code == 400


def test_validate_too_large_raises_413():
    with pytest.raises(HTTPException) as exc_info:
        file_validator.validate_upload(
            filename="big.pdf",
            content=_PDF_BYTES,
            declared_mime="application/pdf",
            max_bytes=5,    # tiny limit to trigger the check
        )
    assert exc_info.value.status_code == 413


def test_validate_disallowed_mime_raises_415():
    with pytest.raises(HTTPException) as exc_info:
        file_validator.validate_upload(
            filename="page.html",
            content=b"<html>hello</html>",
            declared_mime="text/html",
        )
    assert exc_info.value.status_code == 415


# ═══════════════════════════════════════════
# Schema validation — schemas/documents.py
# ═══════════════════════════════════════════

def test_document_out_from_dict():
    doc_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    data = {
        "id": doc_id,
        "tenant_id": tenant_id,
        "title": "User Manual",
        "source_type": "pdf",
        "source_url": None,
        "status": "pending",
        "chunk_count": 0,
        "error_message": None,
        "created_at": datetime.utcnow(),
    }
    out = DocumentOut.model_validate(data)
    assert out.id == doc_id
    assert out.source_type == "pdf"
    assert out.status == "pending"


def test_url_ingest_request_requires_url():
    with pytest.raises(ValidationError):
        UrlIngestRequest.model_validate({})   # url is required


def test_url_ingest_request_valid():
    req = UrlIngestRequest(url="https://example.com/doc.pdf", title="Doc")
    assert req.url == "https://example.com/doc.pdf"
    assert req.title == "Doc"


def test_url_ingest_request_title_optional():
    req = UrlIngestRequest(url="https://example.com/doc.pdf")
    assert req.title is None


# ═══════════════════════════════════════════
# Schema validation — schemas/chat.py
# ═══════════════════════════════════════════

def test_conversation_out_message_count():
    out = ConversationOut(
        id=uuid.uuid4(),
        title="Chat",
        channel="web",
        created_at=datetime.utcnow(),
        message_count=7,
    )
    assert out.message_count == 7


def test_conversation_out_title_optional():
    out = ConversationOut(
        id=uuid.uuid4(),
        title=None,
        channel="slack",
        created_at=datetime.utcnow(),
        message_count=0,
    )
    assert out.title is None


# ═══════════════════════════════════════════
# Schema validation — schemas/tenants.py
# ═══════════════════════════════════════════

def test_tenant_update_partial_name_only():
    update = TenantUpdate(name="New Name")
    dump = update.model_dump(exclude_unset=True)
    assert "name" in dump
    assert "is_active" not in dump
    assert "plan" not in dump


def test_tenant_update_partial_is_active_only():
    update = TenantUpdate(is_active=False)
    dump = update.model_dump(exclude_unset=True)
    assert dump == {"is_active": False}


def test_tenant_update_all_fields():
    update = TenantUpdate(name="x", is_active=True, plan="pro")
    dump = update.model_dump(exclude_unset=True)
    assert set(dump.keys()) == {"name", "is_active", "plan"}
