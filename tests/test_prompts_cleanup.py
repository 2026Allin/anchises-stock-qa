from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "anchises-stock-qa"
SCRIPTS = PLUGIN_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from config import load_config
from output_cleanup import cleanup_outputs
from prompts import (
    get_prompt_bundle,
    get_prompt_catalog,
    initialize_custom_prompts,
    list_custom_prompts,
    preview_custom_prompt_update,
    read_custom_prompt,
    reset_custom_prompt,
    write_custom_prompt,
)


class PromptAndCleanupTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_config = os.environ.get("ANCHISES_STOCK_QA_CONFIG")

    def tearDown(self) -> None:
        if self._old_config is None:
            os.environ.pop("ANCHISES_STOCK_QA_CONFIG", None)
        else:
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = self._old_config

    def test_custom_prompt_falls_back_per_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_prompt_dir = root / "prompts"
            user_prompt_dir.mkdir()
            (user_prompt_dir / "query-planning.md").write_text(
                "custom query planning",
                encoding="utf-8",
            )

            with patch("prompts.USER_PROMPT_DIR", user_prompt_dir):
                bundle = get_prompt_bundle()

        by_name = {item["name"]: item for item in bundle["prompts"]}
        self.assertEqual(by_name["query-planning.md"]["source"], "custom")
        self.assertEqual(
            by_name["query-planning.md"]["content"],
            "custom query planning",
        )
        self.assertEqual(by_name["sql-generation.md"]["source"], "built-in")

    def test_custom_prompt_tools_initialize_write_and_reset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_prompt_dir = root / "custom-prompts"

            with patch("prompts.USER_PROMPT_DIR", user_prompt_dir):
                status = list_custom_prompts()
                init_result = initialize_custom_prompts(
                    ["query-planning"],
                )
                write_result = write_custom_prompt(
                    "query-planning.md",
                    "# Custom Query Planning\n\nUse a shorter plan.",
                )
                bundle_after_write = get_prompt_bundle()
                reset_result = reset_custom_prompt("query-planning")
                bundle_after_reset = get_prompt_bundle()

        by_name_after_write = {
            item["name"]: item for item in bundle_after_write["prompts"]
        }
        by_name_after_reset = {
            item["name"]: item for item in bundle_after_reset["prompts"]
        }
        self.assertTrue(status["ok"])
        self.assertEqual(status["user_prompt_dir"], str(user_prompt_dir))
        self.assertEqual(init_result["prompts"][0]["status"], "created")
        self.assertEqual(write_result["status"], "updated")
        self.assertEqual(by_name_after_write["query-planning.md"]["source"], "custom")
        self.assertIn(
            "Use a shorter plan.",
            by_name_after_write["query-planning.md"]["content"],
        )
        self.assertEqual(reset_result["status"], "deleted")
        self.assertEqual(by_name_after_reset["query-planning.md"]["source"], "built-in")

    def test_custom_prompt_catalog_read_preview_and_hash_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_prompt_dir = root / "custom-prompts"
            revised = "# Final Answer Prompt\n\nUse concise English summaries."
            second_revision = "# Final Answer Prompt\n\nUse detailed English summaries."

            with patch("prompts.USER_PROMPT_DIR", user_prompt_dir):
                catalog = get_prompt_catalog(include_preview=True, preview_chars=80)
                final_item = next(
                    item
                    for item in catalog["prompts"]
                    if item["name"] == "final-answer.md"
                )
                read_result = read_custom_prompt("final-answer")
                preview = preview_custom_prompt_update("final-answer.md", revised)
                write_result = write_custom_prompt(
                    "final-answer.md",
                    revised,
                    expected_current_hash=preview["current_hash"],
                )
                after_write = read_custom_prompt("final-answer.md")

                with self.assertRaises(ValueError):
                    write_custom_prompt(
                        "final-answer.md",
                        second_revision,
                        expected_current_hash=preview["current_hash"],
                    )

        self.assertTrue(catalog["ok"])
        self.assertEqual(final_item["title"], "Final Answer")
        self.assertIn("visible markdown answer", final_item["purpose"])
        self.assertIn("built_in_path", final_item)
        self.assertIn("user_path", final_item)
        self.assertEqual(read_result["active_source"], "built-in")
        self.assertIn("active_content", read_result)
        self.assertEqual(preview["target_path"], str(user_prompt_dir / "final-answer.md"))
        self.assertTrue(preview["will_create_user_file"])
        self.assertIn("--- final-answer.md (built-in)", preview["diff"])
        self.assertIn("+++ final-answer.md (proposed custom)", preview["diff"])
        self.assertEqual(write_result["previous_hash"], preview["current_hash"])
        self.assertEqual(after_write["active_source"], "custom")
        self.assertEqual(after_write["active_content"], revised)

    def test_cleanup_dry_run_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.toml"
            outputs = root / "outputs"
            old_run = outputs / "20260601-1200-123456" / "old_run"
            new_run = outputs / "20260601-1200-123456" / "new_run"
            unsafe_dir = outputs / "manual" / "old_no_metadata"
            old_run.mkdir(parents=True)
            new_run.mkdir(parents=True)
            unsafe_dir.mkdir(parents=True)

            old_date = datetime.now(timezone.utc) - timedelta(days=40)
            new_date = datetime.now(timezone.utc)
            (old_run / "metadata.json").write_text(
                json.dumps({"created_at_utc": old_date.isoformat()}),
                encoding="utf-8",
            )
            (old_run / "result.csv").write_text("a\n1\n", encoding="utf-8")
            (new_run / "metadata.json").write_text(
                json.dumps({"created_at_utc": new_date.isoformat()}),
                encoding="utf-8",
            )
            (unsafe_dir / "result.csv").write_text("a\n1\n", encoding="utf-8")

            config_path.write_text(
                "\n".join(
                    [
                        "[database]",
                        'url = "mysql+pymysql://reader:secret@localhost/Stocks_Tracker"',
                        'access_mode = "readonly"',
                        "[outputs]",
                        f'dir = "{outputs}"',
                        "cleanup_enabled = true",
                        "cleanup_interval_days = 7",
                        "retention_days = 30",
                    ]
                ),
                encoding="utf-8",
            )
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = str(config_path)
            config = load_config()

            preview = cleanup_outputs(config.outputs, dry_run=True)
            applied = cleanup_outputs(config.outputs, dry_run=False)

            self.assertEqual(preview["candidate_run_dirs"], 1)
            self.assertTrue(
                any("old_run" in item["path"] for item in preview["candidates"])
            )
            self.assertEqual(applied["deleted_run_dirs"], 1)
            self.assertFalse(old_run.exists())
            self.assertTrue(new_run.exists())
            self.assertTrue(unsafe_dir.exists())


if __name__ == "__main__":
    unittest.main()
