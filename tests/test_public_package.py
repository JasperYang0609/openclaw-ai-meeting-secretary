import json
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).parents[1]
SKILL = ROOT / "ai-meeting-secretary"


class PublicPackageTests(unittest.TestCase):
    def test_skill_frontmatter_is_minimal_and_quoted(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        frontmatter = text.split("---", 2)[1]
        self.assertIn("name: ai-meeting-secretary", frontmatter)
        self.assertRegex(frontmatter, r'description: "[^"]+"')

    def test_example_config_is_valid_json(self):
        path = SKILL / "assets" / "onboarding-config.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "ai_meeting_secretary.onboarding.v1")

    def test_example_config_passes_structure_validation(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts" / "validate_onboarding_config.py"),
                str(SKILL / "assets" / "onboarding-config.example.json"),
                "--allow-placeholders",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_archive_contains_only_skill_tree(self):
        output = ROOT / "dist" / "test.skill"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_skill_archive.py"),
                "--output",
                str(output),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.addCleanup(lambda: output.unlink(missing_ok=True))
        with zipfile.ZipFile(output) as archive:
            names = archive.namelist()
        self.assertTrue(names)
        self.assertTrue(all(name.startswith("ai-meeting-secretary/") for name in names))
        self.assertNotIn("ai-meeting-secretary/assets/onboarding.json", names)


if __name__ == "__main__":
    unittest.main()

