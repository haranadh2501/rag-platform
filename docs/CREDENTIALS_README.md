# Credentials Setup — Railway + n8n

This guide covers every credential and environment variable needed to run the
ingestion pipeline on Railway.

---

## 1. Railway — n8n Service Variables

Go to: **Railway dashboard → your project → n8n service → Variables tab**

Add each variable with the **+ New Variable** button.

### Required — Pipeline will not work without these

| Variable | Value | Where to get it |
|---|---|---|
| `VOYAGE_API_KEY` | `pa-...` | https://www.voyageai.com → Dashboard → API Keys |
| `OPENAI_API_KEY` | `sk-...` | https://platform.openai.com → API Keys |
| `N8N_CALLBACK_TOKEN` | any random string e.g. `rag-token-2025` | make one up — must match backend |
| `N8N_BLOCK_ENV_ACCESS_IN_NODE` | `false` | set exactly this value |
| `NODE_FUNCTION_ALLOW_EXTERNAL` | `pdf-parse,mammoth` | set exactly this value |

### Required — Postgres (Neon)

| Variable | Value | Where to get it |
|---|---|---|
| `DB_TYPE` | `postgresdb` | set exactly this value |
| `DB_POSTGRESDB_HOST` | `ep-xxxx.us-east-2.aws.neon.tech` | Neon dashboard → Connection Details → Host |
| `DB_POSTGRESDB_DATABASE` | `ragplatform` | Neon dashboard → database name |
| `DB_POSTGRESDB_USER` | `raguser` | Neon dashboard → Connection Details → User |
| `DB_POSTGRESDB_PASSWORD` | `...` | Neon dashboard → Connection Details → Password |
| `DB_POSTGRESDB_PORT` | `5432` | fixed |
| `DB_POSTGRESDB_SSL` | `true` | required for Neon |

### Optional — only needed if backend is also on Railway

| Variable | Value |
|---|---|
| `BACKEND_BASE_URL` | `https://your-backend-service.up.railway.app` |

---

## 2. n8n Credentials (inside n8n UI)

Go to: **n8n UI → Overview → Credentials tab → Add credential**

### Postgres (for Insert Chunk node)

| Field | Value |
|---|---|
| Credential name | `ragplatform-pg` |
| Host | your Neon host e.g. `ep-xxxx.us-east-2.aws.neon.tech` |
| Database | `ragplatform` |
| User | from Neon Connection Details |
| Password | from Neon Connection Details |
| Port | `5432` |
| SSL | Enable → set to **Require** |

### Voyage AI (for Voyage Embed node)

| Field | Value |
|---|---|
| Credential type | `Header Auth` |
| Credential name | `VoyageAuth` |
| Header Name | `Authorization` |
| Header Value | `Bearer <your VOYAGE_API_KEY>` |

### OpenAI (for OpenAI Vision OCR node — scanned PDFs only)

| Field | Value |
|---|---|
| Credential type | `Header Auth` |
| Credential name | `OpenAIAuth` |
| Header Name | `Authorization` |
| Header Value | `Bearer <your OPENAI_API_KEY>` |

---

## 3. n8n Variables (inside n8n UI)

Go to: **n8n UI → Overview → Variables tab → Add Variable**

| Name | Value |
|---|---|
| `BACKEND_BASE_URL` | `https://your-backend.up.railway.app` (or `http://backend:8000` if on same Docker network) |
| `N8N_CALLBACK_TOKEN` | same value as the Railway env var above |

These are used by the **Callback: Success** and **Callback: Failed** nodes via `$vars.BACKEND_BASE_URL` and `$vars.N8N_CALLBACK_TOKEN`.

---

## 4. Assign credentials to workflow nodes

After creating the credentials above, open the ingestion workflow and assign them:

| Node name | Credential to assign |
|---|---|
| **Voyage Embed** | `VoyageAuth` |
| **Insert Chunk** | `ragplatform-pg` |
| **OpenAI Vision OCR** | `OpenAIAuth` |

Click each node → **Credential** dropdown → select the matching credential.

---

## 5. Activate the workflow

Top-right of the workflow editor → toggle from **Inactive** to **Active** → Save.

The production webhook URL will then be:
```
https://n8n-production-c637.up.railway.app/webhook/ingest
```

---

## 6. Test the pipeline

```bash
# URL ingestion (no file needed)
curl -X POST https://n8n-production-c637.up.railway.app/webhook/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "tenant_id":   "11111111-1111-1111-1111-111111111111",
    "source_type": "url",
    "source_url":  "https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
    "title":       "RAG Wikipedia test"
  }'
```

Verify in Neon SQL editor:
```sql
SELECT chunk_index, token_count, left(content, 80)
FROM document_chunks
WHERE document_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
ORDER BY chunk_index;
```

Check execution logs: **n8n UI → Executions tab**.
