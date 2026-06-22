# RAG Evaluation Report

Generated: `2026-06-21T16:51:35.543681+00:00`

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
- Mean latency: 16880.598 ms
- p95 latency: 17249.200 ms

## Batch

- Batch: 13 of 30
- Batch size: 5
- Case positions: 61 to 65
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
| it_helpdesk | 5 | - | - | - | - |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| IT_HELPDESK-001 | it_helpdesk | factoid | One or more RAGAS metrics were not produced |
| IT_HELPDESK-002 | it_helpdesk | procedural | One or more RAGAS metrics were not produced |
| IT_HELPDESK-003 | it_helpdesk | procedural | One or more RAGAS metrics were not produced |
| IT_HELPDESK-004 | it_helpdesk | factoid | One or more RAGAS metrics were not produced |
| IT_HELPDESK-005 | it_helpdesk | reasoning | One or more RAGAS metrics were not produced |
