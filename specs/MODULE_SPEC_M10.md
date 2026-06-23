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
