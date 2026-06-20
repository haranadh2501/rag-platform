# M3: Document & Chat APIs — Implementation Plan

> **Module:** M3: Backend Document & Chat APIs
> Scope defined in `specs/MODULE_SPEC_M3.md` + API contract `specs/openapi.yaml`.
> Branch: `feat/m3-document-chat-api` (base: `dev`).
> Legend: ✅ done · 🟡 partial · ❌ not started.

## TL;DR

The `POST /chat/query` endpoint is fully working (wired via `message_service` +
`pipeline_client`, both M4-owned). The `n8n_client.py` service is implemented
with MOCK support. Everything else — all document endpoints, the n8n callback,
and conversation CRUD — is stubbed with `501 Not Implemented`. This plan covers
all remaining work in priority order, with the n8n ingestion callback and
`GET /admin/documents` as the two earliest unblocking deliverables.

---

## 1. Acceptance Criteria (`MODULE_SPEC_M3` §Acceptance)

| Criterion | State | Notes |
|---|---|---|
| `MOCK_N8N=true`: `POST /chat/query` returns valid mock response | ✅ | Working via `pipeline_client` → `POST /webhooks/mock/pipeline` |
| `POST /admin/documents/upload` saves file + returns 202 with document record | ❌ | Stub returns 501 |
| Document status updates `pending → completed` after n8n callback | ❌ | Callback stub exists but performs no DB write |
| `GET /admin/documents` returns paginated list filtered by current tenant | ❌ | Stub returns 501 |
| Integration test: upload PDF → query → get grounded answer | ❌ | No tests yet |

---

## 2. Files Owned (`MODULE_SPEC_M3` §Files Owned)

| File | State | Notes |
|---|---|---|
| `backend/app/api/admin.py` | 🟡 | Document endpoints are stubs (501). `GET /admin/users` (M2 work) is the only implemented route. |
| `backend/app/api/chat.py` | 🟡 | `POST /chat/query` is done. Conversation CRUD (`GET`, `GET/{id}`, `DELETE`) are stubs (501). |
| `backend/app/services/n8n_client.py` | ✅ | `ingest()` and `retrieve()` implemented with `MOCK_N8N` support. Note: `chat.py` currently uses `pipeline_client` (M4-owned), not `n8n_client`, for the query flow. |
| *(to add)* `backend/app/services/storage.py` | ❌ | Storage backend abstraction — local path today, cloud URL tomorrow. Called by the upload and delete handlers. See §6. |
| *(to add)* `backend/app/schemas/documents.py` | ❌ | Pydantic schemas for document endpoints — prerequisite for all of Phase 2. |
| *(to add)* `backend/app/schemas/chat.py` | ❌ | Pydantic schemas for conversation endpoints — prerequisite for Phase 4. |
| *(to add)* `backend/app/schemas/tenants.py` | ❌ | `TenantOut` + `TenantUpdate` schemas — M3-owned, extensible for future multi-tenant admin work. |

---

## 3. Implementation Phases

### Phase 1 — Schemas + Storage Service (prerequisite, do first)

**New file: `backend/app/services/storage.py`**

Storage backend abstraction. The upload handler calls `store_upload()` and gets
back a location string — a local path today, a cloud URL later. The DELETE
handler calls `delete_upload()`. Neither `admin.py` nor `n8n_client.py` know or
care which backend is active.

```python
from pathlib import Path
from uuid import uuid4
from app.core.config import settings

async def store_upload(filename: str, content: bytes) -> str:
    """Persist file bytes and return a location string passed to n8n as file_path."""
    if settings.STORAGE_BACKEND == "local":
        safe_name = f"{uuid4()}_{Path(filename).name or 'upload'}"
        dest = Path(settings.UPLOAD_DIR) / safe_name
        dest.write_bytes(content)
        return str(dest)
    # [TODO-CLOUD] add GCS / S3 branches here — see §6
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND!r}")

async def delete_upload(location: str) -> None:
    """Remove a previously stored file. Swallows not-found errors."""
    if settings.STORAGE_BACKEND == "local":
        try:
            Path(location).unlink()
        except FileNotFoundError:
            pass
        return
    # [TODO-CLOUD] add GCS / S3 branches here — see §6
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND!r}")
```

