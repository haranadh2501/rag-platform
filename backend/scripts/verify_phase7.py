"""Phase 7 verification — Web adapter (chat.py) import and structural checks."""
import sys, inspect, asyncio

sys.path.insert(0, "C:\\Users\\tush2\\Desktop\\rag-platform\\backend")

# ── schema ────────────────────────────────────────────────────────────────────
from app.schemas.chat import ChatQueryRequest

req = ChatQueryRequest(query="What is the refund policy?")
assert req.query == "What is the refund policy?"
assert req.conversation_id is None

req2 = ChatQueryRequest(query="hello", conversation_id="abc-123")
assert req2.conversation_id == "abc-123"

# Validation: empty query should fail
from pydantic import ValidationError
try:
    ChatQueryRequest(query="")
    assert False, "Empty query should fail validation"
except ValidationError:
    pass

print("ChatQueryRequest schema — validation checks passed")

# ── chat.py routes ────────────────────────────────────────────────────────────
from app.api.chat import router, chat_query

assert asyncio.iscoroutinefunction(chat_query), "chat_query must be async"

routes = {r.path: r for r in router.routes}
assert "/query"                    in routes, f"Missing /query. Found: {list(routes.keys())}"
assert "/conversations"            in routes, f"Missing /conversations. Found: {list(routes.keys())}"
assert "/conversations/{conversation_id}" in routes, "Missing /conversations/{conversation_id}"

# /query route accepts POST
query_route = routes["/query"]
assert "POST" in query_route.methods, f"Expected POST on /query, got {query_route.methods}"

print("chat.py routes — structure checks passed")

# ── full import chain: chat.py → context_builder → types → conversation_router ──
from app.services.context_builder import build_web_context
from app.services.conversation_router import find_or_create_conversation
from app.services.message_handler import handle_message

# build_web_context with a mock User
import uuid

class _MockUser:
    id        = uuid.uuid4()
    tenant_id = uuid.uuid4()
    email     = "web@example.com"

ctx = build_web_context(_MockUser(), "test query", None)
assert ctx.source.value       == "WEB"
assert ctx.reset_requested    is False
assert ctx.conversation_id    is None
assert ctx.external_identity  == "web@example.com"

# With conversation_id string
conv_str = str(uuid.uuid4())
ctx2 = build_web_context(_MockUser(), "test", conv_str)
assert str(ctx2.conversation_id) == conv_str, "conversation_id string should parse to UUID"

print("Full import chain (chat, context_builder, types, router, handler) -- passed")
print()
print("All Phase 7 assertions passed.")
