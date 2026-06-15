# MODULE_SPEC_M4 — Backend: Slack Adapter & Unified Messaging Integration

**Owner**: Tushar Srivastava | **Track**: Backend | **Branch**: `feature/M4_webhook`

## Role

Implement and maintain Slack integration and support the Unified Messaging architecture.

This module is responsible for:

* Receiving Slack Events API requests
* Verifying Slack requests
* Deduplicating Slack events
* Building a normalized MessageContext
* Resolving tenant information
* Routing conversations through the shared Conversation Router
* Invoking the Unified Message Handler
* Delivering responses back to Slack

This module is **not responsible for retrieval, RAG orchestration, history loading, prompt generation, or LLM interaction**.

 

## Scope

### In Scope (Current Sprint)

* Slack Events API
* Web channel request handling
* WhatsApp webhook receipt (payload parsing + validation only — delivery owned by M12)
* Slack request validation
* MessageContext generation (5 required fields: `source`, `user_id`, `input_message`, `new_chat`, `message_id`)
* Request validation with appropriate error responses
* Event deduplication via `message_id`
* Conversation Router integration
* Unified Message Handler integration (identical for all sources)
* BackgroundTask processing
* Slack message delivery

### Out of Scope (Future Phases)

* MCP integration
* Teams integration
* Telegram integration

 

## Day-by-Day Deliverables

| Day | Deliverable                                  | Done? |
| --- | -------------------------------------------- | ----- |
| 1   | Study Slack Events API and Slack Web API     | ☐     |
| 1   | Scaffold Slack webhook routes                | ☐     |
| 2   | Implement Slack event ingestion              | ☐     |
| 2   | Implement URL verification challenge handler | ☐     |
| 3   | Implement MessageContext creation            | ☐     |
| 3   | Integrate Conversation Router                | ☐     |
| 4   | Add event deduplication support              | ☐     |
| 4   | Integrate Unified Message Handler            | ☐     |
| 5   | Implement Slack HMAC verification            | ☐     |
| 5   | Implement Slack response delivery            | ☐     |
| 6   | Load testing, bug fixes, cleanup             | ☐     |

---

## Files Owned

### Existing

* `backend/app/api/webhooks.py`
* `backend/app/bots/slack.py`

### New Integration Files

* `backend/app/services/context_builder.py`
* `backend/app/services/conversation_router.py`
* `backend/app/services/message_handler.py`

 

# Architecture Responsibilities

## Slack Adapter

Endpoint:

```http
POST /webhooks/slack/events
```

Responsibilities:

* Verify Slack signatures
* Handle URL verification
* Parse Slack events
* Create MessageContext
* Resolve tenant
* Resolve conversation
* Trigger background processing
* Return HTTP 200 immediately

Must NOT:

* Call LLMs
* Perform retrieval
* Load history
* Manage conversation state directly

 

## MessageContext Creation

All incoming requests — regardless of channel — are normalized into:

```python
@dataclass
class MessageContext:
    source: str          # WEB | SLACK | WHATSAPP
    user_id: str         # channel-native identity (JWT sub / Slack user ID / phone number)
    input_message: str   # the text of the query
    new_chat: bool       # True = user wants a fresh conversation
    message_id: str      # unique ID per message (Slack event_id / Twilio MessageSid / generated UUID for Web)
```

Example:

```python
ctx = await build_context(slack_payload)
```

Supported source values:

```python
WEB
SLACK
WHATSAPP
```

> MCP is excluded from the current sprint.

 

## Request Validation

All 5 fields in `MessageContext` are mandatory. Validation runs immediately after parsing the payload, before any processing.

| Field | Valid when | Error response if invalid |
|---|---|---|
| `source` | Non-empty string, one of `WEB`, `SLACK`, `WHATSAPP` | `400 {"error": "source is required or invalid"}` |
| `user_id` | Non-empty string | `400 {"error": "user_id is required"}` |
| `input_message` | Non-empty string | `400 {"error": "input_message is required"}` |
| `new_chat` | Boolean | `400 {"error": "new_chat is required"}` |
| `message_id` | Non-empty string | `400 {"error": "message_id is required"}` |

**On valid fields:** return HTTP 200 immediately and hand off to the Unified Message Handler.

**On missing or invalid fields:** return the appropriate error response above and stop — nothing downstream runs.

