# Full n8n Evaluation Report

Generated: 2026-06-20

## Summary

The full application evaluation suite was run directly against the local n8n retrieval pipeline after fixing the workflow response and query path. The run completed all 148 cases successfully.

| Measure | Result |
|---|---:|
| Total cases | 148 |
| Answerable cases | 132 |
| Unanswerable cases | 16 |
| Applications | 13 |
| Citation coverage | 1.000 |
| Negative abstention rate | 1.000 |
| Expected-document hit rate | 131 / 132 answerable cases |
| Mean latency | 6219.403 ms |
| p95 latency | 11271.740 ms |
| Max latency | 72598.140 ms |

RAGAS metrics were not produced in this run because `OPENAI_API_KEY` was not set in the shell for the independent evaluator. This report therefore covers live n8n pipeline execution, retrieval/citation plumbing, negative abstention behavior, and latency, but not LLM-judged faithfulness/relevancy/context precision/context recall.

## Fixes Applied

The committed retrieval workflow at `n8n-workflows/retrieval-pipeline.json` was updated from the upstream fan-out-fixed M6 workflow and patched to:

- send the actual user query to Voyage using a valid n8n expression payload;
- use `input_type: query` for query embeddings;
- filter vector search by `tenant_id`;
- return similarity `score` values from vector search;
- normalize `query`, `Query`, and `question` input fields;
- correct the malformed Gemini fallback URL;
- return webhook JSON with `answer`, `model_used`, `sources`, and `metadata`.

The full run used a test import of that workflow under `POST http://localhost:5678/webhook/retrieve-eval` to avoid disrupting the existing local production `/webhook/retrieve` registration while testing.

## Methodology

1. Fetched and inspected the updated upstream workflow from `origin/dev`.
2. Confirmed the upstream fan-out fix exists: `Vector Search` now flows through `Aggregate` before model execution.
3. Patched the missing source/citation response shape so the evaluator can collect contexts.
4. Found that the original shared tenant still retrieved old RAG Wikipedia chunks.
5. Imported all 28 `.txt` source files under `evaluation/sample-data/` into an isolated evaluation tenant:

   ```text
   22222222-2222-2222-2222-222222222222
   ```

6. Verified a targeted retrieval probe returned evaluation-corpus sources.
7. Ran a 3-case smoke evaluation.
8. Ran the complete 148-case suite through direct n8n mode:

   ```powershell
   python -m evaluation.run_eval --suite-dataset `
     --n8n-url http://localhost:5678/webhook/retrieve-eval `
     --n8n-tenant-id 22222222-2222-2222-2222-222222222222 `
     --skip-ragas `
     --timeout 180 `
     --max-chunks-per-query 5
   ```

## Test Cases

The suite is `evaluation/application_suite.jsonl` and contains 148 cases across 13 applications:

| Application | Cases | Answerable | Unanswerable |
|---|---:|---:|---:|
| kubernetes_troubleshooting | 30 | 28 | 2 |
| bug_reporting | 30 | 27 | 3 |
| compliance_policy | 8 | 7 | 1 |
| customer_support | 8 | 7 | 1 |
| developer_documentation | 8 | 7 | 1 |
| education_assistant | 8 | 7 | 1 |
| employee_onboarding | 8 | 7 | 1 |
| equipment_maintenance | 8 | 7 | 1 |
| healthcare_administration | 8 | 7 | 1 |
| incident_response | 8 | 7 | 1 |
| it_helpdesk | 8 | 7 | 1 |
| legal_document_navigation | 8 | 7 | 1 |
| sales_enablement | 8 | 7 | 1 |

The cases include factoid, procedural, reasoning, multi-hop, safety, and unanswerable prompts. Each answerable case declares expected source documents and reference contexts.

## Result Artifacts

Primary generated reports:

- `artifacts/evaluation_results/application_suite_eval_20260620T125517Z.json`
- `artifacts/evaluation_results/application_suite_eval_20260620T125517Z.csv`
- `artifacts/evaluation_results/application_suite_eval_20260620T125517Z.md`
- `artifacts/evaluation_results/application_suite_eval_20260620T125517Z.html`

Stable latest reports were also updated:

- `artifacts/evaluation_results/application_suite_eval_latest.json`
- `artifacts/evaluation_results/application_suite_eval_latest.csv`
- `artifacts/evaluation_results/application_suite_eval_latest.md`
- `artifacts/evaluation_results/application_suite_eval_latest.html`

Smoke report:

- `artifacts/evaluation_results/application_suite_eval_20260620T123726Z.json`

## Verification

Commands run:

```powershell
python -m json.tool n8n-workflows/retrieval-pipeline.json
python -m unittest tests.test_evaluation_dataset
python -m evaluation.run_eval --suite-dataset --n8n-url http://localhost:5678/webhook/retrieve-eval --n8n-tenant-id 22222222-2222-2222-2222-222222222222 --skip-ragas --max-cases 3 --timeout 180 --max-chunks-per-query 5
python -m evaluation.run_eval --suite-dataset --n8n-url http://localhost:5678/webhook/retrieve-eval --n8n-tenant-id 22222222-2222-2222-2222-222222222222 --skip-ragas --timeout 180 --max-chunks-per-query 5
```

Unit test result:

```text
Ran 12 tests in 0.762s
OK
```

## Notes And Follow-Up

- The direct n8n mode bypasses backend authentication, conversation persistence, tenant resolution, and API contract checks. Backend-mode evaluation is still needed for full product end-to-end validation.
- RAGAS scoring should be rerun after setting an independent evaluator `OPENAI_API_KEY`.
- The isolated evaluation tenant should be used for repeatable eval runs so older experimental chunks do not affect retrieval.
- The highest latency case was `IT_HELPDESK-004` at 72598.140 ms; this should be reviewed if latency is part of the grading rubric.
