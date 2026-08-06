from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "plugins" / "anchises-analysis" / "skills" / "anchises-analysis"
POLICY_PATH = SKILL_ROOT / "references" / "plugin-policy.json"
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate_plugin_policy.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = _load_module("anchises_plugin_policy_validator", VALIDATOR_PATH)


class PluginPolicyTest(unittest.TestCase):
    def test_released_policy_is_valid_and_disabled(self) -> None:
        policy = validator.load_policy(POLICY_PATH)
        self.assertEqual(policy["schema_version"], 1)
        self.assertEqual(policy["market_data"]["restrictions"], "disabled")

    def test_both_maintainer_values_are_valid(self) -> None:
        for value in ("enabled", "disabled"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "policy.json"
                path.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "market_data": {"restrictions": value},
                        }
                    ),
                    encoding="utf-8",
                )
                self.assertEqual(
                    validator.load_policy(path)["market_data"]["restrictions"],
                    value,
                )

    def test_invalid_or_extended_policy_shapes_are_rejected(self) -> None:
        cases = (
            [],
            {},
            {"schema_version": 2, "market_data": {"restrictions": "disabled"}},
            {"schema_version": 1, "market_data": {}},
            {"schema_version": 1, "market_data": {"restrictions": "unrestricted"}},
            {
                "schema_version": 1,
                "market_data": {"restrictions": "disabled", "user_override": True},
            },
            {
                "schema_version": 1,
                "market_data": {"restrictions": "disabled"},
                "user_configurable": True,
            },
        )
        for payload in cases:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "policy.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(ValueError):
                    validator.load_policy(path)

    def test_invalid_json_and_missing_file_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            invalid = Path(tmp) / "invalid.json"
            invalid.write_text("{", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                validator.load_policy(invalid)
            with self.assertRaises(FileNotFoundError):
                validator.load_policy(Path(tmp) / "missing.json")

    def test_cli_reports_only_the_effective_maintainer_value(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.strip(),
            "plugin policy valid: market_data.restrictions=disabled",
        )
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
