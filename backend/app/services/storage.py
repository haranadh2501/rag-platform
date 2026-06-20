"""File storage backend abstraction.

Swap local ↔ cloud by changing STORAGE_BACKEND in config/env.
`admin.py` and `n8n_client.py` only see `store_upload` / `delete_upload`
and receive a location string (local path or cloud URL) they pass straight
through to n8n as `file_path`.

[TODO-CLOUD] See specs/PLAN_M3.md §6 for the GCS/S3 extension plan.
"""
from pathlib import Path
from uuid import uuid4

from app.core.config import settings


async def store_upload(filename: str, content: bytes) -> str:
    """Persist file bytes and return a location string.

    The returned string is stored in `documents.file_path` and forwarded
    to n8n as the `file_path` webhook field — n8n reads a local path or
    fetches a cloud URL transparently.
    """
    if settings.STORAGE_BACKEND == "local":
        safe_name = f"{uuid4()}_{Path(filename).name or 'upload'}"
        dest = Path(settings.UPLOAD_DIR) / safe_name
        dest.write_bytes(content)
        return str(dest)

    # [TODO-CLOUD] add GCS / S3 branches here — see specs/PLAN_M3.md §6
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND!r}")


async def delete_upload(location: str) -> None:
    """Remove a previously stored file. Swallows not-found errors.

    Works for both local paths and future cloud URLs without callers
    needing to know which backend is active.
    """
    if settings.STORAGE_BACKEND == "local":
        try:
            Path(location).unlink()
        except FileNotFoundError:
            pass
        return

    # [TODO-CLOUD] add GCS / S3 branches here — see specs/PLAN_M3.md §6
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND!r}")
