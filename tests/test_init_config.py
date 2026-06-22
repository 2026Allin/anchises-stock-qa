from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "init_config.sh"
DB_URL = 'mysql+pymysql://reader:p"a\\ss@localhost/Stocks_Tracker'


class InitConfigTest(unittest.TestCase):
    def test_print_config_escapes_url_and_sets_defaults(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--db-url", DB_URL, "--print"],
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn('access_mode = "readonly"', result.stdout)
        self.assertIn("cleanup_enabled = true", result.stdout)
        self.assertIn("cleanup_interval_days = 7", result.stdout)
        self.assertIn("retention_days = 30", result.stdout)
        self.assertIn('p\\"a\\\\ss', result.stdout)

    def test_writes_config_file_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            subprocess.run(
                ["bash", str(SCRIPT), "--config", str(config), "--db-url", DB_URL],
                check=True,
                text=True,
                capture_output=True,
            )
            second = subprocess.run(
                ["bash", str(SCRIPT), "--config", str(config), "--db-url", DB_URL],
                text=True,
                capture_output=True,
            )

            self.assertTrue(config.exists())
            self.assertIn('access_mode = "readonly"', config.read_text(encoding="utf-8"))
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("Config already exists", second.stderr)


if __name__ == "__main__":
    unittest.main()
