# RAG Evaluation Report

Generated: `2026-06-21T05:55:16.592081+00:00`

## Aggregate Results

| Metric | Score | Threshold | Pass |
|---|---:|---:|:---:|
| faithfulness | 0.333 | 0.850 | no |
| answer_relevancy | 0.320 | 0.800 | no |
| context_precision | 1.000 | 0.750 | yes |
| context_recall | 0.833 | 0.800 | yes |

- Cases: 3
- Citation coverage: 1.000
- Negative abstention rate: 0.000
- Mean latency: 19552.777 ms
- p95 latency: 21395.060 ms

## Application Results

| Application | Cases | Faithfulness | Relevancy | Context precision | Context recall |
|---|---:|---:|---:|---:|---:|
| kubernetes_troubleshooting | 3 | 0.333 | 0.320 | 1.000 | 0.833 |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| - | - | - | None |
