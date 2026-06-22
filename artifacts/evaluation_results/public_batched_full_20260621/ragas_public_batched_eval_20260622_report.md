# Public Railway RAGAS Attempt Report

Generated: 2026-06-22

## Outcome

The full RAGAS scoring job was launched against the consolidated 148-case public Railway evaluation output. RAGAS processed all 528 internal metric tasks, but OpenAI judge calls returned insufficient quota errors. As a result, the RAGAS metric columns were all null and no valid aggregate RAGAS score could be computed.

## Run Inputs

- Source evaluation JSON: `artifacts\evaluation_results\public_batched_full_20260621\consolidated_public_batched_eval_20260621.json`
- RAGAS output JSON: `artifacts\evaluation_results\public_batched_full_20260621\ragas_public_batched_eval_20260622.json`
- RAGAS output CSV: `artifacts\evaluation_results\public_batched_full_20260621\ragas_public_batched_eval_20260622.csv`
- RAGAS stderr log: `artifacts\evaluation_results\public_batched_full_20260621\ragas_stderr.log`

## Public Evaluation Context

- Total cases: 148
- Answerable cases submitted to RAGAS: 132
- Unanswerable cases retained for non-RAGAS metrics: 16
- Citation coverage: 1.0000
- Source return rate: 1.0000
- Average sources per case: 3.00

## RAGAS Result Availability

| Metric | Aggregate score | Non-null case scores | Null case scores |
|---|---:|---:|---:|
| faithfulness | n/a | 0 | 132 |
| answer_relevancy | n/a | 0 | 132 |
| context_precision | n/a | 0 | 132 |
| context_recall | n/a | 0 | 132 |

## Error Evidence

- Completed all internal RAGAS tasks: True
- Executor exceptions logged: 528
- RateLimitError occurrences logged: 6
- insufficient_quota occurrences logged: 12

The key issue is not the n8n pipeline or the retrieved sources. The public endpoint had already completed all 148 cases and returned sources for every case. The blocker is judge-side OpenAI quota for RAGAS scoring.

## Next Step

Enable billing/quota for the OpenAI judge key or provide a different judge key with available quota, then rerun `score_public_ragas.py`. The script reads the already collected public evaluation output, so it does not need to call the public n8n webhook again.
