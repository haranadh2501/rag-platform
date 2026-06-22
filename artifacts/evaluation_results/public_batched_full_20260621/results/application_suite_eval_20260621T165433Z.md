# RAG Evaluation Report

Generated: `2026-06-21T16:54:33.523017+00:00`

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
- Mean latency: 17661.640 ms
- p95 latency: 19286.300 ms

## Batch

- Batch: 15 of 30
- Batch size: 5
- Case positions: 71 to 75
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
| customer_support | 5 | - | - | - | - |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| CUSTOMER_SUPPORT-003 | customer_support | procedural | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-004 | customer_support | factoid | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-005 | customer_support | procedural | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-006 | customer_support | procedural | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-007 | customer_support | multi_hop | One or more RAGAS metrics were not produced |
