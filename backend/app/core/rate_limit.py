"""In-process rate limiter (slowapi). Owner: M2.

Single shared `Limiter` keyed by client IP. No Redis — state lives in-process,
which is fine for our single-worker dev/demo setup (see CLAUDE.md). Routes opt
in with `@limiter.limit(...)`; `main.py` registers it on `app.state` and wires
the 429 handler.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.RATE_LIMIT_ENABLED)
