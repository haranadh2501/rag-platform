# Public Railway Batched Evaluation Report

Generated: 2026-06-21

## Run Summary

- Endpoint: https://n8n-production-c637.up.railway.app/webhook/retrieve
- Total cases: 148
- Answerable cases: 132
- Unanswerable cases: 16
- Completed batches: 30 / 30
- Batch size: 5 cases
- RAGAS: skipped because `OPENAI_API_KEY` was not present in the runtime environment

## Aggregate Metrics

| Metric | Value |
|---|---:|
| Citation coverage | 1.0000 |
| Negative abstention rate | 0.0000 |
| Mean latency | 18523.09 ms |
| p95 latency | 21227.98 ms |
| Max latency | 41658.92 ms |
| Source return rate | 1.0000 |
| Average sources per case | 3.00 |
| Metadata coverage | 1.0000 |
| Total retry count | 0 |
| Max attempts | 1 |

## Application Breakdown

| Application | Cases | Citation coverage | Negative abstention | Mean latency | Source return rate |
|---|---:|---:|---:|---:|---:|
| bug_reporting | 30 | 1.0000 | 0.0000 | 18035.24 ms | 1.0000 |
| compliance_policy | 8 | 1.0000 | 0.0000 | 18665.67 ms | 1.0000 |
| customer_support | 8 | 1.0000 | 0.0000 | 17663.53 ms | 1.0000 |
| developer_documentation | 8 | 1.0000 | 0.0000 | 18093.36 ms | 1.0000 |
| education_assistant | 8 | 1.0000 | 0.0000 | 17609.31 ms | 1.0000 |
| employee_onboarding | 8 | 1.0000 | 0.0000 | 17610.07 ms | 1.0000 |
| equipment_maintenance | 8 | 1.0000 | 0.0000 | 23408.39 ms | 1.0000 |
| healthcare_administration | 8 | 1.0000 | 0.0000 | 18596.38 ms | 1.0000 |
| incident_response | 8 | 1.0000 | 0.0000 | 18874.84 ms | 1.0000 |
| it_helpdesk | 8 | 1.0000 | 0.0000 | 17307.31 ms | 1.0000 |
| kubernetes_troubleshooting | 30 | 1.0000 | 0.0000 | 18879.34 ms | 1.0000 |
| legal_document_navigation | 8 | 1.0000 | 0.0000 | 17971.79 ms | 1.0000 |
| sales_enablement | 8 | 1.0000 | 0.0000 | 18446.93 ms | 1.0000 |

## Batch Results

| Batch | Cases | Positions | Citation | Source return | Avg sources | Mean latency | Retries |
|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 5 | 1-5 | 1.0000 | 1.0000 | 3.00 | 18562.25 ms | 0 |
| 2 | 5 | 6-10 | 1.0000 | 1.0000 | 3.00 | 18524.46 ms | 0 |
| 3 | 5 | 11-15 | 1.0000 | 1.0000 | 3.00 | 19205.08 ms | 0 |
| 4 | 5 | 16-20 | 1.0000 | 1.0000 | 3.00 | 18849.96 ms | 0 |
| 5 | 5 | 21-25 | 1.0000 | 1.0000 | 3.00 | 19278.08 ms | 0 |
| 6 | 5 | 26-30 | 1.0000 | 1.0000 | 3.00 | 18856.19 ms | 0 |
| 7 | 5 | 31-35 | 1.0000 | 1.0000 | 3.00 | 17877.82 ms | 0 |
| 8 | 5 | 36-40 | 1.0000 | 1.0000 | 3.00 | 18072.43 ms | 0 |
| 9 | 5 | 41-45 | 1.0000 | 1.0000 | 3.00 | 17297.15 ms | 0 |
| 10 | 5 | 46-50 | 1.0000 | 1.0000 | 3.00 | 18969.21 ms | 0 |
| 11 | 5 | 51-55 | 1.0000 | 1.0000 | 3.00 | 17733.96 ms | 0 |
| 12 | 5 | 56-60 | 1.0000 | 1.0000 | 3.00 | 18260.88 ms | 0 |
| 13 | 5 | 61-65 | 1.0000 | 1.0000 | 3.00 | 16880.60 ms | 0 |
| 14 | 5 | 66-70 | 1.0000 | 1.0000 | 3.00 | 17529.80 ms | 0 |
| 15 | 5 | 71-75 | 1.0000 | 1.0000 | 3.00 | 17661.64 ms | 0 |
| 16 | 5 | 76-80 | 1.0000 | 1.0000 | 3.00 | 17402.52 ms | 0 |
| 17 | 5 | 81-85 | 1.0000 | 1.0000 | 3.00 | 17892.05 ms | 0 |
| 18 | 5 | 86-90 | 1.0000 | 1.0000 | 3.00 | 18166.64 ms | 0 |
| 19 | 5 | 91-95 | 1.0000 | 1.0000 | 3.00 | 18425.40 ms | 0 |
| 20 | 5 | 96-100 | 1.0000 | 1.0000 | 3.00 | 19319.91 ms | 0 |
| 21 | 5 | 101-105 | 1.0000 | 1.0000 | 3.00 | 17936.68 ms | 0 |
| 22 | 5 | 106-110 | 1.0000 | 1.0000 | 3.00 | 18643.27 ms | 0 |
| 23 | 5 | 111-115 | 1.0000 | 1.0000 | 3.00 | 17520.02 ms | 0 |
| 24 | 5 | 116-120 | 1.0000 | 1.0000 | 3.00 | 18199.03 ms | 0 |
| 25 | 5 | 121-125 | 1.0000 | 1.0000 | 3.00 | 18867.29 ms | 0 |
| 26 | 5 | 126-130 | 1.0000 | 1.0000 | 3.00 | 17091.08 ms | 0 |
| 27 | 5 | 131-135 | 1.0000 | 1.0000 | 3.00 | 26704.73 ms | 0 |
| 28 | 5 | 136-140 | 1.0000 | 1.0000 | 3.00 | 19040.38 ms | 0 |
| 29 | 5 | 141-145 | 1.0000 | 1.0000 | 3.00 | 18229.47 ms | 0 |
| 30 | 3 | 146-148 | 1.0000 | 1.0000 | 3.00 | 18809.37 ms | 0 |

## Methodology

The evaluator sent every suite test case to the public Railway n8n webhook in deterministic batches of five cases. Each response was normalized into the evaluation schema, including answer text, retrieved contexts, source metadata, latency, and observability fields. The final report merges all timestamped batch JSON files, recomputes aggregate metrics, and keeps a full row-level CSV for case inspection.

## Interpretation

The public Railway endpoint completed all 148 test cases in 30 batches with no failed batches. Source observability was strong: every case returned sources, and the endpoint returned an average of three sources per case. RAGAS was not computed in this full public pass because the judge API key was not available in the shell environment; the output JSON and CSV are ready for a RAGAS scoring pass once that key is configured.

## Artifacts

- Consolidated JSON: `artifacts\evaluation_results\public_batched_full_20260621\consolidated_public_batched_eval_20260621.json`
- Consolidated CSV: `artifacts\evaluation_results\public_batched_full_20260621\consolidated_public_batched_eval_20260621.csv`
- Batch logs: `artifacts\evaluation_results\public_batched_full_20260621\logs`
- Batch result files: `artifacts\evaluation_results\public_batched_full_20260621\results`
