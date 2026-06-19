"""
Admin API routes — documents, users, tenants.
Owner: M3 (documents) + M2 (users/tenants).
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.models import User
from app.schemas.auth import UserList, UserOut

router = APIRouter()


@router.get("/documents", summary="List documents for current tenant")
async def list_documents():
    """M3: Return paginated list of documents filtered by tenant_id."""
    raise HTTPException(status_code=501, detail="M3: implement document list")


@router.post("/documents/upload", status_code=202, summary="Upload document file")
async def upload_document(file: UploadFile = File(...)):
    """
    M3: Implement:
    1. Validate file type + size
    2. Save to UPLOAD_DIR
    3. INSERT into documents table (status=pending)
    4. Call n8n_client.ingest(...)
    5. Return DocumentOut
    """
    raise HTTPException(status_code=501, detail="M3: implement document upload")


@router.post("/documents/url", status_code=202, summary="Ingest from URL")
async def ingest_url(request: dict):
    """M3: Save document record + trigger n8n ingestion for URL."""
    raise HTTPException(status_code=501, detail="M3: implement URL ingestion")


@router.get("/documents/{document_id}", summary="Get document detail")
async def get_document(document_id: str):
    """M3: Return single document by ID (must belong to current tenant)."""
    raise HTTPException(status_code=501, detail="M3: implement get document")


@router.delete("/documents/{document_id}", status_code=204, summary="Delete document")
async def delete_document(document_id: str):
    """M3: Delete document + chunks from DB (cascade)."""
    raise HTTPException(status_code=501, detail="M3: implement delete document")


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


@router.get("/tenants", summary="List all tenants (super_admin only)")
async def list_tenants():
    """M2: super_admin only — list all tenants."""
    raise HTTPException(status_code=501, detail="M2: implement tenant list")


@router.post("/tenants", status_code=201, summary="Create tenant (super_admin only)")
async def create_tenant(request: dict):
    """M2: Create new tenant."""
    raise HTTPException(status_code=501, detail="M2: implement create tenant")
