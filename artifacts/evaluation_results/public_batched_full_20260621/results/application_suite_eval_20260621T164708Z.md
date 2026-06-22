# RAG Evaluation Report

Generated: `2026-06-21T16:47:08.450690+00:00`

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
- Mean latency: 18969.214 ms
- p95 latency: 19713.110 ms

## Batch

- Batch: 10 of 30
- Batch size: 5
- Case positions: 46 to 50
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
| BUG-EVAL-016 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-017 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-018 | bug_reporting | procedural | One or more RAGAS metrics were not produced |
| BUG-EVAL-019 | bug_reporting | multi_hop | One or more RAGAS metrics were not produced |
