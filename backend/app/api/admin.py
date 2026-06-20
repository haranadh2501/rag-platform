"""
Admin API routes — documents, users, tenants.
Owner: M3 (documents + tenant detail/update) · M2 (users, tenant list/create).
"""
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.models import Document, Tenant, UploadAudit, User
from app.schemas.auth import UserList, UserOut
from app.schemas.documents import DocumentList, DocumentOut, UrlIngestRequest
from app.schemas.tenants import TenantOut, TenantUpdate
from app.services import file_validator, n8n_client, storage

logger = logging.getLogger(__name__)
router = APIRouter()

# MIME type → document source_type (matches openapi.yaml enum)
_MIME_TO_SOURCE_TYPE: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "image/png": "image",
    "image/jpeg": "image",
}


# ══════════════════════════════════════════
# DOCUMENTS  (M3)
# ══════════════════════════════════════════

@router.get("/documents", response_model=DocumentList, summary="List documents for current tenant")
async def list_documents(
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    filters = [Document.tenant_id == current_user.tenant_id]
    if status:
        filters.append(Document.status == status)

    total = (await db.execute(
        select(func.count()).select_from(Document).where(*filters)
    )).scalar() or 0

    rows = (await db.execute(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    )).scalars().all()

    return DocumentList(
        documents=[DocumentOut.model_validate(d) for d in rows],
        total=total,
    )


@router.post("/documents/upload", status_code=202, response_model=DocumentOut, summary="Upload document file")
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    content = await file.read()

    # Validate MIME, magic bytes, and size
    validated = file_validator.validate_upload(
        filename=file.filename or "upload",
        content=content,
        declared_mime=file.content_type,
    )

    # Rate limit: max uploads per hour per tenant
    cutoff = datetime.utcnow() - timedelta(hours=1)
    upload_count = (await db.execute(
        select(func.count()).select_from(UploadAudit).where(
            UploadAudit.tenant_id == current_user.tenant_id,
            UploadAudit.uploaded_at > cutoff,
        )
    )).scalar() or 0

    if upload_count >= settings.MAX_UPLOADS_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Upload rate limit exceeded — max {settings.MAX_UPLOADS_PER_HOUR} uploads/hour per tenant",
        )

    # Storage quota: 1 GB per tenant
    used_bytes = (await db.execute(
        select(func.sum(UploadAudit.bytes)).where(
            UploadAudit.tenant_id == current_user.tenant_id
        )
    )).scalar() or 0

    if used_bytes + validated.size_bytes > settings.MAX_BYTES_PER_TENANT:
        raise HTTPException(status_code=413, detail="Tenant storage quota exceeded (1 GB limit)")

    # Persist file via storage backend (local path today, cloud URL later)
    location = await storage.store_upload(validated.filename, content)

    # Insert document record and audit entry in one transaction
    doc = Document(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.id,
        title=title or validated.filename,
        source_type=_MIME_TO_SOURCE_TYPE.get(validated.mime_type, "pdf"),
        file_path=location,
        status="pending",
    )
    db.add(doc)
    db.add(UploadAudit(tenant_id=current_user.tenant_id, bytes=validated.size_bytes))
    await db.commit()
    await db.refresh(doc)

    # Trigger n8n ingestion — best-effort, document is saved regardless
    try:
        await n8n_client.ingest(
            document_id=str(doc.id),
            tenant_id=str(doc.tenant_id),
            file_path=location,
            source_type=doc.source_type,
            title=doc.title,
        )
    except Exception:
        logger.exception("n8n ingestion trigger failed for document %s", doc.id)

    return DocumentOut.model_validate(doc)


@router.post("/documents/url", status_code=202, response_model=DocumentOut, summary="Ingest from URL")
async def ingest_url(
    body: UrlIngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    doc = Document(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.id,
        title=body.title or body.url,
        source_type="url",
        source_url=body.url,
        status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    try:
        await n8n_client.ingest(
            document_id=str(doc.id),
            tenant_id=str(doc.tenant_id),
            file_path=body.url,
            source_type="url",
            title=doc.title,
        )
    except Exception:
        logger.exception("n8n ingestion trigger failed for document %s", doc.id)

    return DocumentOut.model_validate(doc)


@router.get("/documents/{document_id}", response_model=DocumentOut, summary="Get document detail")
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return DocumentOut.model_validate(doc)


@router.delete("/documents/{document_id}", status_code=204, summary="Delete document")
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if doc.file_path:
        await storage.delete_upload(doc.file_path)

    await db.delete(doc)
    await db.commit()


# ══════════════════════════════════════════
# USERS  (M2)
# ══════════════════════════════════════════

@router.get("/users", response_model=UserList, summary="List users in current tenant")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """List users in the caller's tenant. Admin/super_admin only; always scoped
    to the caller's tenant_id (super_admin sees its own tenant here — cross-tenant
    listing lives under /admin/tenants)."""
    result = await db.execute(
        select(User)
        .where(User.tenant_id == current_user.tenant_id)
        .order_by(User.created_at)
    )
    users = result.scalars().all()
    return UserList(users=[UserOut.model_validate(u) for u in users], total=len(users))


@router.post("/users/invite", status_code=201, summary="Invite user")
async def invite_user(request: dict):
    """M2: Create user with specified role in current tenant."""
    raise HTTPException(status_code=501, detail="M2: implement user invite")


# ══════════════════════════════════════════
# TENANTS  (M2 — list/create · M3 — detail/update)
# ══════════════════════════════════════════

@router.get("/tenants", summary="List all tenants (super_admin only)")
async def list_tenants():
    """M2: super_admin only — list all tenants."""
    raise HTTPException(status_code=501, detail="M2: implement tenant list")


@router.post("/tenants", status_code=201, summary="Create tenant (super_admin only)")
async def create_tenant(request: dict):
    """M2: Create new tenant."""
    raise HTTPException(status_code=501, detail="M2: implement create tenant")


@router.get("/tenants/{tenant_id}", response_model=TenantOut, summary="Get tenant by ID (super_admin only)")
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantOut.model_validate(tenant)


@router.patch("/tenants/{tenant_id}", response_model=TenantOut, summary="Update tenant (super_admin only)")
async def update_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(tenant, key, value)
    await db.commit()
    await db.refresh(tenant)
    return TenantOut.model_validate(tenant)