Add `STORAGE_BACKEND: str = "local"` to `backend/app/core/config.py` `Settings`
class. No other config changes needed for Phase 1.

---

**New file: `backend/app/schemas/documents.py`**

Matches `openapi.yaml` `DocumentOut`, `DocumentList`, `UrlIngestRequest` schemas exactly.

```python
class DocumentOut(BaseModel):
    id: UUID
    tenant_id: UUID
    title: str
    source_type: str                  # pdf | docx | txt | url
    source_url: str | None
    status: str                       # pending | processing | completed | failed
    chunk_count: int
    error_message: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DocumentList(BaseModel):
    documents: list[DocumentOut]
    total: int

class UrlIngestRequest(BaseModel):
    url: str
    title: str | None = None
```

---

**New file: `backend/app/schemas/tenants.py`**

M3-owned. Kept separate from M2's `schemas/auth.py` to allow independent
evolution as multi-tenant admin features are added later.

```python
class TenantOut(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TenantUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    plan: str | None = None
```

---

**New file: `backend/app/schemas/chat.py`**

Matches `openapi.yaml` `ConversationOut`, `ChatMessageOut` schemas.
`message_count` is not an ORM column — computed via `len(conversation.messages)`
after eager loading, or a subquery scalar. `faithfulness` is `float | None`
since the pipeline may or may not return it; `requires_clarification` defaults
to `False` via the DB column default.

```python
class ChatMessageOut(BaseModel):
    id: UUID
    role: str                         # user | assistant
    content: str
    sources: list[dict]
    faithfulness: float | None
    requires_clarification: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ConversationOut(BaseModel):
    id: UUID
    title: str | None
    channel: str
    created_at: datetime
    message_count: int

class ConversationDetail(ConversationOut):
    messages: list[ChatMessageOut]
```

---

### Phase 2 — Document Endpoints (`admin.py`)

All document endpoints require `Depends(require_role("admin"))` and are scoped
to `current_user.tenant_id`. Import `n8n_client` and `storage` for ingestion
triggers and file management.

---

#### `GET /admin/documents`

Query params: `status` (optional enum), `page` (default 1), `per_page` (default 20).

Steps:
1. Build `SELECT` from `documents WHERE tenant_id = current_user.tenant_id`
2. Optionally add `AND status = :status` if param provided
3. Run a COUNT query for `total`
4. Apply `LIMIT per_page OFFSET (page - 1) * per_page`
5. Return `DocumentList(documents=[DocumentOut.model_validate(d) for d in rows], total=total)`

---

#### `GET /admin/documents/{document_id}`

Steps:
1. `db.get(Document, document_id)` — 404 if `None`
2. Raise 403 if `document.tenant_id != current_user.tenant_id`
3. Return `DocumentOut.model_validate(document)`

---

#### `DELETE /admin/documents/{document_id}`

Steps:
1. Fetch document (same tenant guard as above, 404/403)
2. If `document.file_path` is set: `await storage.delete_upload(document.file_path)` — swallows not-found, works for both local paths and future cloud URLs
3. `await db.delete(document)` + `await db.commit()` — DB cascade handles `document_chunks`
4. Return 204

---

#### `POST /admin/documents/upload`

Most complex endpoint. Multipart form: `file: UploadFile`, `title: str | None`.

