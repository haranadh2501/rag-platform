"""Tests for the synthetic evaluation dataset and validator."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evaluation.generate_bug_dataset import generate
from evaluation.run_eval import _is_mock_response, build_quality_gate, build_summary
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


if __name__ == "__main__":
    unittest.main()
