from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Sequence


sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "anchises-analysis"
SCRIPT_ROOT = PLUGIN_ROOT / "skills" / "anchises-analysis" / "scripts"
CHECKER_PATH = SCRIPT_ROOT / "check_plugin_update.py"
UPDATER_PATH = SCRIPT_ROOT / "update_installed_plugin.py"
SYNC_PATH = PLUGIN_ROOT / "scripts" / "sync_plugin_release.py"
RELEASE_PATH = (
    PLUGIN_ROOT
    / "skills"
    / "anchises-analysis"
    / "references"
    / "plugin-release.json"
)
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


checker = _load_module("check_plugin_update", CHECKER_PATH)
updater = _load_module("anchises_plugin_updater", UPDATER_PATH)
release_sync = _load_module("anchises_release_sync", SYNC_PATH)


PLUGIN_ID = "anchises-analysis@Anchises-Analysis"
MARKETPLACE = "Anchises-Analysis"
REPOSITORY = "https://github.com/2026Allin/anchises-stock-qa.git"
GIT_REF = "main"
TAG_PREFIX = "anchises-analysis/codex/v"
CURRENT_VERSION = "0.6.0-dev.7"
CURRENT_RELEASE = "0.6.0-dev.7+codex.20260806120000"
TARGET_VERSION = "0.6.0-dev.8"
TARGET_RELEASE = "0.6.0-dev.8+codex.20260807120000"
MAIN_COMMIT = "1" * 40
OTHER_COMMIT = "2" * 40
TAG_OBJECT = "3" * 40

GIT_CHECK = (
    "git",
    "ls-remote",
    "--",
    REPOSITORY,
)
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


class FakeRunner:
    def __init__(self, results: Sequence[Any]) -> None:
        self.results = list(results)
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, command: Sequence[str]) -> Any:
        self.commands.append(tuple(command))
        if not self.results:
            raise AssertionError("an unexpected extra command was executed")
        return self.results.pop(0)


def _ok(stdout: str = "{}") -> Any:
    return updater.CommandResult(0, stdout, "")


def _fail(message: str = "denied") -> Any:
    return updater.CommandResult(1, "", message)


def _refs(
    *versions: str,
    main_commit: str = MAIN_COMMIT,
    tag_commit: str | None = None,
    annotated: bool = False,
    extra: Sequence[str] = (),
) -> str:
    lines = [f"{main_commit}\trefs/heads/main"]
    target_commit = tag_commit or main_commit
    for version in versions:
        ref = f"refs/tags/{TAG_PREFIX}{version}"
        if annotated:
            lines.extend((f"{TAG_OBJECT}\t{ref}", f"{target_commit}\t{ref}^{{}}"))
        else:
            lines.append(f"{target_commit}\t{ref}")
    lines.extend(extra)
    return "\n".join(lines) + "\n"


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