Steps:
1. `content = await file.read()`
2. Call `file_validator.validate_upload(filename=file.filename, content=content, declared_mime=file.content_type)` — raises 400 / 413 / 415 automatically
3. **Rate limit check**: count `UploadAudit` rows `WHERE tenant_id = :tid AND uploaded_at > NOW() - INTERVAL '1 hour'`; raise `HTTP 429` if ≥ `settings.MAX_UPLOADS_PER_HOUR` (20)
4. **Storage quota check**: `SUM(bytes) FROM upload_audit WHERE tenant_id = :tid`; raise `HTTP 413` ("tenant storage quota exceeded") if sum + len(content) > `settings.MAX_BYTES_PER_TENANT` (1 GB)
5. `location = await storage.store_upload(file.filename, content)` — returns a local path today, a cloud URL after §6 migration. This is the only call site that needs to change for cloud storage.
6. INSERT `Document(tenant_id, uploaded_by=current_user.id, title=title or file.filename, source_type=<derived from mime>, file_path=location, status="pending")`
7. INSERT `UploadAudit(tenant_id=current_user.tenant_id, bytes=len(content))`
8. `await db.commit()`
9. Construct `source_url = f"{settings.APP_BASE_URL}/admin/documents/{doc.id}/download"` — a URL n8n can fetch from (works both locally and on Railway since APP_BASE_URL is set per environment)
10. Call `await n8n_client.ingest(document_id=str(doc.id), tenant_id=str(doc.tenant_id), source_url=source_url, source_type=doc.source_type, title=doc.title)`
11. Return `DocumentOut.model_validate(doc)` with status 202

MIME → `source_type` mapping:
| MIME | source_type |
|---|---|
| `application/pdf` | `pdf` |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `docx` |
| `text/plain` | `txt` |

---

#### `POST /admin/documents/url`

Body: `UrlIngestRequest`.

Steps:
1. Validate body (Pydantic handles this)
2. INSERT `Document(tenant_id, uploaded_by=current_user.id, title=body.title or body.url, source_type="url", source_url=body.url, status="pending")`
3. `await db.commit()`
4. Call `await n8n_client.ingest(document_id=str(doc.id), tenant_id=str(doc.tenant_id), source_url=body.url, source_type="url", title=doc.title)`
5. Return `DocumentOut.model_validate(doc)` with status 202

---

#### `GET /admin/documents/{document_id}/download`

Public endpoint (no auth) so n8n can fetch uploaded files by document ID. Serves the raw file bytes with the correct `Content-Type`. Document IDs are UUIDs — not guessable.

Steps:
1. `db.get(Document, document_id)` — 404 if `None`
2. Read `doc.file_path` — 404 if null (URL-ingested docs have no stored file)
3. `Path(doc.file_path).read_bytes()` — 404 if file missing on disk
4. Return `Response(content=bytes, media_type=<inferred from source_type>)`

> When cloud storage is adopted, this endpoint reads from GCS/S3 instead of local disk — no n8n changes needed.

---

#### `GET /admin/tenants/{tenant_id}` *(missing from code, in openapi.yaml)*

Requires `require_role("super_admin")`.

Steps:
1. `db.get(Tenant, tenant_id)` — 404 if `None`
2. Return `TenantOut.model_validate(tenant)` (from `schemas/tenants.py`)

---

#### `PATCH /admin/tenants/{tenant_id}` *(missing from code, in openapi.yaml)*

Requires `require_role("super_admin")`. Body: `TenantUpdate` from `schemas/tenants.py` — all fields optional.

Steps:
1. Fetch tenant by id — 404 if not found
2. Apply updates: iterate `body.model_dump(exclude_unset=True).items()` and `setattr(tenant, k, v)`
3. `await db.commit()`; `await db.refresh(tenant)`
4. Return `TenantOut.model_validate(tenant)`

---

### Phase 3 — n8n Ingestion Callback (`webhooks.py`)

**`POST /webhooks/n8n/ingestion-status`** — complete the existing stub at line 218.

Body (per `openapi.yaml`): `document_id`, `status`, `chunk_count`, `error_message`, `callback_token`.

Steps:
1. Parse body via a Pydantic model (define inline in `webhooks.py`)
2. **Validate token**: `if body.callback_token != settings.N8N_CALLBACK_TOKEN: raise HTTPException(401, "Invalid callback token")`
3. `document = await db.get(Document, body.document_id)` — 404 if not found
4. `document.status = body.status`
5. `document.chunk_count = body.chunk_count or 0`
6. `document.error_message = body.error_message`
7. `await db.commit()`
8. Return `{"ok": True}`

This endpoint needs `db: AsyncSession = Depends(get_db)` added to its signature.

---

