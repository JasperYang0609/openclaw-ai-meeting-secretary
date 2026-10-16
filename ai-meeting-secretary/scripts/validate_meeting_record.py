#!/usr/bin/env python3
"""Validate a confirmed meeting Markdown file before Gemini RAG indexing."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import re
import sys
from pathlib import Path


MAX_FILE_BYTES = 1_200_000
REQUIRED_FIELDS = {
    "schema",
    "document_type",
    "meeting_id",
    "customer_id",
    "company",
    "meeting_date",
    "title",
    "record_status",
    "confirmed_by_id",
    "confirmed_at",
    "confirmation_receipt_id",
    "rag_approval",
    "rag_approved_by_id",
    "rag_approved_at",
    "rag_approval_receipt_id",
    "access_scope",
    "source_id",
    "index_project",
}
SUMMARY_HEADINGS = {
    "Meeting summary",
    "Decisions",
    "Action items",
    "Source integrity",
}
TRANSCRIPT_HEADINGS = {"Cleaned transcript", "Source integrity"}
FORBIDDEN_HEADINGS = {"Private chatter", "Raw transcript", "Uncorrected transcript"}
PLACEHOLDER_PATTERNS = (
    re.compile(r"＿＿+"),
    re.compile(r"\b(?:TODO|TBD)\b", re.IGNORECASE),
    re.compile(r"REPLACE_WITH_[A-Z0-9_]+"),
    re.compile(r"<(?:customer|meeting|project|workspace|skill)-[^>]+>", re.IGNORECASE),
)

RECEIPT_SCRIPT = Path(__file__).with_name("validate_confirmation_receipt.py")
RECEIPT_SPEC = importlib.util.spec_from_file_location(
    "validate_confirmation_receipt", RECEIPT_SCRIPT
)
RECEIPT_MODULE = importlib.util.module_from_spec(RECEIPT_SPEC)
assert RECEIPT_SPEC and RECEIPT_SPEC.loader
RECEIPT_SPEC.loader.exec_module(RECEIPT_MODULE)
SECRET_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    (
        "JWT",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
        ),
    ),
    (
        "service role credential",
        re.compile(
            r"\bservice[_ -]?role[_ -]?(?:key|token)\b\s*[:=]",
            re.IGNORECASE,
        ),
    ),
)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    fields: dict[str, str] = {}
    for raw_line in text[4:end].splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"\'')
    return fields, text[end + 5 :]


def headings(body: str) -> set[str]:
    return {
        match.group(1).strip()
        for match in re.finditer(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE)
    }


def validate(
    path: Path,
    expected_customer_id: str | None,
    expected_index_project: str | None,
    confirmation_receipt_path: Path | None,
    onboarding_config_path: Path | None,
    expected_request_id: str | None,
    now: dt.datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    try:
        size = path.stat().st_size
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"cannot read UTF-8 Markdown: {exc}"]

    if path.suffix.lower() != ".md":
        errors.append("file must use .md extension")
    if size > MAX_FILE_BYTES:
        errors.append(f"file exceeds {MAX_FILE_BYTES} bytes")

    fields, body = parse_frontmatter(text)
    missing = sorted(REQUIRED_FIELDS - fields.keys())
    if missing:
        errors.append("missing frontmatter fields: " + ", ".join(missing))

    if fields.get("schema") != "ai_meeting_secretary.meeting_record.v1":
        errors.append("schema must be ai_meeting_secretary.meeting_record.v1")
    if fields.get("record_status") != "confirmed":
        errors.append("record_status must be confirmed")
    if fields.get("rag_approval") != "approved":
        errors.append("rag_approval must be approved")
    if fields.get("document_type") not in {
        "meeting_summary",
        "meeting_transcript_clean",
    }:
        errors.append(
            "document_type must be meeting_summary or meeting_transcript_clean"
        )

    date_value = fields.get("meeting_date", "")
    try:
        if date_value:
            dt.date.fromisoformat(date_value)
    except ValueError:
        errors.append("meeting_date must be a valid YYYY-MM-DD date")

    access_scope = fields.get("access_scope", "")
    isolated_name = access_scope.removeprefix("isolated-route:").strip()
    if access_scope != "organization-wide" and not (
        access_scope.startswith("isolated-route:") and isolated_name
    ):
        errors.append(
            "access_scope must be organization-wide or isolated-route:<name>"
        )

    if not expected_customer_id:
        errors.append("expected_customer_id is required")
    elif fields.get("customer_id") != expected_customer_id:
        errors.append("customer_id does not match the installed customer identity")
    if not expected_index_project:
        errors.append("expected_index_project is required")
    elif fields.get("index_project") != expected_index_project:
        errors.append("index_project does not match the installed RAG project")

    for field in ("confirmed_at", "rag_approved_at"):
        value = fields.get(field, "")
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError
        except ValueError:
            errors.append(f"{field} must be a timezone-aware ISO-8601 timestamp")

    receipt = None
    config = None
    if not confirmation_receipt_path or not onboarding_config_path or not expected_request_id:
        errors.append(
            "confirmation receipt, onboarding config, and expected_request_id are required"
        )
    else:
        try:
            receipt = RECEIPT_MODULE.load_json(confirmation_receipt_path)
            config = RECEIPT_MODULE.load_json(onboarding_config_path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"cannot read confirmation evidence: {exc}")
        else:
            errors.extend(
                "confirmation receipt: " + error
                for error in RECEIPT_MODULE.validate(
                    receipt,
                    config,
                    expected_meeting_id=fields.get("meeting_id", ""),
                    expected_request_id=expected_request_id,
                    now=now,
                    require_rag_approval=True,
                )
            )
    if config is not None:
        rag_config = config.get("rag")
        if not isinstance(rag_config, dict):
            errors.append("onboarding config must contain a RAG configuration")
        else:
            if rag_config.get("enabled") is not True:
                errors.append("onboarding RAG must be explicitly enabled")
            if rag_config.get("provider") != "google-gemini":
                errors.append("onboarding RAG provider must be google-gemini")
            if rag_config.get("model") != "gemini-embedding-001":
                errors.append("onboarding RAG model must be gemini-embedding-001")
            if rag_config.get("customer_id") != expected_customer_id:
                errors.append("onboarding RAG customer_id does not match the expected customer")
            if rag_config.get("index_project") != expected_index_project:
                errors.append("onboarding RAG index_project does not match the expected project")
            if rag_config.get("customer_id") != fields.get("customer_id"):
                errors.append("document customer_id does not match onboarding RAG identity")
            if rag_config.get("index_project") != fields.get("index_project"):
                errors.append("document index_project does not match onboarding RAG identity")
            if rag_config.get("source_id") != fields.get("source_id"):
                errors.append("document source_id does not match onboarding RAG source")
            if rag_config.get("access_mode") != fields.get("access_scope"):
                errors.append("document access_scope does not match onboarding RAG route")
            if (
                fields.get("document_type") == "meeting_transcript_clean"
                and rag_config.get("include_clean_transcript") is not True
            ):
                errors.append("onboarding RAG does not approve cleaned transcripts")
    if receipt:
        notion = receipt.get("notion", {})
        rag = receipt.get("rag", {})
        receipt_id = receipt.get("receipt_id")
        if fields.get("confirmation_receipt_id") != receipt_id:
            errors.append("confirmation_receipt_id does not match the receipt")
        if fields.get("rag_approval_receipt_id") != receipt_id:
            errors.append("rag_approval_receipt_id does not match the receipt")
        if fields.get("confirmed_by_id") != notion.get("meeting_confirmed_by_id"):
            errors.append("confirmed_by_id does not match the Notion readback")
        if fields.get("confirmed_at") != notion.get("meeting_confirmed_at"):
            errors.append("confirmed_at does not match the Notion readback")
        if fields.get("rag_approved_by_id") != rag.get("approved_by_id"):
            errors.append("rag_approved_by_id does not match the receipt")
        if fields.get("rag_approved_at") != rag.get("approved_at"):
            errors.append("rag_approved_at does not match the receipt")
        approved_scope = rag.get("approved_scope")
        if (
            fields.get("document_type") == "meeting_transcript_clean"
            and approved_scope != "meeting-summary+clean-transcript"
        ):
            errors.append("receipt RAG scope does not approve cleaned transcripts")
        if fields.get("document_type") == "meeting_summary" and approved_scope not in {
            "meeting-summary",
            "meeting-summary+clean-transcript",
        }:
            errors.append("receipt RAG scope does not approve meeting summaries")

    found_headings = headings(body)
    required_headings = (
        TRANSCRIPT_HEADINGS
        if fields.get("document_type") == "meeting_transcript_clean"
        else SUMMARY_HEADINGS
    )
    missing_headings = sorted(required_headings - found_headings)
    if missing_headings:
        errors.append("missing sections: " + ", ".join(missing_headings))

    forbidden = sorted(FORBIDDEN_HEADINGS & found_headings)
    if forbidden:
        errors.append("forbidden sections present: " + ", ".join(forbidden))

    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(text):
            errors.append(f"placeholder content detected: {pattern.pattern}")
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append(f"possible secret detected: {label}")

    if len(re.sub(r"\s+", "", body)) < 120:
        errors.append("document body is too short to be a useful meeting record")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a confirmed meeting Markdown file before Gemini RAG indexing."
    )
    parser.add_argument("path", type=Path)
    parser.add_argument("--expected-customer-id", required=True)
    parser.add_argument("--expected-index-project", required=True)
    parser.add_argument("--confirmation-receipt", type=Path, required=True)
    parser.add_argument("--onboarding-config", type=Path, required=True)
    parser.add_argument("--expected-request-id", required=True)
    parser.add_argument("--now", help="ISO-8601 time for deterministic testing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    now = None
    if args.now:
        try:
            now = dt.datetime.fromisoformat(args.now.replace("Z", "+00:00"))
        except ValueError:
            print("FAIL\n- now must be a valid ISO-8601 timestamp")
            return 1
    errors = validate(
        args.path,
        expected_customer_id=args.expected_customer_id,
        expected_index_project=args.expected_index_project,
        confirmation_receipt_path=args.confirmation_receipt,
        onboarding_config_path=args.onboarding_config,
        expected_request_id=args.expected_request_id,
        now=now,
    )
    result = {
        "status": "PASS" if not errors else "FAIL",
        "path": str(args.path),
        "errors": errors,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
    else:
        print("PASS: meeting record is eligible for the configured Gemini RAG gate")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
