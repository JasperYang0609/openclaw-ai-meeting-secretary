#!/usr/bin/env python3
"""Fail when public files contain likely credentials or private local identities."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return sorted(ROOT / raw.decode("utf-8") for raw in result.stdout.split(b"\0") if raw)


def main() -> None:
    findings: list[str] = []
    for path in public_files():
        raw = path.read_bytes()
        if b"\0" in raw:
            findings.append(f"{path.relative_to(ROOT)}: unexpected binary file")
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeError:
            findings.append(f"{path.relative_to(ROOT)}: non-UTF-8 file")
            continue
        for label, pattern in PATTERNS:
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: {label}")
    if findings:
        raise SystemExit("public-release scan failed:\n- " + "\n- ".join(findings))
    print(f"PASS: scanned {len(public_files())} public text files")


if __name__ == "__main__":
    main()
