# SPEC_M12 — WhatsApp Bot Integration

**Owner**: M12 | **Branch**: `feat/whatsapp-bot` (based on `feature/M4_webhook`)

## Context

M4 (Tushar) has already built a unified message service for Slack in `feature/M4_webhook`.
The WhatsApp integration MUST follow the exact same architecture pattern.

### Existing Code You Must Reuse (DO NOT REWRITE)

| File | What It Does |
|------|-------------|
| `backend/app/services/types.py` | `MessageContext` dataclass — add `whatsapp_from` field |
| `backend/app/services/message_service.py` | Unified handler — add WhatsApp identity resolution path |
| `backend/app/services/pipeline_client.py` | Calls the RAG pipeline (mock or real n8n) |
| `backend/app/core/config.py` | Already has `TWILIO_*` settings |
| `backend/app/models/models.py` | Already has `WhatsAppTenantMap` ORM model |
| `backend/app/services/file_validator.py` | Already has MIME + magic bytes validation |
| `backend/app/services/n8n_client.py` | Has `retrieve()` and mock mode |
| `backend/alembic/versions/0002_m4_messaging.py` | Already adds `phone_number` to users table |

### Architecture Pattern (from M4 Slack — follow exactly)

```
Twilio webhook POST
  → webhooks.py: verify signature → parse form → dedup (MessageSid) → build MessageContext
    → BackgroundTasks: message_service.process_message(ctx, db)
      → _resolve_identity(): phone → whatsapp_tenant_map → tenant_id; phone → users.phone_number → user_id
      → _find_or_create_conversation(): one per (user_id, "whatsapp")
      → _load_history(): last 10 messages
      → pipeline_client.call_pipeline(): get answer + sources
      → whatsapp.post_reply(): send via Twilio REST API
      → _save_messages(): persist user + assistant messages
  → Return empty TwiML ACK (200) immediately
```

---

## Implementation Steps (6 tasks, in order)

### Step 1: Extend MessageContext for WhatsApp

**File**: `backend/app/services/types.py`

Add one field to the existing `MessageContext` dataclass:
```python
whatsapp_from: str | None = None     # Twilio "From" number (e.g. "whatsapp:+919876543210")
```

### Step 2: Implement tenant_map.py — DB Queries

**File**: `backend/app/bots/tenant_map.py`

Replace the stub with real async SQLAlchemy queries:

```python
async def get_tenant_for_phone(phone_number: str, db: AsyncSession) -> Optional[UUID]:
    """Query whatsapp_tenant_map table. Returns tenant_id or None."""
    result = await db.execute(
        text("SELECT tenant_id FROM whatsapp_tenant_map WHERE phone_number = :phone"),
        {"phone": phone_number}
    )
    row = result.first()
    return row.tenant_id if row else None

async def register_phone_for_tenant(phone_number: str, tenant_id: UUID, db: AsyncSession) -> None:
    """INSERT INTO whatsapp_tenant_map."""
    await db.execute(
        text("INSERT INTO whatsapp_tenant_map (phone_number, tenant_id) VALUES (:phone, :tid) ON CONFLICT (phone_number) DO NOTHING"),
        {"phone": phone_number, "tid": tenant_id}
    )
    await db.commit()
```

### Step 3: Implement whatsapp.py — Twilio Delivery

**File**: `backend/app/bots/whatsapp.py`

Replace the stub. Two delivery functions:

```python
async def post_reply(to: str, answer: str, sources: list) -> None:
    """Send answer + sources via Twilio REST API (not TwiML)."""
    # Format: answer text + "\n\n📚 Sources: Title p.N, Title p.N"
    # Truncate to 1600 chars (WhatsApp limit)
    # Use twilio.rest.Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).messages.create()
    # from_=settings.TWILIO_WHATSAPP_NUMBER, to=to, body=formatted_text

async def post_text(to: str, text: str) -> None:
    """Send a plain text message (for "🤔 Thinking..." or error messages)."""
```

Keep `twiml_reply()` as a utility for the immediate ACK response.

### Step 4: Extend message_service.py — WhatsApp Identity Resolution

**File**: `backend/app/services/message_service.py`

In `_resolve_identity()`, add the WhatsApp path AFTER the existing Slack path:

