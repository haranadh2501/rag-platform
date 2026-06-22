from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evaluation.run_eval import (
    build_application_summaries,
    build_quality_gate,
    build_summary,
    run_ragas,
)


RUN_ROOT = Path("artifacts/evaluation_results/public_batched_full_20260621")
INPUT_JSON = RUN_ROOT / "consolidated_public_batched_eval_20260621.json"
OUTPUT_BASE = RUN_ROOT / "ragas_public_batched_eval_20260622"


def main() -> None:
    source_report = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    outputs = source_report["cases"]
    scored_rows, ragas_summary = run_ragas(outputs)
    scored_by_id = {row["id"]: row for row in scored_rows}
    merged_cases = [
        {**row, **{k: scored_by_id[row["id"]][k] for k in ragas_summary if row["id"] in scored_by_id}}
        for row in outputs
    ]

    summary = build_summary(outputs, ragas_summary)
    summary["quality_gate"] = build_quality_gate(
        summary,
        {
            "faithfulness": 0.85,
            "answer_relevancy": 0.75,
            "context_precision": 0.70,
            "context_recall": 0.70,
        },
    )
    summary["applications"] = build_application_summaries(outputs, scored_rows)
    summary["ragas_scoring"] = {
        "scored_answerable_cases": len(scored_rows),
        "total_cases": len(outputs),
        "source_json": str(INPUT_JSON),
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "cases": merged_cases,
    }

    OUTPUT_BASE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_BASE.with_suffix(".json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    fields = [
        "id",
        "application",
        "category",
        "answerable",
        "latency_ms",
        "source_count",
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    ]
    with OUTPUT_BASE.with_suffix(".csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(merged_cases)

    lines = [
        "# Public Railway Full RAGAS Evaluation",
        "",
        "Generated: 2026-06-22",
        "",
        "## Summary",
        "",
        f"- Total cases: {summary['case_count']}",
        f"- Answerable cases scored by RAGAS: {len(scored_rows)}",
        f"- Unanswerable cases retained for abstention/citation metrics: {summary['unanswerable_case_count']}",
        f"- Citation coverage: {summary['citation_coverage']:.4f}",
        f"- Negative abstention rate: {summary['negative_abstention_rate']:.4f}",
        f"- Mean latency: {summary['latency_ms']['mean']:.2f} ms",
        f"- Source return rate: {summary['observability']['source_return_rate']:.4f}",
        f"- Average sources per case: {summary['observability']['average_sources_per_case']:.2f}",
        "",
        "## RAGAS Metrics",
        "",
        "| Metric | Score | Threshold | Result |",
        "|---|---:|---:|---|",
    ]
    for metric, threshold in [
        ("faithfulness", 0.85),
        ("answer_relevancy", 0.75),
        ("context_precision", 0.70),
        ("context_recall", 0.70),
    ]:
        score = ragas_summary.get(metric)
        score_is_valid = score is not None and not math.isnan(score)
        passed = score_is_valid and score >= threshold
        score_text = f"{score:.4f}" if score_is_valid else "n/a"
        lines.append(
            f"| {metric} | {score_text} | {threshold:.2f} | {'PASS' if passed else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Quality Gate",
            "",
            f"- Passed: {summary['quality_gate']['passed']}",
            f"- Reason: {summary['quality_gate'].get('reason', 'One or more RAGAS checks did not pass')}",
            "",
            "## Application RAGAS Breakdown",
            "",
            "| Application | Cases | Faithfulness | Answer relevancy | Context precision | Context recall |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for app, app_summary in sorted(summary["applications"].items()):
        ragas = app_summary.get("ragas") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    app,
                    str(app_summary["case_count"]),
                    f"{ragas.get('faithfulness', 0):.4f}",
                    f"{ragas.get('answer_relevancy', 0):.4f}",
                    f"{ragas.get('context_precision', 0):.4f}",
                    f"{ragas.get('context_recall', 0):.4f}",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- JSON: `{OUTPUT_BASE.with_suffix('.json')}`",
            f"- CSV: `{OUTPUT_BASE.with_suffix('.csv')}`",
        ]
    )
    OUTPUT_BASE.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
