"""Regenerate, validate, test, and report the complete evaluation suite."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from evaluation.generate_application_suite import (
    DEFAULT_DATASET,
    DEFAULT_SOURCE_DIR,
    generate,
)
from evaluation.reporting import write_preflight_bundle
from evaluation.validate_dataset import validate_dataset


ROOT = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = ROOT.parent / "artifacts" / "evaluation_results"


def build_dataset_summary(cases: list[dict], error_count: int, warning_count: int) -> dict:
    applications = Counter(case["application"] for case in cases)
    categories = Counter(case["category"] for case in cases)
    return {
        "case_count": len(cases),
        "application_count": len(applications),
        "answerable_count": sum(case["answerable"] for case in cases),
        "unanswerable_count": sum(not case["answerable"] for case in cases),
        "applications": dict(sorted(applications.items())),
        "categories": dict(sorted(categories.items())),
        "error_count": error_count,
        "warning_count": warning_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--skip-generate", action="store_true")
    args = parser.parse_args()

    if not args.skip_generate:
        generate(args.dataset, args.source_dir)

    validation = validate_dataset(
        args.dataset,
        args.source_dir,
        suite_profile=True,
    )
    test_process = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_evaluation*.py",
            "-v",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    test_output = "\n".join(
        part for part in (test_process.stdout, test_process.stderr) if part
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": validation.is_valid and test_process.returncode == 0,
        "dataset": build_dataset_summary(
            validation.cases,
            len(validation.errors),
            len(validation.warnings),
        ),
        "validation_issues": [issue.format() for issue in validation.issues],
        "tests": {
            "passed": test_process.returncode == 0,
            "exit_code": test_process.returncode,
            "output": test_output,
        },
    }
    paths = write_preflight_bundle(args.results_dir, report)
    print(json.dumps(report["dataset"], indent=2))
    for kind, path in paths.items():
        print(f"{kind.title()} report: {path}")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
