# Microsoft Teams Bot (M14)

Mirrors the WhatsApp bot (M12) for Microsoft Teams using the **Azure Bot Framework**.
Inbound activities hit `POST /webhooks/teams`; replies are sent proactively via the
Bot Connector REST API — the same ACK-fast-then-reply pattern the WhatsApp bot uses
with Twilio.

## How it works

```
Teams client → Azure Bot Service → POST /webhooks/teams (Activity JSON)
  → verify Bot Framework JWT (skipped when APP_ENV=development)
  → dedup on activity id (processed_requests)
  → ACK 200 fast; BackgroundTask:
       resolve identity (channelData.tenant.id → teams_tenant_map → tenant)
       → find/create conversation (channel="teams")
       → file? download + validate + n8n ephemeral ingest
       → text? "🤔 Thinking..." → message_service.process_message
       → teams.post_reply(serviceUrl, conversationId, answer, sources)
```

Reset commands `/new`, `/reset`, `/clear` wipe the Teams conversation, same as WhatsApp/Slack.

## Setup

1. **Create an Azure Bot** (Azure Portal → *Azure Bot* resource). Note the
   **Microsoft App ID** and create a **client secret**.
2. Set the **Messaging endpoint** to `https://<public-host>/webhooks/teams`.
3. Enable the **Microsoft Teams** channel on the bot.
4. Fill in `.env`:
   ```
   MICROSOFT_APP_ID=<app id>
   MICROSOFT_APP_PASSWORD=<client secret>
   MICROSOFT_APP_TENANT_ID=          # single-tenant bots only; blank = multi-tenant
   ```
5. **Register the org → tenant mapping** so messages resolve to a platform tenant.
   The Azure AD tenant id arrives as `channelData.tenant.id`:
   ```sql
   INSERT INTO teams_tenant_map (teams_tenant_id, tenant_id)
   VALUES ('<azure-ad-tenant-guid>', '<platform-tenant-uuid>');
   ```
   (Or use `app.bots.teams_map.register_teams_tenant`.) First message from each
   Teams user auto-provisions a `teams-no-login` user in that tenant.

## Sideloading the app

`manifest.json` is a minimal Teams app manifest. Replace `REPLACE_WITH_MICROSOFT_APP_ID`
with your Microsoft App ID, add `color.png` (192×192) and `outline.png` (32×32) icons,
zip the three files, and upload via Teams → *Apps* → *Manage your apps* → *Upload a custom app*.

## Local testing

Use the [Bot Framework Emulator](https://github.com/microsoft/BotFramework-Emulator)
pointed at `http://localhost:8000/webhooks/teams`, or run the pytest suite:

```bash
docker compose run --rm -v "$PWD":/repo -w /repo backend pytest tests/test_m14_teams.py -v
```
