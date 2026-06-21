# RAG Evaluation Report

Generated: `2026-06-21T14:59:21.866003+00:00`

## Aggregate Results

| Metric | Score | Threshold | Pass |
|---|---:|---:|:---:|
| faithfulness | 0.830 | 0.850 | no |
| answer_relevancy | 0.953 | 0.800 | yes |
| context_precision | 0.979 | 0.750 | yes |
| context_recall | 0.923 | 0.800 | yes |

- Cases: 148
- Citation coverage: 1.000
- Negative abstention rate: 0.000
- Mean latency: 43268.320 ms
- p95 latency: 49701.430 ms

## Application Results

| Application | Cases | Faithfulness | Relevancy | Context precision | Context recall |
|---|---:|---:|---:|---:|---:|
| bug_reporting | 30 | 0.941 | 0.956 | 0.975 | 1.000 |
| compliance_policy | 8 | 0.893 | 0.955 | 1.000 | 1.000 |
| customer_support | 8 | 0.690 | 0.948 | 0.976 | 0.857 |
| developer_documentation | 8 | 1.000 | 0.984 | 0.976 | 0.905 |
| education_assistant | 8 | 0.857 | 0.962 | 1.000 | 1.000 |
| employee_onboarding | 8 | 0.929 | 0.951 | 0.952 | 0.929 |
| equipment_maintenance | 8 | 1.000 | 0.948 | 1.000 | 0.857 |
| healthcare_administration | 8 | 0.798 | 0.974 | 1.000 | 0.905 |
| incident_response | 8 | 0.667 | 0.963 | 1.000 | 0.708 |
| it_helpdesk | 8 | 0.762 | 0.955 | 0.929 | 1.000 |
| kubernetes_troubleshooting | 30 | 0.653 | 0.930 | 0.982 | 0.871 |
| legal_document_navigation | 8 | 0.881 | 0.972 | 0.952 | 1.000 |
| sales_enablement | 8 | 0.905 | 0.946 | 0.976 | 0.857 |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| K8S-EVAL-001 | kubernetes_troubleshooting | factoid | One or more RAGAS metrics were not produced |
| K8S-EVAL-003 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-020 | kubernetes_troubleshooting | multi_hop | One or more RAGAS metrics were not produced |
| K8S-EVAL-021 | kubernetes_troubleshooting | factoid | One or more RAGAS metrics were not produced |
| K8S-EVAL-022 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-023 | kubernetes_troubleshooting | reasoning | One or more RAGAS metrics were not produced |
| K8S-EVAL-027 | kubernetes_troubleshooting | multi_hop | One or more RAGAS metrics were not produced |
| K8S-EVAL-028 | kubernetes_troubleshooting | safety | One or more RAGAS metrics were not produced |
| BUG-EVAL-005 | bug_reporting | reasoning | One or more RAGAS metrics were not produced |
| INCIDENT_RESPONSE-005 | incident_response | reasoning | One or more RAGAS metrics were not produced |
| COMPLIANCE_POLICY-002 | compliance_policy | factoid | One or more RAGAS metrics were not produced |
| EDUCATION_ASSISTANT-006 | education_assistant | procedural | One or more RAGAS metrics were not produced |
