#!/usr/bin/env python3
"""Fail when public files contain likely credentials or private local identities."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "dist", "__pycache__", ".pytest_cache"}
SKIP_FILES = {Path(__file__).resolve()}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".txt"}

PATTERNS = (
    ("private home path", re.compile(r"/(?:Users|home)/[^/\s]+/")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    (
        "JWT",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
        ),
    ),
    ("Discord numeric ID", re.compile(r"\b\d{17,20}\b")),
)


def public_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.resolve() in SKIP_FILES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"LICENSE"}:
            files.append(path)
    return sorted(files)


def main() -> None:
    findings: list[str] = []
    for path in public_files():
        text = path.read_text(encoding="utf-8")
        for label, pattern in PATTERNS:
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: {label}")
    if findings:
        raise SystemExit("public-release scan failed:\n- " + "\n- ".join(findings))
    print(f"PASS: scanned {len(public_files())} public text files")


if __name__ == "__main__":
    main()