```python
if ctx.source == "whatsapp":
    # 1. Look up tenant via whatsapp_tenant_map
    row = (await db.execute(text("""
        SELECT m.tenant_id, u.id AS user_id
        FROM whatsapp_tenant_map m
        LEFT JOIN users u ON u.tenant_id = m.tenant_id AND u.phone_number = :phone
        WHERE m.phone_number = :phone
    """), {"phone": ctx.whatsapp_from})).first()
    
    if row is None:
        raise IdentityResolutionError(f"Phone {ctx.whatsapp_from} not in whatsapp_tenant_map")
    
    ctx.tenant_id = row.tenant_id
    
    if row.user_id is None:
        # Auto-create a "whatsapp" user for this phone in the tenant
        ctx.user_id = (await db.execute(text("""
            INSERT INTO users (tenant_id, email, hashed_password, role, phone_number)
            VALUES (:tid, :email, 'whatsapp-no-login', 'user', :phone)
            RETURNING id
        """), {
            "tid": ctx.tenant_id,
            "email": f"wa-{ctx.whatsapp_from.replace('+','').replace(':','')}@whatsapp.local",
            "phone": ctx.whatsapp_from,
        })).scalar_one()
        await db.commit()
    else:
        ctx.user_id = row.user_id
```

Also add WhatsApp delivery in `process_message()` after the Slack delivery block:

```python
if ctx.source == "whatsapp":
    await whatsapp.post_reply(ctx.whatsapp_from, answer, sources)
```

### Step 5: Implement WhatsApp Webhook Route

**File**: `backend/app/api/webhooks.py`

Replace the WhatsApp stub. Follow the EXACT same pattern as the Slack route:

```python
@router.post("/whatsapp", summary="Twilio WhatsApp incoming message")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    # 1. Read raw body for signature verification
    raw = await request.body()
    
    # 2. Verify Twilio signature (skip in debug mode)
    if not settings.APP_ENV == "development":
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        form_data = dict(await request.form())
        url = str(request.url)
        signature = request.headers.get("X-Twilio-Signature", "")
        if not validator.validate(url, form_data, signature):
            raise HTTPException(403, "Invalid Twilio signature")
    
    # 3. Parse form data
    form = await request.form()
    message_body = form.get("Body", "").strip()
    from_number = form.get("From", "")        # "whatsapp:+919876543210"
    message_sid = form.get("MessageSid", "")   # Dedup key
    
    # 4. Handle media attachments (Day 3 — ephemeral upload)
    num_media = int(form.get("NumMedia", "0"))
    # TODO: Step 6 handles this
    
    # 5. Dedup on MessageSid (same pattern as Slack event_id)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("INSERT INTO processed_requests (request_id) VALUES (:rid) ON CONFLICT DO NOTHING"),
            {"rid": message_sid}
        )
        await db.commit()
        if result.rowcount == 0:
            return Response(content=twiml_ack(), media_type="application/xml")
    
    # 6. Build MessageContext
    if not message_body and num_media == 0:
        return Response(content=twiml_ack(), media_type="application/xml")
    
    # 7. Fire background task
    background_tasks.add_task(_process_whatsapp_message, message_sid, from_number, message_body)
    
    # 8. ACK immediately with empty TwiML
    return Response(content=twiml_ack(), media_type="application/xml")


def twiml_ack() -> str:
    """Empty TwiML response — we reply via Twilio REST API in the background task."""
    return '<?xml version="1.0"?><Response></Response>'


async def _process_whatsapp_message(message_sid: str, from_number: str, query: str) -> None:
    """Background task — runs Steps 2-8 with its own DB session."""
    async with AsyncSessionLocal() as db:
        ctx = MessageContext(
            request_id=message_sid,
            source="whatsapp",
            query=query,
            whatsapp_from=from_number,
        )
        try:
            # Send "thinking" indicator
            await whatsapp.post_text(from_number, "🤔 Thinking...")
            await message_service.process_message(ctx, db)
        except IdentityResolutionError:
            await whatsapp.post_text(from_number, 
                "This number isn't registered. Please ask your admin to add you.")
        except pipeline_client.PipelineError:
            await whatsapp.post_text(from_number, message_service.FALLBACK_MESSAGE)
        except Exception:
            logger.exception("WhatsApp processing failed (sid=%s)", message_sid)
```

### Step 6: Ephemeral File Upload (Day 3)

**File**: `backend/app/api/webhooks.py` (extend the webhook handler)

