"""Run the bug-reporting evaluation against the live /chat/query endpoint."""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import math
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

try:
    from evaluation.validate_dataset import (
        DEFAULT_DATASET,
        DEFAULT_SOURCE_DIR,
        validate_dataset,
    )
except ModuleNotFoundError:
    from validate_dataset import DEFAULT_DATASET, DEFAULT_SOURCE_DIR, validate_dataset


LOGGER = logging.getLogger("rag_evaluation")
ROOT = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = ROOT.parent / "artifacts" / "evaluation_results"
METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)
DEFAULT_THRESHOLDS = {
    "faithfulness": 0.85,
    "answer_relevancy": 0.80,
    "context_precision": 0.75,
    "context_recall": 0.80,
}


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return ordered[index]


def _is_mock_response(payload: dict[str, Any]) -> bool:
    metadata = payload.get("metadata")
    if isinstance(metadata, dict) and metadata.get("mock") is True:
        return True
    answer = str(payload.get("answer", "")).casefold()
    return "mock mode" in answer or "mock response" in answer


def _validate_chat_response(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["Response is not a JSON object"]
    if not isinstance(payload.get("answer"), str) or not payload["answer"].strip():
        errors.append("answer must be a non-empty string")
    if not isinstance(payload.get("sources"), list):
        errors.append("sources must be a list")
    if "follow_up_questions" in payload and not isinstance(payload["follow_up_questions"], list):
        errors.append("follow_up_questions must be a list")
    return errors


async def _get_token(
    client: httpx.AsyncClient,
    token: str | None,
    email: str | None,
    password: str | None,
) -> str | None:
    if token:
        return token
    if not email or not password:
        return None
    response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


async def collect_system_outputs(
    cases: list[dict[str, Any]],
    *,
    base_url: str,
    token: str | None,
    email: str | None,
    password: str | None,
    timeout: float,
    allow_mock: bool,
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout) as client:
        bearer = await _get_token(client, token, email, password)
        headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}

        for position, case in enumerate(cases, start=1):
            started = time.perf_counter()
            response = await client.post(
                "/chat/query",
                headers=headers,
                json={"query": case["question"], "max_chunks": 5},
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            response.raise_for_status()
            payload = response.json()
            response_errors = _validate_chat_response(payload)
            if response_errors:
                raise RuntimeError(
                    f"{case['id']} returned an invalid response: {', '.join(response_errors)}"
                )
            if _is_mock_response(payload) and not allow_mock:
                raise RuntimeError(
                    "The API returned a fixed MOCK_N8N response. "
                    "Run against MOCK_N8N=false or pass --allow-mock only for plumbing tests."
                )

            sources = payload.get("sources", [])
            contexts = [
                source["chunk_text"]
                for source in sources
                if isinstance(source, dict)
                and isinstance(source.get("chunk_text"), str)
                and source["chunk_text"].strip()
            ]
            retrieved_documents = [
                source.get("title")
                for source in sources
                if isinstance(source, dict) and source.get("title")
            ]
            expected_documents = [
                source["document"] for source in case.get("expected_sources", [])
            ]
            outputs.append(
                {
                    **case,
                    "answer": payload["answer"],
                    "contexts": contexts,
                    "retrieved_documents": retrieved_documents,
                    "expected_documents": expected_documents,
                    "system_faithfulness": payload.get("faithfulness"),
                    "requires_clarification": payload.get("requires_clarification", False),
                    "latency_ms": latency_ms,
                    "response_metadata": payload.get("metadata", {}),
                }
            )
            LOGGER.info("Collected %s/%s: %s", position, len(cases), case["id"])
    return outputs


def run_ragas(outputs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, float]]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is required by the pinned RAGAS 0.1.10 evaluator. "
            "This key is used for independent judging, not by the system under test."
        )
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Evaluation dependencies are missing. Install evaluation/requirements.txt."
        ) from exc

    answerable = [row for row in outputs if row["answerable"]]
    if not answerable:
        raise RuntimeError("No answerable cases are available for RAGAS scoring")

    dataset = Dataset.from_dict(
        {
            "question": [row["question"] for row in answerable],
            "answer": [row["answer"] for row in answerable],
            "contexts": [row["contexts"] for row in answerable],
            "ground_truth": [row["ground_truth"] for row in answerable],
        }
    )
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        raise_exceptions=False,
    )
    frame = result.to_pandas()

    scored_rows: list[dict[str, Any]] = []
    for source_row, (_, score_row) in zip(answerable, frame.iterrows()):
        metric_scores: dict[str, float | None] = {}
        for metric in METRIC_NAMES:
            value = score_row.get(metric)
            if value is None:
                metric_scores[metric] = None
                continue
            numeric = float(value)
            metric_scores[metric] = None if math.isnan(numeric) else numeric
        scored_rows.append(
            {
                **source_row,
                **metric_scores,
            }
        )
    summary = {
        metric: float(frame[metric].dropna().mean())
        for metric in METRIC_NAMES
        if metric in frame
    }
    return scored_rows, summary


