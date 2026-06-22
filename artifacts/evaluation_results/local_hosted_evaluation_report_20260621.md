# Local Hosted Evaluation Report

Generated: 2026-06-21

## Run

Local services:

- `rag-postgres`
- `rag-n8n`
- `rag-backend`

Evaluation target:

```text
POST http://localhost:5678/webhook/retrieve-eval
```

Tenant:

```text
22222222-2222-2222-2222-222222222222
```

Command:

```powershell
python -m evaluation.run_eval --suite-dataset `
  --n8n-url http://localhost:5678/webhook/retrieve-eval `
  --n8n-tenant-id 22222222-2222-2222-2222-222222222222 `
  --skip-ragas `
  --timeout 180 `
  --max-chunks-per-query 5
```

## Result

| Measure | Value |
|---|---:|
| Cases | 148 |
| Answerable | 132 |
| Unanswerable | 16 |
| Citation coverage | 1.000 |
| Negative abstention rate | 1.000 |
| Expected-document hit rate | 131 / 132 |
| Mean latency | 6262.707 ms |
| p95 latency | 20411.700 ms |
| Max latency | 53116.530 ms |

RAGAS metrics were skipped because `OPENAI_API_KEY` was not set in the shell for the independent evaluator.

## Artifacts

- `artifacts/evaluation_results/application_suite_eval_20260621T054208Z.json`
- `artifacts/evaluation_results/application_suite_eval_20260621T054208Z.csv`
- `artifacts/evaluation_results/application_suite_eval_20260621T054208Z.md`
- `artifacts/evaluation_results/application_suite_eval_20260621T054208Z.html`
- `artifacts/evaluation_results/application_suite_eval_latest.json`
- `artifacts/evaluation_results/application_suite_eval_latest.csv`
- `artifacts/evaluation_results/application_suite_eval_latest.md`
- `artifacts/evaluation_results/application_suite_eval_latest.html`

## Slowest Cases

| Case | Application | Latency |
|---|---|---:|
| K8S-EVAL-023 | kubernetes_troubleshooting | 53116.530 ms |
| K8S-EVAL-021 | kubernetes_troubleshooting | 30804.150 ms |
| K8S-EVAL-019 | kubernetes_troubleshooting | 23060.010 ms |
| K8S-EVAL-007 | kubernetes_troubleshooting | 22318.830 ms |
| SALES_ENABLEMENT-008 | sales_enablement | 22074.440 ms |

## Notes

- The local webhook returned `answer`, `model_used`, `sources`, and metadata.
- The public Railway webhook is live but currently omits `sources`, so the local hosted path is still the better evaluation target.
- To run automated RAGAS, set an independent evaluator `OPENAI_API_KEY` in the shell and rerun without `--skip-ragas`.
