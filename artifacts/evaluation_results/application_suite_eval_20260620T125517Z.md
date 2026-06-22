# RAG Evaluation Report

Generated: `2026-06-20T12:55:17.315154+00:00`

## Aggregate Results

| Metric | Score | Threshold | Pass |
|---|---:|---:|:---:|
| faithfulness | - | - | - |
| answer_relevancy | - | - | - |
| context_precision | - | - | - |
| context_recall | - | - | - |

- Cases: 148
- Citation coverage: 1.000
- Negative abstention rate: 1.000
- Mean latency: 6219.403 ms
- p95 latency: 11271.740 ms

## Application Results

| Application | Cases | Faithfulness | Relevancy | Context precision | Context recall |
|---|---:|---:|---:|---:|---:|
| bug_reporting | 30 | - | - | - | - |
| compliance_policy | 8 | - | - | - | - |
| customer_support | 8 | - | - | - | - |
| developer_documentation | 8 | - | - | - | - |
| education_assistant | 8 | - | - | - | - |
| employee_onboarding | 8 | - | - | - | - |
| equipment_maintenance | 8 | - | - | - | - |
| healthcare_administration | 8 | - | - | - | - |
| incident_response | 8 | - | - | - | - |
| it_helpdesk | 8 | - | - | - | - |
| kubernetes_troubleshooting | 30 | - | - | - | - |
| legal_document_navigation | 8 | - | - | - | - |
| sales_enablement | 8 | - | - | - | - |

## Failed or Unscored Cases

