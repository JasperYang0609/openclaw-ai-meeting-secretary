import datetime as dt
import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "ai-meeting-secretary"
    / "scripts"
    / "validate_confirmation_receipt.py"
)
SPEC = importlib.util.spec_from_file_location("validate_confirmation_receipt", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


DISCORD_ID = "1234567890" + "1234567"
MESSAGE_ID = "2234567890" + "1234567"
REPLY_ID = "3234567890" + "1234567"
NOTION_ID = "notion-user-example-001"
NOW = dt.datetime(2026, 10, 1, 12, 30, tzinfo=dt.timezone.utc)


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
        "request_message_id": REPLY_ID,
        "issued_at": "2026-10-01T12:00:00Z",
        "discord": {
            "channel_id": DISCORD_ID,
            "author_id": DISCORD_ID,
            "message_id": MESSAGE_ID,
            "reply_to_message_id": REPLY_ID,
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


class ConfirmationReceiptTests(unittest.TestCase):
    def validate(self, receipt=None, config=None, require_rag=False):
        return MODULE.validate(
            receipt or valid_receipt(),
            config or valid_config(),
            expected_meeting_id="example-2026-10-01-kickoff",
            expected_request_id="request-example-001",
            now=NOW,
            require_rag_approval=require_rag,
        )

    def test_valid_receipt_passes(self):
        self.assertEqual(self.validate(require_rag=True), [])

    def test_wrong_discord_author_fails(self):
        receipt = valid_receipt()
        receipt["discord"]["author_id"] = "4234567890" + "1234567"
        self.assertTrue(any("not authorized" in error for error in self.validate(receipt)))

    def test_reply_to_wrong_message_fails(self):
        receipt = valid_receipt()
        receipt["discord"]["reply_to_message_id"] = MESSAGE_ID
        self.assertTrue(any("does not reference" in error for error in self.validate(receipt)))

    def test_expired_receipt_fails(self):
        receipt = valid_receipt()
        receipt["issued_at"] = "2026-10-01T10:00:00Z"
        self.assertTrue(any("expired" in error for error in self.validate(receipt)))

    def test_unconfirmed_task_fails(self):
        receipt = valid_receipt()
        receipt["notion"]["tasks"][0]["confirmed"] = False
        self.assertTrue(any("not confirmed" in error for error in self.validate(receipt)))

    def test_already_dispatched_task_fails(self):
        receipt = valid_receipt()
        receipt["notion"]["tasks"][0]["dispatched"] = True
        self.assertTrue(any("already dispatched" in error for error in self.validate(receipt)))

    def test_rag_requires_explicit_approval(self):
        receipt = valid_receipt()
        receipt["rag"]["approved"] = False
        self.assertTrue(
            any("RAG approval" in error for error in self.validate(receipt, require_rag=True))
        )


if __name__ == "__main__":
    unittest.main()
