"""File storage backend abstraction.

Swap local ↔ cloud by changing STORAGE_BACKEND in .env:
  local  — writes to UPLOAD_DIR on disk (local dev)
  r2     — uploads to Cloudflare R2, returns a public CDN URL

`admin.py` and `n8n_client.py` only see `store_upload` / `delete_upload`
and receive a location string (local path or public URL) back.
"""
import asyncio
from pathlib import Path
from uuid import uuid4

from app.core.config import settings


def _r2_client():
    """Build a boto3 S3 client pointed at Cloudflare R2."""
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


async def store_upload(filename: str, content: bytes) -> str:
    """Persist file bytes and return a location string.

    - local: returns an absolute filesystem path
    - r2:    uploads to R2 and returns the public CDN URL
    """
    if settings.STORAGE_BACKEND == "local":
        safe_name = f"{uuid4()}_{Path(filename).name or 'upload'}"
        dest = Path(settings.UPLOAD_DIR) / safe_name
        dest.write_bytes(content)
        return str(dest)

    if settings.STORAGE_BACKEND == "r2":
        key = f"{uuid4()}_{Path(filename).name or 'upload'}"
        s3 = _r2_client()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: s3.put_object(Bucket=settings.R2_BUCKET_NAME, Key=key, Body=content),
        )
        return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{key}"

    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND!r}")


async def delete_upload(location: str) -> None:
    """Remove a previously stored file. Swallows not-found errors."""
    if settings.STORAGE_BACKEND == "local":
        try:
            Path(location).unlink()
        except FileNotFoundError:
            pass
        return

    if settings.STORAGE_BACKEND == "r2":
        prefix = settings.R2_PUBLIC_URL.rstrip("/") + "/"
        key = location.removeprefix(prefix)
        if not key or key == location:
            return  # location doesn't look like an R2 URL — skip silently
        s3 = _r2_client()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: s3.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key),
        )
        return

    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND!r}")
