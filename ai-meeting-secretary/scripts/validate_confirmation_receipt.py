#!/usr/bin/env python3
"""Validate consistency of fresh Discord and Notion confirmation readbacks.

This script does not fetch or authenticate provider data. Callers must build the
receipt from live provider readback in the same run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


SNOWFLAKE = re.compile(r"^\d{17,20}$")
PLACEHOLDER = re.compile(r"^(?:REPLACE_WITH_|YYYY-MM-DD)")


def parse_time(value: Any, field: str, errors: list[str]) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty ISO-8601 timestamp")
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be a valid ISO-8601 timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone")
        return None
    return parsed.astimezone(dt.timezone.utc)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON must be an object")
    return data


def validate(
    receipt: dict[str, Any],
    config: dict[str, Any],
    expected_meeting_id: str,
    expected_request_id: str,
    now: dt.datetime | None = None,
    require_rag_approval: bool = False,
) -> list[str]:
    errors: list[str] = []
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)

    if receipt.get("schema") != "ai_meeting_secretary.confirmation_receipt.v1":
        errors.append("receipt schema is invalid")
    if receipt.get("meeting_id") != expected_meeting_id:
        errors.append("meeting_id does not match the expected meeting")
    if receipt.get("request_id") != expected_request_id:
        errors.append("request_id does not match the expected confirmation request")

    receipt_id = receipt.get("receipt_id")
    request_message_id = receipt.get("request_message_id")
    if not isinstance(receipt_id, str) or not receipt_id.strip() or PLACEHOLDER.match(receipt_id):
        errors.append("receipt_id must be a stable non-placeholder value")
    if not isinstance(request_message_id, str) or not SNOWFLAKE.fullmatch(request_message_id):
        errors.append("request_message_id must be a numeric Discord message ID")

    issued_at = parse_time(receipt.get("issued_at"), "issued_at", errors)
    discord_config = config.get("discord", {})
    max_age = discord_config.get("confirmation_max_age_minutes")
    if not isinstance(max_age, int) or isinstance(max_age, bool) or max_age <= 0:
        errors.append("config confirmation_max_age_minutes must be a positive integer")
    elif issued_at:
        age = now - issued_at
        if age.total_seconds() < -60:
            errors.append("receipt issued_at is in the future")
        if age > dt.timedelta(minutes=max_age):
            errors.append("confirmation receipt is expired")

    discord = receipt.get("discord")
    if not isinstance(discord, dict):
        errors.append("discord readback must be an object")
    else:
        if discord.get("channel_id") != discord_config.get("notification_channel_id"):
            errors.append("Discord channel does not match onboarding config")
        authorized = discord_config.get("authorized_confirmer_ids", [])
        if discord.get("author_id") not in authorized:
            errors.append("Discord confirmer is not authorized")
        if discord.get("phrase") != discord_config.get("confirmation_phrase"):
            errors.append("Discord confirmation phrase does not match")
        if discord.get("reply_to_message_id") != request_message_id:
            errors.append("Discord reply does not reference the confirmation request")
        if not isinstance(discord.get("message_id"), str) or not SNOWFLAKE.fullmatch(
            discord.get("message_id", "")
        ):
            errors.append("Discord confirmation message_id is invalid")

    notion_config = config.get("notion_confirmation", {})
    notion_authorized = notion_config.get("authorized_confirmer_ids", [])
    notion = receipt.get("notion")
    if not isinstance(notion, dict):
        errors.append("Notion readback must be an object")
    else:
        if notion.get("meeting_confirmed") is not True:
            errors.append("meeting record is not confirmed in Notion")
        if notion.get("meeting_confirmed_by_id") not in notion_authorized:
            errors.append("Notion meeting confirmer is not authorized")
        parse_time(notion.get("meeting_confirmed_at"), "notion.meeting_confirmed_at", errors)
        if not isinstance(notion.get("meeting_page_id"), str) or not notion.get(
            "meeting_page_id", ""
        ).strip():
            errors.append("Notion meeting_page_id is missing")
        tasks = notion.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            errors.append("Notion readback must contain at least one task")
        else:
            task_ids: set[str] = set()
            for index, task in enumerate(tasks):
                prefix = f"notion.tasks[{index}]"
                if not isinstance(task, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                task_id = task.get("task_id")
                if not isinstance(task_id, str) or not task_id.strip():
                    errors.append(f"{prefix}.task_id is missing")
                elif task_id in task_ids:
                    errors.append(f"{prefix}.task_id is duplicated")
                else:
                    task_ids.add(task_id)
                if task.get("confirmed") is not True:
                    errors.append(f"{prefix} is not confirmed")
                if task.get("confirmed_by_id") not in notion_authorized:
                    errors.append(f"{prefix} confirmer is not authorized")
                parse_time(task.get("confirmed_at"), f"{prefix}.confirmed_at", errors)
                if task.get("dispatched") is not False:
                    errors.append(f"{prefix} was already dispatched")

    rag = receipt.get("rag")
    if require_rag_approval:
        if not isinstance(rag, dict) or rag.get("approved") is not True:
            errors.append("meeting-specific RAG approval is required")
        else:
            if rag.get("approved_by_id") not in notion_authorized:
                errors.append("RAG approver is not authorized")
            parse_time(rag.get("approved_at"), "rag.approved_at", errors)
            if not isinstance(rag.get("approved_scope"), str) or not rag.get(
                "approved_scope", ""
            ).strip():
                errors.append("rag.approved_scope must be explicit")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a provider-readback confirmation receipt.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--expected-meeting-id", required=True)
    parser.add_argument("--expected-request-id", required=True)
    parser.add_argument("--now", help="ISO-8601 time for deterministic testing")
    parser.add_argument("--require-rag-approval", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        receipt = load_json(args.path)
        config = load_json(args.config)
        now = None
        if args.now:
            now_errors: list[str] = []
            now = parse_time(args.now, "now", now_errors)
            if now_errors:
                raise ValueError("; ".join(now_errors))
        errors = validate(
            receipt,
            config,
            expected_meeting_id=args.expected_meeting_id,
            expected_request_id=args.expected_request_id,
            now=now,
            require_rag_approval=args.require_rag_approval,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        errors = [f"cannot validate confirmation receipt: {exc}"]

    result = {
        "status": "PASS" if not errors else "FAIL",
        "path": str(args.path),
        "errors": errors,
        "warning": "Receipt consistency is not provider authentication.",
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
    else:
        print("PASS: provider-readback receipt is internally consistent and fresh")
        print("WARNING: this validator does not authenticate provider data")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