When `NumMedia > 0`:
1. Download media from `MediaUrl0` using httpx with Twilio basic auth
2. Validate with `file_validator.validate_upload(max_bytes=settings.MAX_WHATSAPP_UPLOAD_BYTES)`
3. POST to `settings.N8N_EPHEMERAL_INGEST_WEBHOOK_URL` with `conversation_id`
4. Reply: "Indexed ✓ — ask me anything about this file for the next 60 minutes."

```python
async def _handle_whatsapp_media(form: dict, from_number: str, conversation_id: UUID) -> None:
    media_url = form.get("MediaUrl0")
    media_type = form.get("MediaContentType0", "")
    
    # Download with Twilio auth
    async with httpx.AsyncClient() as client:
        resp = await client.get(media_url, auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN))
        content = resp.content
    
    # Validate
    validated = file_validator.validate_upload(
        filename=f"whatsapp_upload.{media_type.split('/')[-1]}",
        content=content,
        declared_mime=media_type,
        max_bytes=settings.MAX_WHATSAPP_UPLOAD_BYTES,
    )
    
    # Send to n8n ephemeral ingestion
    await n8n_client.ingest_ephemeral(content, conversation_id, validated.mime_type)
    await whatsapp.post_text(from_number, "Indexed ✓ — ask me anything about this file for the next 60 minutes.")
```

---

## Tests Required

**File**: `tests/test_m12_whatsapp.py`

1. **test_whatsapp_text_flow** — POST to `/webhooks/whatsapp` with form data → gets 200 + empty TwiML
2. **test_whatsapp_dedup** — Same MessageSid twice → second is ignored
3. **test_whatsapp_unknown_phone** — Unregistered number → "not registered" reply
4. **test_whatsapp_reset** — Send "/new" → conversation reset
5. **test_tenant_map_lookup** — get_tenant_for_phone with seeded data
6. **test_tenant_map_register** — register_phone_for_tenant + verify
7. **test_twilio_signature_validation** — Invalid signature → 403 (when not in dev mode)
8. **test_twiml_truncation** — Messages > 1600 chars are truncated

---

## Config Already Available (no changes needed)

```python
# backend/app/core/config.py — already has:
TWILIO_ACCOUNT_SID: str = ""
TWILIO_AUTH_TOKEN: str = ""
TWILIO_WHATSAPP_NUMBER: str = "whatsapp:+14155238886"
MAX_WHATSAPP_UPLOAD_BYTES: int = 10_485_760      # 10 MB
N8N_EPHEMERAL_INGEST_WEBHOOK_URL: str = "http://localhost:5678/webhook/ingest-ephemeral"
```

## Dependencies Already in requirements.txt

```
twilio==9.1.1
httpx==0.27.0
```

---

## Acceptance Criteria

- [ ] POST form data to `/webhooks/whatsapp` → 200 + empty TwiML ACK
- [ ] Background task resolves phone → tenant → user → conversation
- [ ] Unknown phone → friendly "not registered" message via Twilio API
- [ ] Answer + sources formatted and sent via Twilio REST API (not TwiML)
- [ ] Messages > 1600 chars truncated
- [ ] MessageSid dedup prevents double processing
- [ ] Conversation history (last 10 messages) included in pipeline call
- [ ] `/new` or `/reset` creates fresh conversation
- [ ] Twilio signature validation enforced (skip in development mode)
- [ ] Media attachments: download → validate → ephemeral ingest → confirm
- [ ] All tests pass: `pytest tests/test_m12_whatsapp.py -v`

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `backend/app/services/types.py` | ADD `whatsapp_from` field |
| `backend/app/bots/tenant_map.py` | REWRITE — real DB queries |
| `backend/app/bots/whatsapp.py` | REWRITE — Twilio REST delivery |
| `backend/app/services/message_service.py` | EXTEND — WhatsApp identity + delivery |
| `backend/app/api/webhooks.py` | REWRITE whatsapp route — full implementation |
| `tests/test_m12_whatsapp.py` | CREATE — 8 tests |

## Files to NOT Touch

- `backend/app/core/config.py` (M2-owned, already has what we need)
- `backend/app/services/pipeline_client.py` (M4-owned, works as-is)
- `backend/app/models/models.py` (shared, already has WhatsAppTenantMap)
- `backend/alembic/versions/0002_m4_messaging.py` (M4-owned, already adds phone_number)