class PluginTagCheckTest(unittest.TestCase):
    def _check(self, output: str, *, now: float = 1000) -> dict[str, Any]:
        return checker.check_remote_refs(
            output,
            metadata_path=RELEASE_PATH,
            use_cache=False,
            now=now,
        )

    def test_network_contract_is_fixed_narrow_and_python_is_network_free(self) -> None:
        self.assertEqual(checker.release_check_command(RELEASE_PATH), GIT_CHECK)
        self.assertEqual(checker.release_check_prefix_rule(RELEASE_PATH), GIT_CHECK)
        self.assertNotIn("*", " ".join(GIT_CHECK))
        self.assertNotIn("subprocess", CHECKER_PATH.read_text(encoding="utf-8"))
        self.assertNotIn("ls-remote", UPDATER_PATH.read_text(encoding="utf-8"))
        self.assertIn("只读检查 Anchises Analysis", checker.RELEASE_CHECK_JUSTIFICATION)

    def test_no_newer_codex_tag_is_current(self) -> None:
        for output in (_refs(), _refs(CURRENT_VERSION, "0.5.9")):
            with self.subTest(output=output):
                result = self._check(output)
                self.assertEqual(result["status"], "current")

    def test_newer_lightweight_or_annotated_tag_on_main_is_available(self) -> None:
        for annotated in (False, True):
            with self.subTest(annotated=annotated):
                result = self._check(_refs(TARGET_VERSION, annotated=annotated))
                self.assertEqual(result["status"], "update_available")
                self.assertEqual(result["target_version"], TARGET_VERSION)
                self.assertEqual(result["target_tag"], f"{TAG_PREFIX}{TARGET_VERSION}")
                self.assertEqual(result["target_commit"], MAIN_COMMIT)

    def test_newer_tag_not_on_main_is_fail_closed(self) -> None:
        result = self._check(_refs(TARGET_VERSION, tag_commit=OTHER_COMMIT))
        self.assertEqual(result["status"], "release_inconsistent")

    def test_codex_ignores_claude_tags_and_uses_semver_order(self) -> None:
        claude = f"{MAIN_COMMIT}\trefs/tags/anchises-analysis/claude/v9.0.0"
        unrelated = (
            f"{OTHER_COMMIT}\tHEAD",
            f"{OTHER_COMMIT}\trefs/heads/qa-v2-auth",
            f"{OTHER_COMMIT}\trefs/tags/unrelated/v99.0.0",
        )
        result = self._check(
            _refs("0.6.0-dev.10", extra=(claude, *unrelated))
        )
        self.assertEqual(result["target_version"], "0.6.0-dev.10")
        self.assertGreater(checker.compare_versions("0.6.0-dev.10", "0.6.0-dev.9"), 0)
        self.assertGreater(checker.compare_versions("0.6.0", "0.6.0-dev.99"), 0)

    def test_empty_malformed_and_oversized_ref_inputs_are_unknown(self) -> None:
        empty = self._check("")
        self.assertEqual(empty["status"], "unknown")
        self.assertEqual(empty["reason"], "empty_remote_refs")
        malformed = self._check("not-a-ref\n")
        self.assertEqual(malformed["status"], "unknown")
        self.assertEqual(malformed["reason"], "invalid_remote_refs")
        oversized = self._check("x" * (checker.MAX_REMOTE_OUTPUT_BYTES + 1))
        self.assertEqual(oversized["reason"], "remote_refs_too_large")

    def test_success_cache_is_used_then_expires_and_remote_ingest_refreshes_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "tags.json"
            result = checker.check_remote_refs(
                _refs(TARGET_VERSION),
                metadata_path=RELEASE_PATH,
                cache_path=cache,
                now=1000,
            )
            self.assertEqual(result["cache"], "miss")

            result = checker.check_cached_result(
                metadata_path=RELEASE_PATH,
                cache_path=cache,
                now=1001,
            )
            self.assertEqual(result["cache"], "hit")

            result = checker.check_remote_refs(
                _refs(),
                metadata_path=RELEASE_PATH,
                cache_path=cache,
                now=1002,
            )
            self.assertEqual(result["status"], "current")

            stale = checker.check_cached_result(
                metadata_path=RELEASE_PATH,
                cache_path=cache,
                now=1002 + checker.SUCCESS_CACHE_SECONDS,
            )
            self.assertEqual(stale["status"], checker.CHECK_REQUIRED)
            self.assertEqual(stale["reason"], "cache_miss")

    def test_failed_lookup_cache_expires_after_ten_minutes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "tags.json"
            failed = checker.check_remote_refs(
                "",
                metadata_path=RELEASE_PATH,
                cache_path=cache,
                now=1000,
            )
            self.assertEqual(failed["status"], "unknown")
            cached = checker.check_cached_result(
                metadata_path=RELEASE_PATH,
                cache_path=cache,
                now=1001,
            )
            self.assertEqual(cached["status"], "unknown")
            self.assertEqual(cached["cache"], "hit")
            expired = checker.check_cached_result(
                metadata_path=RELEASE_PATH,
                cache_path=cache,
                now=1000 + checker.FAILURE_CACHE_SECONDS,
            )
            self.assertEqual(expired["status"], checker.CHECK_REQUIRED)

    def test_cli_consumes_mocked_refs_from_stdin_without_network(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(CHECKER_PATH),
                "--remote-refs-stdin",
                "--no-cache",
            ],
            check=False,
            capture_output=True,
            input=_refs(TARGET_VERSION),
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "update_available")
        self.assertEqual(payload["target_version"], TARGET_VERSION)

    @unittest.skipUnless(shutil.which("codex"), "Codex CLI is not installed")
    def test_mock_user_rule_allows_only_the_fixed_release_check_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules = Path(tmp) / "anchises.rules"
            rules.write_text(
                "\n".join(
                    (
                        "prefix_rule(",
                        f"    pattern = {list(GIT_CHECK)!r},",
                        '    decision = "allow",',
                        '    justification = "Allow fixed Anchises release checks",',
                        f"    match = [{' '.join(GIT_CHECK)!r}],",
                        "    not_match = [",
                        f"        {'git ls-remote -- https://github.com/example/wrong.git'!r},",
                        f"        {'python3 scripts/check_plugin_update.py'!r},",
                        "    ],",
                        ")",
                        "",
                    )
                ),
                encoding="utf-8",
            )

            def check(command: Sequence[str]) -> dict[str, Any]:
                completed = subprocess.run(
                    [
                        "codex",
                        "execpolicy",
                        "check",
                        "--pretty",
                        "--rules",
                        str(rules),
                        "--",
                        *command,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

            allowed = check(GIT_CHECK)
            self.assertTrue(allowed["matchedRules"])
            self.assertIn("allow", json.dumps(allowed).lower())

            wrong_repo = check(
                (
                    "git",
                    "ls-remote",
                    "--",
                    "https://github.com/example/wrong.git",
                )
            )
            self.assertEqual(wrong_repo["matchedRules"], [])

            python = check(("python3", "scripts/check_plugin_update.py"))
            self.assertEqual(python["matchedRules"], [])


class PluginUpdateTest(unittest.TestCase):
    def _run(
        self,
        runner: FakeRunner,
        *,
        tag_output: str | None = None,
    ) -> dict[str, Any]:
        result = updater.run_update(
            remote_refs=tag_output or _refs(TARGET_VERSION),
            runner=runner,
            metadata_path=RELEASE_PATH,
        )
        return result

    def test_success_validates_fresh_refs_and_executes_only_five_codex_commands(self) -> None:
        runner = FakeRunner(
            [
                _ok(_plugin_list(CURRENT_RELEASE)),
                _ok(_marketplace_list()),
                _ok(),
                _ok(),
                _ok(_plugin_list(TARGET_RELEASE)),
            ]
        )
        result = self._run(runner)
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["installed_release"], TARGET_RELEASE)
        self.assertEqual(runner.commands, [LIST, MARKETPLACE_LIST, UPGRADE, INSTALL, LIST])

    def test_tag_check_current_or_inconsistent_stops_before_codex(self) -> None:
        for output, expected in (
            (_refs(CURRENT_VERSION), "already_current"),
            (_refs(TARGET_VERSION, tag_commit=OTHER_COMMIT), "preflight_failed"),
        ):
            with self.subTest(expected=expected):
                runner = FakeRunner([])
                result = self._run(runner, tag_output=output)
                self.assertEqual(result["status"], expected)
                self.assertEqual(runner.commands, [])

    def test_installed_target_stops_after_complete_source_preflight(self) -> None:
        runner = FakeRunner([_ok(_plugin_list(TARGET_RELEASE)), _ok(_marketplace_list())])
        result = self._run(runner)
        self.assertEqual(result["status"], "already_current")
        self.assertEqual(runner.commands, [LIST, MARKETPLACE_LIST])

    def test_local_wrong_qa_and_incomplete_sources_are_unsupported(self) -> None:
        sources = (
            _marketplace_list(source_type="local", source="/tmp/dev"),
            _marketplace_list(source="https://github.com/example/wrong.git"),
            _marketplace_list(git_ref="qa-v2-auth"),
            json.dumps({"marketplaces": [{"name": MARKETPLACE}]}),
        )
        for payload in sources:
            with self.subTest(payload=payload):
                runner = FakeRunner([_ok(_plugin_list(CURRENT_RELEASE)), _ok(payload)])
                result = self._run(runner)
                self.assertEqual(result["status"], "unsupported_source")
                self.assertEqual(result["step"], "source_validation")
                self.assertEqual(runner.commands, [LIST, MARKETPLACE_LIST])

    def test_each_fixed_step_failure_stops_without_retry(self) -> None:
        cases = (
            ([_fail()], "preflight_failed", [LIST]),
            ([_ok(_plugin_list(CURRENT_RELEASE)), _fail()], "preflight_failed", [LIST, MARKETPLACE_LIST]),
            ([_ok(_plugin_list(CURRENT_RELEASE)), _ok(_marketplace_list()), _fail()], "upgrade_failed", [LIST, MARKETPLACE_LIST, UPGRADE]),
            ([_ok(_plugin_list(CURRENT_RELEASE)), _ok(_marketplace_list()), _ok(), _fail()], "install_failed", [LIST, MARKETPLACE_LIST, UPGRADE, INSTALL]),
            ([_ok(_plugin_list(CURRENT_RELEASE)), _ok(_marketplace_list()), _ok(), _ok(), _fail()], "verification_failed", [LIST, MARKETPLACE_LIST, UPGRADE, INSTALL, LIST]),
        )
        for results, status, expected_commands in cases:
            with self.subTest(status=status):
                runner = FakeRunner(results)
                result = self._run(runner)
                self.assertEqual(result["status"], status)
                self.assertEqual(runner.commands, expected_commands)

    def test_verification_requires_target_or_newer_base_version(self) -> None:
        runner = FakeRunner(
            [
                _ok(_plugin_list(CURRENT_RELEASE)),
                _ok(_marketplace_list()),
                _ok(),
                _ok(),
                _ok(_plugin_list(CURRENT_RELEASE)),
            ]
        )
        result = self._run(runner)
        self.assertEqual(result["status"], "verification_failed")

    def test_release_metadata_matches_manifest_and_sync_helper(self) -> None:
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], f"{release['version']}+{release['release_id']}")
        self.assertEqual(release["git_ref"], "main")
        self.assertEqual(release["tag_prefix"], TAG_PREFIX)
        self.assertFalse(release_sync.sync_release(check=True))

        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "plugin.json"
            release_path = Path(tmp) / "plugin-release.json"
            manifest_path.write_text(
                json.dumps({"version": TARGET_RELEASE}), encoding="utf-8"
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
            self.assertEqual(synced["release_id"], "codex.20260807120000")


if __name__ == "__main__":
    unittest.main()
