# MODULE_SPEC_M10 — Evaluation & Testing

**Owner**: Member 10 | **Track**: QA / Eval | **Branch**: `feat/evaluation`

## Role
RAGAS evaluation framework, Q&A test dataset, multi-tenant isolation tests, API integration tests.

## Day-by-Day Deliverables
| Day | Deliverable | Done? |
|---|---|---|
| 1 | Collect 5–10 sample customer PDFs (public manuals, SOPs). Branch. | ☐ |
| 2 | Write 30 Q&A pairs with ground truth answers + expected source documents | ☐ |
| 2 | Set up RAGAS evaluation framework environment | ☐ |
| 3 | Evaluation script: ingest docs → query → measure vs ground truth | ☐ |
| 4 | First RAGAS evaluation run. Metrics: faithfulness, answer_relevancy, context_precision, context_recall | ☐ |
| 5 | Multi-tenant isolation test: Tenant A cannot retrieve Tenant B's chunks | ☐ |
| 5 | API integration tests (pytest): auth flow, upload, query, conversations | ☐ |
| 6 | Final evaluation report + load test (10 concurrent queries) | ☐ |

## Files Owned
- `evaluation/`
- `tests/`
- `evaluation/sample-data/`

## Q&A Dataset Format (`evaluation/qa_dataset.json`)
```json
[
  {
    "question": "How do I reset the Bosch dishwasher?",
    "ground_truth": "Press and hold the Start button for 3 seconds...",
    "expected_source_document": "bosch_manual.pdf",
    "expected_source_page": 12
  }
]
```

## RAGAS Evaluation Script
```python
# evaluation/run_eval.py
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
# 1. Ingest test documents into test tenant
# 2. Run all 30 questions through POST /chat/query
# 3. Collect {question, answer, contexts, ground_truth}
# 4. Run RAGAS metrics
# 5. Generate report as evaluation_results/report_{date}.json
```

## Current Evaluation Suite

The implemented suite now lives in `evaluation/application_suite.jsonl` and
contains 148 cases across 13 applications. The Kubernetes troubleshooting suite
is generated first so small smoke runs exercise the priority domain before the
other applications.

Quick preflight:

```powershell
python -m evaluation.run_test_suite
```

This regenerates deterministic synthetic data, validates reference contexts,
runs `tests/test_evaluation_dataset.py`, and writes readiness reports under
`artifacts/evaluation_results/`.

Live smoke test:

```powershell
python -m evaluation.run_eval --suite-dataset --skip-ragas --max-cases 3
```

Full scored evaluation:

```powershell
python -m evaluation.run_eval --suite-dataset --enforce-thresholds
```

Use the smoke test before the full scored run. If the smoke test cannot reach
the backend or receives a mock response, do not treat the result as evaluation
evidence.

Direct Railway n8n smoke test:

```powershell
$env:EVAL_N8N_URL = "https://<n8n-service>/webhook/<retrieval-path>"
$env:EVAL_TENANT_ID = "<tenant-id-visible-to-ingested-docs>"

python -m evaluation.run_eval --suite-dataset --n8n-url $env:EVAL_N8N_URL --skip-ragas --max-cases 3
```

Use direct n8n mode only when the retrieval workflow is deployed in Railway n8n
but the FastAPI backend is not wired to that workflow yet. It validates retrieval
and answer generation, but it does not validate backend auth, conversation
history, tenant guards, or API response contracts.

## Live Evaluation Prerequisites

Full evaluation must run against the real n8n-backed pipeline, not mock mode.

- `MOCK_N8N=false` in the backend environment.
- Backend reachable at `EVAL_BASE_URL` and returning `mock_n8n: false` from
  `/health`.
- n8n workflows imported, credentialed, active, and reachable by the backend.
- For direct n8n mode, a public retrieval webhook URL is available through
  `EVAL_N8N_URL`.
- Evaluation tenant has all `.txt` files under `evaluation/sample-data/`
  ingested and completed.
- Evaluator auth is configured with either `EVAL_BEARER_TOKEN` or both
  `EVAL_EMAIL` and `EVAL_PASSWORD`.
- `OPENAI_API_KEY` is set for independent RAGAS scoring.
- Do not pass `--allow-mock` for quality evidence; it is only for plumbing
  checks.

Expected local setup:

```powershell
$env:EVAL_BASE_URL = "http://localhost:8000"
$env:EVAL_EMAIL = "admin@iisc-demo.com"
$env:EVAL_PASSWORD = "<password>"
$env:OPENAI_API_KEY = "<independent-evaluator-key>"
```