| ID | Application | Category | Notes |
|---|---|---|---|
| K8S-EVAL-001 | kubernetes_troubleshooting | factoid | One or more RAGAS metrics were not produced |
| K8S-EVAL-002 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-003 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-004 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-005 | kubernetes_troubleshooting | factoid | One or more RAGAS metrics were not produced |
| K8S-EVAL-006 | kubernetes_troubleshooting | factoid | One or more RAGAS metrics were not produced |
| K8S-EVAL-007 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-008 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-009 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-010 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-011 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-012 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-013 | kubernetes_troubleshooting | factoid | One or more RAGAS metrics were not produced |
| K8S-EVAL-014 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-015 | kubernetes_troubleshooting | reasoning | One or more RAGAS metrics were not produced |
| K8S-EVAL-016 | kubernetes_troubleshooting | safety | One or more RAGAS metrics were not produced |
| K8S-EVAL-017 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-018 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-019 | kubernetes_troubleshooting | reasoning | One or more RAGAS metrics were not produced |
| K8S-EVAL-020 | kubernetes_troubleshooting | multi_hop | One or more RAGAS metrics were not produced |
| K8S-EVAL-021 | kubernetes_troubleshooting | factoid | One or more RAGAS metrics were not produced |
| K8S-EVAL-022 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-023 | kubernetes_troubleshooting | reasoning | One or more RAGAS metrics were not produced |
| K8S-EVAL-024 | kubernetes_troubleshooting | procedural | One or more RAGAS metrics were not produced |
| K8S-EVAL-025 | kubernetes_troubleshooting | multi_hop | One or more RAGAS metrics were not produced |
| K8S-EVAL-026 | kubernetes_troubleshooting | multi_hop | One or more RAGAS metrics were not produced |
| K8S-EVAL-027 | kubernetes_troubleshooting | multi_hop | One or more RAGAS metrics were not produced |
| K8S-EVAL-028 | kubernetes_troubleshooting | safety | One or more RAGAS metrics were not produced |
| BUG-EVAL-001 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-002 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-003 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-004 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-005 | bug_reporting | reasoning | One or more RAGAS metrics were not produced |
| BUG-EVAL-006 | bug_reporting | procedural | One or more RAGAS metrics were not produced |
| BUG-EVAL-007 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-008 | bug_reporting | safety | One or more RAGAS metrics were not produced |
| BUG-EVAL-009 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-010 | bug_reporting | reasoning | One or more RAGAS metrics were not produced |
| BUG-EVAL-011 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-012 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-013 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-014 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-015 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-016 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-017 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-018 | bug_reporting | procedural | One or more RAGAS metrics were not produced |
| BUG-EVAL-019 | bug_reporting | multi_hop | One or more RAGAS metrics were not produced |
| BUG-EVAL-021 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-022 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-023 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-024 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-025 | bug_reporting | procedural | One or more RAGAS metrics were not produced |
| BUG-EVAL-026 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-027 | bug_reporting | factoid | One or more RAGAS metrics were not produced |
| BUG-EVAL-028 | bug_reporting | procedural | One or more RAGAS metrics were not produced |
| IT_HELPDESK-001 | it_helpdesk | factoid | One or more RAGAS metrics were not produced |
| IT_HELPDESK-002 | it_helpdesk | procedural | One or more RAGAS metrics were not produced |
| IT_HELPDESK-003 | it_helpdesk | procedural | One or more RAGAS metrics were not produced |
| IT_HELPDESK-004 | it_helpdesk | factoid | One or more RAGAS metrics were not produced |
| IT_HELPDESK-005 | it_helpdesk | reasoning | One or more RAGAS metrics were not produced |
| IT_HELPDESK-006 | it_helpdesk | procedural | One or more RAGAS metrics were not produced |
| IT_HELPDESK-007 | it_helpdesk | multi_hop | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-001 | customer_support | factoid | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-002 | customer_support | factoid | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-003 | customer_support | procedural | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-004 | customer_support | factoid | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-005 | customer_support | procedural | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-006 | customer_support | procedural | One or more RAGAS metrics were not produced |
| CUSTOMER_SUPPORT-007 | customer_support | multi_hop | One or more RAGAS metrics were not produced |
| EMPLOYEE_ONBOARDING-001 | employee_onboarding | factoid | One or more RAGAS metrics were not produced |
| EMPLOYEE_ONBOARDING-002 | employee_onboarding | procedural | One or more RAGAS metrics were not produced |
| EMPLOYEE_ONBOARDING-003 | employee_onboarding | factoid | One or more RAGAS metrics were not produced |
| EMPLOYEE_ONBOARDING-004 | employee_onboarding | factoid | One or more RAGAS metrics were not produced |
| EMPLOYEE_ONBOARDING-005 | employee_onboarding | factoid | One or more RAGAS metrics were not produced |
| EMPLOYEE_ONBOARDING-006 | employee_onboarding | procedural | One or more RAGAS metrics were not produced |
| EMPLOYEE_ONBOARDING-007 | employee_onboarding | reasoning | One or more RAGAS metrics were not produced |
| DEVELOPER_DOCUMENTATION-001 | developer_documentation | factoid | One or more RAGAS metrics were not produced |
| DEVELOPER_DOCUMENTATION-002 | developer_documentation | factoid | One or more RAGAS metrics were not produced |
| DEVELOPER_DOCUMENTATION-003 | developer_documentation | factoid | One or more RAGAS metrics were not produced |
| DEVELOPER_DOCUMENTATION-004 | developer_documentation | factoid | One or more RAGAS metrics were not produced |
| DEVELOPER_DOCUMENTATION-005 | developer_documentation | factoid | One or more RAGAS metrics were not produced |
| DEVELOPER_DOCUMENTATION-006 | developer_documentation | procedural | One or more RAGAS metrics were not produced |
| DEVELOPER_DOCUMENTATION-007 | developer_documentation | multi_hop | One or more RAGAS metrics were not produced |
| INCIDENT_RESPONSE-001 | incident_response | factoid | One or more RAGAS metrics were not produced |
| INCIDENT_RESPONSE-002 | incident_response | factoid | One or more RAGAS metrics were not produced |
| INCIDENT_RESPONSE-003 | incident_response | procedural | One or more RAGAS metrics were not produced |
| INCIDENT_RESPONSE-004 | incident_response | factoid | One or more RAGAS metrics were not produced |
| INCIDENT_RESPONSE-005 | incident_response | reasoning | One or more RAGAS metrics were not produced |
| INCIDENT_RESPONSE-006 | incident_response | procedural | One or more RAGAS metrics were not produced |
| INCIDENT_RESPONSE-007 | incident_response | multi_hop | One or more RAGAS metrics were not produced |
| COMPLIANCE_POLICY-001 | compliance_policy | factoid | One or more RAGAS metrics were not produced |
| COMPLIANCE_POLICY-002 | compliance_policy | factoid | One or more RAGAS metrics were not produced |
| COMPLIANCE_POLICY-003 | compliance_policy | factoid | One or more RAGAS metrics were not produced |
| COMPLIANCE_POLICY-004 | compliance_policy | procedural | One or more RAGAS metrics were not produced |
| COMPLIANCE_POLICY-005 | compliance_policy | factoid | One or more RAGAS metrics were not produced |
| COMPLIANCE_POLICY-006 | compliance_policy | reasoning | One or more RAGAS metrics were not produced |
| COMPLIANCE_POLICY-007 | compliance_policy | multi_hop | One or more RAGAS metrics were not produced |
| EDUCATION_ASSISTANT-001 | education_assistant | factoid | One or more RAGAS metrics were not produced |
| EDUCATION_ASSISTANT-002 | education_assistant | factoid | One or more RAGAS metrics were not produced |
| EDUCATION_ASSISTANT-003 | education_assistant | reasoning | One or more RAGAS metrics were not produced |
| EDUCATION_ASSISTANT-004 | education_assistant | factoid | One or more RAGAS metrics were not produced |
| EDUCATION_ASSISTANT-005 | education_assistant | factoid | One or more RAGAS metrics were not produced |
| EDUCATION_ASSISTANT-006 | education_assistant | procedural | One or more RAGAS metrics were not produced |
| EDUCATION_ASSISTANT-007 | education_assistant | multi_hop | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-001 | healthcare_administration | factoid | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-002 | healthcare_administration | procedural | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-003 | healthcare_administration | factoid | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-004 | healthcare_administration | safety | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-005 | healthcare_administration | procedural | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-006 | healthcare_administration | procedural | One or more RAGAS metrics were not produced |
| HEALTHCARE_ADMINISTRATION-007 | healthcare_administration | reasoning | One or more RAGAS metrics were not produced |
| LEGAL_DOCUMENT_NAVIGATION-001 | legal_document_navigation | factoid | One or more RAGAS metrics were not produced |
| LEGAL_DOCUMENT_NAVIGATION-002 | legal_document_navigation | factoid | One or more RAGAS metrics were not produced |
| LEGAL_DOCUMENT_NAVIGATION-003 | legal_document_navigation | factoid | One or more RAGAS metrics were not produced |
| LEGAL_DOCUMENT_NAVIGATION-004 | legal_document_navigation | factoid | One or more RAGAS metrics were not produced |
| LEGAL_DOCUMENT_NAVIGATION-005 | legal_document_navigation | factoid | One or more RAGAS metrics were not produced |
| LEGAL_DOCUMENT_NAVIGATION-006 | legal_document_navigation | procedural | One or more RAGAS metrics were not produced |
| LEGAL_DOCUMENT_NAVIGATION-007 | legal_document_navigation | multi_hop | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-001 | equipment_maintenance | procedural | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-002 | equipment_maintenance | safety | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-003 | equipment_maintenance | factoid | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-004 | equipment_maintenance | procedural | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-005 | equipment_maintenance | safety | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-006 | equipment_maintenance | factoid | One or more RAGAS metrics were not produced |
| EQUIPMENT_MAINTENANCE-007 | equipment_maintenance | multi_hop | One or more RAGAS metrics were not produced |
| SALES_ENABLEMENT-001 | sales_enablement | factoid | One or more RAGAS metrics were not produced |
| SALES_ENABLEMENT-002 | sales_enablement | factoid | One or more RAGAS metrics were not produced |
| SALES_ENABLEMENT-003 | sales_enablement | factoid | One or more RAGAS metrics were not produced |
| SALES_ENABLEMENT-004 | sales_enablement | safety | One or more RAGAS metrics were not produced |
| SALES_ENABLEMENT-005 | sales_enablement | reasoning | One or more RAGAS metrics were not produced |
| SALES_ENABLEMENT-006 | sales_enablement | procedural | One or more RAGAS metrics were not produced |
| SALES_ENABLEMENT-007 | sales_enablement | multi_hop | One or more RAGAS metrics were not produced |