def build_summary(
    outputs: list[dict[str, Any]],
    ragas_summary: dict[str, float] | None,
) -> dict[str, Any]:
    latencies = [float(row["latency_ms"]) for row in outputs]
    answerable = [row for row in outputs if row["answerable"]]
    negatives = [row for row in outputs if not row["answerable"]]
    citation_coverage = (
        sum(bool(row["contexts"]) for row in answerable) / len(answerable)
        if answerable
        else 0.0
    )
    negative_abstention_rate = (
        sum(
            bool(row["requires_clarification"])
            or not row["contexts"]
            or "do not contain" in row["answer"].casefold()
            or "don't have enough information" in row["answer"].casefold()
            for row in negatives
        )
        / len(negatives)
        if negatives
        else 0.0
    )
    return {
        "case_count": len(outputs),
        "answerable_case_count": len(answerable),
        "unanswerable_case_count": len(negatives),
        "citation_coverage": citation_coverage,
        "negative_abstention_rate": negative_abstention_rate,
        "latency_ms": {
            "mean": statistics.fmean(latencies) if latencies else 0.0,
            "p95": _percentile(latencies, 0.95),
            "max": max(latencies, default=0.0),
        },
        "ragas": ragas_summary,
    }


def build_quality_gate(
    ragas_summary: dict[str, float] | None,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    if ragas_summary is None:
        return {
            "passed": None,
            "reason": "RAGAS scoring was skipped",
            "checks": {},
        }
    checks = {
        metric: {
            "score": ragas_summary.get(metric),
            "threshold": threshold,
            "passed": (
                ragas_summary.get(metric) is not None
                and ragas_summary[metric] >= threshold
            ),
        }
        for metric, threshold in thresholds.items()
    }
    return {
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
    }


def write_results(
    results_dir: Path,
    outputs: list[dict[str, Any]],
    scored_rows: list[dict[str, Any]] | None,
    summary: dict[str, Any],
) -> tuple[Path, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = results_dir / f"bug_eval_{stamp}.json"
    csv_path = results_dir / f"bug_eval_{stamp}.csv"
    scored_by_id = {row["id"]: row for row in scored_rows or []}
    combined = [scored_by_id.get(row["id"], row) for row in outputs]

    json_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "cases": combined,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    fields = [
        "id",
        "category",
        "answerable",
        "question",
        "ground_truth",
        "answer",
        "latency_ms",
        "system_faithfulness",
        *METRIC_NAMES,
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(combined)
    return json_path, csv_path


async def async_main(args: argparse.Namespace) -> int:
    validation = validate_dataset(
        args.dataset,
        args.source_dir,
        strict_synthetic_profile=args.strict_dataset,
    )
    if not validation.is_valid:
        for issue in validation.errors:
            LOGGER.error(issue.format())
        return 2

    cases = validation.cases[: args.max_cases] if args.max_cases else validation.cases
    outputs = await collect_system_outputs(
        cases,
        base_url=args.base_url,
        token=args.token,
        email=args.email,
        password=args.password,
        timeout=args.timeout,
        allow_mock=args.allow_mock,
    )

    scored_rows: list[dict[str, Any]] | None = None
    ragas_summary: dict[str, float] | None = None
    if not args.skip_ragas:
        scored_rows, ragas_summary = run_ragas(outputs)

    summary = build_summary(outputs, ragas_summary)
    thresholds = {
        "faithfulness": args.min_faithfulness,
        "answer_relevancy": args.min_answer_relevancy,
        "context_precision": args.min_context_precision,
        "context_recall": args.min_context_recall,
    }
    summary["quality_gate"] = build_quality_gate(ragas_summary, thresholds)
    json_path, csv_path = write_results(
        args.results_dir,
        outputs,
        scored_rows,
        summary,
    )
    print(json.dumps(summary, indent=2))
    print(f"JSON report: {json_path}")
    print(f"CSV report:  {csv_path}")
    if args.enforce_thresholds and summary["quality_gate"]["passed"] is not True:
        return 3
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument(
        "--base-url",
        default=os.getenv("EVAL_BASE_URL", "http://localhost:8000"),
    )
    parser.add_argument("--token", default=os.getenv("EVAL_BEARER_TOKEN"))
    parser.add_argument("--email", default=os.getenv("EVAL_EMAIL"))
    parser.add_argument("--password", default=os.getenv("EVAL_PASSWORD"))
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--skip-ragas", action="store_true")
    parser.add_argument("--allow-mock", action="store_true")
    parser.add_argument("--strict-dataset", action="store_true")
    parser.add_argument("--enforce-thresholds", action="store_true")
    parser.add_argument(
        "--min-faithfulness",
        type=float,
        default=DEFAULT_THRESHOLDS["faithfulness"],
    )
    parser.add_argument(
        "--min-answer-relevancy",
        type=float,
        default=DEFAULT_THRESHOLDS["answer_relevancy"],
    )
    parser.add_argument(
        "--min-context-precision",
        type=float,
        default=DEFAULT_THRESHOLDS["context_precision"],
    )
    parser.add_argument(
        "--min-context-recall",
        type=float,
        default=DEFAULT_THRESHOLDS["context_recall"],
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(asyncio.run(async_main(parse_args())))


if __name__ == "__main__":
    main()