### Phase 4 — Conversation CRUD (`chat.py`)

All three require `Depends(get_current_user)` and are scoped to `current_user.id`.

---

#### `GET /chat/conversations`

Steps:
1. Query `conversations WHERE user_id = current_user.id ORDER BY created_at DESC`
2. For each conversation, compute `message_count` via a scalar subquery (`SELECT COUNT(*) FROM chat_messages WHERE conversation_id = :cid`) or by loading with `selectinload(Conversation.messages)`
3. Return `{"conversations": [ConversationOut(...) for c in rows]}`

---

#### `GET /chat/conversations/{conversation_id}`

Steps:
1. Fetch conversation with `selectinload(Conversation.messages)` ordered by `created_at ASC`
2. 404 if not found; 403 if `conversation.user_id != current_user.id`
3. Build `message_count = len(conversation.messages)`
4. Return `ConversationDetail` with nested `messages` list

---

#### `DELETE /chat/conversations/{conversation_id}`

Steps:
1. Fetch conversation — 404 if not found, 403 if wrong user
2. `await db.delete(conversation)` + `await db.commit()` — cascade deletes `chat_messages`
3. Return 204

---

## 4. Implementation Order

| Step | File | Endpoint / Task | Reason |
|---|---|---|---|
| 1 | `services/storage.py` | `store_upload()`, `delete_upload()` | Prerequisite for upload + delete; isolates filesystem coupling |
| 2 | `schemas/documents.py` | `DocumentOut`, `DocumentList`, `UrlIngestRequest` | Unblocks all document endpoints |
| 3 | `schemas/tenants.py` | `TenantOut`, `TenantUpdate` | Unblocks tenant endpoints |
| 4 | `schemas/chat.py` | `ConversationOut`, `ConversationDetail`, `ChatMessageOut` | Unblocks conversation endpoints |
| 5 | `core/config.py` | Add `STORAGE_BACKEND = "local"` setting | Required by `storage.py` |
| 6 | `main.py` | Add `mkdir` for `UPLOAD_DIR` in lifespan | Required before any upload can succeed |
| 7 | `admin.py` | `GET /admin/documents` | Simplest read — good first check of tenant scoping |
| 8 | `admin.py` | `GET /admin/documents/{id}`, `DELETE /admin/documents/{id}` | Read + delete before write |
| 9 | `admin.py` | `POST /admin/documents/upload` | Most complex; depends on `storage`, `file_validator`, `n8n_client`, `UploadAudit` |
| 10 | `admin.py` | `POST /admin/documents/url` | Simpler variant of upload |
| 11 | `admin.py` | `GET /admin/tenants/{id}`, `PATCH /admin/tenants/{id}` | Missing spec endpoints |
| 12 | `webhooks.py` | `POST /webhooks/n8n/ingestion-status` | Completes the upload → n8n → callback cycle |
| 13 | `chat.py` | `GET /chat/conversations` | Conversation list |
| 14 | `chat.py` | `GET /chat/conversations/{id}` | Conversation detail with messages |
| 15 | `chat.py` | `DELETE /chat/conversations/{id}` | Conversation delete |

---

## 5. Integration Decisions (Locked)

These were verified against the existing codebase and confirmed before implementation.

| Decision | Resolution |
|---|---|
| Storage quota enforcement | `SUM(bytes) FROM upload_audit WHERE tenant_id = :tid` — no ORM changes needed. `tenants.storage_used_bytes` exists in `init.sql` but not in the ORM/migration; leave it alone. |
| `TenantOut` Pydantic schema | New `backend/app/schemas/tenants.py` — clean separation, extensible as multi-tenant support grows. Do not edit M2-owned `schemas/auth.py`. |
| n8n ingestion callback (`webhooks.py`) | M3 opens the PR; M4 reviews before merge. File is M4-owned per `CLAUDE.md` but M3 spec owns Day 4 deliverable. |
| `UPLOAD_DIR` (`/uploads`) creation | Add `Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)` in FastAPI `lifespan` startup in `main.py`. Zero-friction for local dev, harmless in Docker. |
| `documents.size_bytes` | Skip — column exists in `init.sql` but not in ORM/migration `0001`. Use `upload_audit.bytes` as the only size record for quota. No ORM or migration changes needed. |
| Tenant scope | Platform currently runs as effectively single-tenant (IISc Demo). `GET/PATCH /admin/tenants/{id}` are `super_admin`-only and designed to be extensible for full multi-tenant later. |

