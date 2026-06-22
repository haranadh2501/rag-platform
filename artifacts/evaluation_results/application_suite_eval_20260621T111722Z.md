# RAG Evaluation Report

Generated: `2026-06-21T11:17:22.510023+00:00`

## Aggregate Results

| Metric | Score | Threshold | Pass |
|---|---:|---:|:---:|
| faithfulness | 0.638 | 0.850 | no |
| answer_relevancy | 0.940 | 0.800 | yes |
| context_precision | 0.918 | 0.750 | yes |
| context_recall | 1.000 | 0.800 | yes |

- Cases: 5
- Citation coverage: 1.000
- Negative abstention rate: 0.000
- Mean latency: 5041.888 ms
- p95 latency: 5822.470 ms

## Application Results

| Application | Cases | Faithfulness | Relevancy | Context precision | Context recall |
|---|---:|---:|---:|---:|---:|
| kubernetes_troubleshooting | 5 | 0.638 | 0.940 | 0.918 | 1.000 |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| - | - | - | None |
