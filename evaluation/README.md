# Multi-Application RAG Evaluation

This module provides synthetic knowledge bases, test cases, validation,
live-system execution, RAGAS scoring, quality gates, and automatic reports.

The combined suite contains **148 cases across 13 applications**. Kubernetes
troubleshooting is generated first, so smoke runs with `--max-cases` exercise it
before the other domains.

| Application | Purpose | Cases |
|---|---|---:|
| `kubernetes_troubleshooting` | Pods, networking, storage, managed K8s, post-mortem patterns | 30 |
| `bug_reporting` | Triage, known issues, severity, evidence | 30 |
| `it_helpdesk` | Password, VPN, MFA, devices, software | 8 |
| `customer_support` | Warranty, returns, troubleshooting | 8 |
| `employee_onboarding` | First-day, training, leave, information handling | 8 |
| `developer_documentation` | API, SDK, errors, webhooks | 8 |
| `incident_response` | Declaration, recovery, evidence, review | 8 |
| `compliance_policy` | Classification, retention, vendors, breaches | 8 |
| `education_assistant` | Assessment, labs, projects, integrity | 8 |
| `healthcare_administration` | Scheduling, records, billing, privacy | 8 |
| `legal_document_navigation` | Synthetic clause location and summary | 8 |
| `equipment_maintenance` | Inspection, lockout, temperature, service | 8 |
| `sales_enablement` | Plans, trials, discounts, approved claims | 8 |

Healthcare cases are administrative only. Legal cases use a fully synthetic
agreement and test clause navigation rather than legal advice.

## Metrics

The live runner calculates:

- Faithfulness
- Answer relevancy
- Context precision
- Context recall

It also reports citation coverage, negative-case abstention, mean/p95 latency,
the system-provided faithfulness score, aggregate quality gates, and
per-application metrics.

## Quick Preflight

This command regenerates all synthetic data, validates every reference context,
runs the evaluation unit tests, and writes JSON and Markdown readiness reports:

```powershell
python -m evaluation.run_test_suite
```

Reports are written to `artifacts/evaluation_results/`, including stable
`evaluation_preflight_latest.json` and `evaluation_preflight_latest.md` files.

## Live Evaluation

After the source documents are ingested and `MOCK_N8N=false`:

```powershell
$env:EVAL_BASE_URL = "http://localhost:8000"
$env:EVAL_EMAIL = "admin@iisc-demo.com"
$env:EVAL_PASSWORD = "your-password"
$env:OPENAI_API_KEY = "independent-evaluator-key"

python -m evaluation.run_eval --suite-dataset --enforce-thresholds
```

To evaluate a source-returning n8n retrieval webhook directly, bypassing the
FastAPI backend:

```powershell
$env:EVAL_N8N_URL = "https://<n8n-service>/webhook/retrieve"
$env:EVAL_TENANT_ID = "<tenant-id-visible-to-ingested-docs>"

python -m evaluation.run_eval --suite-dataset `
  --n8n-url $env:EVAL_N8N_URL `
  --n8n-tenant-id $env:EVAL_TENANT_ID
```

For slow or flaky public webhooks, split the suite into deterministic batches.
Batch indices are 1-based:

```powershell
python -m evaluation.run_eval --suite-dataset `
  --n8n-url $env:EVAL_N8N_URL `
  --n8n-tenant-id $env:EVAL_TENANT_ID `
  --batch-size 10 `
  --batch-index 1
```

Each report includes an `Observability` section with source return rate,
average sources per case, metadata coverage, retry count, and max attempts.

Each run automatically writes timestamped and `latest` versions of:

- JSON: complete machine-readable results
- CSV: one row per case
- Markdown: review-friendly summary
- HTML: browser-friendly report

Use `--application it_helpdesk` to test one application. Repeat the argument to
select several applications.

Use `--application kubernetes_troubleshooting` to run only the Kubernetes
troubleshooting priority suite.

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for the complete workflow.