---

## 6. Cloudflare R2 Storage Backend

> **Status: Approved, pending implementation.**

### Why R2 (not local disk)

Railway's filesystem is ephemeral — files written to disk are lost on every
redeploy. R2 provides durable object storage with zero egress cost (Cloudflare
serves the file directly to n8n without bandwidth charges).

### R2 bucket details (non-secret)

| Setting | Value |
|---|---|
| Bucket name | `rag-platform` |
| Public base URL | `https://pub-a9bb7d7b516244eaacc47d9cab962786.r2.dev` |
| Region | `auto` (Cloudflare-managed) |
| Access credentials | `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` in `.env` / Railway Variables (never committed) |

### How source_url changes

```
Before (local disk):  source_url = "https://<APP_BASE_URL>/admin/documents/{id}/download"
After  (R2):          source_url = "https://pub-a9bb7d7b516244eaacc47d9cab962786.r2.dev/<uuid>_filename.pdf"
```

n8n fetches the file directly from R2's CDN — FastAPI is not in the download path.

### Files to change

| File | Change |
|---|---|
| `requirements.txt` | Add `boto3>=1.34` (R2 is S3-compatible) |
| `backend/app/core/config.py` | Add `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL` settings |
| `backend/app/services/storage.py` | Add `r2` branch: `put_object` on upload, `delete_object` on delete; run via `asyncio.run_in_executor` (boto3 is sync) |
| `backend/app/api/admin.py` | `upload_document`: use R2 URL directly as `source_url` when `STORAGE_BACKEND=r2`; keep `/download` endpoint for local backend |
| `.env.example` | Document R2 settings with placeholders |
| `backend/.env` | Set `STORAGE_BACKEND=r2` + real R2 credentials (not committed) |

### `storage.py` R2 implementation sketch

```python
def _r2_client():
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

# store_upload — R2 branch
elif settings.STORAGE_BACKEND == "r2":
    key = f"{uuid4()}_{Path(filename).name or 'upload'}"
    s3 = _r2_client()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: s3.put_object(
        Bucket=settings.R2_BUCKET_NAME, Key=key, Body=content
    ))
    return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{key}"

# delete_upload — R2 branch
elif settings.STORAGE_BACKEND == "r2":
    key = location.removeprefix(settings.R2_PUBLIC_URL.rstrip("/") + "/")
    s3 = _r2_client()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: s3.delete_object(
        Bucket=settings.R2_BUCKET_NAME, Key=key
    ))
```

### `admin.py` source_url logic (upload_document)

```python
if settings.STORAGE_BACKEND == "r2":
    source_url = location          # store_upload returns the R2 public URL
else:
    source_url = f"{settings.APP_BASE_URL}/admin/documents/{doc.id}/download"
```

### Acceptance criteria

- [ ] `POST /admin/documents/upload` → file appears in R2 bucket `rag-platform`
- [ ] `source_url` in n8n payload is the R2 public URL
- [ ] n8n successfully fetches the file from R2 (document status moves to `completed`)
- [ ] `DELETE /admin/documents/{id}` removes the object from R2
- [ ] Local dev still works with `STORAGE_BACKEND=local` (no R2 credentials needed)

---

## 7. Unit Test Plan

> **Status: approved, not yet written.**
> Run all tests: `cd backend && pytest ../tests/ -v`

### Test file structure

```
tests/
├── test_m3_units.py          # Pure unit tests — no DB, no HTTP
├── test_m3_admin.py          # Integration tests — admin document endpoints
└── test_m3_conversations.py  # Integration tests — conversation CRUD
```

**Pure unit tests** (`test_m3_units.py`) run with no Postgres dependency — using `tmp_path`
for filesystem tests and plain Pydantic for schema tests.

