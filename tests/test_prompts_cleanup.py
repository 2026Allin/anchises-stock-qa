from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from config import load_config
from output_cleanup import cleanup_outputs
from prompts import get_prompt_bundle


class PromptAndCleanupTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_config = os.environ.get("ANCHISES_STOCK_QA_CONFIG")

    def tearDown(self) -> None:
        if self._old_config is None:
            os.environ.pop("ANCHISES_STOCK_QA_CONFIG", None)
        else:
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = self._old_config

    def test_prompt_override_falls_back_per_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            override_dir = root / "prompts"
            override_dir.mkdir()
            (override_dir / "query-planning.md").write_text(
                "custom query planning",
                encoding="utf-8",
            )
            config_path = root / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[database]",
                        'url = "mysql+pymysql://reader:secret@localhost/Stocks_Tracker"',
                        'access_mode = "readonly"',
                        "[prompts]",
                        f'override_dir = "{override_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = str(config_path)

            bundle = get_prompt_bundle(load_config(require_database_url=False))

        by_name = {item["name"]: item for item in bundle["prompts"]}
        self.assertEqual(by_name["query-planning.md"]["source"], "override")
        self.assertEqual(
            by_name["query-planning.md"]["content"],
            "custom query planning",
        )
        self.assertEqual(by_name["sql-generation.md"]["source"], "built-in")

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
