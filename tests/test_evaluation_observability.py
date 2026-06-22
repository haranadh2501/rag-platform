"""Tests for the evaluation module's observability instrumentation.

"Observability" in this module is the operational signal the eval harness
extracts from every RAG response and aggregates across a run:
  * per-response: source_count / has_sources / metadata coverage
    (``run_eval._source_observability``)
  * per-case:     latency_ms, n8n_attempts, n8n_retry_count
    (``collect_system_outputs`` / ``collect_direct_n8n_outputs``)
  * aggregate:    source_return_rate, average_sources_per_case,
    metadata_coverage, total_retry_count, max_attempts and the
    mean/p95/max latency block (``build_summary`` + ``_percentile``)
  * rendered:     the ``## Observability`` table in the markdown report
    (``reporting.render_evaluation_markdown``)

These tests pin each layer with deterministic, network-free fixtures.
The live collectors are exercised through an ``httpx.MockTransport`` so the
latency timer and the n8n retry counters run for real without a server.
"""
from __future__ import annotations

import asyncio
import unittest
from typing import Any, Callable
from unittest.mock import patch

import httpx

from evaluation import run_eval
from evaluation.reporting import render_evaluation_markdown
from evaluation.run_eval import (
    _percentile,
    _source_observability,
    build_summary,
    collect_direct_n8n_outputs,
    collect_system_outputs,
)

_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _mock_client_factory(handler: Callable[[httpx.Request], httpx.Response]):
    """Return an AsyncClient factory that routes requests through ``handler``.

    ``run_eval`` constructs ``httpx.AsyncClient`` internally, so we patch the
    name it sees and inject a MockTransport while preserving base_url/timeout.
    """

    def factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(handler)
        return _REAL_ASYNC_CLIENT(*args, **kwargs)

    return factory


async def _noop_sleep(_seconds: float) -> None:
    """Drop the retry back-off so retry tests stay fast and deterministic."""
    return None


def _case(case_id: str = "OBS-1", **overrides: Any) -> dict[str, Any]:
    case = {
        "id": case_id,
        "application": "kubernetes_troubleshooting",
        "category": "factoid",
        "answerable": True,
        "question": "How do I roll back a bad deployment?",
        "ground_truth": "Use kubectl rollout undo.",
        "expected_sources": [{"document": "runbook.txt"}],
    }
    case.update(overrides)
    return case


class SourceObservabilityTests(unittest.TestCase):
    """``_source_observability`` is the per-response signal extractor."""

    def test_counts_sources_and_sorts_metadata_keys(self) -> None:
        sources = [
            {"title": "a.txt", "chunk_text": "alpha"},
            {"title": "b.txt", "chunk_text": "beta"},
        ]
        metadata = {"trace_id": "t-1", "model": "gpt-4o-mini", "tokens": 42}

        observability = _source_observability(sources, metadata)

        self.assertEqual(observability["source_count"], 2)
        self.assertTrue(observability["has_sources"])
        self.assertEqual(observability["metadata_key_count"], 3)
        # Keys are stringified and sorted for stable reporting/diffing.
        self.assertEqual(
            observability["metadata_keys"], ["model", "tokens", "trace_id"]
        )

    def test_empty_response_reports_no_sources_or_metadata(self) -> None:
        observability = _source_observability([], {})

        self.assertEqual(observability["source_count"], 0)
        self.assertFalse(observability["has_sources"])
        self.assertEqual(observability["metadata_key_count"], 0)
        self.assertEqual(observability["metadata_keys"], [])


class PercentileLatencyTests(unittest.TestCase):
    """``_percentile`` backs the p95 latency signal."""

    def test_empty_series_is_zero(self) -> None:
        self.assertEqual(_percentile([], 0.95), 0.0)

    def test_single_value_series(self) -> None:
        self.assertEqual(_percentile([12.5], 0.95), 12.5)

    def test_p95_picks_high_end_and_ignores_order(self) -> None:
        latencies = [50.0, 10.0, 30.0, 20.0, 40.0, 100.0, 60.0, 70.0, 80.0, 90.0]
        # p95 over 10 samples -> index round(9 * 0.95) = 9 -> the max.
        self.assertEqual(_percentile(latencies, 0.95), 100.0)
        self.assertEqual(_percentile(latencies, 0.0), 10.0)


