"""Tests for the synthetic evaluation dataset and validator."""
from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from evaluation.generate_application_suite import generate as generate_application_suite
from evaluation.generate_bug_dataset import generate
from evaluation.generate_kubernetes_dataset import generate as generate_kubernetes_dataset
from evaluation.reporting import write_evaluation_bundle, write_preflight_bundle
from evaluation.run_eval import (
    _is_mock_response,
    build_application_summaries,
    build_quality_gate,
    build_summary,
)
from evaluation.validate_dataset import validate_dataset


class EvaluationDatasetTests(unittest.TestCase):
    def test_generated_dataset_passes_strict_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "qa_dataset.jsonl"
            source_dir = root / "sources"
            generate(dataset, source_dir)

            report = validate_dataset(
                dataset,
                source_dir,
                strict_synthetic_profile=True,
            )

            self.assertTrue(report.is_valid, [issue.format() for issue in report.errors])
            self.assertEqual(len(report.cases), 30)
            self.assertGreaterEqual(
                sum(case["answerable"] for case in report.cases),
                24,
            )

    def test_complete_application_suite_passes_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "application_suite.jsonl"
            source_dir = root / "sources"
            generate_application_suite(dataset, source_dir)

            report = validate_dataset(dataset, source_dir, suite_profile=True)
            applications = Counter(case["application"] for case in report.cases)

            self.assertTrue(report.is_valid, [issue.format() for issue in report.errors])
            self.assertEqual(len(report.cases), 148)
            self.assertEqual(len(applications), 13)
            self.assertEqual(report.cases[0]["application"], "kubernetes_troubleshooting")
            self.assertEqual(applications["kubernetes_troubleshooting"], 30)
            self.assertEqual(applications["bug_reporting"], 30)
            self.assertTrue(all(count >= 8 for count in applications.values()))

    def test_kubernetes_dataset_passes_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "kubernetes_dataset.jsonl"
            source_dir = root / "sources"
            generate_kubernetes_dataset(dataset, source_dir)

            report = validate_dataset(dataset, source_dir)
            categories = Counter(case["category"] for case in report.cases)

            self.assertTrue(report.is_valid, [issue.format() for issue in report.errors])
            self.assertEqual(len(report.cases), 30)
            self.assertEqual(
                {case["application"] for case in report.cases},
                {"kubernetes_troubleshooting"},
            )
            self.assertGreaterEqual(sum(case["answerable"] for case in report.cases), 28)
            self.assertEqual(sum(not case["answerable"] for case in report.cases), 2)
            self.assertGreaterEqual(categories["multi_hop"], 4)
            self.assertGreaterEqual(categories["safety"], 2)

    def test_validator_rejects_reference_not_present_in_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "qa_dataset.jsonl"
            source_dir = root / "sources"
            generate(dataset, source_dir)

            cases = [
                json.loads(line)
                for line in dataset.read_text(encoding="utf-8").splitlines()
            ]
            cases[0]["reference_contexts"][0] = "This text is not in the source."
            dataset.write_text(
                "\n".join(json.dumps(case) for case in cases) + "\n",
                encoding="utf-8",
            )

            report = validate_dataset(dataset, source_dir)

            self.assertFalse(report.is_valid)
            self.assertTrue(
                any("not verbatim" in issue.message for issue in report.errors)
            )

    def test_validator_rejects_duplicate_questions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "qa_dataset.jsonl"
            source_dir = root / "sources"
            generate(dataset, source_dir)

            cases = [
                json.loads(line)
                for line in dataset.read_text(encoding="utf-8").splitlines()
            ]
            cases[1]["question"] = cases[0]["question"]
            dataset.write_text(
                "\n".join(json.dumps(case) for case in cases) + "\n",
                encoding="utf-8",
            )

            report = validate_dataset(dataset, source_dir)

            self.assertFalse(report.is_valid)
            self.assertTrue(
                any("Duplicate question" in issue.message for issue in report.errors)
            )

    def test_mock_response_detection_checks_metadata_and_answer(self) -> None:
        self.assertTrue(_is_mock_response({"answer": "ok", "metadata": {"mock": True}}))
        self.assertTrue(_is_mock_response({"answer": "This is a mock response"}))
        self.assertFalse(_is_mock_response({"answer": "Grounded production response"}))

    def test_summary_separates_ragas_and_negative_cases(self) -> None:
        outputs = [
            {
                "answerable": True,
                "contexts": ["retrieved context"],
                "requires_clarification": False,
                "answer": "Grounded answer",
                "latency_ms": 100.0,
            },
            {
                "answerable": False,
                "contexts": [],
                "requires_clarification": True,
                "answer": "I need more information.",
                "latency_ms": 300.0,
            },
        ]

        summary = build_summary(outputs, {"faithfulness": 0.9})

        self.assertEqual(summary["citation_coverage"], 1.0)
        self.assertEqual(summary["negative_abstention_rate"], 1.0)
        self.assertEqual(summary["latency_ms"]["mean"], 200.0)
        self.assertEqual(summary["ragas"]["faithfulness"], 0.9)

    def test_quality_gate_reports_failed_metric(self) -> None:
        gate = build_quality_gate(
            {
                "faithfulness": 0.90,
                "answer_relevancy": 0.79,
                "context_precision": 0.80,
                "context_recall": 0.85,
            },
            {
                "faithfulness": 0.85,
                "answer_relevancy": 0.80,
                "context_precision": 0.75,
                "context_recall": 0.80,
            },
        )

        self.assertFalse(gate["passed"])
        self.assertFalse(gate["checks"]["answer_relevancy"]["passed"])
        self.assertTrue(gate["checks"]["faithfulness"]["passed"])

    def test_application_summary_groups_outputs(self) -> None:
        outputs = [
            {
                "id": "A-1",
                "application": "alpha",
                "answerable": True,
                "contexts": ["context"],
                "requires_clarification": False,
                "answer": "answer",
                "latency_ms": 10.0,
            },
            {
                "id": "B-1",
                "application": "beta",
                "answerable": False,
                "contexts": [],
                "requires_clarification": True,
                "answer": "unknown",
                "latency_ms": 20.0,
            },
        ]
        scored = [
            {
                **outputs[0],
                "faithfulness": 0.9,
                "answer_relevancy": 0.8,
                "context_precision": 0.7,
                "context_recall": 0.6,
            }
        ]

        summaries = build_application_summaries(outputs, scored)

        self.assertEqual(set(summaries), {"alpha", "beta"})
        self.assertEqual(summaries["alpha"]["ragas"]["faithfulness"], 0.9)
        self.assertEqual(summaries["beta"]["negative_abstention_rate"], 1.0)

    def test_report_bundles_create_latest_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            results_dir = Path(temp_dir)
            evaluation_report = {
                "generated_at": "2026-06-13T00:00:00+00:00",
                "summary": {
                    "case_count": 1,
                    "citation_coverage": 1.0,
                    "negative_abstention_rate": 1.0,
                    "latency_ms": {"mean": 10.0, "p95": 10.0},
                    "quality_gate": {"checks": {}},
                    "applications": {},
                },
                "cases": [
                    {
                        "id": "TEST-1",
                        "application": "test",
                        "category": "factoid",
                        "answerable": True,
                        "question": "What is tested?",
                        "ground_truth": "Reports are tested.",
                        "answer": "Reports are tested.",
                    }
                ],
            }
            paths = write_evaluation_bundle(results_dir, evaluation_report)
            preflight_paths = write_preflight_bundle(
                results_dir,
                {
                    "generated_at": "2026-06-13T00:00:00+00:00",
                    "passed": True,
                    "dataset": {
                        "case_count": 1,
                        "application_count": 1,
                        "answerable_count": 1,
                        "unanswerable_count": 0,
                        "error_count": 0,
                        "warning_count": 0,
                        "applications": {"test": 1},
                    },
                    "tests": {"exit_code": 0, "passed": True, "output": "OK"},
                },
            )

            self.assertTrue(all(path.exists() for path in paths.values()))
            self.assertTrue(all(path.exists() for path in preflight_paths.values()))
            self.assertTrue((results_dir / "application_suite_eval_latest.html").exists())
            self.assertTrue((results_dir / "evaluation_preflight_latest.md").exists())


if __name__ == "__main__":
    unittest.main()
