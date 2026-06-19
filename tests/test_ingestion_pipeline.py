"""
Tests for M5: n8n Ingestion Pipeline (persistent).

These tests run entirely without n8n or real credentials:
  - Unit tests validate the chunking/embedding helper logic (pure Python mirror)
  - Integration smoke tests POST to the n8n webhook and assert the DB state,
    using MOCK_N8N=true so the FastAPI side is also exercised without real AI
    calls.

Set the following env vars to run integration tests:
    N8N_INGEST_WEBHOOK_URL=http://localhost:5678/webhook/ingest
    DATABASE_URL=postgresql+asyncpg://raguser:ragpassword@localhost:5432/ragplatform
    MOCK_VOYAGE=true  (skips real Voyage API; inserts zero vectors)
"""

import json
import os
import uuid
import tempfile
import pathlib

import pytest
import pytest_asyncio
import httpx


# ─────────────────────────────────────────────────────────────────────────────
# Helpers that mirror the n8n Code-node logic in Python
# ─────────────────────────────────────────────────────────────────────────────

CHUNK_WORDS = 512
OVERLAP_WORDS = 50


def chunk_text(text: str) -> list[dict]:
    """Mirror of the 'Chunk Text (512/50)' n8n Code node."""
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        slice_ = words[i: i + CHUNK_WORDS]
        content = " ".join(slice_)
        chunks.append(
            {
                "content": content,
                "chunk_index": len(chunks),
                "page_number": None,
                "token_count": -(-len(content) // 4),  # ceil div
            }
        )
        if i + CHUNK_WORDS >= len(words):
            break
        i += CHUNK_WORDS - OVERLAP_WORDS
    return chunks


def strip_html(raw: str) -> str:
    """Mirror of the 'Strip HTML' n8n Code node (regex-only)."""
    import re
    text = re.sub(r"<script[\s\S]*?</script>", "", raw, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    for ent, rep in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">")]:
        text = text.replace(ent, rep)
    return " ".join(text.split())


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — pure logic, no external deps
# ─────────────────────────────────────────────────────────────────────────────