class BuildSummaryObservabilityTests(unittest.TestCase):
    """``build_summary`` aggregates per-case observability across a run."""

    def test_empty_outputs_do_not_divide_by_zero(self) -> None:
        summary = build_summary([], None)

        observability = summary["observability"]
        self.assertEqual(observability["source_return_rate"], 0.0)
        self.assertEqual(observability["average_sources_per_case"], 0.0)
        self.assertEqual(observability["metadata_coverage"], 0.0)
        self.assertEqual(observability["total_retry_count"], 0)
        self.assertEqual(observability["max_attempts"], 1)
        self.assertEqual(summary["latency_ms"]["mean"], 0.0)
        self.assertEqual(summary["latency_ms"]["p95"], 0.0)
        self.assertEqual(summary["latency_ms"]["max"], 0.0)

    def test_source_count_falls_back_to_context_length(self) -> None:
        # A row without explicit source_count/observability should still be
        # counted via its contexts so the signal degrades gracefully.
        outputs = [
            {
                "answerable": True,
                "contexts": ["ctx-1", "ctx-2"],
                "requires_clarification": False,
                "answer": "Grounded answer",
                "latency_ms": 100.0,
            }
        ]

        summary = build_summary(outputs, None)

        self.assertEqual(summary["observability"]["source_return_rate"], 1.0)
        self.assertEqual(summary["observability"]["average_sources_per_case"], 2.0)
        # No observability dict -> metadata coverage is zero, no crash.
        self.assertEqual(summary["observability"]["metadata_coverage"], 0.0)

    def test_latency_block_reports_mean_p95_and_max(self) -> None:
        outputs = [
            {
                "answerable": True,
                "contexts": ["c"],
                "source_count": 1,
                "observability": {"metadata_key_count": 1},
                "requires_clarification": False,
                "answer": "ok",
                "latency_ms": value,
            }
            for value in (100.0, 200.0, 300.0)
        ]

        latency = build_summary(outputs, None)["latency_ms"]

        self.assertEqual(latency["mean"], 200.0)
        self.assertEqual(latency["max"], 300.0)
        self.assertEqual(latency["p95"], 300.0)

    def test_retry_signals_are_aggregated(self) -> None:
        outputs = [
            {
                "answerable": True,
                "contexts": ["c"],
                "source_count": 1,
                "observability": {
                    "metadata_key_count": 2,
                    "n8n_retry_count": 2,
                    "n8n_attempts": 3,
                },
                "requires_clarification": False,
                "answer": "ok",
                "latency_ms": 10.0,
            },
            {
                "answerable": True,
                "contexts": ["c"],
                "source_count": 1,
                "observability": {
                    "metadata_key_count": 2,
                    "n8n_retry_count": 1,
                    "n8n_attempts": 2,
                },
                "requires_clarification": False,
                "answer": "ok",
                "latency_ms": 10.0,
            },
        ]

        observability = build_summary(outputs, None)["observability"]

        self.assertEqual(observability["total_retry_count"], 3)
        self.assertEqual(observability["max_attempts"], 3)
        self.assertEqual(observability["metadata_coverage"], 1.0)


class ObservabilityRenderingTests(unittest.TestCase):
    """The markdown report must surface the observability signals."""

    def test_markdown_renders_observability_table(self) -> None:
        report = {
            "generated_at": "2026-06-22T00:00:00+00:00",
            "summary": {
                "case_count": 2,
                "citation_coverage": 1.0,
                "negative_abstention_rate": 1.0,
                "latency_ms": {"mean": 150.0, "p95": 300.0, "max": 300.0},
                "observability": {
                    "source_return_rate": 0.5,
                    "average_sources_per_case": 1.5,
                    "metadata_coverage": 0.75,
                    "total_retry_count": 4,
                    "max_attempts": 3,
                },
                "quality_gate": {"checks": {}},
                "applications": {},
            },
            "cases": [],
        }

        markdown = render_evaluation_markdown(report)

        self.assertIn("## Observability", markdown)
        self.assertIn("| Source return rate | 0.500 |", markdown)
        self.assertIn("| Average sources per case | 1.500 |", markdown)
        self.assertIn("| Metadata coverage | 0.750 |", markdown)
        self.assertIn("| Total retry count | 4 |", markdown)
        self.assertIn("| Max attempts | 3 |", markdown)

    def test_markdown_tolerates_missing_observability_block(self) -> None:
        report = {
            "generated_at": "2026-06-22T00:00:00+00:00",
            "summary": {
                "case_count": 0,
                "latency_ms": {},
                "quality_gate": {"checks": {}},
                "applications": {},
            },
            "cases": [],
        }

        markdown = render_evaluation_markdown(report)

        # Falls back to the documented defaults rather than raising.
        self.assertIn("## Observability", markdown)
        self.assertIn("| Total retry count | 0 |", markdown)
        self.assertIn("| Max attempts | 1 |", markdown)


