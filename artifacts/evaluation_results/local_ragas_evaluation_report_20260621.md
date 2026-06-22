# Local RAGAS Evaluation Report - 2026-06-21

## Target

- Local n8n endpoint: `http://localhost:5678/webhook/retrieve-eval`
- Evaluation tenant: `22222222-2222-2222-2222-222222222222`
- Dataset profile: full multi-application suite
- RAGAS evaluator: `ragas==0.1.10` with OpenAI evaluator calls

## Methodology

1. Verified local Docker services were running: `rag-postgres`, `rag-n8n`, and `rag-backend`.
2. Ran a 3-case local smoke test with `--skip-ragas` after adding WhatsApp-style payload fields.
3. Ran the full 148-case local evaluation without `--skip-ragas`.
4. For each case, the evaluator called local n8n directly and collected answer, retrieved source chunks, latency, and response metadata.
5. RAGAS scored answerable cases on faithfulness, answer relevancy, context precision, and context recall.

## Full Run Command Shape

```powershell
python -m evaluation.run_eval `
  --suite-dataset `
  --n8n-url http://localhost:5678/webhook/retrieve-eval `
  --n8n-tenant-id 22222222-2222-2222-2222-222222222222 `
  --timeout 300 `
  --n8n-retries 2 `
  --max-chunks-per-query 5
```

The OpenAI key was supplied only through the process environment for RAGAS scoring and was not written to repo files or reports.

## Results

- Total cases: `148`
- Answerable cases: `132`
- Unanswerable cases: `16`
- Citation coverage: `1.0`
- Negative abstention rate: `1.0`
- Expected-document hit rate: `131/132`
- Mean latency: `7174.041 ms`
- p95 latency: `17613.670 ms`
- Max latency: `143953.700 ms`

## RAGAS Summary

| Metric | Score | Threshold | Passed |
|---|---:|---:|---|
| faithfulness | `0.7824` | `0.85` | no |
| answer_relevancy | `0.8427` | `0.80` | yes |
| context_precision | `0.9398` | `0.75` | yes |
| context_recall | `0.9348` | `0.80` | yes |

Overall quality gate: **failed** because faithfulness was below threshold.

## RAGAS Completeness Notes

The run reached `528/528` RAGAS metric jobs. OpenAI returned many transient `429 Too Many Requests` responses, and RAGAS retried them. A few metric-level requests timed out near the end, so some per-case metric values are null:

- faithfulness nulls: `8`
- answer_relevancy nulls: `4`
- context_precision nulls: `1`
- context_recall nulls: `17`

The aggregate means above are computed from available non-null metric values.

## Artifacts

- `artifacts/evaluation_results/application_suite_eval_20260621T074025Z.json`
- `artifacts/evaluation_results/application_suite_eval_20260621T074025Z.csv`
- `artifacts/evaluation_results/application_suite_eval_20260621T074025Z.md`
- `artifacts/evaluation_results/application_suite_eval_20260621T074025Z.html`
- `artifacts/evaluation_results/local_ragas_full_run_20260621T0715/stdout.log`
- `artifacts/evaluation_results/local_ragas_full_run_20260621T0715/stderr.log`

## Conclusion

Local source-returning n8n evaluation is complete. Retrieval and abstention behavior are strong: citation coverage, negative abstention, context precision, and context recall all pass. The remaining quality issue is faithfulness, which scored below the configured threshold and should be improved by tightening generation prompts, reducing unsupported answer synthesis, or adding a final grounded-answer validation step before returning responses.
