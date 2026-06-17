"""Phase 6 verification — Slack adapter import and structural checks."""
import sys, inspect, asyncio

sys.path.insert(0, "C:\\Users\\tush2\\Desktop\\rag-platform\\backend")

# ── slack.py ─────────────────────────────────────────────────────────────────
from app.bots.slack import post_reply, post_text, _build_blocks

assert asyncio.iscoroutinefunction(post_reply),  "post_reply must be async"
assert asyncio.iscoroutinefunction(post_text),   "post_text must be async"
assert callable(_build_blocks),                   "_build_blocks must be callable"

# Signature checks
sig = inspect.signature(post_reply)
assert list(sig.parameters.keys()) == ["ctx", "answer", "sources"], \
    f"post_reply params: {list(sig.parameters.keys())}"

sig = inspect.signature(post_text)
assert list(sig.parameters.keys()) == ["channel", "thread_ts", "text"], \
    f"post_text params: {list(sig.parameters.keys())}"

# Block kit structure — answer only
blocks = _build_blocks("The answer is 42.", [])
assert len(blocks) == 1, "No sources → 1 block"
assert blocks[0]["type"] == "section"
assert blocks[0]["text"]["type"] == "mrkdwn"

# Block kit structure — with sources
sources = [
    {"title": "Manual", "page_number": 5, "score": 0.9},
    {"title": "FAQ", "score": 0.8},
    {"title": "Guide", "page_number": 2},
]
blocks = _build_blocks("The answer is 42.", sources)
assert len(blocks) == 2, "Sources present → 2 blocks (section + context)"
assert blocks[1]["type"] == "context"
context_text = blocks[1]["elements"][0]["text"]
assert "Manual" in context_text and "p.5" in context_text, "Source title+page not in context block"
assert "FAQ" in context_text,   "FAQ source missing"
assert "Guide" in context_text, "Guide source missing"

# Only caps at 3 sources even if more provided
sources_many = [{"title": f"Doc{i}", "score": 0.5} for i in range(10)]
blocks_many = _build_blocks("answer", sources_many)
assert blocks_many[1]["elements"][0]["text"].count("•") == 3, "Should cap at 3 source bullets"

print("slack.py (post_reply, post_text, _build_blocks) — all checks passed")

# ── webhooks.py ──────────────────────────────────────────────────────────────
from app.api.webhooks import slack_events, _verify_slack_signature, router

assert asyncio.iscoroutinefunction(slack_events), "slack_events must be async"
assert callable(_verify_slack_signature),          "_verify_slack_signature must be callable"

# Check router has the expected routes
routes = {r.path for r in router.routes}
assert "/slack/events" in routes,          f"Missing /slack/events route. Found: {routes}"
assert "/whatsapp" in routes,              f"Missing /whatsapp route. Found: {routes}"
assert "/n8n/ingestion-status" in routes,  f"Missing /n8n/ingestion-status route. Found: {routes}"

# Verify _verify_slack_signature rejects stale timestamps
import time as _time
import hashlib as _hashlib
import hmac as _hmac
from fastapi import HTTPException

# Stale timestamp
stale_ts  = str(int(_time.time()) - 400)
stale_sig = "v0=fakesig"
try:
    _verify_slack_signature(
        {"x-slack-request-timestamp": stale_ts, "x-slack-signature": stale_sig},
        b"body",
    )
    assert False, "Should have raised HTTPException for stale timestamp"
except HTTPException as exc:
    assert exc.status_code == 403
    assert "timestamp" in exc.detail.lower(), f"Expected 'timestamp' in detail: {exc.detail}"

# Invalid signature (fresh timestamp)
fresh_ts = str(int(_time.time()))
try:
    _verify_slack_signature(
        {"x-slack-request-timestamp": fresh_ts, "x-slack-signature": "v0=badhex"},
        b"body",
    )
    assert False, "Should have raised HTTPException for bad signature"
except HTTPException as exc:
    assert exc.status_code == 403
    assert "signature" in exc.detail.lower(), f"Expected 'signature' in detail: {exc.detail}"

print("webhooks.py — import, route, and HMAC checks passed")
print()
print("All Phase 6 assertions passed.")