class CollectSystemOutputsObservabilityTests(unittest.TestCase):
    """The backend collector must time each call and attach observability."""

    def test_records_latency_and_source_observability(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/chat/query")
            return httpx.Response(
                200,
                json={
                    "answer": "Roll back with kubectl rollout undo.",
                    "sources": [
                        {"title": "runbook.txt", "chunk_text": "Use rollout undo."}
                    ],
                    "metadata": {"trace_id": "t-9", "model": "gpt-4o-mini"},
                },
            )

        with patch.object(run_eval.httpx, "AsyncClient", _mock_client_factory(handler)):
            outputs = asyncio.run(
                collect_system_outputs(
                    [_case()],
                    base_url="http://test",
                    token="fake-token",  # skips the /auth/login round-trip
                    email=None,
                    password=None,
                    timeout=5.0,
                    allow_mock=False,
                )
            )

        self.assertEqual(len(outputs), 1)
        row = outputs[0]
        self.assertIsInstance(row["latency_ms"], float)
        self.assertGreaterEqual(row["latency_ms"], 0.0)
        self.assertEqual(row["source_count"], 1)
        self.assertTrue(row["observability"]["has_sources"])
        self.assertEqual(
            row["observability"]["metadata_keys"], ["model", "trace_id"]
        )
        self.assertEqual(row["response_metadata"]["trace_id"], "t-9")


class CollectDirectN8nObservabilityTests(unittest.TestCase):
    """The n8n collector must instrument transient-failure retries."""

    @staticmethod
    def _ok_response() -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "answer": "Grounded n8n answer about rollouts.",
                "sources": [{"document": "kb.md", "content": "Evidence excerpt."}],
            },
        )

    def test_no_retry_on_first_success(self) -> None:
        calls = {"count": 0}

        def handler(_request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return self._ok_response()

        with patch.object(run_eval.httpx, "AsyncClient", _mock_client_factory(handler)):
            outputs = asyncio.run(
                collect_direct_n8n_outputs(
                    [_case()],
                    n8n_url="http://n8n.test/webhook/retrieval",
                    token="t",
                    tenant_id="tenant-1",
                    timeout=5.0,
                    allow_mock=False,
                    max_chunks=5,
                    retries=2,
                )
            )

        self.assertEqual(calls["count"], 1)
        row = outputs[0]
        self.assertEqual(row["observability"]["n8n_attempts"], 1)
        self.assertEqual(row["observability"]["n8n_retry_count"], 0)
        self.assertEqual(row["response_metadata"]["evaluation_target"], "direct_n8n")

    def test_transient_5xx_is_retried_and_counted(self) -> None:
        calls = {"count": 0}

        def handler(_request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] == 1:
                return httpx.Response(503, text="upstream temporarily unavailable")
            return self._ok_response()

        with patch.object(run_eval.httpx, "AsyncClient", _mock_client_factory(handler)), \
                patch.object(run_eval.asyncio, "sleep", _noop_sleep):
            outputs = asyncio.run(
                collect_direct_n8n_outputs(
                    [_case()],
                    n8n_url="http://n8n.test/webhook/retrieval",
                    token="t",
                    tenant_id="tenant-1",
                    timeout=5.0,
                    allow_mock=False,
                    max_chunks=5,
                    retries=2,
                )
            )

        self.assertEqual(calls["count"], 2)  # one failure + one success
        row = outputs[0]
        self.assertEqual(row["observability"]["n8n_attempts"], 2)
        self.assertEqual(row["observability"]["n8n_retry_count"], 1)

        # The retry signal must propagate into the aggregate summary.
        summary = build_summary(outputs, None)
        self.assertEqual(summary["observability"]["total_retry_count"], 1)
        self.assertEqual(summary["observability"]["max_attempts"], 2)


if __name__ == "__main__":
    unittest.main()