> **Webhook channels (Slack, WhatsApp):** Returning a non-200 to Slack or Twilio triggers a retry. If validation fails for a webhook request, return `200` to prevent retries AND send an error message back to the user via the channel API (e.g. `chat.postMessage` for Slack). Web callers receive the standard `400` directly.

Example:

```python
ctx = await build_context(payload)
if not validate_context(ctx):
    if ctx.source in ("SLACK", "WHATSAPP"):
        await deliver_error(ctx, "Missing required fields.")
        return Response(status_code=200)
    raise HTTPException(status_code=400, detail="Missing required fields.")
```

 

## Event Deduplication

Slack retries events if acknowledgements are delayed. Deduplication uses `message_id` from the `MessageContext` and must run before any DB or handler work.

Example:

```python
if await is_duplicate(ctx.message_id):
    return Response(status_code=200)
```

Source of `message_id` per channel:

| Channel | Source of `message_id` |
|---|---|
| Slack | `event.event_id` from the Slack payload |
| WhatsApp | Twilio `MessageSid` header |
| Web | UUID generated by the adapter on receipt |

 

## Conversation Router Integration

Slack handlers must not contain conversation lifecycle logic.

Example:

```python
ctx.conversation_id = (
    await find_or_create_conversation(ctx)
)
```

Supported actions:

* Existing conversation lookup
* New conversation creation
* `/new`
* `/restart`
* `/clear`

 

## Unified Message Handler Integration

Business processing is delegated to:

```python
services/message_handler.py
```

The handler is **identical for all sources** — no channel-specific branching inside it. The channel adapter (Slack, Web, WhatsApp) is responsible for building the `MessageContext`; after that the handler takes over uniformly.

```python
async def handle_message(ctx: MessageContext) -> None:
    # 1. If new_chat, create a fresh conversation and reply confirmation
    # 2. Load conversation history for existing conversation
    # 3. Call n8n with input_message + history
    # 4. Save user message + assistant response (one transaction)
    # 5. Deliver reply via channel-specific delivery function
```

Each adapter invokes it the same way:

```python
background_tasks.add_task(handle_message, ctx)
```

 

## Slack Event Handler Example

```python
@router.post("/slack/events")
async def slack_events(
    request: Request,
    background_tasks: BackgroundTasks
):
    # Read raw bytes once; verify HMAC against bytes before parsing
    body = await request.body()
    verify_slack_signature(request.headers, body)

    payload = json.loads(body)

    if payload["type"] == "url_verification":
        return {"challenge": payload["challenge"]}

    # Build and validate MessageContext — all 5 fields required
    ctx = await build_context(payload)
    if not validate_context(ctx):
        await deliver_error(ctx, "Missing required fields.")
        return Response(status_code=200)   # prevent Slack retry

    # Dedup on message_id before any processing
    if await is_duplicate(ctx.message_id):
        return Response(status_code=200)

    # ACK immediately; process in background
    background_tasks.add_task(handle_message, ctx)
    return Response(status_code=200)
```

 

## Slack Response Delivery

Responses are sent through:

```python
chat.postMessage
```

Requirements:

* Reply in thread
* Preserve conversation context
* Handle Slack API failures gracefully
* Log delivery errors

 

## Acceptance Criteria

* [ ] Slack webhook validates HMAC signatures against raw request body bytes
* [ ] URL verification challenge succeeds
* [ ] All 5 required fields (`source`, `user_id`, `input_message`, `new_chat`, `message_id`) are present → HTTP 200 returned immediately
* [ ] Any missing or invalid field → webhook channels return 200 + error message to user; Web returns 400 with field-level detail
* [ ] Slack events generate valid `MessageContext` objects
* [ ] Duplicate events (same `message_id`) are ignored safely — no double processing
* [ ] Deduplication check runs after validation, before any handler or DB work
* [ ] `new_chat=True` creates a fresh conversation and returns confirmation without calling n8n
* [ ] `new_chat=False` loads existing conversation history before calling n8n
* [ ] Unified Message Handler is called identically for all sources (no per-channel branching inside the handler)
* [ ] Slack responses are delivered via `chat.postMessage` in thread
* [ ] BackgroundTasks execute successfully and log failures with fallback reply to user
* [ ] Slack webhook returns HTTP 200 within Slack's 3-second window
* [ ] Webhook endpoint passes load testing

 

## Future Expansion

The architecture should support future channel adapters with minimal changes:

* WhatsApp
* MCP

Future channels should reuse:

* MessageContext
* Conversation Router
* Unified Message Handler

without introducing channel-specific business logic.
