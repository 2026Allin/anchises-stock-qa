from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Sequence


sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "anchises-analysis"
UPDATER_PATH = (
    PLUGIN_ROOT
    / "skills"
    / "anchises-analysis"
    / "scripts"
    / "update_installed_plugin.py"
)
SYNC_PATH = PLUGIN_ROOT / "scripts" / "sync_client_release.py"
RELEASE_PATH = (
    PLUGIN_ROOT
    / "skills"
    / "anchises-analysis"
    / "references"
    / "client-release.json"
)


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


updater = _load_module("anchises_plugin_updater", UPDATER_PATH)
release_sync = _load_module("anchises_release_sync", SYNC_PATH)


PLUGIN_ID = "anchises-analysis@Anchises-Analysis"
MARKETPLACE = "Anchises-Analysis"
REPOSITORY = "https://github.com/2026Allin/anchises-stock-qa.git"
GIT_REF = "qa-v2-auth"
INITIAL = "0.6.0-dev.5+codex.20260805102442"
TARGET_VERSION = "0.6.0-dev.6"
TARGET_RELEASE_ID = "codex.20260806120000"
TARGET = f"{TARGET_VERSION}+{TARGET_RELEASE_ID}"

LIST = ("codex", "plugin", "list", "--json")
MARKETPLACE_LIST = ("codex", "plugin", "marketplace", "list", "--json")
UPGRADE = (
    "codex",
    "plugin",
    "marketplace",
    "upgrade",
    MARKETPLACE,
    "--json",
)
INSTALL = ("codex", "plugin", "add", PLUGIN_ID, "--json")


def _plugin_list(version: str, *, enabled: bool = True) -> str:
    return json.dumps(
        {
            "installed": [
                {
                    "pluginId": PLUGIN_ID,
                    "version": version,
                    "installed": True,
                    "enabled": enabled,
                }
            ],
            "available": [],
        }
    )


def _marketplace_list(
    *,
    source_type: str = "git",
    source: str = REPOSITORY,
    git_ref: str = GIT_REF,
) -> str:
    return json.dumps(
        {
            "marketplaces": [
                {
                    "name": MARKETPLACE,
                    "marketplaceSource": {
                        "sourceType": source_type,
                        "source": source,
                        "refName": git_ref,
                    },
                }
            ]
        }
    )


class FakeRunner:
    def __init__(self, results: Sequence[Any]) -> None:
        self.results = list(results)
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, command: Sequence[str]) -> Any:
        self.commands.append(tuple(command))
        if not self.results:
            raise AssertionError("updater executed an unexpected extra command")
        return self.results.pop(0)


def _ok(stdout: str = "{}") -> Any:
    return updater.CommandResult(0, stdout, "")


def _fail(message: str = "denied") -> Any:
    return updater.CommandResult(1, "", message)


