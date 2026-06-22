# RAG Evaluation Report

Generated: `2026-06-21T16:56:01.386488+00:00`

## Aggregate Results

| Metric | Score | Threshold | Pass |
|---|---:|---:|:---:|
| faithfulness | - | - | - |
| answer_relevancy | - | - | - |
| context_precision | - | - | - |
| context_recall | - | - | - |

- Cases: 5
- Citation coverage: 1.000
- Negative abstention rate: 0.000
- Mean latency: 17402.520 ms
- p95 latency: 19406.490 ms

## Batch

- Batch: 16 of 30
- Batch size: 5
- Case positions: 76 to 80
- Total cases before batching: 148

## Observability

| Signal | Value |
|---|---:|
| Source return rate | 1.000 |
| Average sources per case | 3.000 |
| Metadata coverage | 1.000 |
| Total retry count | 0 |
| Max attempts | 1 |

## Application Results

| Application | Cases | Faithfulness | Relevancy | Context precision | Context recall |
|---|---:|---:|---:|---:|---:|
| customer_support | 1 | - | - | - | - |
| employee_onboarding | 4 | - | - | - | - |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| EMPLOYEE_ONBOARDING-001 | employee_onboarding | factoid | One or more RAGAS metrics were not produced |
| EMPLOYEE_ONBOARDING-002 | employee_onboarding | procedural | One or more RAGAS metrics were not produced |
| EMPLOYEE_ONBOARDING-003 | employee_onboarding | factoid | One or more RAGAS metrics were not produced |
| EMPLOYEE_ONBOARDING-004 | employee_onboarding | factoid | One or more RAGAS metrics were not produced |
