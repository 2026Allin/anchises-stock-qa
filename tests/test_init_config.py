from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "stock-data-desk"
SCRIPT = PLUGIN_ROOT / "scripts" / "init_config.sh"
API_TOKEN = 'tk_test_p"a\\ss'
DEFAULT_API_URL = "https://anchisesdata.com/anchises-stock-qa"


class InitConfigTest(unittest.TestCase):
    def test_print_config_escapes_token_and_sets_defaults(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--api-token", API_TOKEN, "--print"],
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn('[backend]', result.stdout)
        self.assertIn('mode = "remote_api"', result.stdout)
        self.assertIn(f'api_base_url = "{DEFAULT_API_URL}"', result.stdout)
        self.assertIn('url = ""', result.stdout)
        self.assertIn('access_mode = "readonly"', result.stdout)
        self.assertIn("cleanup_enabled = true", result.stdout)
        self.assertIn("cleanup_interval_days = 7", result.stdout)
        self.assertIn("retention_days = 30", result.stdout)
        self.assertNotIn("[prompts]", result.stdout)
        self.assertIn('p\\"a\\\\ss', result.stdout)

    def test_rerun_updates_token_without_overwriting_other_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            custom_api_url = "https://custom.example.com/anchises-stock-qa"
            subprocess.run(
                [
                    "bash",
                    str(SCRIPT),
                    "--config",
                    str(config),
                    "--remote-api-url",
                    custom_api_url,
                    "--api-token",
                    "old-token",
                    "--outputs-dir",
                    "~/custom-stock-outputs",
                    "--cleanup-enabled",
                    "false",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            second = subprocess.run(
                ["bash", str(SCRIPT), "--config", str(config), "--api-token", API_TOKEN],
                check=True,
                text=True,
                capture_output=True,
            )

            text = config.read_text(encoding="utf-8")
            self.assertIn('mode = "remote_api"', text)
            self.assertIn(f'api_base_url = "{custom_api_url}"', text)
            self.assertIn('api_token = "tk_test_p\\"a\\\\ss"', text)
            self.assertIn('dir = "~/custom-stock-outputs"', text)
            self.assertIn("cleanup_enabled = false", text)
            self.assertNotIn("old-token", text)
            self.assertIn("Updated API token", second.stdout)

    def test_remote_api_url_can_be_overridden(self) -> None:
        result = subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--remote-api-url",
                "https://api.example.com/anchises-stock-qa",
                "--api-token",
                "secret-token",
                "--print",
            ],
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn('mode = "remote_api"', result.stdout)
        self.assertIn(
            'api_base_url = "https://api.example.com/anchises-stock-qa"',
            result.stdout,
        )
        self.assertIn('api_token = "secret-token"', result.stdout)
        self.assertIn('url = ""', result.stdout)

    def test_rerun_can_update_remote_api_url_when_provided(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            subprocess.run(
                [
                    "bash",
                    str(SCRIPT),
                    "--config",
                    str(config),
                    "--remote-api-url",
                    "https://old.example.com/anchises-stock-qa",
                    "--api-token",
                    "old-token",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "bash",
                    str(SCRIPT),
                    "--config",
                    str(config),
                    "--remote-api-url",
                    "https://new.example.com/anchises-stock-qa",
                    "--api-token",
                    "new-token",
                ],
                check=True,
                text=True,
                capture_output=True,
            )

            text = config.read_text(encoding="utf-8")
            self.assertIn(
                'api_base_url = "https://new.example.com/anchises-stock-qa"',
                text,
            )
            self.assertIn('api_token = "new-token"', text)
            self.assertNotIn("old-token", text)

    def test_rerun_migrates_existing_config_to_remote_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            config.write_text(
                "\n".join(
                    [
                        "[database]",
                        'url = "mysql+pymysql://reader:secret@localhost/Stocks_Tracker"',
                        'access_mode = "readonly"',
                        "[outputs]",
                        'dir = "~/custom-stock-outputs"',
                    ]
                ),
                encoding="utf-8",
            )

            subprocess.run(
                ["bash", str(SCRIPT), "--config", str(config), "--api-token", "new-token"],
                check=True,
                text=True,
                capture_output=True,
            )

            text = config.read_text(encoding="utf-8")
            self.assertIn("[backend]", text)
            self.assertIn('mode = "remote_api"', text)
            self.assertIn(f'api_base_url = "{DEFAULT_API_URL}"', text)
            self.assertIn('api_token = "new-token"', text)
            self.assertIn('url = ""', text)
            self.assertIn('dir = "~/custom-stock-outputs"', text)
            self.assertNotIn("mysql+pymysql", text)

    def test_requires_token_for_noninteractive_use(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--print"],
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No API token provided", result.stderr)

    def test_local_database_options_are_not_exposed(self) -> None:
        result = subprocess.run(
            [
                "bash",
                str(SCRIPT),
                "--db-url",
                "mysql+pymysql://reader:secret@localhost/Stocks_Tracker",
                "--print",
            ],
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown option: --db-url", result.stderr)

    def test_prepare_runtime_option_is_documented(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--help"],
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn("--prepare-runtime", result.stdout)
        self.assertIn("plugin Python runtime", result.stdout)


if __name__ == "__main__":
    unittest.main()
