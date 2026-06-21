"""Generate the complete synthetic multi-application RAG benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evaluation.generate_kubernetes_dataset import SOURCE_DOCUMENTS as KUBERNETES_DOCUMENTS
from evaluation.generate_kubernetes_dataset import build_cases as build_kubernetes_cases
from evaluation.generate_bug_dataset import SOURCE_DOCUMENTS as BUG_DOCUMENTS
from evaluation.generate_bug_dataset import build_cases as build_bug_cases


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "application_suite.jsonl"
DEFAULT_SOURCE_DIR = ROOT / "sample-data"


def _documents(
    title_a: str,
    sections_a: list[tuple[str, str]],
    title_b: str,
    sections_b: list[tuple[str, str]],
) -> dict[str, str]:
    def render(title: str, sections: list[tuple[str, str]]) -> str:
        body = "\n\n".join(f"Section: {name}\n{text}" for name, text in sections)
        return f"{title}\n\n{body}\n"

    return {
        "primary_guide.txt": render(title_a, sections_a),
        "secondary_guide.txt": render(title_b, sections_b),
    }


def _definition(
    documents: dict[str, str],
    sections: dict[str, tuple[str, str]],
    questions: list[tuple[str, str, str, str, list[str], bool]],
) -> dict[str, Any]:
    return {"documents": documents, "sections": sections, "questions": questions}


APPLICATIONS: dict[str, dict[str, Any]] = {}


def _register(
    application: str,
    title_a: str,
    sections_a: list[tuple[str, str]],
    title_b: str,
    sections_b: list[tuple[str, str]],
    questions: list[tuple[str, str, str, str, list[str], bool]],
) -> None:
    section_map: dict[str, tuple[str, str]] = {}
    for document, sections in (
        ("primary_guide.txt", sections_a),
        ("secondary_guide.txt", sections_b),
    ):
        for section, text in sections:
            section_map[section] = (document, text)
    APPLICATIONS[application] = _definition(
        _documents(title_a, sections_a, title_b, sections_b),
        section_map,
        questions,
    )


_register(
    "it_helpdesk",
    "IT Helpdesk Access Guide",
    [
        ("Password reset", "Employees reset a forgotten password at access.example.test/reset. The reset link expires after 20 minutes. After five failed attempts, the account is locked for 30 minutes."),
        ("VPN troubleshooting", "For VPN error 720, restart the SecureLink service, remove any saved VPN profile, and import the current profile from the IT portal. Escalate if the error remains after one retry."),
        ("MFA device replacement", "A user replacing a phone must keep the old authenticator until the new device is enrolled. If the old phone is unavailable, the service desk verifies identity with the manager and issues a 15-minute recovery code."),
    ],
    "IT Helpdesk Software Guide",
    [
        ("Software installation", "Standard software is installed from Company Portal without administrator rights. Restricted software requires a manager-approved request and security review."),
        ("Laptop encryption", "All company laptops must use full-disk encryption. A missing encryption status or recovery-key prompt must be reported as priority P2 and the laptop disconnected from sensitive systems."),
        ("Ticket evidence", "Helpdesk tickets should include the asset tag, operating system, exact error text, timestamp, network location, and troubleshooting already attempted. Passwords and recovery codes must never be attached."),
    ],
    [
        ("001", "How long is a password reset link valid?", "The password reset link is valid for 20 minutes.", "factoid", ["Password reset"], True),
        ("002", "What should I do for VPN error 720?", "Restart the SecureLink service, remove the saved VPN profile, import the current profile, and retry once.", "procedural", ["VPN troubleshooting"], True),
        ("003", "How is MFA recovered when the old phone is unavailable?", "The service desk verifies identity with the manager and issues a 15-minute recovery code.", "procedural", ["MFA device replacement"], True),
        ("004", "Can employees install standard software without administrator rights?", "Yes. Standard software is installed through Company Portal without administrator rights.", "factoid", ["Software installation"], True),
        ("005", "What priority applies when laptop encryption status is missing?", "It must be reported as priority P2 and disconnected from sensitive systems.", "reasoning", ["Laptop encryption"], True),
        ("006", "What evidence belongs in a helpdesk ticket?", "Include the asset tag, OS, exact error, timestamp, network location, and attempted troubleshooting, but never passwords or recovery codes.", "procedural", ["Ticket evidence"], True),
        ("007", "A locked user also lost the old MFA phone. What timing constraints apply?", "The account lock lasts 30 minutes, while an identity-verified MFA recovery code is valid for 15 minutes.", "multi_hop", ["Password reset", "MFA device replacement"], True),
        ("008", "What is the company Wi-Fi password?", "The supplied IT helpdesk documents do not contain a Wi-Fi password.", "unanswerable", [], False),
    ],
)

_register(
    "customer_support",
    "Customer Support Policy",
    [
        ("Warranty", "The NovaHub device has a two-year limited hardware warranty from the purchase date. Accidental damage and unauthorized repairs are excluded."),
        ("Returns", "Unopened products may be returned within 30 calendar days. Opened defective products require a support case number and prepaid return label."),
        ("Replacement SLA", "Approved in-warranty replacements ship within two business days. Expedited shipping is available only for premium support customers."),
    ],
    "NovaHub Troubleshooting",
    [
        ("Factory reset", "To reset NovaHub, hold the rear reset button for 10 seconds until the status light flashes amber. The reset removes local settings but does not cancel the subscription."),
        ("Offline status", "If NovaHub shows offline, verify power, restart the router, and move the device within eight metres of the access point. If still offline, collect the diagnostic code."),
        ("Escalation", "Escalate when three resets fail, the device overheats, or a diagnostic code begins with HW-. Overheating devices must be unplugged immediately."),
    ],
    [
        ("001", "How long is the NovaHub hardware warranty?", "The limited hardware warranty lasts two years from purchase.", "factoid", ["Warranty"], True),
        ("002", "Can accidental damage be claimed under warranty?", "No. Accidental damage is excluded from the limited warranty.", "factoid", ["Warranty"], True),
        ("003", "How are opened defective products returned?", "They require a support case number and a prepaid return label.", "procedural", ["Returns"], True),
        ("004", "How quickly does an approved replacement ship?", "It ships within two business days.", "factoid", ["Replacement SLA"], True),
        ("005", "How do I factory-reset NovaHub?", "Hold the rear reset button for 10 seconds until the light flashes amber.", "procedural", ["Factory reset"], True),
        ("006", "What should be tried when NovaHub is offline?", "Verify power, restart the router, move the device within eight metres of the access point, and collect the diagnostic code if it remains offline.", "procedural", ["Offline status"], True),
        ("007", "The unit overheats after repeated resets. What should support do?", "Unplug it immediately and escalate; overheating is an escalation condition.", "multi_hop", ["Escalation", "Factory reset"], True),
        ("008", "Does NovaHub support satellite internet?", "The supplied customer-support documents do not state whether satellite internet is supported.", "unanswerable", [], False),
    ],
)

_register(
    "employee_onboarding",
    "Employee Onboarding Handbook",
    [
        ("First day", "New employees report at 9:30 AM, present government identification, collect a badge, and attend the security briefing before receiving system access."),
        ("Mandatory training", "Security awareness and data privacy training must be completed within five business days. Managers receive an alert when either course is overdue."),
        ("Equipment", "Remote employees receive a laptop and headset by courier. Damage must be reported within 24 hours of delivery with photographs of the packaging."),
    ],
    "Workplace Policies",
    [
        ("Probation check-ins", "Probation check-ins occur at 30, 60, and 90 days. The employee and manager record goals and blockers in the people portal."),
        ("Leave requests", "Planned leave is requested in the people portal at least five business days in advance. Emergency leave may be reported to the manager on the same day."),
        ("Information handling", "Confidential documents must remain in approved storage. Personal cloud drives and personal email accounts are prohibited for company information."),
    ],
    [
        ("001", "What time should a new employee report on the first day?", "A new employee should report at 9:30 AM.", "factoid", ["First day"], True),
        ("002", "What happens before system access is issued?", "The employee presents identification, collects a badge, and attends the security briefing.", "procedural", ["First day"], True),
        ("003", "When must mandatory training be completed?", "Security and privacy training must be completed within five business days.", "factoid", ["Mandatory training"], True),
        ("004", "How quickly should courier damage be reported?", "It must be reported within 24 hours with packaging photographs.", "factoid", ["Equipment"], True),
        ("005", "When are probation check-ins held?", "They occur at 30, 60, and 90 days.", "factoid", ["Probation check-ins"], True),
        ("006", "How is planned leave requested?", "Submit it in the people portal at least five business days in advance.", "procedural", ["Leave requests"], True),
        ("007", "Can onboarding documents be sent to a personal email to finish training at home?", "No. Company information cannot be sent to personal email and must remain in approved storage.", "reasoning", ["Mandatory training", "Information handling"], True),
        ("008", "What is the employee cafeteria menu?", "The supplied onboarding documents do not contain cafeteria menus.", "unanswerable", [], False),
    ],
)

_register(
    "developer_documentation",
    "Payments API Guide",
    [
        ("Authentication", "API requests use a Bearer service token. Tokens are environment-specific and must not be embedded in mobile or browser code."),
        ("Create payment", "POST /v1/payments creates a payment. The idempotency-key header is required and may be reused for 24 hours to safely retry the same request."),
        ("Errors", "HTTP 400 indicates invalid input, 401 invalid credentials, 409 an idempotency conflict, and 429 rate limiting. Retry 429 responses using exponential backoff."),
    ],
    "SDK and Webhook Guide",
    [
        ("SDK support", "Official SDKs support Python 3.11+, Node.js 20+, and Java 17+. Older runtimes receive security fixes only until December 2026."),
        ("Webhook verification", "Verify the x-pay-signature header against the raw body using HMAC-SHA256. Reject events older than five minutes."),
        ("Pagination", "List endpoints use cursor pagination. Pass next_cursor as cursor on the following request; a null next_cursor indicates the final page."),
    ],
    [
        ("001", "How are Payments API requests authenticated?", "Use an environment-specific Bearer service token.", "factoid", ["Authentication"], True),
        ("002", "What header is required when creating a payment?", "The idempotency-key header is required.", "factoid", ["Create payment"], True),
        ("003", "How long may an idempotency key be reused?", "It may be reused for 24 hours to retry the same request safely.", "factoid", ["Create payment"], True),
        ("004", "What does HTTP 409 mean?", "It indicates an idempotency conflict.", "factoid", ["Errors"], True),
        ("005", "Which Python versions are officially supported?", "Python 3.11 and newer are officially supported.", "factoid", ["SDK support"], True),
        ("006", "How should a webhook signature be verified?", "Verify x-pay-signature over the raw body with HMAC-SHA256 and reject events older than five minutes.", "procedural", ["Webhook verification"], True),
        ("007", "How should a Node.js client retry a rate-limited payment creation safely?", "Use Node.js 20+, retry with exponential backoff, and reuse the same idempotency key within 24 hours.", "multi_hop", ["SDK support", "Errors", "Create payment"], True),
        ("008", "Does the API expose a GraphQL endpoint?", "The supplied developer documentation does not describe a GraphQL endpoint.", "unanswerable", [], False),
    ],
)

_register(
    "incident_response",
    "Incident Response Runbook",
    [
        ("Declaration", "Declare an incident when customer impact is ongoing, security is suspected, or recovery needs coordination across two or more teams. The incident commander owns decisions and timeline updates."),
        ("First fifteen minutes", "Within 15 minutes, create the incident channel, assign commander and scribe, record impact, freeze risky deployments, and publish an initial internal update."),
        ("Customer updates", "For severity SEV-1, publish customer updates every 30 minutes. For SEV-2, update every 60 minutes while impact continues."),
    ],
    "Recovery and Review",
    [
        ("Rollback", "Prefer rollback when a recent deployment correlates with impact and rollback is tested. Record the deployment identifier and validation checks before execution."),
        ("Evidence preservation", "Preserve logs, traces, alerts, command history, and configuration snapshots. Do not edit original evidence; store analysis in a separate document."),
        ("Post-incident review", "A review is due within five business days for SEV-1 and SEV-2 incidents. It must include contributing factors, timeline, corrective actions, owners, and due dates."),
    ],
    [
        ("001", "When should an incident be declared?", "Declare one for ongoing customer impact, suspected security issues, or cross-team recovery coordination.", "factoid", ["Declaration"], True),
        ("002", "Who owns incident decisions and timeline updates?", "The incident commander owns them.", "factoid", ["Declaration"], True),
        ("003", "What must happen in the first 15 minutes?", "Create the channel, assign commander and scribe, record impact, freeze risky deployments, and publish an initial internal update.", "procedural", ["First fifteen minutes"], True),
        ("004", "How often are SEV-1 customers updated?", "Every 30 minutes while impact continues.", "factoid", ["Customer updates"], True),
        ("005", "When is rollback preferred?", "When a recent deployment correlates with impact and the rollback is tested.", "reasoning", ["Rollback"], True),
        ("006", "How should original incident evidence be handled?", "Preserve it without editing; place analysis in a separate document.", "procedural", ["Evidence preservation"], True),
        ("007", "A SEV-1 follows a recent deployment. What immediate and follow-up actions apply?", "Freeze risky deployments, consider the tested rollback, preserve evidence, and complete a review within five business days.", "multi_hop", ["First fifteen minutes", "Rollback", "Evidence preservation", "Post-incident review"], True),
        ("008", "Which video-conference vendor must incidents use?", "The supplied incident runbooks do not mandate a video-conference vendor.", "unanswerable", [], False),
    ],
)

_register(
    "compliance_policy",
    "Data Governance Policy",
    [
        ("Classification", "Data is classified Public, Internal, Confidential, or Restricted. Customer identifiers, authentication data, and payment records are Restricted."),
        ("Retention", "Support tickets are retained for three years. Security audit logs are retained for seven years. Expired records are deleted through the approved disposal workflow."),
        ("Access review", "Owners review access to Restricted data quarterly. Removed users must lose access within four hours of the approved removal request."),
    ],
    "Vendor and Incident Compliance",
    [
        ("Vendor assessment", "Vendors processing Confidential or Restricted data require security review, a data-processing agreement, and annual reassessment."),
        ("Breach notification", "Suspected exposure of Restricted data must be reported to Security within one hour. Legal and Privacy determine external notification obligations."),
        ("Evidence", "Compliance evidence must identify the control, system, owner, collection date, and source. Screenshots without timestamps are insufficient."),
    ],
    [
        ("001", "How are payment records classified?", "Payment records are Restricted data.", "factoid", ["Classification"], True),
        ("002", "How long are support tickets retained?", "They are retained for three years.", "factoid", ["Retention"], True),
        ("003", "How often is Restricted-data access reviewed?", "Quarterly.", "factoid", ["Access review"], True),
        ("004", "What is required before a vendor processes Restricted data?", "Security review, a data-processing agreement, and annual reassessment are required.", "procedural", ["Vendor assessment"], True),
        ("005", "How quickly must suspected Restricted-data exposure be reported?", "It must be reported to Security within one hour.", "factoid", ["Breach notification"], True),
        ("006", "Why is an untimestamped screenshot insufficient evidence?", "Evidence must include the control, system, owner, collection date, and source; an untimestamped screenshot lacks required provenance.", "reasoning", ["Evidence"], True),
        ("007", "A vendor stores payment records. Which classification and review requirements apply?", "The records are Restricted, so the vendor needs security review, a data-processing agreement, and annual reassessment.", "multi_hop", ["Classification", "Vendor assessment"], True),
        ("008", "What fine applies for a late access review?", "The supplied compliance policies do not specify a monetary fine.", "unanswerable", [], False),
    ],
)

_register(
    "education_assistant",
    "Machine Learning Course Guide",
    [
        ("Assessment", "The final grade is 30 percent assignments, 20 percent quizzes, 20 percent midterm, and 30 percent project. A total score of 50 percent is required to pass."),
        ("Late work", "Assignments lose 10 percent per calendar day for up to three days. After three days, submissions are accepted only with an approved extension."),
        ("Project", "Projects are completed in teams of three or four. The proposal is due in week 5, checkpoint in week 9, and presentation in week 13."),
    ],
    "Laboratory Handbook",
    [
        ("Lab access", "GPU lab access is available from 8 AM to 10 PM. Students authenticate with the course account and may reserve at most four GPU hours per day."),
        ("Reproducibility", "Every experiment submission must include a random seed, environment file, training command, dataset version, and metric definition."),
        ("Academic integrity", "Students may discuss concepts but must write their own code and report. Reusing public code requires attribution and license compliance."),
    ],
    [
        ("001", "How much is the course project worth?", "The project is worth 30 percent of the final grade.", "factoid", ["Assessment"], True),
        ("002", "What score is required to pass?", "A total score of 50 percent is required.", "factoid", ["Assessment"], True),
        ("003", "What happens to an assignment submitted two days late?", "It receives a 20 percent late penalty.", "reasoning", ["Late work"], True),
        ("004", "When is the project checkpoint?", "It is due in week 9.", "factoid", ["Project"], True),
        ("005", "How many GPU hours may a student reserve per day?", "At most four GPU hours per day.", "factoid", ["Lab access"], True),
        ("006", "What makes an experiment submission reproducible?", "Include a random seed, environment file, training command, dataset version, and metric definition.", "procedural", ["Reproducibility"], True),
        ("007", "Can a team reuse public training code in its project?", "Yes, if the team writes its own report and provides attribution while complying with the code license.", "multi_hop", ["Project", "Academic integrity"], True),
        ("008", "Which textbook chapter is assigned for week 7?", "The supplied course documents do not list weekly textbook chapters.", "unanswerable", [], False),
    ],
)

_register(
    "healthcare_administration",
    "Clinic Administration Manual",
    [
        ("Appointments", "Routine appointments may be rescheduled without charge up to 24 hours before the visit. Later changes are marked late cancellation unless waived by clinic management."),
        ("Records requests", "Patients submit record requests using form MR-12 with identity verification. The records team acknowledges requests within two business days and normally completes them within ten business days."),
        ("Interpreter services", "Professional interpreter services are available without charge. Staff must not ask minor children to interpret clinical or consent discussions."),
    ],
    "Billing and Privacy Procedures",
    [
        ("Billing questions", "Billing disputes require the invoice number, service date, disputed line item, and contact details. Clinical staff must not promise that a charge will be removed."),
        ("Privacy incidents", "Misdirected records or unauthorized chart access must be reported to the Privacy Office immediately. Staff should preserve evidence and avoid contacting the unintended recipient without instructions."),
        ("Administrative boundary", "Administrative staff may explain scheduling, records, billing, and privacy procedures. They must not diagnose conditions, interpret test results, or recommend treatment."),
    ],
    [
        ("001", "When can a routine appointment be rescheduled without charge?", "Up to 24 hours before the visit.", "factoid", ["Appointments"], True),
        ("002", "How does a patient request medical records?", "Submit form MR-12 and complete identity verification.", "procedural", ["Records requests"], True),
        ("003", "How quickly are records requests acknowledged?", "Within two business days.", "factoid", ["Records requests"], True),
        ("004", "May a minor child interpret a consent discussion?", "No. Staff must use professional interpreter services.", "safety", ["Interpreter services"], True),
        ("005", "What details are needed for a billing dispute?", "The invoice number, service date, disputed line item, and contact details.", "procedural", ["Billing questions"], True),
        ("006", "What should staff do after records are sent to the wrong recipient?", "Report immediately to the Privacy Office, preserve evidence, and wait for instructions before contacting the recipient.", "procedural", ["Privacy incidents"], True),
        ("007", "Can administrative staff explain a laboratory result while handling a records request?", "No. They may explain the records process but must not interpret test results.", "reasoning", ["Records requests", "Administrative boundary"], True),
        ("008", "Which medication should a patient take for a fever?", "The supplied administrative documents do not provide treatment recommendations, and administrative staff must not recommend treatment.", "unanswerable", [], False),
    ],
)

_register(
    "legal_document_navigation",
    "Synthetic Services Agreement",
    [
        ("Term", "The agreement begins on 1 July 2026 and continues for 12 months. It renews for additional 12-month terms unless either party gives 30 days written notice."),
        ("Payment", "Invoices are due within 30 days. Undisputed late amounts accrue interest at one percent per month."),
        ("Confidentiality", "Confidential information may be used only to perform the agreement and must be protected with reasonable safeguards. The obligation survives termination for three years."),
    ],
    "Synthetic Contract Procedures",
    [
        ("Notices", "Formal notices must be sent by tracked courier or email to the notice addresses in Schedule A. Email notice is effective when receipt is acknowledged."),
        ("Termination", "Either party may terminate for material breach if the breach is not cured within 15 days after written notice. Insolvency permits immediate termination."),
        ("Navigation boundary", "The contract assistant may locate and summarize clauses from supplied documents. It must not predict court outcomes or replace review by qualified counsel."),
    ],
    [
        ("001", "When does the agreement begin and how long is the initial term?", "It begins on 1 July 2026 and has a 12-month initial term.", "factoid", ["Term"], True),
        ("002", "How much renewal notice is required?", "Either party must give 30 days written notice to prevent renewal.", "factoid", ["Term"], True),
        ("003", "When are invoices due?", "Within 30 days.", "factoid", ["Payment"], True),
        ("004", "How long does confidentiality survive termination?", "For three years after termination.", "factoid", ["Confidentiality"], True),
        ("005", "When is an email notice effective?", "When receipt is acknowledged.", "factoid", ["Notices"], True),
        ("006", "What cure period applies to a material breach?", "The breaching party has 15 days after written notice to cure.", "procedural", ["Termination"], True),
        ("007", "How should a party terminate for uncured material breach?", "Send formal written notice using the permitted notice method, then allow the 15-day cure period before termination.", "multi_hop", ["Notices", "Termination"], True),
        ("008", "Will a court enforce the renewal clause?", "The supplied documents cannot predict a court outcome; qualified legal counsel must review that question.", "unanswerable", [], False),
    ],
)

_register(
    "equipment_maintenance",
    "Hydraulic Press Maintenance Manual",
    [
        ("Daily inspection", "Before each shift, inspect guards, hoses, fluid level, emergency stop, and visible leaks. Do not operate if a guard is missing or a hose shows exposed reinforcement."),
        ("Lubrication", "Lubricate guide rails every 250 operating hours with grease type GX-4. Over-lubrication can contaminate the position sensor."),
        ("Pressure drift", "If pressure drifts more than five percent, check fluid temperature, filter restriction, and relief-valve setting before replacing the pump."),
    ],
    "Hydraulic Press Safety Guide",
    [
        ("Lockout", "Maintenance inside the guarded area requires electrical and hydraulic lockout, stored-pressure release, and zero-energy verification by the technician."),
        ("Overheating", "Stop the press when hydraulic fluid exceeds 75 degrees Celsius. Check the cooler fan and oil level, and resume only below 60 degrees Celsius."),
        ("Service records", "Record operating hours, inspection findings, parts replaced, technician name, and return-to-service checks after maintenance."),
    ],
    [
        ("001", "What must be inspected before each shift?", "Inspect guards, hoses, fluid level, emergency stop, and visible leaks.", "procedural", ["Daily inspection"], True),
        ("002", "When must the press not be operated?", "Do not operate it with a missing guard or a hose showing exposed reinforcement.", "safety", ["Daily inspection"], True),
        ("003", "How often are the guide rails lubricated?", "Every 250 operating hours using GX-4 grease.", "factoid", ["Lubrication"], True),
        ("004", "What should be checked before replacing a pump for pressure drift?", "Check fluid temperature, filter restriction, and relief-valve setting.", "procedural", ["Pressure drift"], True),
        ("005", "What lockout steps are required inside the guarded area?", "Apply electrical and hydraulic lockout, release stored pressure, and verify zero energy.", "safety", ["Lockout"], True),
        ("006", "At what temperature must the press stop?", "Stop when hydraulic fluid exceeds 75 degrees Celsius.", "factoid", ["Overheating"], True),
        ("007", "A leaking hose has exposed reinforcement and the fluid is 78 degrees. What actions apply?", "Do not operate the press, stop it for overheating, inspect the cooler fan and oil level, and complete lockout before maintenance.", "multi_hop", ["Daily inspection", "Overheating", "Lockout"], True),
        ("008", "What is the purchase price of a replacement pump?", "The supplied maintenance documents do not contain parts pricing.", "unanswerable", [], False),
    ],
)

_register(
    "sales_enablement",
    "CloudDesk Product Guide",
    [
        ("Plans", "CloudDesk Standard supports up to 100 users and 500 GB storage. CloudDesk Enterprise supports unlimited users, 5 TB storage, SSO, audit export, and a dedicated success manager."),
        ("Trial", "The trial lasts 14 days and includes Standard features for up to 20 users. Trial data is retained for 30 days after expiration."),
        ("Positioning", "CloudDesk is positioned for regulated teams needing controlled document collaboration. Sales must not claim that the product guarantees regulatory compliance."),
    ],
    "Sales Process Guide",
    [
        ("Discounts", "Account executives may approve discounts up to 10 percent. Discounts from 11 to 20 percent require sales-director approval; larger discounts require finance approval."),
        ("Security questions", "Use the approved security brief for encryption, data residency, and certifications. Unknown security answers must be routed to the security team rather than guessed."),
        ("Competitor claims", "Comparisons must use current approved battlecards. Do not claim a competitor lacks a feature without a dated, cited source."),
    ],
    [
        ("001", "How many users does CloudDesk Standard support?", "Up to 100 users.", "factoid", ["Plans"], True),
        ("002", "Which plan includes SSO and audit export?", "CloudDesk Enterprise.", "factoid", ["Plans"], True),
        ("003", "How long is trial data retained after expiration?", "For 30 days.", "factoid", ["Trial"], True),
        ("004", "May sales promise that CloudDesk guarantees compliance?", "No. Sales must not claim the product guarantees regulatory compliance.", "safety", ["Positioning"], True),
        ("005", "Who approves a 15 percent discount?", "The sales director must approve it.", "reasoning", ["Discounts"], True),
        ("006", "What should a seller do when the security brief lacks an answer?", "Route the question to the security team instead of guessing.", "procedural", ["Security questions"], True),
        ("007", "A regulated customer needs SSO and asks for a 15 percent discount. What applies?", "Recommend Enterprise for SSO, avoid compliance guarantees, and obtain sales-director approval for the discount.", "multi_hop", ["Plans", "Positioning", "Discounts"], True),
        ("008", "What exact price does a competitor charge?", "The supplied sales documents do not contain competitor pricing.", "unanswerable", [], False),
    ],
)


def _case(
    application: str,
    sequence: str,
    question: str,
    ground_truth: str,
    category: str,
    references: list[str],
    answerable: bool,
    definition: dict[str, Any],
) -> dict[str, Any]:
    sources = [definition["sections"][reference] for reference in references]
    return {
        "id": f"{application.upper()}-{sequence}",
        "application": application,
        "question": question,
        "ground_truth": ground_truth,
        "reference_contexts": [text for _, text in sources],
        "expected_sources": [
            {
                "document": f"{application}/{document}",
                "section": reference,
            }
            for reference, (document, _) in zip(references, sources)
        ],
        "category": category,
        "answerable": answerable,
        "tags": [application, category],
    }


def build_suite_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for case in build_kubernetes_cases():
        copied = dict(case)
        copied["expected_sources"] = [
            {
                **source,
                "document": f"kubernetes_troubleshooting/{source['document']}",
            }
            for source in case["expected_sources"]
        ]
        cases.append(copied)

    for case in build_bug_cases():
        copied = dict(case)
        copied["expected_sources"] = [
            {
                **source,
                "document": f"bug-reporting/{source['document']}",
            }
            for source in case["expected_sources"]
        ]
        cases.append(copied)

    for application, definition in APPLICATIONS.items():
        for question in definition["questions"]:
            cases.append(_case(application, *question, definition))
    return cases


def generate(dataset_path: Path, source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    dataset_path.parent.mkdir(parents=True, exist_ok=True)

    kubernetes_dir = source_dir / "kubernetes_troubleshooting"
    kubernetes_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in KUBERNETES_DOCUMENTS.items():
        (kubernetes_dir / filename).write_text(content, encoding="utf-8")

    bug_dir = source_dir / "bug-reporting"
    bug_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in BUG_DOCUMENTS.items():
        (bug_dir / filename).write_text(content, encoding="utf-8")

    for application, definition in APPLICATIONS.items():
        app_dir = source_dir / application
        app_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in definition["documents"].items():
            (app_dir / filename).write_text(content, encoding="utf-8")

    cases = build_suite_cases()
    with dataset_path.open("w", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    args = parser.parse_args()
    generate(args.output, args.source_dir)
    cases = build_suite_cases()
    print(f"Generated {len(cases)} cases across {len(APPLICATIONS) + 2} applications")
    print(f"Dataset: {args.output}")
    print(f"Sources: {args.source_dir}")


if __name__ == "__main__":
    main()
