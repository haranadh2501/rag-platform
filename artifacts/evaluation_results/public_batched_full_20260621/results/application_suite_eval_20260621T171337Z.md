# RAG Evaluation Report

Generated: `2026-06-21T17:13:37.007414+00:00`

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
- Mean latency: 26704.728 ms
- p95 latency: 41658.920 ms

## Batch

- Batch: 27 of 30
- Batch size: 5
- Case positions: 131 to 135
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
| equipment_maintenance | 3 | - | - | - | - |
| legal_document_navigation | 2 | - | - | - | - |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| LEGAL_DOCUMENT_NAVIGATION-007 | legal_document_navigation | multi_hop | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-001 | equipment_maintenance | procedural | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-002 | equipment_maintenance | safety | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-003 | equipment_maintenance | factoid | One or more RAGAS metrics were not produced |
