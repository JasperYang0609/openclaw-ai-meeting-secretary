import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "ai-meeting-secretary"
    / "scripts"
    / "validate_meeting_record.py"
)
SPEC = importlib.util.spec_from_file_location("validate_meeting_record", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_record(document_type="meeting_summary", status="confirmed", approval="approved"):
    if document_type == "meeting_transcript_clean":
        sections = """## Cleaned transcript

The confirmed transcript preserves the order, decision context, objections, and relevant statements. The organization approved this cleaned source for its isolated Gemini retrieval route. Raw audio, uncorrected output, private chatter, and credentials remain outside the source root.

"""
    else:
        sections = """## Meeting summary

The meeting confirmed the project direction, constraints, and acceptance criteria.

## Decisions

- Use the approved workflow and preserve source traceability.

## Action items

- [ ] Prepare the verified meeting record | Operations | 2026-10-08 | agenda topic two

"""
    return f"""---
schema: ai_meeting_secretary.meeting_record.v1
document_type: {document_type}
meeting_id: example-2026-10-01-kickoff
customer_id: example
company: Example Organization
meeting_date: 2026-10-01
title: Project kickoff
record_status: {status}
rag_approval: {approval}
access_scope: isolated-route:example-meetings
index_project: ExampleMeetings
---

# 2026-10-01 | Project kickoff

{sections}## Source integrity

- The source is a human-confirmed meeting page. Coverage is complete and excludes uncorrected or non-meeting content.
"""


class MeetingRecordValidationTests(unittest.TestCase):
    def write(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "record.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_valid_summary_passes(self):
        errors = MODULE.validate(
            self.write(valid_record()),
            expected_customer_id="example",
            expected_index_project="ExampleMeetings",
        )
        self.assertEqual(errors, [])

    def test_valid_clean_transcript_passes(self):
        self.assertEqual(
            MODULE.validate(self.write(valid_record("meeting_transcript_clean"))), []
        )

    def test_unconfirmed_record_fails(self):
        errors = MODULE.validate(self.write(valid_record(status="draft")))
        self.assertTrue(any("record_status" in error for error in errors))

    def test_unapproved_record_fails(self):
        errors = MODULE.validate(self.write(valid_record(approval="pending")))
        self.assertTrue(any("rag_approval" in error for error in errors))

    def test_customer_mismatch_fails_closed(self):
        errors = MODULE.validate(
            self.write(valid_record()), expected_customer_id="another-customer"
        )
        self.assertTrue(any("customer_id" in error for error in errors))

    def test_missing_section_fails(self):
        record = valid_record().replace("## Decisions", "## Other content")
        errors = MODULE.validate(self.write(record))
        self.assertTrue(any("Decisions" in error for error in errors))

    def test_private_chatter_section_fails(self):
        record = valid_record() + "\n## Private chatter\n\nExcluded material.\n"
        errors = MODULE.validate(self.write(record))
        self.assertTrue(any("Private chatter" in error for error in errors))

    def test_invalid_access_scope_fails(self):
        record = valid_record().replace(
            "access_scope: isolated-route:example-meetings",
            "access_scope: department-label-only",
        )
        errors = MODULE.validate(self.write(record))
        self.assertTrue(any("access_scope" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

