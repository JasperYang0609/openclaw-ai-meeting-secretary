#!/usr/bin/env python3
"""Validate the customer-private onboarding contract without external services."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


PLACEHOLDER = re.compile(r"^(?:REPLACE_WITH_|YYYY-MM-DD)")
SNOWFLAKE = re.compile(r"^\d{17,20}$")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)


def get(data: dict[str, Any], dotted: str, errors: list[str]) -> Any:
    value: Any = data
    for key in dotted.split("."):
        if not isinstance(value, dict) or key not in value:
            errors.append(f"missing field: {dotted}")
            return None
        value = value[key]
    return value


def strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for child in value.values():
            found.extend(strings(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(strings(child))
    return found


def validate(data: dict[str, Any], allow_placeholders: bool = False) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "ai_meeting_secretary.onboarding.v1":
        errors.append("schema must be ai_meeting_secretary.onboarding.v1")

    required = [
        "organization.name",
        "organization.departments",
        "notion.transcripts_database_id",
        "notion.meeting_records_database_id",
        "notion.task_master_database_id",
        "notion.department_database_ids",
        "notion.meeting_template_page_id",
        "notion.ai_section_marker",
        "discord.notification_channel_id",
        "discord.confirmation_phrase",
        "task_dispatch.mode",
        "local_records.canonical_root",
        "rag.enabled",
    ]
    values = {field: get(data, field, errors) for field in required}

    departments = values.get("organization.departments")
    if not isinstance(departments, list) or not departments or not all(
        isinstance(item, str) and item.strip() for item in departments
    ):
        errors.append("organization.departments must contain at least one name")
    elif len(set(departments)) != len(departments):
        errors.append("organization.departments must not contain duplicates")

    department_targets = values.get("notion.department_database_ids")
    if isinstance(departments, list) and isinstance(department_targets, dict):
        if set(department_targets) != set(departments):
            errors.append(
                "notion.department_database_ids keys must exactly match departments"
            )
    elif department_targets is not None:
        errors.append("notion.department_database_ids must be an object")

    dispatch_mode = values.get("task_dispatch.mode")
    if dispatch_mode not in {"manual", "scheduled", "disabled"}:
        errors.append("task_dispatch.mode must be manual, scheduled, or disabled")

    channel_id = values.get("discord.notification_channel_id")
    if (
        isinstance(channel_id, str)
        and not allow_placeholders
        and not SNOWFLAKE.fullmatch(channel_id)
    ):
        errors.append("discord.notification_channel_id must be a numeric Discord ID")

    rag = data.get("rag")
    if not isinstance(rag, dict):
        errors.append("rag must be an object")
    elif rag.get("enabled") is True:
        rag_required = [
            "provider",
            "model",
            "plugin_project_root",
            "canonical_root",
            "source_id",
            "index_project",
            "customer_id",
            "access_mode",
            "include_clean_transcript",
            "approval_by",
            "approval_at",
        ]
        for field in rag_required:
            if field not in rag:
                errors.append(f"missing field: rag.{field}")
        if rag.get("provider") != "google-gemini":
            errors.append("rag.provider must be google-gemini")
        if rag.get("model") != "gemini-embedding-001":
            errors.append("rag.model must be gemini-embedding-001")
        access_mode = rag.get("access_mode", "")
        if access_mode != "organization-wide" and not str(access_mode).startswith(
            "isolated-route:"
        ):
            errors.append(
                "rag.access_mode must be organization-wide or isolated-route:<name>"
            )
        if not isinstance(rag.get("include_clean_transcript"), bool):
            errors.append("rag.include_clean_transcript must be true or false")
        approval_at = rag.get("approval_at", "")
        if not allow_placeholders:
            try:
                dt.date.fromisoformat(str(approval_at))
            except ValueError:
                errors.append("rag.approval_at must be a valid YYYY-MM-DD date")

    all_strings = strings(data)
    if not allow_placeholders:
        for value in all_strings:
            if PLACEHOLDER.match(value):
                errors.append("placeholder values must be replaced before use")
                break
    for value in all_strings:
        if any(pattern.search(value) for pattern in SECRET_PATTERNS):
            errors.append("possible credential detected in onboarding config")
            break
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate meeting onboarding JSON.")
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Validate the repository example without treating placeholders as live values.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        data = json.loads(args.path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors = [f"cannot read onboarding JSON: {exc}"]
    else:
        errors = validate(data, allow_placeholders=args.allow_placeholders)

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
        print("PASS: onboarding contract is structurally ready")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

