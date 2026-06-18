"""Validate an evaluation JSONL file and its source grounding."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "application_suite.jsonl"
DEFAULT_SOURCE_DIR = ROOT / "sample-data"
EXPECTED_APPLICATIONS = {
    "kubernetes_troubleshooting",
    "bug_reporting",
    "it_helpdesk",
    "customer_support",
    "employee_onboarding",
    "developer_documentation",
    "incident_response",
    "compliance_policy",
    "education_assistant",
    "healthcare_administration",
    "legal_document_navigation",
    "equipment_maintenance",
    "sales_enablement",
}
REQUIRED_FIELDS = {
    "id",
    "application",
    "question",
    "ground_truth",
    "reference_contexts",
    "expected_sources",
    "category",
    "answerable",
    "tags",
}


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    message: str
    case_id: str | None = None

    def format(self) -> str:
        prefix = f"[{self.level.upper()}]"
        location = f" {self.case_id}:" if self.case_id else ""
        return f"{prefix}{location} {self.message}"


@dataclass
class ValidationReport:
    cases: list[dict[str, Any]]
    issues: list[ValidationIssue]

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.level == "warning"]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[ValidationIssue]]:
    cases: list[dict[str, Any]] = []
    issues: list[ValidationIssue] = []
    if not path.exists():
        return [], [ValidationIssue("error", f"Dataset does not exist: {path}")]

    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                issues.append(
                    ValidationIssue(
                        "error",
                        f"Invalid JSON on line {line_number}: {exc.msg}",
                    )
                )
                continue
            if not isinstance(value, dict):
                issues.append(
                    ValidationIssue(
                        "error",
                        f"Line {line_number} must contain a JSON object",
                    )
                )
                continue
            cases.append(value)
    return cases, issues


def _safe_source_path(source_dir: Path, document: str) -> Path | None:
    root = source_dir.resolve()
    candidate = (source_dir / document).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def validate_dataset(
    dataset_path: Path = DEFAULT_DATASET,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    *,
    strict_synthetic_profile: bool = False,
    suite_profile: bool = False,
) -> ValidationReport:
    cases, issues = load_jsonl(dataset_path)
    ids: set[str] = set()
    questions: set[str] = set()
    source_cache: dict[Path, str] = {}

    for index, case in enumerate(cases, start=1):
        case_id = case.get("id") if isinstance(case.get("id"), str) else f"line-{index}"
        missing = REQUIRED_FIELDS - set(case)
        if missing:
            issues.append(
                ValidationIssue(
                    "error",
                    f"Missing fields: {', '.join(sorted(missing))}",
                    case_id,
                )
            )
            continue

        if not isinstance(case["id"], str) or not case["id"].strip():
            issues.append(ValidationIssue("error", "id must be a non-empty string", case_id))
        elif case["id"] in ids:
            issues.append(ValidationIssue("error", "Duplicate id", case_id))
        else:
            ids.add(case["id"])

        question = case["question"]
        if not isinstance(question, str) or len(question.strip()) < 10:
            issues.append(ValidationIssue("error", "question is too short", case_id))
        elif question.casefold() in questions:
            issues.append(ValidationIssue("error", "Duplicate question", case_id))
        else:
            questions.add(question.casefold())

        ground_truth = case["ground_truth"]
        if not isinstance(ground_truth, str) or len(ground_truth.strip()) < 10:
            issues.append(ValidationIssue("error", "ground_truth is too short", case_id))

        if not isinstance(case["category"], str) or not case["category"].strip():
            issues.append(ValidationIssue("error", "category must be a non-empty string", case_id))
        if not isinstance(case["application"], str) or not case["application"].strip():
            issues.append(ValidationIssue("error", "application must be a non-empty string", case_id))
        if not isinstance(case["answerable"], bool):
            issues.append(ValidationIssue("error", "answerable must be boolean", case_id))
            continue
        if not isinstance(case["tags"], list) or not all(isinstance(tag, str) for tag in case["tags"]):
            issues.append(ValidationIssue("error", "tags must be a list of strings", case_id))

        contexts = case["reference_contexts"]
        expected_sources = case["expected_sources"]
        if not isinstance(contexts, list) or not all(
            isinstance(context, str) and context.strip() for context in contexts
        ):
            issues.append(
                ValidationIssue("error", "reference_contexts must be a list of non-empty strings", case_id)
            )
            continue
        if not isinstance(expected_sources, list) or not all(
            isinstance(source, dict)
            and isinstance(source.get("document"), str)
            and isinstance(source.get("section"), str)
            for source in expected_sources
        ):
            issues.append(
                ValidationIssue(
                    "error",
                    "expected_sources must contain document and section strings",
                    case_id,
                )
            )
            continue

        if case["answerable"]:
            if not contexts:
                issues.append(ValidationIssue("error", "answerable case has no reference context", case_id))
            if not expected_sources:
                issues.append(ValidationIssue("error", "answerable case has no expected source", case_id))
            if len(contexts) != len(expected_sources):
                issues.append(
                    ValidationIssue(
                        "error",
                        "reference_contexts and expected_sources must have equal length",
                        case_id,
                    )
                )
        elif contexts or expected_sources:
            issues.append(
                ValidationIssue(
                    "error",
                    "unanswerable case must not declare reference contexts or expected sources",
                    case_id,
                )
            )

        for position, source in enumerate(expected_sources):
            source_path = _safe_source_path(source_dir, source["document"])
            if source_path is None:
                issues.append(ValidationIssue("error", "source document escapes source directory", case_id))
                continue
            if not source_path.is_file():
                issues.append(
                    ValidationIssue("error", f"source document not found: {source['document']}", case_id)
                )
                continue
            if source_path not in source_cache:
                source_cache[source_path] = source_path.read_text(encoding="utf-8")
            if position < len(contexts) and contexts[position] not in source_cache[source_path]:
                issues.append(
                    ValidationIssue(
                        "error",
                        f"reference context is not verbatim in {source['document']}",
                        case_id,
                    )
                )
            if f"Section: {source['section']}" not in source_cache[source_path]:
                issues.append(
                    ValidationIssue(
                        "error",
                        f"section not found in {source['document']}: {source['section']}",
                        case_id,
                    )
                )

    if strict_synthetic_profile:
        if len(cases) != 30:
            issues.append(ValidationIssue("error", f"Expected 30 cases, found {len(cases)}"))
        answerable_count = sum(case.get("answerable") is True for case in cases)
        unanswerable_count = sum(case.get("answerable") is False for case in cases)
        if answerable_count < 24:
            issues.append(ValidationIssue("error", "Expected at least 24 answerable cases"))
        if unanswerable_count < 3:
            issues.append(ValidationIssue("error", "Expected at least 3 unanswerable cases"))
        categories = Counter(case.get("category") for case in cases)
        for required in ("factoid", "procedural", "reasoning", "multi_hop", "unanswerable"):
            if not categories[required]:
                issues.append(ValidationIssue("error", f"Missing category: {required}"))

    if suite_profile:
        applications = Counter(case.get("application") for case in cases)
        if len(cases) != 148:
            issues.append(ValidationIssue("error", f"Expected 148 suite cases, found {len(cases)}"))
        missing_applications = EXPECTED_APPLICATIONS - set(applications)
        unexpected_applications = set(applications) - EXPECTED_APPLICATIONS
        if missing_applications:
            issues.append(
                ValidationIssue(
                    "error",
                    f"Missing applications: {', '.join(sorted(missing_applications))}",
                )
            )
        if unexpected_applications:
            issues.append(
                ValidationIssue(
                    "error",
                    f"Unexpected applications: {', '.join(sorted(unexpected_applications))}",
                )
            )
        for application in EXPECTED_APPLICATIONS:
            if applications[application] < 8:
                issues.append(
                    ValidationIssue(
                        "error",
                        f"Application {application} has fewer than 8 cases",
                    )
                )
            app_cases = [case for case in cases if case.get("application") == application]
            if not any(case.get("answerable") is False for case in app_cases):
                issues.append(
                    ValidationIssue(
                        "error",
                        f"Application {application} has no unanswerable case",
                    )
                )

    if not cases:
        issues.append(ValidationIssue("error", "Dataset contains no cases"))
    return ValidationReport(cases=cases, issues=issues)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--strict", action="store_true", help="Enforce the bundled 30-case profile")
    parser.add_argument(
        "--suite",
        action="store_true",
        help="Enforce the complete 118-case, 12-application profile",
    )
    args = parser.parse_args()

    report = validate_dataset(
        args.dataset,
        args.source_dir,
        strict_synthetic_profile=args.strict,
        suite_profile=args.suite,
    )
    for issue in report.issues:
        print(issue.format())
    print(
        f"Validated {len(report.cases)} cases: "
        f"{len(report.errors)} errors, {len(report.warnings)} warnings"
    )
    raise SystemExit(0 if report.is_valid else 1)


if __name__ == "__main__":
    main()
