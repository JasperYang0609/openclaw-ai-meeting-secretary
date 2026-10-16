#!/usr/bin/env python3
"""Build a deterministic .skill archive from the public Skill folder."""

from __future__ import annotations

import argparse
import hashlib
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "ai-meeting-secretary"
DEFAULT_OUTPUT = ROOT / "dist" / "openclaw-ai-meeting-secretary.skill"
FIXED_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
PACKAGE_FILES = (
    "ai-meeting-secretary/SKILL.md",
    "ai-meeting-secretary/assets/confirmation-receipt.example.json",
    "ai-meeting-secretary/assets/meeting-record-template.md",
    "ai-meeting-secretary/assets/notion-meeting-template.md",
    "ai-meeting-secretary/assets/onboarding-config.example.json",
    "ai-meeting-secretary/references/architecture.md",
    "ai-meeting-secretary/references/meeting-rag-contract.md",
    "ai-meeting-secretary/references/notion-contract.md",
    "ai-meeting-secretary/scripts/validate_confirmation_receipt.py",
    "ai-meeting-secretary/scripts/validate_local_transcript.py",
    "ai-meeting-secretary/scripts/validate_meeting_record.py",
    "ai-meeting-secretary/scripts/validate_onboarding_config.py",
)


def build(output: Path) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    files = [ROOT / relative for relative in PACKAGE_FILES]
    missing = [str(path.relative_to(ROOT)) for path in files if not path.is_file()]
    if missing:
        raise SystemExit("package manifest files missing: " + ", ".join(missing))
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(relative, date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return hashlib.sha256(output.read_bytes()).hexdigest()


def check() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        first = Path(tmp) / "first.skill"
        second = Path(tmp) / "second.skill"
        first_hash = build(first)
        second_hash = build(second)
        if first_hash != second_hash or first.read_bytes() != second.read_bytes():
            raise SystemExit("archive build is not deterministic")
        with zipfile.ZipFile(first) as archive:
            names = set(archive.namelist())
        expected = set(PACKAGE_FILES)
        if names != expected:
            raise SystemExit(
                "archive manifest mismatch: missing="
                + repr(sorted(expected - names))
                + " extra="
                + repr(sorted(names - expected))
            )
        print(f"PASS: deterministic archive {first_hash}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check()
        return
    digest = build(args.output)
    print(f"WROTE {args.output}")
    print(f"SHA256 {digest}")


if __name__ == "__main__":
    main()
