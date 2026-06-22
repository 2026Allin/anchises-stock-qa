from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from config import ConfigError, config_as_dict, load_config, redact_url


class ConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_config = os.environ.get("ANCHISES_STOCK_QA_CONFIG")

    def tearDown(self) -> None:
        if self._old_config is None:
            os.environ.pop("ANCHISES_STOCK_QA_CONFIG", None)
        else:
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = self._old_config

    def test_missing_config_reports_helpful_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = str(Path(tmp) / "missing.toml")

            with self.assertRaises(ConfigError) as ctx:
                load_config(require_database_url=True)

        self.assertIn("config file not found", str(ctx.exception))
        self.assertIn("config.example.toml", str(ctx.exception))

    def test_config_loads_and_redacts_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[database]",
                        'url = "mysql+pymysql://reader:secret@db.example.com:3306/Stocks_Tracker?charset=utf8mb4"',
                        'access_mode = "readonly"',
                        "[outputs]",
                        'dir = "~/stock-qa-test-outputs"',
                        "cleanup_enabled = false",
                        "cleanup_interval_days = 3",
                        "retention_days = 9",
                        "[exchanges.aliases]",
                        '"London" = "lse"',
                        '"伦敦" = "lse"',
                    ]
                ),
                encoding="utf-8",
            )
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = str(config_path)

            config = load_config()
            data = config_as_dict(config)

        self.assertEqual(config.database.access_mode, "readonly")
        self.assertFalse(config.outputs.cleanup_enabled)
        self.assertEqual(config.outputs.cleanup_interval_days, 3)
        self.assertEqual(config.outputs.retention_days, 9)
        self.assertEqual(config.exchanges.aliases["London"], "lse")
        self.assertEqual(data["exchanges"]["aliases"]["伦敦"], "lse")
        self.assertIn("reader:***@db.example.com", data["database"]["url"])
        self.assertNotIn("secret", data["database"]["url"])

    def test_invalid_access_mode_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[database]",
                        'url = "mysql+pymysql://reader:secret@localhost/Stocks_Tracker"',
                        'access_mode = "write"',
                    ]
                ),
                encoding="utf-8",
            )
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = str(config_path)

            with self.assertRaises(ConfigError):
                load_config()

    def test_redact_url_masks_password(self) -> None:
        redacted = redact_url(
            "mysql+pymysql://reader:secret@127.0.0.1:3306/Stocks_Tracker"
        )

        self.assertEqual(
            redacted,
            "mysql+pymysql://reader:***@127.0.0.1:3306/Stocks_Tracker",
        )


if __name__ == "__main__":
    unittest.main()
