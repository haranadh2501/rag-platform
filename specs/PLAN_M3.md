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
9. Call `await n8n_client.ingest(document_id=str(doc.id), tenant_id=str(doc.tenant_id), file_path=location, source_type=doc.source_type, title=doc.title)` — `location` is passed as `file_path`; n8n reads a local path or fetches a cloud URL transparently
10. Return `DocumentOut.model_validate(doc)` with status 202

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
4. Call `await n8n_client.ingest(document_id=str(doc.id), tenant_id=str(doc.tenant_id), file_path=body.url, source_type="url", title=doc.title)`
5. Return `DocumentOut.model_validate(doc)` with status 202

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

## 6. [TODO] Cloud Storage Backend Extension

> **Status: Not started. Implement after local path is tested and verified.**

The `storage.py` abstraction is designed so that moving from local disk to cloud
storage requires changes in exactly one place: the `store_upload()` and
`delete_upload()` functions in `backend/app/services/storage.py`.

### Why this is needed

FastAPI and n8n run as separate services (separate containers / Railway
instances). In Docker Compose they share a volume mount today. In a cloud
deployment they have isolated filesystems — n8n cannot read `/uploads` from
the FastAPI container. The fix is to put the file in a location both services
can reach: a cloud storage bucket.

### Handover mechanism

The `file_path` field in the n8n ingest webhook payload is already the
abstraction point:

```
Local (today):  file_path = "/uploads/abc_manual.pdf"
                n8n reads from shared Docker volume

Cloud (future): file_path = "https://storage.googleapis.com/iisc-rag/abc_manual.pdf"
                n8n does an HTTP GET to fetch the file
```

`n8n_client.ingest()`, `admin.py`, and the `Document` ORM model all stay the
same. Only `storage.py` changes.

### What to implement when ready

1. **Choose a provider** — GCS (free tier generous), S3, or Azure Blob. GCS
   recommended given free hosting targets in ARCHITECTURE.md.

2. **Add config** to `config.py`:
   ```python
   STORAGE_BACKEND: str = "local"       # "local" | "gcs" | "s3"
   GCS_BUCKET_NAME: str = ""
   GCS_CREDENTIALS_JSON: str = ""       # base64-encoded service account JSON
   ```

3. **Implement cloud branch in `storage.py`**:
   ```python
   # [TODO-CLOUD] GCS example
   elif settings.STORAGE_BACKEND == "gcs":
       from google.cloud import storage as gcs
       client = gcs.Client.from_service_account_info(...)
       bucket = client.bucket(settings.GCS_BUCKET_NAME)
       blob_name = f"{uuid4()}_{Path(filename).name}"
       blob = bucket.blob(blob_name)
       blob.upload_from_string(content, content_type=mime_type)
       return blob.public_url   # or generate a signed URL for private buckets
   ```

4. **Update n8n ingestion workflow** (M5) — change the "read file" node from
   filesystem read to HTTP GET on the URL. n8n's built-in HTTP node handles
   this natively.

5. **Remove Docker shared volume** from `docker-compose.yml` (M7) once cloud
   path is live and tested.

### Acceptance criteria for cloud extension

- [ ] Upload via `POST /admin/documents/upload` → file lands in GCS bucket
- [ ] n8n ingestion workflow reads file from GCS URL (not local path)
- [ ] `DELETE /admin/documents/{id}` removes the GCS object
- [ ] Local dev still works with `STORAGE_BACKEND=local` (no cloud credentials needed)
- [ ] Docker Compose volume mount removed from `docker-compose.yml`
