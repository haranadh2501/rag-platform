# RAG Evaluation Report

Generated: `2026-06-21T16:48:38.067342+00:00`

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
- Mean latency: 17733.964 ms
- p95 latency: 18225.730 ms

## Batch

- Batch: 11 of 30
- Batch size: 5
- Case positions: 51 to 55
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
| bug_reporting | 5 | - | - | - | - |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| BUG-EVAL-021 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-022 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-023 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-024 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-025 | bug_reporting | procedural | One or more RAGAS metrics were not produced |
