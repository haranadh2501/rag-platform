# Evaluation Preflight Report

Generated: `2026-06-12T19:01:46.672379+00:00`
Status: **PASS**

## Dataset

- Cases: 118
- Applications: 12
- Answerable: 104
- Unanswerable: 14
- Validation errors: 0
- Validation warnings: 0

| Application | Cases |
|---|---:|
| bug_reporting | 30 |
| compliance_policy | 8 |
| customer_support | 8 |
| developer_documentation | 8 |
| education_assistant | 8 |
| employee_onboarding | 8 |
| equipment_maintenance | 8 |
| healthcare_administration | 8 |
| incident_response | 8 |
| it_helpdesk | 8 |
| legal_document_navigation | 8 |
| sales_enablement | 8 |

## Automated Tests

- Exit code: 0
- Passed: yes

```text
test_application_summary_groups_outputs (test_evaluation_dataset.EvaluationDatasetTests.test_application_summary_groups_outputs) ... ok
test_complete_application_suite_passes_validation (test_evaluation_dataset.EvaluationDatasetTests.test_complete_application_suite_passes_validation) ... ok
test_generated_dataset_passes_strict_validation (test_evaluation_dataset.EvaluationDatasetTests.test_generated_dataset_passes_strict_validation) ... ok
test_mock_response_detection_checks_metadata_and_answer (test_evaluation_dataset.EvaluationDatasetTests.test_mock_response_detection_checks_metadata_and_answer) ... ok
test_quality_gate_reports_failed_metric (test_evaluation_dataset.EvaluationDatasetTests.test_quality_gate_reports_failed_metric) ... ok
test_report_bundles_create_latest_files (test_evaluation_dataset.EvaluationDatasetTests.test_report_bundles_create_latest_files) ... ok
test_summary_separates_ragas_and_negative_cases (test_evaluation_dataset.EvaluationDatasetTests.test_summary_separates_ragas_and_negative_cases) ... ok
test_validator_rejects_duplicate_questions (test_evaluation_dataset.EvaluationDatasetTests.test_validator_rejects_duplicate_questions) ... ok
test_validator_rejects_reference_not_present_in_source (test_evaluation_dataset.EvaluationDatasetTests.test_validator_rejects_reference_not_present_in_source) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.425s

OK
```
