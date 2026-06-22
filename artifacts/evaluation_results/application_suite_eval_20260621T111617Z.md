# RAG Evaluation Report

Generated: `2026-06-21T11:16:17.881375+00:00`

## Aggregate Results

| Metric | Score | Threshold | Pass |
|---|---:|---:|:---:|
| faithfulness | nan | 0.850 | no |
| answer_relevancy | nan | 0.800 | no |
| context_precision | nan | 0.750 | no |
| context_recall | nan | 0.800 | no |

- Cases: 5
- Citation coverage: 1.000
- Negative abstention rate: 0.000
- Mean latency: 4660.712 ms
- p95 latency: 5345.990 ms

## Application Results

| Application | Cases | Faithfulness | Relevancy | Context precision | Context recall |
|---|---:|---:|---:|---:|---:|
| kubernetes_troubleshooting | 5 | - | - | - | - |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| K8S-EVAL-001 | kubernetes_troubleshooting | factoid | One or more RAGAS metrics were not produced |
| K8S-EVAL-002 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-003 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-004 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-005 | kubernetes_troubleshooting | factoid | One or more RAGAS metrics were not produced |
