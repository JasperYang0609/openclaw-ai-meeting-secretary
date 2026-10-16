#!/usr/bin/env python3
"""Validate a confirmed meeting Markdown file before Gemini RAG indexing."""

from __future__ import annotations

import argparse
import datetime as dt
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
    "rag_approval",
    "access_scope",
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
    expected_customer_id: str | None = None,
    expected_index_project: str | None = None,
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
    if access_scope != "organization-wide" and not access_scope.startswith(
        "isolated-route:"
    ):
        errors.append(
            "access_scope must be organization-wide or isolated-route:<name>"
        )

    if expected_customer_id and fields.get("customer_id") != expected_customer_id:
        errors.append("customer_id does not match the installed customer identity")
    if expected_index_project and fields.get("index_project") != expected_index_project:
        errors.append("index_project does not match the installed RAG project")

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
    parser.add_argument("--expected-customer-id")
    parser.add_argument("--expected-index-project")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    errors = validate(
        args.path,
        expected_customer_id=args.expected_customer_id,
        expected_index_project=args.expected_index_project,
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

