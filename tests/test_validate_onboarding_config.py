import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "ai-meeting-secretary"
    / "scripts"
    / "validate_onboarding_config.py"
)
SPEC = importlib.util.spec_from_file_location("validate_onboarding_config", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_config(rag_enabled=True):
    return {
        "schema": "ai_meeting_secretary.onboarding.v1",
        "organization": {
            "name": "Example Organization",
            "departments": ["Operations", "Finance"],
        },
        "notion": {
            "transcripts_database_id": "db-transcripts",
            "meeting_records_database_id": "db-meetings",
            "task_master_database_id": "db-tasks",
            "department_database_ids": {
                "Operations": "db-operations",
                "Finance": "db-finance",
            },
            "meeting_template_page_id": "page-template",
            "ai_section_marker": "PIN: AI-WRITABLE SECTION",
        },
        "discord": {
            "notification_channel_id": "1234567890" + "1234567",
            "confirmation_phrase": "confirmed",
            "authorized_confirmer_ids": ["1234567890" + "1234567"],
            "confirmation_max_age_minutes": 1440,
        },
        "notion_confirmation": {
            "authorized_confirmer_ids": ["notion-user-example-001"]
        },
        "task_dispatch": {"mode": "manual"},
        "local_records": {"canonical_root": "/srv/example/meeting-notes"},
        "rag": {
            "enabled": rag_enabled,
            "provider": "google-gemini",
            "model": "gemini-embedding-001",
            "plugin_project_root": "/srv/example/rag",
            "canonical_root": "/srv/example/meetings",
            "source_id": "meeting-records",
            "index_project": "ExampleMeetings",
            "customer_id": "example",
            "access_mode": "isolated-route:example-meetings",
            "include_clean_transcript": False,
            "approval_by": "Example Approver",
            "approval_at": "2026-10-01",
        },
    }


class OnboardingConfigTests(unittest.TestCase):
    def test_valid_config_passes(self):
        self.assertEqual(MODULE.validate(valid_config()), [])

    def test_rag_disabled_does_not_require_live_approval(self):
        config = valid_config(rag_enabled=False)
        config["rag"] = {"enabled": False}
        self.assertEqual(MODULE.validate(config), [])

    def test_department_target_mismatch_fails(self):
        config = valid_config()
        del config["notion"]["department_database_ids"]["Finance"]
        errors = MODULE.validate(config)
        self.assertTrue(any("exactly match" in error for error in errors))

    def test_wrong_embedding_provider_fails(self):
        config = valid_config()
        config["rag"]["provider"] = "another-provider"
        errors = MODULE.validate(config)
        self.assertTrue(any("provider" in error for error in errors))

    def test_wrong_embedding_model_fails(self):
        config = valid_config()
        config["rag"]["model"] = "another-model"
        errors = MODULE.validate(config)
        self.assertTrue(any("model" in error for error in errors))

    def test_bad_access_mode_fails(self):
        config = valid_config()
        config["rag"]["access_mode"] = "project-label"
        errors = MODULE.validate(config)
        self.assertTrue(any("access_mode" in error for error in errors))

    def test_placeholder_fails_in_live_mode(self):
        config = valid_config()
        config["organization"]["name"] = "REPLACE_WITH_ORGANIZATION_NAME"
        errors = MODULE.validate(config)
        self.assertTrue(any("placeholder" in error for error in errors))

    def test_placeholder_allowed_for_repository_example(self):
        config = valid_config()
        config["organization"]["name"] = "REPLACE_WITH_ORGANIZATION_NAME"
        self.assertEqual(MODULE.validate(config, allow_placeholders=True), [])

    def test_secret_like_value_fails(self):
        config = valid_config()
        config["organization"]["name"] = "sk-" + "exampleexampleexampleexample123"
        errors = MODULE.validate(config)
        self.assertTrue(any("credential" in error for error in errors))

    def test_string_rag_enabled_fails(self):
        config = valid_config()
        config["rag"]["enabled"] = "true"
        errors = MODULE.validate(config)
        self.assertTrue(any("rag.enabled" in error for error in errors))

    def test_empty_notion_target_fails(self):
        config = valid_config()
        config["notion"]["task_master_database_id"] = ""
        errors = MODULE.validate(config)
        self.assertTrue(any("task_master_database_id" in error for error in errors))

    def test_empty_marker_and_phrase_fail(self):
        config = valid_config()
        config["notion"]["ai_section_marker"] = ""
        config["discord"]["confirmation_phrase"] = ""
        errors = MODULE.validate(config)
        self.assertTrue(any("ai_section_marker" in error for error in errors))
        self.assertTrue(any("confirmation_phrase" in error for error in errors))

    def test_relative_local_path_fails(self):
        config = valid_config()
        config["local_records"]["canonical_root"] = "records/meetings"
        errors = MODULE.validate(config)
        self.assertTrue(any("absolute path" in error for error in errors))

    def test_empty_isolated_route_fails(self):
        config = valid_config()
        config["rag"]["access_mode"] = "isolated-route:"
        errors = MODULE.validate(config)
        self.assertTrue(any("access_mode" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
