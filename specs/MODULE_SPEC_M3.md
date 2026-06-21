# MODULE_SPEC_M3 — Backend: Document & Chat APIs

**Owner**: Member 3 | **Track**: Backend | **Branch**: `feat/admin-api`, `feat/chat-api`

## Role
File upload endpoint, document management, chat proxy to n8n with MOCK mode.
**Critical**: Ship `chat.py` with `MOCK_N8N=true` on Day 2 — this unblocks M4, M8, M9, M12.

## Day-by-Day Deliverables
| Day | Deliverable | Done? |
|---|---|---|
| 1 | Read `specs/openapi.yaml`. Understand n8n webhook contract. | ☐ |
| 2 | `backend/app/api/chat.py` with `MOCK_N8N=true` returning valid mock response | ☐ |
| 2 | `POST /admin/documents/upload` — save file, create DB record, trigger n8n | ☐ |
| 2 | `POST /admin/documents/url` — URL ingestion trigger | ☐ |
| 2 | `GET /admin/documents`, `GET /admin/documents/{id}`, `DELETE` | ☐ |
| 3 | Wire real n8n retrieval into `POST /chat/query` (disable mock) | ☐ |
| 3 | Conversation + ChatMessage models + endpoints | ☐ |
| 4 | Upload → ingestion flow working end-to-end | ☐ |
| 5–6 | Integration tests, bug fixes | ☐ |

## Files Owned
- `backend/app/api/admin.py`
- `backend/app/api/chat.py`
- `backend/app/services/n8n_client.py`
- `backend/app/services/storage.py` (local + Cloudflare R2 backends)

## MOCK_N8N Implementation (Day 2 priority)
```python
# backend/app/api/chat.py
import os
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user

router = APIRouter()

MOCK_RESPONSE = {
    "answer": "Based on the uploaded documentation, here is the answer with details...",
    "sources": [{"document_id": "mock-uuid", "title": "Sample Manual", "chunk_text": "Relevant excerpt...", "page_number": 12, "score": 0.94}],
    "follow_up_questions": ["Can you explain more?", "What are the steps?", "Who should I contact?"],
    "metadata": {"model": "gpt-4o-mini", "retrieval_time_ms": 1200, "chunks_retrieved": 5}
}

@router.post("/query")
async def chat_query(request: ChatQueryRequest, current_user=Depends(get_current_user)):
    if os.getenv("MOCK_N8N", "false").lower() == "true":
        return MOCK_RESPONSE  # <-- ship this Day 2
    # real implementation below (Day 3)
    return await n8n_client.retrieve(...)
```

## n8n Client Service
```python
# backend/app/services/n8n_client.py
async def ingest(document_id, tenant_id, source_url, source_type, title): ...
async def retrieve(query, tenant_id, conversation_history, max_chunks=5): ...
```
- Uses `httpx.AsyncClient`
- Reads `N8N_RETRIEVE_WEBHOOK_URL`, `N8N_INGEST_WEBHOOK_URL` from config
- `source_url` for file uploads = R2 public URL (`https://pub-a9bb7d7b516244eaacc47d9cab962786.r2.dev/<key>`) when `STORAGE_BACKEND=r2`; falls back to `APP_BASE_URL/admin/documents/{id}/download` for local backend. For URL ingestion = the original URL.
- Raises `HTTPException(502)` if n8n returns non-200

## Acceptance Criteria
- [ ] `MOCK_N8N=true`: `POST /chat/query` returns valid mock response (Day 2)
- [ ] `POST /admin/documents/upload` saves file + returns 202 with document record
- [ ] Document status updates from `pending` → `completed` after n8n callback
- [ ] `GET /admin/documents` returns paginated list filtered by current tenant
- [ ] Integration test: upload PDF → query → get grounded answer


---
<!-- AUTO-APPENDED:SKILLS-V1 -->
## Skills Required
- **Must-have:** FastAPI, async Python, httpx, file upload (UploadFile, multipart), Pydantic v2, environment-driven config.
- **Nice-to-have:** Streaming responses, background tasks, n8n webhook conventions.
- **Soft skills:** Mock-first development (build against fake n8n so frontend isn't blocked).

## Detailed Step-by-Step Plan
### Day 1 — Mock-First
1. Branch `feat/chat-api` from `main`.
2. Read `specs/openapi.yaml` sections for `POST /chat/query` and `POST /admin/documents/upload`.
3. Confirm `settings.MOCK_N8N = true` returns a hardcoded plausible response in `services/n8n_client.py`.

### Day 2 — Document Upload
4. Implement `POST /admin/documents/upload` (multipart): accept file → call `services/file_validator.validate_upload` → save to `UPLOAD_DIR` with UUID name → INSERT row into `documents` with status=`pending` → call `n8n_client.ingest()` → return document ID.
5. Implement `GET /admin/documents` — paginated list filtered by `tenant_id`.
6. Implement `DELETE /admin/documents/{id}` — soft-delete + remove chunks.
7. Implement `POST /admin/documents/url` — accept JSON `{url, title}`; same flow but pass URL to n8n instead of file.

### Day 3 — Chat Endpoint
8. Implement `POST /chat/query`: validate JWT → load last 5 messages from `chat_messages` for conversation_id → call `n8n_client.retrieve(query, tenant_id, history)` → INSERT both user + assistant messages → return `{answer, sources, faithfulness, requires_clarification, follow_up_questions}`.
9. Implement `POST /chat/conversations` (create new) and `GET /chat/conversations` (list).

### Day 4 — Ingestion Callback
10. Implement `POST /webhooks/ingestion-status` — guard with `X-Callback-Token` header == `settings.N8N_CALLBACK_TOKEN` → UPDATE `documents` set status, page_count, chunk_count.

### Day 5 — MCP Hook
11. Coordinate with MCP tools (`backend/app/mcp/tools.py`): replace TODO with real tenant_slug → tenant_id DB lookup, then call `n8n_client.retrieve`.

### Day 6 — Tests
12. `tests/test_chat.py`: query returns sources, conversation history persisted, tenant isolation (user A cannot read user B's docs).

## Unit Test Coverage

> Full test plan in `specs/PLAN_M3.md §7`. Summary below.

| Test file | Type | Cases | Coverage |
|---|---|---|---|
| `tests/test_m3_units.py` | Pure unit (no DB) | 14 | `storage.py`, `file_validator.py`, all M3 schemas |
| `tests/test_m3_admin.py` | Integration (DB + monkeypatch) | 30 | All document endpoints, tenant endpoints, n8n callback |
| `tests/test_m3_conversations.py` | Integration (DB + monkeypatch) | 12 | Conversation list, detail, delete |

Key testing decisions:
- **Pure unit tests** use `pytest tmp_path` for storage; no DB required
- **Integration tests** follow the same pattern as `tests/test_auth.py` — real Postgres, auto-skip if DB unreachable, self-seeding fixtures with teardown
- **External services** (`n8n_client`, `storage`) are monkeypatched in integration tests so no network calls or filesystem side-effects
- `POST /chat/query` is already tested in `tests/test_m4_chat.py` — not duplicated here

## Learning Resources
- FastAPI file uploads: https://fastapi.tiangolo.com/tutorial/request-files/
- httpx async: https://www.python-httpx.org/async/
