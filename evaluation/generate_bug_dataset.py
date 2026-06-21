"""Generate a deterministic synthetic dataset for a bug-reporting knowledge base.

The corpus and questions are intentionally synthetic, so they are safe to commit
and can be regenerated exactly. Reference contexts are copied verbatim from the
generated source documents, which lets the validator catch unsupported labels.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "qa_dataset.jsonl"
DEFAULT_SOURCE_DIR = ROOT / "sample-data" / "bug-reporting"


SOURCE_DOCUMENTS = {
    "bug_triage_playbook.txt": """Bug Triage Playbook

Section: Required report fields
Every bug report must include a concise title, affected product and version, environment, reproduction steps, expected behavior, actual behavior, frequency, business impact, and relevant logs or screenshots. Reports containing customer data must be redacted before submission.

Section: Severity S1
Severity S1 is reserved for a production outage, active security compromise, irreversible data loss, or a complete blocker affecting most customers with no workaround. The on-call engineer must acknowledge an S1 report within 15 minutes and open an incident channel immediately.

Section: Severity S2
Severity S2 covers major functionality that is unavailable for multiple customers, severe performance degradation, or a high-impact defect with only a difficult workaround. The owning team must acknowledge an S2 report within 2 business hours.

Section: Severity S3 and S4
Severity S3 covers limited-impact defects with a practical workaround and should be acknowledged within 1 business day. Severity S4 covers cosmetic problems, documentation mistakes, and low-impact enhancement requests and should be acknowledged within 3 business days.

Section: Duplicate handling
When a new report matches an existing issue, mark it as a duplicate, link the canonical issue, copy any new evidence to the canonical issue, and notify the reporter. Do not close the canonical issue merely because a duplicate was filed.

Section: Security and privacy
Suspected vulnerabilities must be tagged security-sensitive and moved to the restricted security queue. Secrets, access tokens, personal data, and customer payloads must never be pasted into a public issue. Replace them with redacted samples.

Section: Escalation
Escalate to the incident process when an issue meets S1 criteria, when an S2 issue affects more than 25 percent of active tenants, or when support receives five or more matching reports within 30 minutes.
""",
    "mobile_app_known_issues.txt": """Mobile Application Known Issues

Section: BUG-MOB-101 Android login loop
BUG-MOB-101 affects Android 14 devices running mobile app versions 5.4.0 through 5.4.2. After successful authentication, the app may return to the login screen when battery optimization is enabled. The temporary workaround is to disable battery optimization for the app and sign in again. The permanent fix is included in version 5.4.3.

Section: BUG-MOB-102 Attachment crash
BUG-MOB-102 affects Android and iOS app version 5.5.0. Adding a video attachment larger than 50 MB to a bug report can close the app before the draft is saved. Users should compress the video below 50 MB or upload it through the web portal. A fix is planned for version 5.5.1.

Section: BUG-MOB-103 Missing iOS notifications
BUG-MOB-103 affects iOS 17 users on app version 5.3.1 when notification permission was denied during first launch and enabled later from system settings. Reinstalling the app refreshes the notification token. The issue is fixed in version 5.3.2.

Section: Mobile evidence collection
For mobile crashes, collect the app version, operating system version, device model, timestamp with timezone, reproduction steps, and the diagnostic bundle from Settings > Help > Export diagnostics. Screen recordings are useful but must not display passwords, tokens, or personal customer data.
""",
    "api_known_issues.txt": """API Known Issues and Troubleshooting

Section: BUG-API-201 Rate limiting after token rotation
BUG-API-201 affects API clients that rotate an access token while keeping HTTP/2 connections open. Requests may receive HTTP 429 for up to five minutes because the old and new token buckets are temporarily combined. Closing the connection pool after rotation is the recommended workaround. The server-side fix was deployed in API release 2026.06.2.

Section: BUG-API-202 Duplicate webhook delivery
BUG-API-202 can deliver the same webhook event twice when the first acknowledgement arrives after the ten-second timeout. Consumers must treat the event_id field as an idempotency key and return a 2xx response within ten seconds. Duplicate delivery does not indicate duplicate data was stored by the platform.

Section: Webhook signature troubleshooting
Webhook signatures use HMAC-SHA256 over the exact raw request body. Signature validation fails if middleware parses and reserializes JSON before verification, if the wrong tenant secret is used, or if the timestamp differs from server time by more than five minutes.

