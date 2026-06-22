# RAG Evaluation Report

Generated: `2026-06-21T17:08:20.436727+00:00`

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
- Mean latency: 18199.028 ms
- p95 latency: 19700.020 ms

## Batch

- Batch: 24 of 30
- Batch size: 5
- Case positions: 116 to 120
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
| education_assistant | 1 | - | - | - | - |
| healthcare_administration | 4 | - | - | - | - |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| HEALTHCARE_ADMINISTRATION-001 | healthcare_administration | factoid | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-002 | healthcare_administration | procedural | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-003 | healthcare_administration | factoid | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-004 | healthcare_administration | safety | One or more RAGAS metrics were not produced |