**Integration tests** follow the same pattern as `tests/test_auth.py` and
`tests/test_m4_chat.py`: real Postgres (auto-skip if unreachable), `httpx.AsyncClient`
with `ASGITransport`, self-seeding fixtures, `monkeypatch` for external services
(n8n_client, storage).

---

### `test_m3_units.py` — Pure unit tests (14 cases)

**Storage service (`services/storage.py`)**

| # | Test | What is verified |
|---|---|---|
| 1 | `test_store_upload_local_writes_file` | `store_upload()` creates file in UPLOAD_DIR, returns valid path string |
| 2 | `test_store_upload_unknown_backend_raises` | raises `ValueError` for unknown `STORAGE_BACKEND` |
| 3 | `test_delete_upload_local_removes_file` | `delete_upload()` removes existing file |
| 4 | `test_delete_upload_missing_file_is_noop` | `delete_upload()` swallows `FileNotFoundError` (idempotent) |
| 5 | `test_delete_upload_unknown_backend_raises` | raises `ValueError` for unknown `STORAGE_BACKEND` |

**File validator (`services/file_validator.py`)**

| # | Test | What is verified |
|---|---|---|
| 6 | `test_validate_pdf_valid` | valid PDF magic bytes + MIME passes, returns `ValidatedUpload` |
| 7 | `test_validate_wrong_magic_raises_415` | DOCX magic declared as `application/pdf` → HTTP 415 |
| 8 | `test_validate_empty_raises_400` | empty bytes → HTTP 400 |
| 9 | `test_validate_too_large_raises_413` | bytes > `MAX_UPLOAD_BYTES` → HTTP 413 |
| 10 | `test_validate_disallowed_mime_raises_415` | `text/html` MIME → HTTP 415 |

**Schema validation (`schemas/documents.py`, `schemas/chat.py`, `schemas/tenants.py`)**

| # | Test | What is verified |
|---|---|---|
| 11 | `test_document_out_from_dict` | `DocumentOut` validates from dict with all fields (from_attributes) |
| 12 | `test_url_ingest_request_requires_url` | `UrlIngestRequest` without `url` raises `ValidationError` |
| 13 | `test_conversation_out_message_count` | `ConversationOut` accepts manually set `message_count` |
| 14 | `test_tenant_update_partial` | `TenantUpdate.model_dump(exclude_unset=True)` only includes set fields |

---

### `test_m3_admin.py` — Admin document endpoints (30 cases)

Fixtures:
- `admin_user` — creates tenant + admin user + JWT; tears down after test
- `super_admin_user` — same but `role="super_admin"`
- `doc_in_db` — inserts a `Document` row (`status="pending"`) for `admin_user`'s tenant

**`GET /admin/documents`**

| # | Test | What is verified |
|---|---|---|
| 1 | `test_list_documents_empty` | new tenant → `{"documents": [], "total": 0}` |
| 2 | `test_list_documents_tenant_scoped` | another tenant's docs are not returned |
| 3 | `test_list_documents_status_filter` | `?status=pending` returns only pending docs |
| 4 | `test_list_documents_pagination` | `?page=2&per_page=1` returns correct subset |
| 5 | `test_list_documents_non_admin_403` | regular user role → 403 |

**`GET /admin/documents/{id}`**

| # | Test | What is verified |
|---|---|---|
| 6 | `test_get_document_200` | own doc → 200 with correct fields |
| 7 | `test_get_document_404` | non-existent UUID → 404 |
| 8 | `test_get_document_403` | another tenant's doc → 403 |

**`DELETE /admin/documents/{id}`**

| # | Test | What is verified |
|---|---|---|
| 9 | `test_delete_document_204` | own doc → 204, row removed from DB |
| 10 | `test_delete_document_404` | non-existent → 404 |
| 11 | `test_delete_document_403` | another tenant's doc → 403 |
| 12 | `test_delete_document_calls_storage_cleanup` | `storage.delete_upload` called with `doc.file_path` |

**`POST /admin/documents/upload`**

