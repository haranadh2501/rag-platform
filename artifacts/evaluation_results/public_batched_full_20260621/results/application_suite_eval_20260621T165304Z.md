# RAG Evaluation Report

Generated: `2026-06-21T16:53:04.333980+00:00`

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
- Mean latency: 17529.798 ms
- p95 latency: 18809.210 ms

## Batch

- Batch: 14 of 30
- Batch size: 5
- Case positions: 66 to 70
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
| customer_support | 2 | - | - | - | - |
| it_helpdesk | 3 | - | - | - | - |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| IT_HELPDESK-006 | it_helpdesk | procedural | One or more RAGAS metrics were not produced |
| IT_HELPDESK-007 | it_helpdesk | multi_hop | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-001 | customer_support | factoid | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-002 | customer_support | factoid | One or more RAGAS metrics were not produced |
