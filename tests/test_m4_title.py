"""Unit tests for deterministic conversation-title derivation (M4).

Pure-function tests — no DB/app boot required, unlike test_m4_chat.py.

    pytest tests/test_m4_title.py -v

NOTE: tests/ is M10-owned — this file is additive; coordinate sign-off with M10.
"""
import os
import sys

_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.services.message_service import DEFAULT_TITLE, _derive_title  # noqa: E402


def test_strips_question_prefix_and_punctuation():
    assert _derive_title("What is Kubernetes?") == "Kubernetes"


def test_strips_summarize_prefix():
    title = _derive_title("Summarize the onboarding guide in three bullet points")
    assert title != DEFAULT_TITLE
    assert "Summarize" not in title
    assert len(title) <= 40


def test_truncates_to_max_40_chars_on_word_boundary():
    title = _derive_title("Explain the full end to end ingestion pipeline architecture in detail please")
    assert len(title) <= 40
    assert not title.endswith(" ")


def test_empty_query_falls_back_to_default():
    assert _derive_title("") == DEFAULT_TITLE
    assert _derive_title("   ") == DEFAULT_TITLE


def test_prefix_only_query_falls_back_to_default():
    assert _derive_title("What is") == DEFAULT_TITLE


def test_no_recognized_prefix_is_title_cased_as_is():
    assert _derive_title("refund policy") == "Refund Policy"
