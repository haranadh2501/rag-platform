# RAG Evaluation Report

Generated: `2026-06-21T17:09:56.105706+00:00`

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
- Mean latency: 18867.286 ms
- p95 latency: 23960.920 ms

## Batch

- Batch: 25 of 30
- Batch size: 5
- Case positions: 121 to 125
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
| healthcare_administration | 4 | - | - | - | - |
| legal_document_navigation | 1 | - | - | - | - |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| HEALTHCARE_ADMINISTRATION-005 | healthcare_administration | procedural | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-006 | healthcare_administration | procedural | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-007 | healthcare_administration | reasoning | One or more RAGAS metrics were not produced |
| LEGAL_DOCUMENT_NAVIGATION-001 | legal_document_navigation | factoid | One or more RAGAS metrics were not produced |
