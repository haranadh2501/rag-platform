# Evaluation Testing Guide

## 1. What Is Tested

The suite tests retrieval and answer generation across 13 application domains.
Kubernetes troubleshooting is first in the generated dataset, so small
connectivity checks exercise it before the other domains.
Every answerable case contains:

- A question
- A reference answer
- One or more verbatim reference contexts
- Expected source document and section
- Application and question category

Every application also contains an unanswerable question. These cases test
whether the system abstains instead of inventing information.

## 2. Files

| File | Purpose |
|---|---|
| `generate_application_suite.py` | Generates all source documents and 148 cases |
| `generate_kubernetes_dataset.py` | Generates the Kubernetes priority dataset |
| `application_suite.jsonl` | Combined benchmark |
| `sample-data/<application>/` | Documents to ingest |
| `validate_dataset.py` | Structural and grounding validation |
| `run_test_suite.py` | Regeneration, validation, tests, preflight report |
| `run_eval.py` | Live API collection and RAGAS evaluation |
| `reporting.py` | JSON, CSV, Markdown, and HTML reports |
| `requirements.txt` | Evaluation-only dependencies |

The standalone 30-case Kubernetes troubleshooting dataset is available as
`kubernetes_dataset.jsonl`. The original 30-case bug-reporting dataset remains
available as `qa_dataset.jsonl`.

## 3. Install Dependencies

From the repository root:

```powershell
pip install -r backend/requirements.txt
pip install -r evaluation/requirements.txt
```

The pinned RAGAS version uses an evaluator LLM and embeddings. Set
`OPENAI_API_KEY` for that independent evaluator. The API's own Gemini
faithfulness score is stored separately as `system_faithfulness` and is not used
as the independent grade.

## 4. Generate Synthetic Data

```powershell
python -m evaluation.generate_application_suite
```

Expected output:

```text
Generated 148 cases across 13 applications
```

Generation is deterministic. Running it again should produce the same source
documents and dataset.

## 5. Validate the Dataset

```powershell
python -m evaluation.validate_dataset --suite
```

Validation checks:

1. Required fields and data types
2. Unique IDs and questions
3. All 13 applications are present
4. Minimum eight cases per application
5. At least one unanswerable case per application
6. Expected source files and section names exist
7. Reference contexts occur verbatim in the declared files
8. No source path escapes `evaluation/sample-data`

Expected result:

```text
Validated 148 cases: 0 errors, 0 warnings
```

## 6. Run Automated Preflight

```powershell
python -m evaluation.run_test_suite
```

This performs generation, suite validation, unit-test discovery, and automatic
report creation. It exits non-zero if validation or tests fail.

Generated files:

```text
artifacts/evaluation_results/evaluation_preflight_<timestamp>.json
artifacts/evaluation_results/evaluation_preflight_<timestamp>.md
artifacts/evaluation_results/evaluation_preflight_latest.json
artifacts/evaluation_results/evaluation_preflight_latest.md
```

Use `--skip-generate` when testing a manually edited dataset:

```powershell
python -m evaluation.run_test_suite --skip-generate
```

## 7. Prepare the RAG System

The current evaluation suite assumes the documents are visible to the tenant
used by the evaluation credentials.

For a combined benchmark tenant:

1. Create or choose an evaluation tenant.
2. Upload every `.txt` file under `evaluation/sample-data/`.
3. Wait until every document has status `completed`.
4. Confirm `MOCK_N8N=false`.
5. Ask one known question manually and verify that real source chunks are
   returned.

For stronger isolation testing, create one tenant per application and run the
runner separately with `--application`.

Do not run scored evaluation against `MOCK_N8N=true`. The runner rejects mock
responses by default.

## 8. Configure Credentials

Use an existing token:

```powershell
$env:EVAL_BEARER_TOKEN = "<jwt>"
```

Or allow the runner to log in:

```powershell
$env:EVAL_EMAIL = "admin@iisc-demo.com"
$env:EVAL_PASSWORD = "<password>"
```

Set the endpoint and evaluator key:

```powershell
$env:EVAL_BASE_URL = "http://localhost:8000"
$env:OPENAI_API_KEY = "<independent-evaluator-key>"
```

## 9. Run Live Tests

Run all applications:

```powershell
python -m evaluation.run_eval --suite-dataset
```

Run one application:

```powershell
python -m evaluation.run_eval --suite-dataset --application it_helpdesk
```

Run the Kubernetes priority suite:

```powershell
python -m evaluation.run_eval --suite-dataset --application kubernetes_troubleshooting
```

Run several applications:

```powershell
python -m evaluation.run_eval --suite-dataset `
  --application customer_support `
  --application equipment_maintenance
```

Run a small connectivity check without RAGAS:

```powershell
python -m evaluation.run_eval --suite-dataset --skip-ragas --max-cases 3
```

Fixed mock responses are accepted only for explicit plumbing tests:

```powershell
python -m evaluation.run_eval --suite-dataset --skip-ragas --allow-mock --max-cases 3
```

Mock results must never be used as quality evidence.

## 10. Quality Gates

Enable pass/fail thresholds:

```powershell
python -m evaluation.run_eval --suite-dataset --enforce-thresholds
```

Defaults:

| Metric | Minimum |
|---|---:|
| Faithfulness | 0.85 |
| Answer relevancy | 0.80 |
| Context precision | 0.75 |
| Context recall | 0.80 |

Override a threshold:

```powershell
python -m evaluation.run_eval --suite-dataset --enforce-thresholds `
  --min-context-recall 0.85
```

Exit codes:

| Code | Meaning |
|---:|---|
| `0` | Evaluation completed and enabled gates passed |
| `2` | Dataset validation or application selection failed |
| `3` | One or more quality gates failed |
| Other | API, dependency, authentication, or evaluator failure |

## 11. Live Reports

Every live run creates:

```text
application_suite_eval_<timestamp>.json
application_suite_eval_<timestamp>.csv
application_suite_eval_<timestamp>.md
application_suite_eval_<timestamp>.html
```

Stable `application_suite_eval_latest.*` copies are updated automatically.

The aggregate report includes:

- Four RAGAS averages
- Threshold results
- Per-application metric averages
- Citation coverage
- Negative abstention rate
- Mean, p95, and maximum latency
- Per-case answers and scores

## 12. Interpreting Failures

Low context recall usually means the expected evidence was not retrieved. Check
chunking, query embeddings, tenant filters, and top-K.

Low context precision means irrelevant chunks are ranked too highly. Check
reranking, chunk size, duplicated content, and metadata filters.

Low faithfulness means the answer contains claims unsupported by retrieved
chunks. Tighten the generation prompt, citation requirements, or fallback.

Low answer relevancy means the answer is grounded but does not directly answer
the question. Check query understanding, conversation history, and answer style.

Failures concentrated in one application are more actionable than a single
aggregate score. Use the report's per-application table before changing the
whole retrieval pipeline.