class PluginUpdateTest(unittest.TestCase):
    def _run(self, runner: FakeRunner) -> dict[str, Any]:
        return updater.run_update(
            TARGET_VERSION,
            TARGET_RELEASE_ID,
            runner=runner,
            metadata_path=RELEASE_PATH,
        )

    def test_success_executes_the_only_five_commands_once(self) -> None:
        runner = FakeRunner(
            [
                _ok(_plugin_list(INITIAL)),
                _ok(_marketplace_list()),
                _ok(),
                _ok(),
                _ok(_plugin_list(TARGET)),
            ]
        )
        result = self._run(runner)
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["installed_release"], TARGET)
        self.assertEqual(
            runner.commands,
            [LIST, MARKETPLACE_LIST, UPGRADE, INSTALL, LIST],
        )
        self.assertEqual(runner.results, [])

    def test_already_current_stops_after_complete_preflight(self) -> None:
        runner = FakeRunner(
            [_ok(_plugin_list(TARGET)), _ok(_marketplace_list())]
        )
        result = self._run(runner)
        self.assertEqual(result["status"], "already_current")
        self.assertEqual(runner.commands, [LIST, MARKETPLACE_LIST])

    def test_local_wrong_and_incomplete_sources_are_unsupported(self) -> None:
        sources = (
            _marketplace_list(source_type="local", source="/tmp/dev"),
            _marketplace_list(source="https://github.com/example/wrong.git"),
            _marketplace_list(git_ref="main"),
            json.dumps({"marketplaces": [{"name": MARKETPLACE}]}),
        )
        for payload in sources:
            with self.subTest(payload=payload):
                runner = FakeRunner([_ok(_plugin_list(INITIAL)), _ok(payload)])
                result = self._run(runner)
                self.assertEqual(result["status"], "unsupported_source")
                self.assertEqual(result["step"], "source_validation")
                self.assertEqual(runner.commands, [LIST, MARKETPLACE_LIST])

    def test_each_failure_stops_without_retry_or_fallback(self) -> None:
        cases = (
            ([_fail()], "preflight_failed", [LIST]),
            (
                [_ok(_plugin_list(INITIAL)), _fail()],
                "preflight_failed",
                [LIST, MARKETPLACE_LIST],
            ),
            (
                [_ok(_plugin_list(INITIAL)), _ok(_marketplace_list()), _fail()],
                "upgrade_failed",
                [LIST, MARKETPLACE_LIST, UPGRADE],
            ),
            (
                [
                    _ok(_plugin_list(INITIAL)),
                    _ok(_marketplace_list()),
                    _ok(),
                    _fail(),
                ],
                "install_failed",
                [LIST, MARKETPLACE_LIST, UPGRADE, INSTALL],
            ),
            (
                [
                    _ok(_plugin_list(INITIAL)),
                    _ok(_marketplace_list()),
                    _ok(),
                    _ok(),
                    _fail(),
                ],
                "verification_failed",
                [LIST, MARKETPLACE_LIST, UPGRADE, INSTALL, LIST],
            ),
        )
        for results, status, expected_commands in cases:
            with self.subTest(status=status):
                runner = FakeRunner(results)
                result = self._run(runner)
                self.assertEqual(result["status"], status)
                self.assertEqual(runner.commands, expected_commands)

    def test_verification_requires_the_target_or_a_newer_release(self) -> None:
        runner = FakeRunner(
            [
                _ok(_plugin_list(INITIAL)),
                _ok(_marketplace_list()),
                _ok(),
                _ok(),
                _ok(_plugin_list(INITIAL)),
            ]
        )
        result = self._run(runner)
        self.assertEqual(result["status"], "verification_failed")

    def test_release_comparison_handles_prerelease_and_cachebuster(self) -> None:
        compare = updater.compare_releases
        self.assertLess(compare(INITIAL, TARGET), 0)
        self.assertGreater(compare(TARGET, INITIAL), 0)
        self.assertEqual(compare(TARGET, TARGET), 0)
        self.assertLess(
            compare(
                "0.6.0-dev.6+codex.20260806115959",
                "0.6.0-dev.6+codex.20260806120000",
            ),
            0,
        )
        with self.assertRaises(ValueError):
            compare("0.6.0-dev.6", TARGET)

    def test_release_metadata_matches_manifest_and_sync_helper(self) -> None:
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["version"],
            f"{release['version']}+{release['release_id']}",
        )
        self.assertFalse(release_sync.sync_release(check=True))

        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "plugin.json"
            release_path = Path(tmp) / "client-release.json"
            manifest_path.write_text(
                json.dumps({"version": TARGET}), encoding="utf-8"
            )
            stale = dict(release)
            stale["version"] = "0.6.0-dev.1"
            release_path.write_text(json.dumps(stale), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "out of sync"):
                release_sync.sync_release(
                    check=True,
                    manifest_path=manifest_path,
                    release_path=release_path,
                )
            self.assertTrue(
                release_sync.sync_release(
                    check=False,
                    manifest_path=manifest_path,
                    release_path=release_path,
                )
            )
            synced = json.loads(release_path.read_text(encoding="utf-8"))
            self.assertEqual(synced["version"], TARGET_VERSION)
            self.assertEqual(synced["release_id"], TARGET_RELEASE_ID)


if __name__ == "__main__":
    unittest.main()