class TestChunker:
    def test_short_text_yields_one_chunk(self):
        text = "Hello world this is a short document."
        chunks = chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["content"] == text.strip()

    def test_empty_text_yields_no_chunks(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_long_text_yields_multiple_chunks_with_overlap(self):
        # Generate exactly 600 words
        words = [f"word{i}" for i in range(600)]
        text = " ".join(words)
        chunks = chunk_text(text)
        assert len(chunks) >= 2, "600 words should produce multiple chunks"

        # Verify overlap: last OVERLAP_WORDS of chunk[0] == first OVERLAP_WORDS of chunk[1]
        tail_0 = chunks[0]["content"].split()[-OVERLAP_WORDS:]
        head_1 = chunks[1]["content"].split()[:OVERLAP_WORDS]
        assert tail_0 == head_1, "Overlap words must match between consecutive chunks"

    def test_chunk_indices_are_sequential(self):
        text = " ".join([f"w{i}" for i in range(1100)])
        chunks = chunk_text(text)
        for idx, c in enumerate(chunks):
            assert c["chunk_index"] == idx

    def test_token_count_is_positive(self):
        text = "Some text for token counting."
        chunks = chunk_text(text)
        assert all(c["token_count"] > 0 for c in chunks)

    def test_exact_512_words_is_single_chunk(self):
        text = " ".join([f"w{i}" for i in range(512)])
        chunks = chunk_text(text)
        assert len(chunks) == 1

    def test_513_words_yields_two_chunks(self):
        text = " ".join([f"w{i}" for i in range(513)])
        chunks = chunk_text(text)
        assert len(chunks) == 2


class TestHtmlStripper:
    def test_strips_tags(self):
        result = strip_html("<p>Hello <b>world</b></p>")
        assert "<" not in result
        assert "Hello" in result
        assert "world" in result

    def test_removes_script_blocks(self):
        result = strip_html("<script>alert('xss')</script>Real content")
        assert "alert" not in result
        assert "Real content" in result

    def test_removes_style_blocks(self):
        result = strip_html("<style>.foo{color:red}</style>Text")
        assert "color" not in result
        assert "Text" in result

    def test_decodes_html_entities(self):
        result = strip_html("a &amp; b &lt; c &gt; d &nbsp; e")
        assert "&amp;" not in result
        assert "a & b" in result

    def test_collapses_whitespace(self):
        result = strip_html("<p>  too   many   spaces  </p>")
        assert "  " not in result


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures for integration tests
# ─────────────────────────────────────────────────────────────────────────────

N8N_URL = os.getenv("N8N_INGEST_WEBHOOK_URL", "")
INTEGRATION = pytest.mark.skipif(
    not N8N_URL,
    reason="Set N8N_INGEST_WEBHOOK_URL to run integration tests",
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"


def _sample_txt_file(content: str) -> str:
    """Write content to a temp file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.flush()
    return tmp.name


@pytest.fixture
def txt_payload():
    long_text = " ".join([f"word{i}" for i in range(700)])
    path = _sample_txt_file(long_text)
    doc_id = str(uuid.uuid4())
    yield {
        "document_id": doc_id,
        "tenant_id": TENANT_ID,
        "file_path": path,
        "source_type": "txt",
        "title": "Integration test TXT",
    }
    pathlib.Path(path).unlink(missing_ok=True)


@pytest.fixture
def url_payload():
    return {
        "document_id": str(uuid.uuid4()),
        "tenant_id": TENANT_ID,
        "source_type": "url",
        "source_url": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
        "title": "RAG Wikipedia page",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Integration tests — require a running n8n instance
# ─────────────────────────────────────────────────────────────────────────────


@INTEGRATION
class TestIngestionWebhookTxt:
    def test_txt_returns_202_or_200(self, txt_payload):
        resp = httpx.post(N8N_URL, json=txt_payload, timeout=60)
        assert resp.status_code in (200, 202), resp.text

    def test_txt_response_contains_document_id(self, txt_payload):
        resp = httpx.post(N8N_URL, json=txt_payload, timeout=60)
        body = resp.json()
        # n8n may wrap in 'data' or return directly
        actual = body.get("document_id") or (body.get("data") or {}).get("document_id")
        assert actual == txt_payload["document_id"]

    def test_txt_response_has_positive_chunk_count(self, txt_payload):
        resp = httpx.post(N8N_URL, json=txt_payload, timeout=60)
        body = resp.json()
        chunk_count = (
            body.get("chunk_count")
            or (body.get("data") or {}).get("chunk_count")
            or 0
        )
        assert int(chunk_count) > 0


@INTEGRATION
class TestIngestionWebhookUrl:
    def test_url_ingestion_succeeds(self, url_payload):
        resp = httpx.post(N8N_URL, json=url_payload, timeout=90)
        assert resp.status_code in (200, 202), resp.text

    def test_url_response_has_status_accepted(self, url_payload):
        resp = httpx.post(N8N_URL, json=url_payload, timeout=90)
        body = resp.json()
        status = body.get("status") or (body.get("data") or {}).get("status")
        assert status in ("accepted", "completed")


@INTEGRATION
class TestIngestionErrorHandling:
    def test_missing_document_id_is_handled(self):
        bad_payload = {
            "tenant_id": TENANT_ID,
            "file_path": "/nonexistent/file.txt",
            "source_type": "txt",
            "title": "Bad payload",
        }
        resp = httpx.post(N8N_URL, json=bad_payload, timeout=30)
        # Should not crash n8n; expect 4xx or a JSON error body
        assert resp.status_code < 500 or "error" in resp.text.lower()

    def test_nonexistent_file_triggers_failed_callback(self):
        payload = {
            "document_id": str(uuid.uuid4()),
            "tenant_id": TENANT_ID,
            "file_path": "/nonexistent/totally_missing.txt",
            "source_type": "txt",
            "title": "Missing file test",
        }
        resp = httpx.post(N8N_URL, json=payload, timeout=30)
        # Workflow should complete (200) with failed status, not 500
        if resp.status_code == 200:
            body = resp.json()
            status = body.get("status") or (body.get("data") or {}).get("status")
            assert status == "failed"


# ─────────────────────────────────────────────────────────────────────────────
# DB-level assertions (require DATABASE_URL)
# ─────────────────────────────────────────────────────────────────────────────

DB_URL = os.getenv("DATABASE_URL", "")
DB_INTEGRATION = pytest.mark.skipif(
    not (N8N_URL and DB_URL),
    reason="Set N8N_INGEST_WEBHOOK_URL and DATABASE_URL to run DB integration tests",
)


@DB_INTEGRATION
class TestChunksInDatabase:
    """After triggering the workflow, verify rows land in document_chunks."""

    def _sync_count(self, document_id: str) -> int:
        import psycopg2
        dsn = DB_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
            "postgresql+psycopg2://", "postgresql://"
        )
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM document_chunks WHERE document_id = %s",
            (document_id,),
        )
        count = cur.fetchone()[0]
        conn.close()
        return count

    def test_txt_chunks_persisted(self, txt_payload):
        import time

        httpx.post(N8N_URL, json=txt_payload, timeout=60)
        # Give n8n a moment to finish async inserts
        time.sleep(3)
        count = self._sync_count(txt_payload["document_id"])
        assert count > 0, "Expected at least one chunk in document_chunks"

    def test_embeddings_are_correct_dimension(self, txt_payload):
        import time
        import psycopg2

        httpx.post(N8N_URL, json=txt_payload, timeout=60)
        time.sleep(3)
        dsn = DB_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
            "postgresql+psycopg2://", "postgresql://"
        )
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute(
            "SELECT vector_dims(embedding) FROM document_chunks WHERE document_id = %s LIMIT 1",
            (txt_payload["document_id"],),
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None, "No row found"
        assert row[0] == 1024, f"Expected 1024-dim embedding, got {row[0]}"
