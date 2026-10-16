#!/usr/bin/env python3
"""Validate the required local cleaned transcript before cloud mirroring."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


MIN_CONTENT_CHARS = 120
PLACEHOLDER_PATTERNS = (
    re.compile(r"＿＿+"),
    re.compile(r"\b(?:TODO|TBD)\b", re.IGNORECASE),
    re.compile(r"REPLACE_WITH_[A-Z0-9_]+"),
)


def validate(
    path: Path,
    expected_first_marker: str | None = None,
    expected_last_marker: str | None = None,
) -> list[str]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"cannot read UTF-8 transcript: {exc}"]

    if path.suffix.lower() != ".md":
        errors.append("transcript must use .md extension")
    if path.name not in {"transcript-clean.md"} and not re.fullmatch(
        r"transcript-clean\.part-\d{3}\.md", path.name
    ):
        errors.append(
            "filename must be transcript-clean.md or transcript-clean.part-NNN.md"
        )
    if len(re.sub(r"\s+", "", text)) < MIN_CONTENT_CHARS:
        errors.append("transcript is empty or too short to prove a complete local copy")
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(text):
            errors.append(f"placeholder content detected: {pattern.pattern}")
    if expected_first_marker and expected_first_marker not in text:
        errors.append("expected first marker was not found")
    if expected_last_marker and expected_last_marker not in text:
        errors.append("expected last marker was not found")
    if "�" in text:
        errors.append("replacement characters suggest invalid or damaged text")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a local cleaned meeting transcript."
    )
    parser.add_argument("path", type=Path)
    parser.add_argument("--expected-first-marker")
    parser.add_argument("--expected-last-marker")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    errors = validate(
        args.path,
        expected_first_marker=args.expected_first_marker,
        expected_last_marker=args.expected_last_marker,
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
        print("PASS: local cleaned transcript is readable and meets the configured checks")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

