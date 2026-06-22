# RAG Evaluation Report

Generated: `2026-06-21T17:15:13.468866+00:00`

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
- Mean latency: 19040.384 ms
- p95 latency: 21422.250 ms

## Batch

- Batch: 28 of 30
- Batch size: 5
- Case positions: 136 to 140
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
| equipment_maintenance | 5 | - | - | - | - |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| EQUIPMENT_MAINTENANCE-004 | equipment_maintenance | procedural | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-005 | equipment_maintenance | safety | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-006 | equipment_maintenance | factoid | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-007 | equipment_maintenance | multi_hop | One or more RAGAS metrics were not produced |