Section: API evidence collection
API bug reports should include the request method, redacted URL, response status, request_id response header, timestamp with timezone, SDK name and version, and a minimal reproducible request. Authorization headers and complete access tokens must be removed.
""",
}


def _source(document: str, section: str, text: str) -> dict[str, str]:
    return {"document": document, "section": section, "text": text}


TRIAGE_FIELDS = (
    "Every bug report must include a concise title, affected product and version, "
    "environment, reproduction steps, expected behavior, actual behavior, frequency, "
    "business impact, and relevant logs or screenshots. Reports containing customer "
    "data must be redacted before submission."
)
S1 = (
    "Severity S1 is reserved for a production outage, active security compromise, "
    "irreversible data loss, or a complete blocker affecting most customers with no "
    "workaround. The on-call engineer must acknowledge an S1 report within 15 minutes "
    "and open an incident channel immediately."
)
S2 = (
    "Severity S2 covers major functionality that is unavailable for multiple customers, "
    "severe performance degradation, or a high-impact defect with only a difficult "
    "workaround. The owning team must acknowledge an S2 report within 2 business hours."
)
S34 = (
    "Severity S3 covers limited-impact defects with a practical workaround and should "
    "be acknowledged within 1 business day. Severity S4 covers cosmetic problems, "
    "documentation mistakes, and low-impact enhancement requests and should be "
    "acknowledged within 3 business days."
)
DUPLICATES = (
    "When a new report matches an existing issue, mark it as a duplicate, link the "
    "canonical issue, copy any new evidence to the canonical issue, and notify the "
    "reporter. Do not close the canonical issue merely because a duplicate was filed."
)
SECURITY = (
    "Suspected vulnerabilities must be tagged security-sensitive and moved to the "
    "restricted security queue. Secrets, access tokens, personal data, and customer "
    "payloads must never be pasted into a public issue. Replace them with redacted samples."
)
ESCALATION = (
    "Escalate to the incident process when an issue meets S1 criteria, when an S2 issue "
    "affects more than 25 percent of active tenants, or when support receives five or "
    "more matching reports within 30 minutes."
)
MOB101 = (
    "BUG-MOB-101 affects Android 14 devices running mobile app versions 5.4.0 through "
    "5.4.2. After successful authentication, the app may return to the login screen "
    "when battery optimization is enabled. The temporary workaround is to disable battery "
    "optimization for the app and sign in again. The permanent fix is included in version 5.4.3."
)
MOB102 = (
    "BUG-MOB-102 affects Android and iOS app version 5.5.0. Adding a video attachment "
    "larger than 50 MB to a bug report can close the app before the draft is saved. "
    "Users should compress the video below 50 MB or upload it through the web portal. "
    "A fix is planned for version 5.5.1."
)
MOB103 = (
    "BUG-MOB-103 affects iOS 17 users on app version 5.3.1 when notification permission "
    "was denied during first launch and enabled later from system settings. Reinstalling "
    "the app refreshes the notification token. The issue is fixed in version 5.3.2."
)
MOBILE_EVIDENCE = (
    "For mobile crashes, collect the app version, operating system version, device model, "
    "timestamp with timezone, reproduction steps, and the diagnostic bundle from Settings "
    "> Help > Export diagnostics. Screen recordings are useful but must not display "
    "passwords, tokens, or personal customer data."
)
API201 = (
    "BUG-API-201 affects API clients that rotate an access token while keeping HTTP/2 "
    "connections open. Requests may receive HTTP 429 for up to five minutes because the "
    "old and new token buckets are temporarily combined. Closing the connection pool "
    "after rotation is the recommended workaround. The server-side fix was deployed in "
    "API release 2026.06.2."
)
API202 = (
    "BUG-API-202 can deliver the same webhook event twice when the first acknowledgement "
    "arrives after the ten-second timeout. Consumers must treat the event_id field as an "
    "idempotency key and return a 2xx response within ten seconds. Duplicate delivery "
    "does not indicate duplicate data was stored by the platform."
)
SIGNATURES = (
    "Webhook signatures use HMAC-SHA256 over the exact raw request body. Signature "
    "validation fails if middleware parses and reserializes JSON before verification, "
    "if the wrong tenant secret is used, or if the timestamp differs from server time "
    "by more than five minutes."
)
API_EVIDENCE = (
    "API bug reports should include the request method, redacted URL, response status, "
    "request_id response header, timestamp with timezone, SDK name and version, and a "
    "minimal reproducible request. Authorization headers and complete access tokens must be removed."
)


def _case(
    case_id: str,
    question: str,
    ground_truth: str,
    category: str,
    sources: list[dict[str, str]],
    *,
    answerable: bool = True,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": case_id,
        "application": "bug_reporting",
        "question": question,
        "ground_truth": ground_truth,
        "reference_contexts": [source["text"] for source in sources],
        "expected_sources": [
            {"document": source["document"], "section": source["section"]}
            for source in sources
        ],
        "category": category,
        "answerable": answerable,
        "tags": tags or [],
    }


def build_cases() -> list[dict[str, Any]]:
    triage = "bug_triage_playbook.txt"
    mobile = "mobile_app_known_issues.txt"
    api = "api_known_issues.txt"
    cases = [
        _case("BUG-EVAL-001", "What information is mandatory in a new bug report?", TRIAGE_FIELDS, "factoid", [_source(triage, "Required report fields", TRIAGE_FIELDS)], tags=["triage"]),
        _case("BUG-EVAL-002", "Which situations qualify as severity S1?", S1, "factoid", [_source(triage, "Severity S1", S1)], tags=["severity"]),
        _case("BUG-EVAL-003", "How quickly must an S1 issue be acknowledged, and what else must happen?", "An S1 issue must be acknowledged within 15 minutes and an incident channel must be opened immediately.", "factoid", [_source(triage, "Severity S1", S1)], tags=["severity", "sla"]),
        _case("BUG-EVAL-004", "What is the acknowledgement target for an S2 report?", "The owning team must acknowledge an S2 report within 2 business hours.", "factoid", [_source(triage, "Severity S2", S2)], tags=["severity", "sla"]),
        _case("BUG-EVAL-005", "How should a cosmetic documentation typo be classified and acknowledged?", "It should be classified as S4 and acknowledged within 3 business days.", "reasoning", [_source(triage, "Severity S3 and S4", S34)], tags=["severity"]),
        _case("BUG-EVAL-006", "What steps should a triager take when a report is a duplicate?", "Mark it as a duplicate, link the canonical issue, copy new evidence to the canonical issue, notify the reporter, and keep the canonical issue open.", "procedural", [_source(triage, "Duplicate handling", DUPLICATES)], tags=["triage"]),
        _case("BUG-EVAL-007", "Where should a suspected vulnerability be filed?", "Tag it security-sensitive and move it to the restricted security queue.", "factoid", [_source(triage, "Security and privacy", SECURITY)], tags=["security"]),
        _case("BUG-EVAL-008", "Can an access token be pasted into a public issue for debugging?", "No. Access tokens and other secrets must be removed and replaced with redacted samples.", "safety", [_source(triage, "Security and privacy", SECURITY)], tags=["security", "privacy"]),
        _case("BUG-EVAL-009", "When do repeated support reports trigger the incident process?", "Escalate when support receives at least five matching reports within 30 minutes.", "factoid", [_source(triage, "Escalation", ESCALATION)], tags=["escalation"]),
        _case("BUG-EVAL-010", "An S2 defect affects 30 percent of active tenants. Should it enter the incident process?", "Yes. An S2 issue affecting more than 25 percent of active tenants must be escalated to the incident process.", "reasoning", [_source(triage, "Escalation", ESCALATION), _source(triage, "Severity S2", S2)], tags=["severity", "escalation"]),
        _case("BUG-EVAL-011", "Which devices and app versions are affected by BUG-MOB-101?", "Android 14 devices running app versions 5.4.0 through 5.4.2 are affected.", "factoid", [_source(mobile, "BUG-MOB-101 Android login loop", MOB101)], tags=["mobile"]),
        _case("BUG-EVAL-012", "What is the workaround for the Android login loop?", "Disable battery optimization for the app and sign in again.", "factoid", [_source(mobile, "BUG-MOB-101 Android login loop", MOB101)], tags=["mobile", "workaround"]),
        _case("BUG-EVAL-013", "Which version permanently fixes BUG-MOB-101?", "The permanent fix is included in mobile app version 5.4.3.", "factoid", [_source(mobile, "BUG-MOB-101 Android login loop", MOB101)], tags=["mobile", "version"]),
        _case("BUG-EVAL-014", "What triggers BUG-MOB-102?", "Adding a video attachment larger than 50 MB in mobile app version 5.5.0 can close the app before the draft is saved.", "factoid", [_source(mobile, "BUG-MOB-102 Attachment crash", MOB102)], tags=["mobile"]),
        _case("BUG-EVAL-015", "How can a user avoid the attachment crash?", "Compress the video below 50 MB or upload it through the web portal.", "factoid", [_source(mobile, "BUG-MOB-102 Attachment crash", MOB102)], tags=["mobile", "workaround"]),
        _case("BUG-EVAL-016", "What should an iOS 17 user do when notifications remain missing after enabling permission?", "Reinstall the app to refresh the notification token.", "factoid", [_source(mobile, "BUG-MOB-103 Missing iOS notifications", MOB103)], tags=["mobile", "workaround"]),
        _case("BUG-EVAL-017", "Which version fixes the missing iOS notification issue?", "BUG-MOB-103 is fixed in mobile app version 5.3.2.", "factoid", [_source(mobile, "BUG-MOB-103 Missing iOS notifications", MOB103)], tags=["mobile", "version"]),
        _case("BUG-EVAL-018", "What evidence should be collected for a mobile crash report?", MOBILE_EVIDENCE, "procedural", [_source(mobile, "Mobile evidence collection", MOBILE_EVIDENCE)], tags=["mobile", "evidence"]),
        _case("BUG-EVAL-019", "Compare the workarounds for BUG-MOB-101 and BUG-MOB-102.", "For BUG-MOB-101, disable battery optimization and sign in again. For BUG-MOB-102, compress the video below 50 MB or use the web portal.", "multi_hop", [_source(mobile, "BUG-MOB-101 Android login loop", MOB101), _source(mobile, "BUG-MOB-102 Attachment crash", MOB102)], tags=["mobile", "workaround"]),
        _case("BUG-EVAL-020", "What is the official password reset policy for the mobile app?", "The supplied bug-reporting documents do not contain a password reset policy.", "unanswerable", [], answerable=False, tags=["negative"]),
        _case("BUG-EVAL-021", "Why can HTTP 429 responses appear after an access-token rotation?", "For clients that keep HTTP/2 connections open, the old and new token buckets may be temporarily combined for up to five minutes.", "factoid", [_source(api, "BUG-API-201 Rate limiting after token rotation", API201)], tags=["api"]),
        _case("BUG-EVAL-022", "What is the workaround for BUG-API-201?", "Close the HTTP connection pool after rotating the access token.", "factoid", [_source(api, "BUG-API-201 Rate limiting after token rotation", API201)], tags=["api", "workaround"]),
        _case("BUG-EVAL-023", "Which API release contains the server-side fix for BUG-API-201?", "The fix was deployed in API release 2026.06.2.", "factoid", [_source(api, "BUG-API-201 Rate limiting after token rotation", API201)], tags=["api", "version"]),
        _case("BUG-EVAL-024", "Why might the same webhook event be delivered twice?", "A duplicate can occur when the first acknowledgement arrives after the ten-second timeout.", "factoid", [_source(api, "BUG-API-202 Duplicate webhook delivery", API202)], tags=["api", "webhook"]),
        _case("BUG-EVAL-025", "How should consumers prevent duplicate webhook processing?", "Use event_id as an idempotency key and return a 2xx response within ten seconds.", "procedural", [_source(api, "BUG-API-202 Duplicate webhook delivery", API202)], tags=["api", "webhook"]),
        _case("BUG-EVAL-026", "Does duplicate webhook delivery mean the platform stored duplicate data?", "No. Duplicate delivery does not indicate that duplicate data was stored by the platform.", "factoid", [_source(api, "BUG-API-202 Duplicate webhook delivery", API202)], tags=["api", "webhook"]),
        _case("BUG-EVAL-027", "What are the documented causes of webhook signature validation failure?", SIGNATURES, "factoid", [_source(api, "Webhook signature troubleshooting", SIGNATURES)], tags=["api", "security"]),
        _case("BUG-EVAL-028", "What details belong in an API bug report, and what sensitive value must be removed?", API_EVIDENCE, "procedural", [_source(api, "API evidence collection", API_EVIDENCE)], tags=["api", "evidence", "privacy"]),
        _case("BUG-EVAL-029", "Which GraphQL mutations are affected by the current known issues?", "The supplied bug-reporting documents do not describe any GraphQL mutation issue.", "unanswerable", [], answerable=False, tags=["negative"]),
        _case("BUG-EVAL-030", "What is the price of the enterprise API plan?", "The supplied bug-reporting documents do not contain API pricing information.", "unanswerable", [], answerable=False, tags=["negative"]),
    ]
    return cases


def generate(dataset_path: Path, source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    dataset_path.parent.mkdir(parents=True, exist_ok=True)

    for filename, content in SOURCE_DOCUMENTS.items():
        (source_dir / filename).write_text(content, encoding="utf-8")

    with dataset_path.open("w", encoding="utf-8", newline="\n") as handle:
        for case in build_cases():
            handle.write(json.dumps(case, ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    args = parser.parse_args()
    generate(args.output, args.source_dir)
    print(f"Generated 30 cases at {args.output}")
    print(f"Generated {len(SOURCE_DOCUMENTS)} source documents at {args.source_dir}")


if __name__ == "__main__":
    main()
