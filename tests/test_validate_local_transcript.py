import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "ai-meeting-secretary"
    / "scripts"
    / "validate_local_transcript.py"
)
SPEC = importlib.util.spec_from_file_location("validate_local_transcript", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


VALID_TEXT = """# Cleaned transcript

[00:00] The facilitator opens the meeting and confirms the project goal.

[04:12] The team reviews the current workflow, known constraints, and the evidence required before changing the process.

[12:33] The group confirms the next action, owner, review gate, and expected completion criteria.
"""


class LocalTranscriptTests(unittest.TestCase):
    def write(self, text=VALID_TEXT, name="transcript-clean.md"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_valid_transcript_passes(self):
        self.assertEqual(MODULE.validate(self.write()), [])

    def test_markers_are_verified(self):
        self.assertEqual(
            MODULE.validate(
                self.write(),
                expected_first_marker="00:00",
                expected_last_marker="12:33",
            ),
            [],
        )

    def test_missing_last_marker_fails(self):
        errors = MODULE.validate(self.write(), expected_last_marker="20:00")
        self.assertTrue(any("last marker" in error for error in errors))

    def test_short_transcript_fails(self):
        errors = MODULE.validate(self.write("# Transcript\n\nshort"))
        self.assertTrue(any("too short" in error for error in errors))

    def test_wrong_filename_fails(self):
        errors = MODULE.validate(self.write(name="notes.md"))
        self.assertTrue(any("filename" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

