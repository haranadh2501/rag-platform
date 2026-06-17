"""Phase 3-5 verification — import and structural checks for context_builder,
conversation_router, and message_handler."""
import sys, inspect, asyncio

sys.path.insert(0, "C:\\Users\\tush2\\Desktop\\rag-platform\\backend")

# ── Phase 3: context_builder ─────────────────────────────────────────────────
from app.services.context_builder import build_slack_context, build_web_context, RESET_COMMANDS

assert callable(build_slack_context), "build_slack_context must be callable"
assert callable(build_web_context),   "build_web_context must be callable"
assert asyncio.iscoroutinefunction(build_slack_context), "build_slack_context must be async"
assert not asyncio.iscoroutinefunction(build_web_context), "build_web_context must be sync"

assert RESET_COMMANDS == {"/new", "/restart", "/clear"}, f"RESET_COMMANDS mismatch: {RESET_COMMANDS}"

# build_slack_context signature
sig = inspect.signature(build_slack_context)
params = list(sig.parameters.keys())
assert params == ["payload", "db"], f"build_slack_context params: {params}"

# build_web_context signature
sig = inspect.signature(build_web_context)
params = list(sig.parameters.keys())
assert params == ["user", "query", "conversation_id"], f"build_web_context params: {params}"

print("Phase 3 (context_builder) — import + signature checks passed")

# ── Phase 4: conversation_router ─────────────────────────────────────────────
from app.services.conversation_router import (
    find_or_create_conversation,
    reset_conversation,
    _create_conversation,
)

assert asyncio.iscoroutinefunction(find_or_create_conversation), "find_or_create_conversation must be async"
assert asyncio.iscoroutinefunction(reset_conversation),          "reset_conversation must be async"
assert asyncio.iscoroutinefunction(_create_conversation),        "_create_conversation must be async"

# Check function signatures
sig = inspect.signature(find_or_create_conversation)
assert list(sig.parameters.keys()) == ["ctx", "db"], \
    f"find_or_create_conversation params: {list(sig.parameters.keys())}"

sig = inspect.signature(reset_conversation)
assert list(sig.parameters.keys()) == ["ctx", "db"], \
    f"reset_conversation params: {list(sig.parameters.keys())}"

print("Phase 4 (conversation_router) — import + signature checks passed")

# ── Phase 5: message_handler ─────────────────────────────────────────────────
from app.services.message_handler import (
    handle_message,
    HISTORY_WINDOW,
    MAX_HISTORY_CHARS,
    FALLBACK_REPLY,
)

assert asyncio.iscoroutinefunction(handle_message), "handle_message must be async"
assert HISTORY_WINDOW    == 10,    f"HISTORY_WINDOW should be 10, got {HISTORY_WINDOW}"
assert MAX_HISTORY_CHARS == 5000,  f"MAX_HISTORY_CHARS should be 5000, got {MAX_HISTORY_CHARS}"
assert FALLBACK_REPLY    == "Sorry, something went wrong — please try again.", \
    f"FALLBACK_REPLY mismatch: {FALLBACK_REPLY!r}"

sig = inspect.signature(handle_message)
assert list(sig.parameters.keys()) == ["ctx"], \
    f"handle_message should take only 'ctx', got: {list(sig.parameters.keys())}"

print("Phase 5 (message_handler) — import + structural checks passed")

# ── Cross-module: types flow through all three ────────────────────────────────
from app.services.types import MessageContext, ChannelType
import uuid

# build_web_context produces a valid MessageContext (using a mock User object)
class _MockUser:
    id        = uuid.uuid4()
    tenant_id = uuid.uuid4()
    email     = "test@example.com"

ctx = build_web_context(_MockUser(), "What is the refund policy?", None)
assert isinstance(ctx, MessageContext),     "build_web_context must return MessageContext"
assert ctx.source            == ChannelType.WEB
assert ctx.reset_requested   is False
assert ctx.conversation_id   is None
assert ctx.team_id           is None
assert ctx.external_identity == "test@example.com"

# conversation_id can be pre-set by caller
ctx2 = build_web_context(_MockUser(), "hello", str(uuid.uuid4()))
assert ctx2.conversation_id is not None, "conversation_id should be parsed from string"

print("Cross-module type flow — passed")
print()
print("All Phase 3-5 assertions passed.")
print(f"  RESET_COMMANDS    : {sorted(RESET_COMMANDS)}")
print(f"  HISTORY_WINDOW    : {HISTORY_WINDOW}")
print(f"  MAX_HISTORY_CHARS : {MAX_HISTORY_CHARS}")
print(f"  FALLBACK_REPLY    : {FALLBACK_REPLY!r}")
