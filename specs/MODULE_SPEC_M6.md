# MODULE_SPEC_M6 — n8n: Retrieval + Generation Pipeline

**Owner**: Member 6 | **Track**: n8n | **Branch**: `feat/n8n-retrieve`
**⚠️ CRITICAL PATH** — Must be complete by end of Day 3.

## Role
Build the RAG retrieval n8n workflow: webhook → embed query → pgvector search → LLM call → citations → response.

## Day-by-Day Deliverables
| Day | Deliverable | Done? |
|---|---|---|
| 1 | Read n8n contract spec. Set up n8n alongside M5. Understand pgvector query. | ☐ |
| 2 | Webhook trigger + OpenAI `/embeddings` HTTP Request node | ☐ |
| 2 | Postgres pgvector cosine similarity query node | ☐ |
| 3 | Context assembly Code node | ☐ |
| 3 | System prompt engineering (customer support persona) | ☐ |
| 3 | OpenAI `/chat/completions` HTTP Request node | ☐ |
| 3 | Source citation extraction Code node | ☐ |
| 4 | Follow-up question generation (add to LLM prompt) | ☐ |
| 4 | Conversation history inclusion in context | ☐ |
| 5 | Prompt tuning — improve answer quality and citation format | ☐ |
| 6 | Export `n8n-workflows/retrieval-pipeline.json` | ☐ |

## Files Owned
- `n8n-workflows/retrieval-pipeline.json`

## Workflow Architecture
```
[Webhook Trigger] ← POST /webhook/retrieve
  {query, tenant_id, conversation_history, max_chunks}
        │
        ▼
[HTTP Request: OpenAI /embeddings]
  POST https://api.openai.com/v1/embeddings
  {input: query, model: "text-embedding-3-small"}
        │
        ▼
[Postgres: pgvector similarity search]
  SELECT id, content, document_id, page_number,
         1 - (embedding <=> $query_embedding::vector) AS score
  FROM document_chunks
  WHERE tenant_id = $tenant_id
  ORDER BY embedding <=> $query_embedding::vector
  LIMIT $max_chunks
        │
        ▼
[Code: Build Prompt]
  context = top chunks formatted as numbered list
  history = last 10 conversation_history messages
  system_prompt = (see below)
        │
        ▼
[HTTP Request: OpenAI /chat/completions]
  POST https://api.openai.com/v1/chat/completions
  {model: "gpt-4o-mini", messages: [system, ...history, user_query], max_tokens: 1500}
        │
        ▼
[Code: Format Response]
  Extract answer text
  Map citations: match answer to source chunks
  Generate follow-up questions (in same LLM call)
        │
        ▼
[Respond to Webhook] → N8nRetrieveResponse JSON
```

## System Prompt
```
You are a helpful customer support assistant. Answer questions ONLY using
the provided context documents. If the answer is not in the context,
say "I don't have enough information in the uploaded documents to answer this question."

Always cite your sources by referencing the document title and page number.
Format citations as [Document Title, p.N].

After your answer, generate exactly 3 follow-up questions the user might ask.
Format them as JSON: {"follow_up_questions": ["q1", "q2", "q3"]}
```

## Response Schema
```json
{
  "answer": "To reset the device, press and hold the power button for 5 seconds [Manual, p.12].",
  "sources": [
    {"document_id": "uuid", "title": "Product Manual", "chunk_text": "...", "page_number": 12, "score": 0.94}
  ],
  "follow_up_questions": ["What if the reset fails?", "Where is the reset button?", "How long does reset take?"],
  "metadata": {"model": "gpt-4o-mini", "retrieval_time_ms": 1200, "chunks_retrieved": 5}
}
```

## Acceptance Criteria
- [ ] Query → embedded → pgvector search returns relevant chunks (test with 10 queries)
- [ ] LLM answer is grounded (does not hallucinate beyond context)
- [ ] Citations mapped correctly to source chunks
- [ ] 3 follow-up questions generated per response
- [ ] Conversation history included in LLM context
- [ ] `tenant_id` filter applied — cross-tenant leakage = 0
- [ ] Export `n8n-workflows/retrieval-pipeline.json` committed to repo

---

## [LOCKED] Locked Scope Update (M1 / 29-May)

**Agentic loop**: The retrieval workflow uses n8n's **AI Agent node** with these tools:
1. `search_knowledge_base` -- Voyage embed -> pgvector kNN(top 20) -> Voyage rerank -> top 5 chunks
2. `search_ephemeral` -- same as above but on `ephemeral_chunks` (filter by `conversation_id`)
3. `ask_clarifying_question` -- returns `requires_clarification=true` early
4. `web_lookup` -- optional, per-tenant opt-in

