"""Phase 2 verification — n8n_client.retrieve() signature and mock mode."""
import sys
import asyncio
import inspect

sys.path.insert(0, "C:\\Users\\tush2\\Desktop\\rag-platform\\backend")

# Force MOCK_N8N=true so we never hit real n8n
import os
os.environ.setdefault("MOCK_N8N", "true")

from app.services.n8n_client import retrieve, MOCK_RETRIEVE_RESPONSE

# ── Signature check ───────────────────────────────────────────────────────────
sig = inspect.signature(retrieve)
params = list(sig.parameters.keys())
expected = ["request_id", "tenant_id", "conversation_id", "current_message", "history"]
assert params == expected, f"Param mismatch: got {params}"
assert asyncio.iscoroutinefunction(retrieve), "retrieve must be async"

# ── Mock response shape ───────────────────────────────────────────────────────
result = asyncio.run(retrieve(
    request_id="test-req-001",
    tenant_id="aaaaaaaa-0000-0000-0000-000000000001",
    conversation_id="bbbbbbbb-0000-0000-0000-000000000002",
    current_message="What is the refund policy?",
    history=[
        {"role": "user",      "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ],
))

assert result is MOCK_RETRIEVE_RESPONSE, "Mock mode must return MOCK_RETRIEVE_RESPONSE sentinel"
assert "answer"              in result, "Missing 'answer' key"
assert "sources"             in result, "Missing 'sources' key"
assert "follow_up_questions" in result, "Missing 'follow_up_questions' key"
assert "metadata"            in result, "Missing 'metadata' key"
assert result["metadata"]["mock"] is True, "metadata.mock must be True"
assert isinstance(result["sources"], list), "sources must be a list"
assert len(result["sources"]) > 0, "sources must be non-empty in mock"

# ── MOCK_RETRIEVE_RESPONSE has correct source shape ───────────────────────────
src = result["sources"][0]
for key in ("document_id", "title", "chunk_text", "page_number", "score"):
    assert key in src, f"Missing source field: {key}"

# ── Timeout constant check (introspect source) ────────────────────────────────
import app.services.n8n_client as _mod
src_text = inspect.getsource(_mod.retrieve)
assert "timeout=120.0" in src_text, "Timeout must be 120.0 seconds"
assert "request_id"      in src_text, "payload must include request_id"
assert "current_message" in src_text, "payload must include current_message"
assert "conversation_id" in src_text, "payload must include conversation_id"
# Removed fields must be absent from the retrieve() body
assert "max_chunks" not in src_text, "'max_chunks' must not appear in retrieve()"
assert "query" not in src_text.split("def retrieve")[1].split("ingest")[0], \
    "'query' key must not appear in retrieve() payload"

print("Phase 2 — all assertions passed")
print(f"  Signature     : retrieve({', '.join(params)})")
print(f"  Async         : {asyncio.iscoroutinefunction(retrieve)}")
print(f"  Timeout       : 120.0s confirmed in source")
print(f"  Mock answer   : {result['answer'][:60]}...")
print(f"  Mock sources  : {len(result['sources'])} source(s)")
print(f"  Follow-ups    : {len(result['follow_up_questions'])} question(s)")