## n8n Setup References

n8n setup is documented elsewhere in the repo. M10 depends on these steps being
complete before running live evaluation:

- `docs/LOCAL_SETUP.md` - local Docker setup, `.env`, service URLs, and
  troubleshooting.
- `docs/DEPLOYMENT.md` - Railway backend+n8n deployment and workflow import.
- `docs/CREDENTIALS_README.md` - n8n service variables, credentials, workflow
  credential assignment, activation, and webhook test.
- `specs/MODULE_SPEC_M5.md` - ingestion workflow ownership and setup notes.
- `specs/MODULE_SPEC_M6.md` - retrieval/generation workflow ownership and setup
  notes.
- `specs/MODULE_SPEC_M11.md` - short n8n setup guide template for importing and
  activating workflows.

Workflow files are committed under `n8n-workflows/`:

- `ingestion-pipeline.json`
- `retrieval-pipeline.json`
- `ingest-ephemeral.json`

## Multi-Tenant Isolation Test
```python
# tests/test_isolation.py
def test_tenant_a_cannot_see_tenant_b_docs():
    # 1. Create Tenant A + upload doc_a.pdf
    # 2. Create Tenant B + upload doc_b.pdf
    # 3. Query using Tenant A's JWT for content ONLY in doc_b.pdf
    # 4. Assert: answer is "I don't have enough information..."
    # 5. Assert: sources list is empty
```

## API Integration Tests
```python
# tests/test_api.py
# test_login_success, test_login_wrong_password
# test_upload_pdf, test_upload_returns_202
# test_chat_query_mock, test_chat_query_real
# test_conversation_history
# test_admin_cannot_see_other_tenant_docs
```

## Acceptance Criteria (Minimum Bar)
| Metric | Minimum |
|---|---|
| Faithfulness | ≥ 0.80 |
| Answer Relevancy | ≥ 0.75 |
| Citation Coverage | ≥ 85% of answers |
| Tenant Isolation | 100% (0 cross-tenant leaks) |
| API Tests Passing | ≥ 90% |
- [ ] `pytest tests/` passes with ≥ 90% pass rate
- [ ] RAGAS report generated as JSON + printed summary
- [ ] Load test: 10 concurrent `/chat/query` requests complete < 30s each


---
<!-- AUTO-APPENDED:SKILLS-V1 -->
## Skills Required
- **Must-have:** Python, pytest, RAGAS framework, Pandas, prompt-engineering judgment, dataset curation.
- **Nice-to-have:** Locust or k6 for load testing, GitHub Actions for CI eval, Jupyter notebooks for analysis.

## Detailed Step-by-Step Plan
### Day 1 — Sample Data
1. Collect 5-10 sample PDFs (manuals, FAQs, SOPs) → drop in `evaluation/sample-data/` (≤ 5 MB each).
2. Create folder `evaluation/qa-set/` with `ground_truth.jsonl` — start writing 30 entries.

### Day 2 — Q&A Curation (30 pairs)
3. For each PDF, write 3 questions of 3 types: factoid, multi-hop reasoning, "no answer in docs" (negative). JSON shape: `{question, expected_answer, expected_source_doc, expected_page, type}`.

### Day 3 — RAGAS Harness
4. `pip install ragas pandas pytest`.
5. Create `evaluation/run_eval.py`:
   - For each Q&A: POST /chat/query → collect `answer + sources`.
   - Feed to RAGAS metrics: `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`.
   - Save results CSV to `evaluation/results/run-{timestamp}.csv`.

### Day 4 — Baseline + Negative Cases
6. Run eval against staging. Publish baseline scores in `evaluation/RESULTS.md`.
7. Add a "negative" check: for "no answer" questions, assert `requires_clarification=true`.

### Day 5 — Integration Tests
8. `tests/test_e2e.py` (pytest): upload doc → poll until status=completed → query → assert source appears in response. Use `MOCK_N8N=false` (point to staging).
9. `tests/test_tenant_isolation.py`: tenant A's user cannot retrieve tenant B's docs.

### Day 6 — Load Test (Stretch)
10. Locust: 20 concurrent users for 5 min on /chat/query. Record p95 latency in RESULTS.md.

## Learning Resources
- RAGAS: https://docs.ragas.io/en/stable/
- pytest fixtures: https://docs.pytest.org/en/stable/how-to/fixtures.html
- Locust: https://locust.io/