**Models** (locked):
- Generation: **DeepSeek V4 Flash** via OpenAI-compatible base URL `https://api.deepseek.com`
- Self-check: **Gemini 3.5 Flash** -- returns 0--1 faithfulness score
- Fallback: if faithfulness < 0.7 -> retry once with **DeepSeek V4 Pro**

**Output contract** (must match `specs/openapi.yaml` `ChatQueryResponse`):
```json
{
  "answer": "...",
  "sources": [...],
  "follow_up_questions": [...],
  "faithfulness": 0.92,
  "requires_clarification": false,
  "metadata": { "model": "deepseek-v4-flash", ... }
}
```

See [`n8n-workflows/retrieval-pipeline.json`](../n8n-workflows/retrieval-pipeline.json) for the scaffold M1 committed.


---

## [ADDED] Ephemeral Retrieval & Purge (separate workflows)

> Added to complete the WhatsApp/chat **session loop**: a user uploads a document
> (ingested by M5's `ingest-ephemeral.json` into `ephemeral_chunks`), asks
> questions scoped to that session, and the data is wiped on session end or TTL.
> **Owner: M6.** ⚠️ **Deviation flag for M1:** the locked design models ephemeral
> search as a `search_ephemeral` *tool* inside the unified `/webhook/retrieve`
> (`include_ephemeral`). These ship as **two standalone workflows** instead — a
> deliberate, user-approved lean v1. To be unified into the agentic loop later;
> until then the backend `n8n_client.retrieve()` (which only targets
> `/webhook/retrieve`) must be extended (M3) to call these.

### New files (owner M6)
- `n8n-workflows/retrieval-ephemeral.json`
- `n8n-workflows/purge-ephemeral.json`

Reuses the **existing `ephemeral_chunks` table** (no new table) and the proven
error-handling pattern from `ingest-ephemeral.json` (per-node
`onError:"continueErrorOutput"` → single `Format Error` classifier →
`Respond (failure)` with `responseCode = {{ $json.statusCode }}`; 422 validation /
5xx runtime).

### v1 scope decision
Lean, fully-working: `embed → pgvector kNN → Voyage rerank → DeepSeek answer`.
**Gemini self-check + DeepSeek Pro fallback are OUT for v1** (the response still
carries `faithfulness: null` for forward-compat). v2 insertion point: between
`Generate (DeepSeek)` and `Format response`, add Gemini `gemini-3.5-flash`
self-check → `IF faithfulness < 0.7` → DeepSeek `deepseek-v4-pro` retry.

### Contract — `POST /webhook/retrieve-ephemeral`
Request:
```json
{
  "query": "What is the refund window?",
  "tenant_id": "uuid",
  "conversation_id": "uuid",
  "max_chunks": 5,
  "conversation_history": [{ "role": "user", "content": "..." }]
}
```
Response:
```json
{
  "answer": "... [1] ...",
  "sources": [{ "chunk_text": "...", "source_name": "refund-policy.txt", "chunk_index": 0, "score": 0.94 }],
  "follow_up_questions": ["...", "...", "..."],
  "faithfulness": null,
  "requires_clarification": false,
  "conversation_id": "uuid",
  "metadata": { "model": "deepseek-v4-flash", "chunks_retrieved": 3 }
}
```
Empty session (no chunks found for this `conversation_id`) returns HTTP 200 with a
graceful `answer` ("I couldn't find any documents in this session…") and
`sources: []` — no DeepSeek call is made.

pgvector kNN (note `tenant_id` **and** `conversation_id` **and** `expires_at` filter):
```sql
SELECT id, content, source_name, chunk_index, metadata,
       1 - (embedding <=> $1::vector) AS score
FROM ephemeral_chunks
WHERE tenant_id = $2 AND conversation_id = $3 AND expires_at > NOW()
ORDER BY embedding <=> $1::vector
LIMIT $4;
```

### Contract — `POST /webhook/purge-ephemeral` (session-end signal)
Request: `{ "conversation_id": "uuid", "tenant_id": "uuid", "token": "<N8N_PURGE_TOKEN?>" }`
Response: `{ "status": "purged", "conversation_id": "uuid", "deleted_count": 3 }`
(`deleted_count: 0` is a valid, idempotent success.)
```sql
DELETE FROM ephemeral_chunks
WHERE tenant_id = $1 AND conversation_id = $2
RETURNING id;
```
`tenant_id` in the WHERE is **mandatory** (cross-tenant purge defense). This is an
**additional** path; the hourly `cleanup_expired_ephemeral_chunks()` TTL cron stays
as the lifetime safety net. Destructive endpoint — enable the shared-secret
`token` before exposing the webhook beyond localhost.

### Acceptance criteria
- [ ] Retrieve returns grounded, cited answers from the session's uploaded docs
- [ ] Every retrieval SQL filters `tenant_id` + `conversation_id` + `expires_at > NOW()`
- [ ] Cross-tenant query (same `conversation_id`, different `tenant_id`) → 0 chunks, empty-session answer
- [ ] Empty session → graceful answer, no DeepSeek call, HTTP 200
- [ ] Purge deletes only the target `(tenant_id, conversation_id)`; cross-tenant purge = 0 rows
- [ ] Validation errors → HTTP 422 with `{status:"failed", phase:"validation", ...}`
- [ ] Export both workflow JSONs committed to repo

### Backend wiring (coordinate — not M6-owned)
- `backend/app/core/config.py` (M2): `N8N_RETRIEVE_EPHEMERAL_WEBHOOK_URL`,
  `N8N_PURGE_EPHEMERAL_WEBHOOK_URL`, `N8N_PURGE_TOKEN`.
- `backend/app/services/n8n_client.py` (M3): `retrieve_ephemeral(...)`,
  `purge_ephemeral(...)`.
- WhatsApp session-end → `purge_ephemeral()` (M4/M12).


---
<!-- AUTO-APPENDED:SKILLS-V1 -->
## Skills Required
- **Must-have:** n8n LangChain nodes (`@n8n/n8n-nodes-langchain.agent`), tool-calling agents, Postgres + pgvector kNN queries, Voyage rerank API, Google Gemini API, DeepSeek API (OpenAI-compatible).
- **Nice-to-have:** Prompt engineering for grounded answers, faithfulness scoring, fallback chains.

## Detailed Step-by-Step Plan
### Day 1 — Import & Credentials
1. Import `n8n-workflows/retrieval-pipeline.json`.
2. Add credentials: `DeepSeekAuth` (Bearer DEEPSEEK_API_KEY, base URL `https://api.deepseek.com`), `GeminiAuth`, `VoyageAuth` (reuse M5's).

### Day 2 — Query Embed + Retrieval Tool
3. Webhook `/retrieve` POST → receives `{query, tenant_id, conversation_history, max_chunks}`.
4. HTTP "Embed Query": Voyage embeddings with `input_type: "query"`.
5. Postgres "Search KB": `SELECT chunk_id, document_id, text, page_number, 1 - (embedding <=> ) AS score FROM document_chunks WHERE tenant_id =  ORDER BY embedding <=>  LIMIT 20`.
6. Postgres "Search Ephemeral": same against `ephemeral_chunks` filtered by `conversation_id` and `expires_at > NOW()`.

### Day 3 — Rerank + Agent
7. HTTP "Voyage Rerank": POST `https://api.voyageai.com/v1/rerank` `{query, documents:[chunk_texts], model: "rerank-2.5", top_k: 5}`.
8. LangChain Agent node:
   - LLM: DeepSeek V4 Flash (HTTP creds, model=`deepseek-chat`).
   - System prompt: "You are a grounded assistant. Cite sources as [doc_title, p.X]. If chunks don't answer, set requires_clarification=true."
   - Tools: `search_kb`, `search_ephemeral`, `ask_clarifying_question`, `web_lookup` (stretch).

### Day 4 — Self-Check Loop
9. HTTP "Gemini Faithfulness": POST `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent` with prompt scoring (0-1) whether answer is supported by chunks.
10. IF node `faithfulness < 0.7` → branch to DeepSeek V4 Pro retry (model=`deepseek-reasoner`) with stricter prompt.

### Day 5 — Output Contract
11. Function "Format Response": emit JSON `{answer, sources:[{document_id, title, chunk_text, page_number, score}], faithfulness, requires_clarification, follow_up_questions:[3], metadata:{model, retrieval_time_ms, chunks_retrieved}}`.
12. Respond to Webhook node.

### Day 6 — Test + Export
13. Manually trigger with sample queries. Verify citation accuracy. Export workflow → overwrite JSON → commit.

## Learning Resources
- n8n AI Agent node: https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/
- DeepSeek API: https://api-docs.deepseek.com/
- Gemini API: https://ai.google.dev/gemini-api/docs
- pgvector kNN: https://github.com/pgvector/pgvector#querying
