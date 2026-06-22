# Backend DB-Backed RAGAS Agent Report - 2026-06-21

## Objective

Run RAGAS through the backend API, then verify that the answer sources were saved in the database. A database-checking sub-agent inspected the local Postgres state independently.

## Method

1. Started a database/evidence checker agent to inspect local Docker/Postgres state.
2. Confirmed the normal backend pipeline URL `/webhook/retrieve` returned an empty body through n8n.
3. Temporarily restarted backend with `PIPELINE_URL=http://n8n:5678/webhook/retrieve-eval`, because `/webhook/retrieve-eval` returns JSON with `answer` and `sources`.
4. Created a local eval tenant/user for tenant `22222222-2222-2222-2222-222222222222`, matching the n8n evaluation corpus tenant.
5. Ran backend `/chat/query` evaluation with `--contexts-from-db`, so the evaluator collected answers from the API and then read saved contexts from `chat_messages.sources`.
6. Ran RAGAS on 5 Kubernetes evaluation cases with OpenAI as the independent evaluator.
7. Restored backend to the normal compose configuration after the run.

## Artifacts

- JSON: `artifacts/evaluation_results/application_suite_eval_20260621T111722Z.json`
- CSV: `artifacts/evaluation_results/application_suite_eval_20260621T111722Z.csv`
- Markdown: `artifacts/evaluation_results/application_suite_eval_20260621T111722Z.md`
- HTML: `artifacts/evaluation_results/application_suite_eval_20260621T111722Z.html`

## RAGAS Summary

| Metric | Score | Threshold | Status |
|---|---:|---:|---|
| Faithfulness | 0.6381 | 0.85 | Fail |
| Answer relevancy | 0.9402 | 0.80 | Pass |
| Context precision | 0.9178 | 0.75 | Pass |
| Context recall | 1.0000 | 0.80 | Pass |

Quality gate: failed because faithfulness was below threshold.

## Retrieval/API Summary

- Cases: 5
- Answerable cases: 5
- Citation coverage: 1.0
- Mean latency: 5041.888 ms
- P95 latency: 5822.47 ms
- All 5 cases returned backend HTTP 200.
- The evaluator read contexts from local `chat_messages.sources`, not directly from the API response.

## Per-Case Scores

| Case | Faithfulness | Answer Relevancy | Context Precision | Context Recall |
|---|---:|---:|---:|---:|
| K8S-EVAL-001 | 0.3333 | 0.9349 | 1.0000 | 1.0000 |
| K8S-EVAL-002 | 1.0000 | 0.9661 | 0.7556 | 1.0000 |
| K8S-EVAL-003 | 1.0000 | 0.9712 | 1.0000 | 1.0000 |
| K8S-EVAL-004 | 0.2857 | 0.8602 | 1.0000 | 1.0000 |
| K8S-EVAL-005 | 0.5714 | 0.9688 | 0.8333 | 1.0000 |

## Database Evidence

Database checker findings before/around the run:

- Local `rag-postgres` was reachable and healthy.
- Local app DB had 1 original tenant and 1 original user before adding the eval tenant/user.
- Local `documents`: 0 rows.
- Local `document_chunks`: 0 rows.
- Local `ephemeral_chunks`: 0 rows.
- Historical `chat_messages` existed and had assistant sources, but those were not proof of the current evaluation corpus.

Post-run evidence for eval tenant `22222222-2222-2222-2222-222222222222`:

- Local `documents`: 0 rows.
- Local `document_chunks`: 0 rows.
- Latest backend-generated assistant rows had `source_count=5`.
- Saved source objects included `chunk_text`, `document_id`, and `score`.
- First source title in latest rows: `kubernetes_troubleshooting/cluster_debugging_runbook.txt`.

Interpretation: backend persistence is working, because answers and returned sources were saved into `chat_messages.sources`. However, local app `documents` and `document_chunks` are not populated, so the retrieved evaluation corpus appears to live behind the n8n workflow's configured Postgres credential rather than the local app DB.

## Key Caveat

This run validates:

- backend `/chat/query` can call n8n and return answers,
- backend saves sources to local `chat_messages.sources`,
- RAGAS can score those saved contexts,
- the saved source shape is suitable for evaluation.

This run does not validate that local app `document_chunks` powered retrieval, because local `document_chunks` is empty. For strict end-to-end corpus validation, align n8n's Postgres credential with the local app DB or ingest the same evaluation corpus into the local app DB.

## Recommended Next Step

Populate local `documents` and `document_chunks` for tenant `22222222-2222-2222-2222-222222222222`, or repoint n8n's Postgres credential to local `rag-postgres`. Then rerun:

```powershell
python -m evaluation.run_eval --suite-dataset --base-url http://localhost:8000 --email eval-ragas@example.com --password evalpass123 --contexts-from-db --db-url postgresql+asyncpg://raguser:changeme@localhost:5432/ragplatform
```
