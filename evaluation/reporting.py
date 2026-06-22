"""Report rendering helpers for evaluation and preflight runs."""
from __future__ import annotations

import csv
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def local_stamp() -> str:
    """Local-time stamp for human-facing artifact filenames.

    Uses the machine's local timezone (no trailing 'Z', which would imply UTC).
    """
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")


# Back-compat alias: callers/imports that still say utc_stamp get local time now.
utc_stamp = local_stamp


def _format_score(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.3f}"
    return "-"


def render_evaluation_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# RAG Evaluation Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Aggregate Results",
        "",
        "| Metric | Score | Threshold | Pass |",
        "|---|---:|---:|:---:|",
    ]
    gate_checks = summary.get("quality_gate", {}).get("checks", {})
    for metric in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
        check = gate_checks.get(metric, {})
        passed = check.get("passed")
        lines.append(
            f"| {metric} | {_format_score(check.get('score'))} | "
            f"{_format_score(check.get('threshold'))} | "
            f"{'yes' if passed is True else 'no' if passed is False else '-'} |"
        )
    lines.extend(
        [
            "",
            f"- Cases: {summary.get('case_count', 0)}",
            f"- Citation coverage: {_format_score(summary.get('citation_coverage'))}",
            f"- Negative abstention rate: {_format_score(summary.get('negative_abstention_rate'))}",
            f"- Mean latency: {_format_score(summary.get('latency_ms', {}).get('mean'))} ms",
            f"- p95 latency: {_format_score(summary.get('latency_ms', {}).get('p95'))} ms",
        "",
        ]
    )
    batch = summary.get("batch")
    if batch:
        lines.extend(
            [
                "## Batch",
                "",
                f"- Batch: {batch.get('batch_index')} of {batch.get('total_batches')}",
                f"- Batch size: {batch.get('batch_size')}",
                f"- Case positions: {batch.get('start_position')} to {batch.get('end_position')}",
                f"- Total cases before batching: {batch.get('total_cases_before_batching')}",
                "",
            ]
        )
    observability = summary.get("observability") or {}
    lines.extend(
        [
            "## Observability",
            "",
            "| Signal | Value |",
            "|---|---:|",
            f"| Source return rate | {_format_score(observability.get('source_return_rate'))} |",
            f"| Average sources per case | {_format_score(observability.get('average_sources_per_case'))} |",
            f"| Metadata coverage | {_format_score(observability.get('metadata_coverage'))} |",
            f"| Total retry count | {observability.get('total_retry_count', 0)} |",
            f"| Max attempts | {observability.get('max_attempts', 1)} |",
            "",
            "## Application Results",
            "",
            "| Application | Cases | Faithfulness | Relevancy | Context precision | Context recall |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for application, values in sorted(summary.get("applications", {}).items()):
        ragas = values.get("ragas") or {}
        lines.append(
            f"| {application} | {values.get('case_count', 0)} | "
            f"{_format_score(ragas.get('faithfulness'))} | "
            f"{_format_score(ragas.get('answer_relevancy'))} | "
            f"{_format_score(ragas.get('context_precision'))} | "
            f"{_format_score(ragas.get('context_recall'))} |"
        )
    lines.extend(
        [
            "",
            "## Failed or Unscored Cases",
            "",
            "| ID | Application | Category | Notes |",
            "|---|---|---|---|",
        ]
    )
    failures = 0
    for case in report["cases"]:
        scores = [case.get(metric) for metric in ("faithfulness", "answer_relevancy", "context_precision", "context_recall")]
        if case.get("answerable") and any(score is None for score in scores):
            failures += 1
            lines.append(
                f"| {case['id']} | {case['application']} | {case['category']} | "
                "One or more RAGAS metrics were not produced |"
            )
    if not failures:
        lines.append("| - | - | - | None |")
    return "\n".join(lines) + "\n"


def render_evaluation_html(markdown_report: str) -> str:
    escaped = html.escape(markdown_report)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<title>RAG Evaluation Report</title>"
        "<style>body{font-family:system-ui;max-width:1100px;margin:2rem auto;"
        "padding:0 1rem}pre{white-space:pre-wrap;line-height:1.45}</style>"
        f"</head><body><pre>{escaped}</pre></body></html>\n"
    )


def write_evaluation_bundle(
    results_dir: Path,
    report: dict[str, Any],
    *,
    prefix: str = "application_suite_eval",
) -> dict[str, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = local_stamp()
    paths = {
        "json": results_dir / f"{prefix}_{stamp}.json",
        "csv": results_dir / f"{prefix}_{stamp}.csv",
        "markdown": results_dir / f"{prefix}_{stamp}.md",
        "html": results_dir / f"{prefix}_{stamp}.html",
    }
    paths["json"].write_text(
        json.dumps(report, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    fields = [
        "id",
        "application",
        "category",
        "answerable",
        "question",
        "ground_truth",
        "answer",
        "latency_ms",
        "system_faithfulness",
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "source_count",
    ]
    with paths["csv"].open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["cases"])
    markdown_report = render_evaluation_markdown(report)
    paths["markdown"].write_text(markdown_report, encoding="utf-8")
    paths["html"].write_text(render_evaluation_html(markdown_report), encoding="utf-8")

    for kind, path in paths.items():
        latest = results_dir / f"{prefix}_latest{path.suffix}"
        latest.write_bytes(path.read_bytes())
    return paths


def render_preflight_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Evaluation Preflight Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: **{'PASS' if report['passed'] else 'FAIL'}**",
        "",
        "## Dataset",
        "",
        f"- Cases: {report['dataset']['case_count']}",
        f"- Applications: {report['dataset']['application_count']}",
        f"- Answerable: {report['dataset']['answerable_count']}",
        f"- Unanswerable: {report['dataset']['unanswerable_count']}",
        f"- Validation errors: {report['dataset']['error_count']}",
        f"- Validation warnings: {report['dataset']['warning_count']}",
        "",
        "| Application | Cases |",
        "|---|---:|",
    ]
    for application, count in sorted(report["dataset"]["applications"].items()):
        lines.append(f"| {application} | {count} |")
    lines.extend(
        [
            "",
            "## Automated Tests",
            "",
            f"- Exit code: {report['tests']['exit_code']}",
            f"- Passed: {'yes' if report['tests']['passed'] else 'no'}",
            "",
            "```text",
            report["tests"]["output"].strip(),
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def write_preflight_bundle(results_dir: Path, report: dict[str, Any]) -> dict[str, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = local_stamp()
    paths = {
        "json": results_dir / f"evaluation_preflight_{stamp}.json",
        "markdown": results_dir / f"evaluation_preflight_{stamp}.md",
    }
    paths["json"].write_text(
        json.dumps(report, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    paths["markdown"].write_text(render_preflight_markdown(report), encoding="utf-8")
    for path in paths.values():
        latest = results_dir / f"evaluation_preflight_latest{path.suffix}"
        latest.write_bytes(path.read_bytes())
    return paths
