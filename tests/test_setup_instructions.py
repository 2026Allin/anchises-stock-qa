from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ask_stock import get_setup_instructions


class SetupInstructionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_config = os.environ.get("ANCHISES_STOCK_QA_CONFIG")

    def tearDown(self) -> None:
        if self._old_config is None:
            os.environ.pop("ANCHISES_STOCK_QA_CONFIG", None)
        else:
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = self._old_config

    def test_missing_config_returns_first_time_setup_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = str(config_path)

            result = get_setup_instructions()

        command = result["commands"]["setup_or_reset_token"]
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "first_time_setup")
        self.assertFalse(result["config_exists"])
        self.assertFalse(result["backend"]["api_token_configured"])
        self.assertEqual(
            result["backend"]["api_base_url"],
            "https://anchisesdata.com/anchises-stock-qa",
        )
        self.assertIn("bash ", command)
        self.assertIn("scripts/init_config.sh", command)
        self.assertIn("--prepare-runtime", command)
        self.assertTrue(result["runtime"]["prepare_runtime_on_setup"])
        self.assertIn(".venv", result["runtime"]["venv_dir"])
        self.assertIn("Set up Anchises Stock QA", result["trigger_phrases"])

    def test_configured_remote_returns_reset_command_without_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[backend]",
                        'mode = "remote_api"',
                        'api_base_url = "https://api.example.com/anchises-stock-qa"',
                        'api_token = "secret-token"',
                        "[database]",
                        'url = ""',
                        'access_mode = "readonly"',
                    ]
                ),
                encoding="utf-8",
            )
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = str(config_path)

            result = get_setup_instructions()

        serialized = json.dumps(result)
        self.assertTrue(result["configured"])
        self.assertEqual(result["action"], "reset_token")
        self.assertTrue(result["backend"]["api_token_configured"])
        self.assertIn("setup_or_reset_token", result["commands"])
        self.assertIn("--prepare-runtime", result["commands"]["setup_or_reset_token"])
        self.assertIn(
            "setup_or_reset_token_without_runtime_prepare",
            result["commands"],
        )
        self.assertNotIn("secret-token", serialized)

    def test_old_local_config_gets_remote_setup_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[database]",
                        'url = "mysql+pymysql://reader:secret@localhost/Stocks_Tracker"',
                        'access_mode = "readonly"',
                    ]
                ),
                encoding="utf-8",
            )
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = str(config_path)

            result = get_setup_instructions()

        self.assertFalse(result["configured"])
        self.assertEqual(result["backend"]["mode"], "remote_api")
        self.assertIn("setup_or_reset_token", result["commands"])
        self.assertNotIn("mysql+pymysql", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
