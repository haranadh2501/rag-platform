"""Phase 1 verification — types.py import and MessageContext assertions."""
import sys
import uuid

sys.path.insert(0, "C:\\Users\\tush2\\Desktop\\rag-platform\\backend")

from app.services.types import ChannelType, MessageContext

# ── ChannelType ──────────────────────────────────────────────────────────────
assert ChannelType.WEB   == "WEB",   "WEB value mismatch"
assert ChannelType.SLACK == "SLACK", "SLACK value mismatch"
assert isinstance(ChannelType.WEB, str), "ChannelType should be str subclass"

# ── Web MessageContext ────────────────────────────────────────────────────────
ctx_web = MessageContext(
    request_id        = "test-uuid-1234",
    source            = ChannelType.WEB,
    user_id           = uuid.uuid4(),
    tenant_id         = uuid.uuid4(),
    external_identity = "user@example.com",
    team_id           = None,
    raw_query         = "What is the refund policy?",
    reset_requested   = False,
)
assert ctx_web.conversation_id is None,  "Web: conversation_id should default to None"
assert ctx_web._slack_event    == {},    "Web: _slack_event should default to empty dict"
assert ctx_web.team_id         is None,  "Web: team_id should be None"
assert ctx_web.reset_requested is False, "Web: reset_requested should be False"

# ── Slack MessageContext ──────────────────────────────────────────────────────
ctx_slack = MessageContext(
    request_id        = "ev-slack-abc123",
    source            = ChannelType.SLACK,
    user_id           = uuid.uuid4(),
    tenant_id         = uuid.uuid4(),
    external_identity = "U012AB3CD",
    team_id           = "T01234567",
    raw_query         = "hello",
    reset_requested   = False,
    _slack_event      = {"channel": "C01234", "ts": "1234567890.123"},
)
assert ctx_slack.team_id                 == "T01234567", "Slack: team_id mismatch"
assert ctx_slack._slack_event["channel"] == "C01234",   "Slack: _slack_event channel mismatch"
assert ctx_slack._slack_event["ts"]      == "1234567890.123"

# ── Reset flag ────────────────────────────────────────────────────────────────
ctx_reset = MessageContext(
    request_id        = "r1",
    source            = ChannelType.SLACK,
    user_id           = uuid.uuid4(),
    tenant_id         = uuid.uuid4(),
    external_identity = "U999",
    team_id           = "T999",
    raw_query         = "/new",
    reset_requested   = True,
)
assert ctx_reset.reset_requested is True, "Reset: reset_requested should be True"

# ── Conversation ID set after construction ────────────────────────────────────
conv_id = uuid.uuid4()
ctx_web.conversation_id = conv_id
assert ctx_web.conversation_id == conv_id, "conversation_id assignment failed"

print("Phase 1 — all assertions passed")
print(f"  ChannelType members : {[c.value for c in ChannelType]}")
print(f"  Web  ctx.source     : {ctx_web.source!r}")
print(f"  Web  ctx.team_id    : {ctx_web.team_id!r}")
print(f"  Web  ctx.conv_id    : {ctx_web.conversation_id}")
print(f"  Slack ctx.team_id   : {ctx_slack.team_id!r}")
print(f"  Slack ctx.event     : {ctx_slack._slack_event}")
print(f"  Reset ctx flag      : {ctx_reset.reset_requested!r}")
