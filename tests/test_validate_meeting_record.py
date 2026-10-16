import datetime as dt
import importlib.util
import json
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


DISCORD_ID = "1234567890" + "1234567"
MESSAGE_ID = "2234567890" + "1234567"
REQUEST_MESSAGE_ID = "3234567890" + "1234567"
NOTION_ID = "notion-user-example-001"
NOW = dt.datetime(2026, 10, 1, 12, 30, tzinfo=dt.timezone.utc)


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
confirmed_by_id: {NOTION_ID}
confirmed_at: 2026-10-01T12:00:00Z
confirmation_receipt_id: receipt-example-001
rag_approval: {approval}
rag_approved_by_id: {NOTION_ID}
rag_approved_at: 2026-10-01T12:05:00Z
rag_approval_receipt_id: receipt-example-001
access_scope: isolated-route:example-meetings
index_project: ExampleMeetings
---

# 2026-10-01 | Project kickoff

{sections}## Source integrity

- The source is a human-confirmed meeting page. Coverage is complete and excludes uncorrected or non-meeting content.
"""


def valid_config():
    return {
        "discord": {
            "notification_channel_id": DISCORD_ID,
            "confirmation_phrase": "confirmed",
            "authorized_confirmer_ids": [DISCORD_ID],
            "confirmation_max_age_minutes": 60,
        },
        "notion_confirmation": {"authorized_confirmer_ids": [NOTION_ID]},
    }


def valid_receipt():
    return {
        "schema": "ai_meeting_secretary.confirmation_receipt.v1",
        "receipt_id": "receipt-example-001",
        "meeting_id": "example-2026-10-01-kickoff",
        "request_id": "request-example-001",
        "request_message_id": REQUEST_MESSAGE_ID,
        "issued_at": "2026-10-01T12:00:00Z",
        "discord": {
            "channel_id": DISCORD_ID,
            "author_id": DISCORD_ID,
            "message_id": MESSAGE_ID,
            "reply_to_message_id": REQUEST_MESSAGE_ID,
            "phrase": "confirmed",
        },
        "notion": {
            "meeting_page_id": "notion-page-example-001",
            "meeting_confirmed": True,
            "meeting_confirmed_by_id": NOTION_ID,
            "meeting_confirmed_at": "2026-10-01T12:00:00Z",
            "tasks": [
                {
                    "task_id": "notion-task-example-001",
                    "confirmed": True,
                    "confirmed_by_id": NOTION_ID,
                    "confirmed_at": "2026-10-01T12:00:00Z",
                    "dispatched": False,
                }
            ],
        },
        "rag": {
            "approved": True,
            "approved_by_id": NOTION_ID,
            "approved_at": "2026-10-01T12:05:00Z",
            "approved_scope": "meeting summary only",
        },
    }


class MeetingRecordValidationTests(unittest.TestCase):
    def validate_record(
        self,
        text,
        expected_customer="example",
        expected_project="ExampleMeetings",
        receipt=None,
    ):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        record_path = root / "record.md"
        config_path = root / "onboarding.json"
        receipt_path = root / "receipt.json"
        record_path.write_text(text, encoding="utf-8")
        config_path.write_text(json.dumps(valid_config()), encoding="utf-8")
        receipt_path.write_text(json.dumps(receipt or valid_receipt()), encoding="utf-8")
        return MODULE.validate(
            record_path,
            expected_customer_id=expected_customer,
            expected_index_project=expected_project,
            confirmation_receipt_path=receipt_path,
            onboarding_config_path=config_path,
            expected_request_id="request-example-001",
            now=NOW,
        )

    def test_valid_summary_passes(self):
        self.assertEqual(self.validate_record(valid_record()), [])

    def test_valid_clean_transcript_passes(self):
        self.assertEqual(
            self.validate_record(valid_record("meeting_transcript_clean")), []
        )

    def test_unconfirmed_record_fails(self):
        errors = self.validate_record(valid_record(status="draft"))
        self.assertTrue(any("record_status" in error for error in errors))

    def test_unapproved_record_fails(self):
        errors = self.validate_record(valid_record(approval="pending"))
        self.assertTrue(any("rag_approval" in error for error in errors))

    def test_customer_mismatch_fails_closed(self):
        errors = self.validate_record(valid_record(), expected_customer="another-customer")
        self.assertTrue(any("customer_id" in error for error in errors))

    def test_missing_section_fails(self):
        record = valid_record().replace("## Decisions", "## Other content")
        errors = self.validate_record(record)
        self.assertTrue(any("Decisions" in error for error in errors))

    def test_private_chatter_section_fails(self):
        record = valid_record() + "\n## Private chatter\n\nExcluded material.\n"
        errors = self.validate_record(record)
        self.assertTrue(any("Private chatter" in error for error in errors))

    def test_invalid_access_scope_fails(self):
        record = valid_record().replace(
            "access_scope: isolated-route:example-meetings",
            "access_scope: isolated-route:",
        )
        errors = self.validate_record(record)
        self.assertTrue(any("access_scope" in error for error in errors))

    def test_missing_receipt_fails(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "record.md"
        path.write_text(valid_record(), encoding="utf-8")
        errors = MODULE.validate(
            path,
            expected_customer_id="example",
            expected_index_project="ExampleMeetings",
            confirmation_receipt_path=None,
            onboarding_config_path=None,
            expected_request_id=None,
            now=NOW,
        )
        self.assertTrue(any("confirmation receipt" in error for error in errors))

    def test_unapproved_receipt_fails(self):
        receipt = valid_receipt()
        receipt["rag"]["approved"] = False
        errors = self.validate_record(valid_record(), receipt=receipt)
        self.assertTrue(any("RAG approval" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
