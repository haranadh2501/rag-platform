# Consolidated RAGAS and Public API Evaluation Report

Generated: 2026-06-21

## Objective

This report consolidates the completed RAG evaluation work for the n8n-backed retrieval pipeline. The latest evaluator update breaks the test suite into deterministic batches, adds an observability parameter to the result summary, and supports direct evaluation of the public n8n webhook.

## What changed in the evaluator

- Restored direct n8n evaluation support through `--n8n-url`.
- Added deterministic test batching with `--batch-size` and `--batch-index`.
- Added public-webhook retry handling for request errors, HTTP 408, HTTP 429, HTTP 5xx, empty responses, and non-JSON responses.
- Added per-case source observability and run-level observability aggregation.
- Added `source_count` to CSV output.
- Added Observability and Batch sections to generated markdown and HTML reports.
- Documented the new n8n and batching workflow in `evaluation/README.md`.

## Observability parameter

The new observability block is computed from every evaluated case:

- `source_return_rate`: fraction of cases where the API returned at least one source.
- `average_sources_per_case`: average number of sources returned per case.
- `metadata_coverage`: fraction of cases with response metadata.
- `total_retry_count`: total direct n8n retries across the run.
- `max_attempts`: maximum attempts needed by any case.

## Test case breakup

The public Railway endpoint is functional, but slow enough that a single 148-case run is brittle. The suite should be split into deterministic batches.

Recommended full public run:

```powershell
python -m evaluation.run_eval --suite-dataset `
  --n8n-url https://n8n-production-c637.up.railway.app/webhook/retrieve `
  --n8n-tenant-id 22222222-2222-2222-2222-222222222222 `
  --batch-size 10 `
  --batch-index <1-15> `
  --timeout 240 `
  --max-chunks-per-query 5 `
  --n8n-retries 8
```

For lower timeout risk, use `--batch-size 5` and run batch indices `1` through `30`.

## Consolidated results

| Run | Scope | Cases | RAGAS | Citation coverage | Negative abstention | Mean latency | Observability |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| Local full RAGAS | Local n8n eval webhook | 148 | faithfulness 0.7824, answer relevancy 0.8427, context precision 0.9398, context recall 0.9348 | 1.0000 | 1.0000 | 7174.04 ms | Not captured in older run |
| Backend DB-backed RAGAS | Backend API plus saved DB sources | 5 | faithfulness 0.6381, answer relevancy 0.9402, context precision 0.9178, context recall 1.0000 | 1.0000 | 0.0000 | 5041.89 ms | Not captured in older run |
| Public Railway source check | Public n8n webhook | 1 | Skipped | 1.0000 | 0.0000 | 30159.68 ms | Sources returned by API |
| Public Railway batched smoke | Public n8n webhook, batch-capable evaluator | 5 | Skipped | 1.0000 | 0.0000 | 18524.62 ms | source_return_rate 1.0000, avg sources 3.0, metadata_coverage 1.0000, retries 0, max_attempts 1 |

## Completed artifact references

- Local full RAGAS JSON: `artifacts/evaluation_results/application_suite_eval_20260621T074025Z.json`
- Backend DB-backed RAGAS JSON: `artifacts/evaluation_results/application_suite_eval_20260621T111722Z.json`
- Public Railway source check JSON: `artifacts/evaluation_results/application_suite_eval_20260621T131844Z.json`
- Public Railway batched smoke JSON: `artifacts/evaluation_results/application_suite_eval_20260621T154730Z.json`

## Public webhook reliability findings

The public Railway webhook is now confirmed to return answers and source records, but the full monolithic run had reliability issues:

- `public_ragas_full_run_20260621T1128`: reached 58/148 cases, then failed on HTTP 502 Bad Gateway.
- `public_ragas_full_run_20260621T1319`: reached 9/148 cases, then failed on an empty or non-JSON response.
- `public_ragas_full_run_20260621T1332`: reached 2/148 cases before the run was intentionally stopped so the suite could be split into batches.

These results support using smaller batches for the full public endpoint evaluation.

## Methodology

The evaluation suite sends each test question to the configured retrieval target and records the answer, contexts, source metadata, and latency. RAGAS metrics are then computed where enabled:

- Faithfulness checks whether the answer is supported by retrieved context.
- Answer relevancy checks whether the answer addresses the question.
- Context precision checks whether retrieved contexts are relevant.
- Context recall checks whether the expected evidence is present in retrieved context.

For direct public n8n runs, the evaluator now sends WhatsApp-style fields including `current_message`, `history`, `request_id`, and `conversation_id`, then normalizes the public response into the same schema used by the local evaluator.

## Interpretation

The strongest completed end-to-end RAGAS evidence is still the local full run over 148 cases. It passed citation coverage, negative abstention, context precision, and context recall targets, but faithfulness remained below the configured threshold.

The public Railway webhook is working and returns sources. The new five-case batched smoke test showed 100 percent source return rate and three sources per case with no retries. Because latency is high, the full public RAGAS run should be executed in batches before making final claims about the production deployment.

## Recommended next step

Run the public Railway suite in batches, preferably `--batch-size 5` for stability. After all batch JSON files are produced, consolidate them into a single public-production report and compute RAGAS on the completed batch set.