| # | Test | What is verified |
|---|---|---|
| 13 | `test_upload_pdf_202` | valid PDF → 202, `Document` row created with `status="pending"` |
| 14 | `test_upload_invalid_mime_415` | `text/html` content-type → 415 |
| 15 | `test_upload_wrong_magic_415` | DOCX bytes declared as PDF → 415 |
| 16 | `test_upload_rate_limit_429` | inject 20+ `UploadAudit` rows within last hour → 429 |
| 17 | `test_upload_quota_exceeded_413` | inject `UploadAudit.bytes` = `MAX_BYTES_PER_TENANT` → 413 |
| 18 | `test_upload_n8n_failure_still_202` | monkeypatch `n8n_client.ingest` to raise → still 202 (best-effort) |

**`POST /admin/documents/url`**

| # | Test | What is verified |
|---|---|---|
| 19 | `test_ingest_url_202` | valid URL body → 202 with `source_type="url"` |
| 20 | `test_ingest_url_n8n_failure_still_202` | n8n failure is non-fatal → 202 |

**`GET /admin/tenants/{id}`**

| # | Test | What is verified |
|---|---|---|
| 21 | `test_get_tenant_super_admin_200` | super_admin → 200 with tenant fields |
| 22 | `test_get_tenant_admin_403` | regular admin role → 403 |
| 23 | `test_get_tenant_404` | unknown UUID → 404 |

**`PATCH /admin/tenants/{id}`**

| # | Test | What is verified |
|---|---|---|
| 24 | `test_update_tenant_name` | PATCH `name` → updated, other fields unchanged |
| 25 | `test_update_tenant_partial` | only `is_active=false` sent → only that field changed |
| 26 | `test_update_tenant_admin_403` | regular admin → 403 |

**`POST /webhooks/n8n/ingestion-status`**

| # | Test | What is verified |
|---|---|---|
| 27 | `test_ingestion_callback_completes_document` | valid token + doc_id → status/chunk_count written, returns `{"ok": True}` |
| 28 | `test_ingestion_callback_invalid_token_401` | wrong token → 401 |
| 29 | `test_ingestion_callback_unknown_doc_404` | non-existent doc_id → 404 |
| 30 | `test_ingestion_callback_failure_sets_error` | `status=failed` + `error_message` → both persisted |

---

### `test_m3_conversations.py` — Conversation CRUD (12 cases)

Fixtures:
- `conv_user` — creates tenant + user + JWT; tears down after test (same pattern as `test_m4_chat.py::web_user`)
- `conv_with_messages` — creates a `Conversation` + 2 `ChatMessage` rows for `conv_user`

**`GET /chat/conversations`**

| # | Test | What is verified |
|---|---|---|
| 1 | `test_list_conversations_empty` | new user → `{"conversations": []}` |
| 2 | `test_list_conversations_own_only` | other user's conversations not returned |
| 3 | `test_list_conversations_message_count` | `message_count` matches actual messages in DB |
| 4 | `test_list_conversations_unauthenticated_401` | no token → 401 |

**`GET /chat/conversations/{id}`**

| # | Test | What is verified |
|---|---|---|
| 5 | `test_get_conversation_200` | own conversation → 200, messages in chronological order |
| 6 | `test_get_conversation_404` | non-existent UUID → 404 |
| 7 | `test_get_conversation_403` | another user's conversation → 403 |
| 8 | `test_get_conversation_message_count_matches` | `message_count == len(messages)` in response body |

**`DELETE /chat/conversations/{id}`**

| # | Test | What is verified |
|---|---|---|
| 9 | `test_delete_conversation_204` | own conversation → 204 |
| 10 | `test_delete_conversation_404` | non-existent → 404 |
| 11 | `test_delete_conversation_403` | another user's → 403 |
| 12 | `test_delete_conversation_cascade` | after delete, `chat_messages` rows are also gone |

---

### Summary

| File | Type | Cases |
|---|---|---|
| `test_m3_units.py` | pure unit (no DB) | 14 |
| `test_m3_admin.py` | integration (DB + monkeypatch) | 30 |
| `test_m3_conversations.py` | integration (DB + monkeypatch) | 12 |
| **Total** | | **56** |
