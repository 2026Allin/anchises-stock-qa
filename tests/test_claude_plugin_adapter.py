from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Sequence
from unittest import mock


sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "anchises-analysis"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "anchises-analysis"
SCRIPT_ROOT = SKILL_ROOT / "scripts"
CHECKER_PATH = SCRIPT_ROOT / "check_plugin_update.py"
UPDATER_PATH = SCRIPT_ROOT / "update_installed_plugin.py"
SYNC_PATH = PLUGIN_ROOT / "scripts" / "sync_plugin_release.py"
CLAUDE_RELEASE_PATH = SKILL_ROOT / "references" / "plugin-release-claude.json"
CLAUDE_MANIFEST_PATH = ROOT / ".claude-plugin" / "plugin.json"
CLAUDE_MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"
CLAUDE_SKILL_ROOT = SKILL_ROOT
LEGACY_CLAUDE_MANIFEST_PATH = (
    PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
)
CLAUDE_INSTALL_GUIDE = ROOT / "docs" / "anchises-analysis-claude-install.md"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
checker = sys.modules.get("check_plugin_update") or _load_module(
    "check_plugin_update",
    CHECKER_PATH,
)
updater = _load_module("anchises_claude_plugin_updater", UPDATER_PATH)
release_sync = _load_module("anchises_claude_release_sync", SYNC_PATH)


PLUGIN_ID = "anchises-analysis@anchises-capital"
MARKETPLACE = "anchises-capital"
REPOSITORY = "https://github.com/2026Allin/anchises-stock-qa.git"
GITHUB_REPOSITORY = "2026Allin/anchises-stock-qa"
TAG_PREFIX = "anchises-analysis/claude/v"
CURRENT_VERSION = "0.6.0-dev.9"
CURRENT_RELEASE = "0.6.0-dev.9+claude.20260806163701"
TARGET_VERSION = "0.6.0-dev.10"
TARGET_RELEASE = "0.6.0-dev.10+claude.20260808120000"
MAIN_COMMIT = "4" * 40
OTHER_COMMIT = "5" * 40

CLAUDE_LIST = ("claude", "plugin", "list", "--json")
CLAUDE_MARKETPLACE_LIST = (
    "claude",
    "plugin",
    "marketplace",
    "list",
    "--json",
)
CLAUDE_MARKETPLACE_UPDATE = (
    "claude",
    "plugin",
    "marketplace",
    "update",
    MARKETPLACE,
)
CLAUDE_UPDATE = ("claude", "plugin", "update", PLUGIN_ID)


class FakeRunner:
    def __init__(self, results: Sequence[Any]) -> None:
        self.results = list(results)
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, command: Sequence[str]) -> Any:
        self.commands.append(tuple(command))
        if not self.results:
            raise AssertionError("an unexpected extra command was executed")
        return self.results.pop(0)


def _ok(stdout: str = "") -> Any:
    return updater.CommandResult(0, stdout, "")


def _fail(message: str = "denied") -> Any:
    return updater.CommandResult(1, "", message)


def _refs(
    *versions: str,
    main_commit: str = MAIN_COMMIT,
    head_commit: str | None = None,
    include_head: bool = True,
    tag_commit: str | None = None,
    extra: Sequence[str] = (),
) -> str:
    lines = []
    if include_head:
        lines.append(f"{head_commit or main_commit}\tHEAD")
    lines.append(f"{main_commit}\trefs/heads/main")
    for version in versions:
        lines.append(
            f"{tag_commit or main_commit}\trefs/tags/{TAG_PREFIX}{version}"
        )
    lines.extend(extra)
    return "\n".join(lines) + "\n"


def _plugin_list(version: str, *, enabled: bool = True) -> str:
    return json.dumps(
        [
            {
                "id": PLUGIN_ID,
                "version": version,
                "enabled": enabled,
            }
        ]
    )


def _marketplace_list(
    *,
    source: str = "github",
    repo: str = GITHUB_REPOSITORY,
    url: str | None = None,
    ref: str | None = "main",
    include_ref: bool = True,
) -> str:
    entry: dict[str, Any] = {
        "name": MARKETPLACE,
        "source": source,
        "installLocation": "/tmp/claude-marketplace",
    }
    if source == "github":
        entry["repo"] = repo
    if url is not None:
        entry["url"] = url
    if include_ref:
        entry["ref"] = ref
    return json.dumps([entry])


class ClaudeManifestTest(unittest.TestCase):
    def test_marketplace_exposes_one_self_contained_claude_skill(self) -> None:
        marketplace = json.loads(CLAUDE_MARKETPLACE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            set(marketplace),
            {"name", "owner", "description", "plugins"},
        )
        self.assertEqual(marketplace["name"], MARKETPLACE)
        self.assertEqual(marketplace["owner"]["name"], "Anchises Capital")
        self.assertEqual(
            marketplace["owner"]["url"],
            "https://anchisesdata.com",
        )
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(
            set(entry),
            {"name", "displayName", "source", "description", "category"},
        )
        self.assertEqual(entry["name"], "anchises-analysis")
        self.assertEqual(entry["displayName"], "Anchises Analysis")
        self.assertEqual(entry["source"], "./")
        self.assertNotIn("version", entry)

        claude = json.loads(CLAUDE_MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            set(claude),
            {
                "name",
                "displayName",
                "version",
                "description",
                "author",
                "homepage",
                "repository",
                "license",
                "keywords",
                "skills",
                "mcpServers",
            },
        )
        codex = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(claude["name"], "anchises-analysis")
        self.assertEqual(claude["displayName"], "Anchises Analysis")
        self.assertRegex(
            claude["version"],
            r"^0\.6\.0-dev\.9\+claude\.\d{14}$",
        )
        for key in (
            "description",
            "author",
            "homepage",
            "repository",
            "license",
            "keywords",
        ):
            self.assertEqual(claude[key], codex[key], key)
        self.assertNotIn("interface", claude)
        self.assertEqual(
            claude["skills"],
            "./plugins/anchises-analysis/skills/anchises-analysis/",
        )
        self.assertEqual(
            claude["mcpServers"],
            "./plugins/anchises-analysis/.mcp.json",
        )

        plugin_root = ROOT / entry["source"]
        self.assertEqual(plugin_root.resolve(), ROOT.resolve())
        self.assertEqual(
            CLAUDE_MANIFEST_PATH.parent.resolve(),
            plugin_root.resolve() / ".claude-plugin",
        )
        self.assertFalse(LEGACY_CLAUDE_MANIFEST_PATH.exists())
        self.assertTrue((plugin_root / claude["mcpServers"]).is_file())
        self.assertEqual(
            (plugin_root / claude["skills"]).resolve(),
            CLAUDE_SKILL_ROOT.resolve(),
        )
        self.assertEqual(
            sorted(path.name for path in (PLUGIN_ROOT / "skills").iterdir()),
            [
                "anchises-analysis",
                "company-brief",
                "company-comparison",
                "company-report",
                "market-analysis",
            ],
        )

    def test_claude_skill_is_closed_and_contains_exactly_one_skill_file(self) -> None:
        self.assertTrue((CLAUDE_SKILL_ROOT / "SKILL.md").is_file())
        self.assertEqual(
            [path.relative_to(CLAUDE_SKILL_ROOT) for path in CLAUDE_SKILL_ROOT.rglob("SKILL.md")],
            [Path("SKILL.md")],
        )
        for directory in ("agents", "references", "scripts", "workflows"):
            self.assertTrue((CLAUDE_SKILL_ROOT / directory).is_dir(), directory)

        markdown_link = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
        for source in sorted(CLAUDE_SKILL_ROOT.rglob("*.md")):
            for raw_target in markdown_link.findall(source.read_text(encoding="utf-8")):
                target = raw_target.split("#", 1)[0]
                if not target or "://" in target:
                    continue
                resolved = (source.parent / target).resolve()
                self.assertTrue(
                    resolved.is_relative_to(CLAUDE_SKILL_ROOT.resolve()),
                    f"{source.relative_to(CLAUDE_SKILL_ROOT)} escapes to {target}",
                )
                self.assertTrue(
                    resolved.is_file(),
                    f"{source.relative_to(CLAUDE_SKILL_ROOT)} has missing {target}",
                )

        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / "anchises-analysis"
            shutil.copytree(CLAUDE_SKILL_ROOT, copied)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(copied / "scripts" / "check_plugin_update.py"),
                    "--platform",
                    "claude",
                    "--remote-refs-stdin",
                    "--no-cache",
                ],
                input=_refs(TARGET_VERSION),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                json.loads(completed.stdout)["status"],
                "update_available",
            )

    def test_codex_keeps_five_thin_skill_entries(self) -> None:
        skill_roots = sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual(len(skill_roots), 5)
        for name in (
            "company-brief",
            "company-comparison",
            "company-report",
            "market-analysis",
        ):
            wrapper = PLUGIN_ROOT / "skills" / name / "SKILL.md"
            text = wrapper.read_text(encoding="utf-8")
            self.assertIn(f"name: {name}", text)
            self.assertIn("../anchises-analysis/workflows/", text)
            self.assertLess(len(text.splitlines()), 20)

    def test_shared_mcp_contract_remains_exactly_twelve_tools(self) -> None:
        mcp = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(
            mcp,
            {
                "mcpServers": {
                    "anchises_analysis": {
                        "type": "http",
                        "url": "https://mcp.anchisesdata.com/mcp",
                    }
                }
            },
        )
        contract = json.loads(
            (PLUGIN_ROOT / "contracts" / "hosted-mcp-v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(contract["tools"]), 12)

        release = json.loads(CLAUDE_RELEASE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            set(release),
            {
                "schema_version",
                "name",
                "platform",
                "version",
                "release_id",
                "plugin_id",
                "marketplace",
                "repository",
                "git_ref",
                "tag_prefix",
            },
        )
        self.assertEqual(release["platform"], "claude")
        self.assertEqual(release["plugin_id"], PLUGIN_ID)
        self.assertEqual(release["marketplace"], MARKETPLACE)

    def test_install_guide_covers_github_cli_and_all_claude_surfaces(self) -> None:
        guide = CLAUDE_INSTALL_GUIDE.read_text(encoding="utf-8")
        normalized = " ".join(guide.split())
        for expected in (
            "2026Allin/anchises-stock-qa@main",
            "--sparse .claude-plugin plugins/anchises-analysis",
            "claude plugin install anchises-analysis@anchises-capital",
            "claude --plugin-dir .",
            "https://github.com/2026Allin/anchises-stock-qa",
            "Claude Chat",
            "Claude Desktop",
            "Cowork",
            "Claude Code",
            "Customize → Plugins → Anchises Analysis → Update",
            "anchises-analysis/claude/v<semver>",
            "Exactly one visible Skill",
            "exactly 12 tools",
        ):
            self.assertIn(expected, normalized)


class ClaudeTagCheckTest(unittest.TestCase):
    def test_claude_namespace_is_separate_and_uses_the_fixed_repository(self) -> None:
        codex_tag = (
            f"{MAIN_COMMIT}\trefs/tags/anchises-analysis/codex/v99.0.0"
        )
        result = checker.check_remote_refs(
            _refs(TARGET_VERSION, extra=(codex_tag,)),
            metadata_path=CLAUDE_RELEASE_PATH,
            use_cache=False,
        )
        self.assertEqual(result["status"], "update_available")
        self.assertEqual(result["target_version"], TARGET_VERSION)
        self.assertEqual(result["target_tag"], f"{TAG_PREFIX}{TARGET_VERSION}")
        self.assertEqual(
            checker.release_check_command(CLAUDE_RELEASE_PATH),
            ("git", "ls-remote", "--", REPOSITORY),
        )

    def test_claude_cache_prefers_plugin_data_and_falls_back_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_DATA": tmp}):
                self.assertEqual(
                    checker._default_cache_path("claude"),
                    Path(tmp) / "release-check-cache.json",
                )
            with mock.patch.dict(
                os.environ,
                {"CLAUDE_PLUGIN_DATA": "relative/not-allowed"},
            ):
                fallback = checker._default_cache_path("claude")
                self.assertTrue(fallback.is_absolute())
                self.assertIn("anchises-analysis-claude-tags-", fallback.name)
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_DATA": "/"}):
                self.assertNotEqual(
                    checker._default_cache_path("claude"),
                    Path("/release-check-cache.json"),
                )

    def test_claude_success_and_failure_cache_ttls_match_shared_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            success_cache = Path(tmp) / "success.json"
            checker.check_remote_refs(
                _refs(TARGET_VERSION),
                metadata_path=CLAUDE_RELEASE_PATH,
                cache_path=success_cache,
                now=1000,
            )
            self.assertEqual(
                checker.check_cached_result(
                    metadata_path=CLAUDE_RELEASE_PATH,
                    cache_path=success_cache,
                    now=1000 + checker.SUCCESS_CACHE_SECONDS - 1,
                )["status"],
                "update_available",
            )
            self.assertEqual(
                checker.check_cached_result(
                    metadata_path=CLAUDE_RELEASE_PATH,
                    cache_path=success_cache,
                    now=1000 + checker.SUCCESS_CACHE_SECONDS,
                )["status"],
                checker.CHECK_REQUIRED,
            )

            failure_cache = Path(tmp) / "failure.json"
            checker.check_remote_refs(
                "",
                metadata_path=CLAUDE_RELEASE_PATH,
                cache_path=failure_cache,
                now=2000,
            )
            self.assertEqual(
                checker.check_cached_result(
                    metadata_path=CLAUDE_RELEASE_PATH,
                    cache_path=failure_cache,
                    now=2000 + checker.FAILURE_CACHE_SECONDS - 1,
                )["status"],
                "unknown",
            )
            self.assertEqual(
                checker.check_cached_result(
                    metadata_path=CLAUDE_RELEASE_PATH,
                    cache_path=failure_cache,
                    now=2000 + checker.FAILURE_CACHE_SECONDS,
                )["status"],
                checker.CHECK_REQUIRED,
            )

    def test_cli_selects_claude_metadata_without_network(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(CHECKER_PATH),
                "--platform",
                "claude",
                "--remote-refs-stdin",
                "--no-cache",
            ],
            check=False,
            capture_output=True,
            input=_refs(TARGET_VERSION),
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "update_available")
        self.assertEqual(result["installed_version"], CURRENT_VERSION)

    def test_malformed_platform_metadata_fails_closed(self) -> None:
        metadata = json.loads(CLAUDE_RELEASE_PATH.read_text(encoding="utf-8"))
        metadata["platform"] = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "release.json"
            path.write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported platform"):
                checker._load_metadata(path)


class ClaudeUpdateTest(unittest.TestCase):
    def _run(self, runner: FakeRunner, *, refs: str | None = None) -> dict[str, Any]:
        return updater.run_update(
            remote_refs=refs or _refs(TARGET_VERSION),
            runner=runner,
            metadata_path=CLAUDE_RELEASE_PATH,
        )

    def test_success_executes_only_the_five_fixed_claude_commands(self) -> None:
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
        self.assertEqual(
            runner.commands,
            [
                CLAUDE_LIST,
                CLAUDE_MARKETPLACE_LIST,
                CLAUDE_MARKETPLACE_UPDATE,
                CLAUDE_UPDATE,
                CLAUDE_LIST,
            ],
        )

    def test_exact_git_url_and_unpinned_matching_head_are_supported(self) -> None:
        for marketplace in (
            _marketplace_list(source="git", url=REPOSITORY),
            _marketplace_list(source="url", url=REPOSITORY),
            _marketplace_list(include_ref=False),
        ):
            with self.subTest(marketplace=marketplace):
                runner = FakeRunner(
                    [
                        _ok(_plugin_list(CURRENT_RELEASE)),
                        _ok(marketplace),
                        _ok(),
                        _ok(),
                        _ok(_plugin_list(TARGET_RELEASE)),
                    ]
                )
                self.assertEqual(self._run(runner)["status"], "updated")

    def test_wrong_source_or_non_main_ref_fails_closed(self) -> None:
        for marketplace in (
            _marketplace_list(repo="other/repository"),
            _marketplace_list(ref="qa-v2-auth"),
            _marketplace_list(source="local"),
        ):
            with self.subTest(marketplace=marketplace):
                runner = FakeRunner(
                    [_ok(_plugin_list(CURRENT_RELEASE)), _ok(marketplace)]
                )
                result = self._run(runner)
                self.assertEqual(result["status"], "unsupported_source")
                self.assertEqual(
                    runner.commands,
                    [CLAUDE_LIST, CLAUDE_MARKETPLACE_LIST],
                )

    def test_failure_stops_without_retry_or_fallback(self) -> None:
        runner = FakeRunner(
            [
                _ok(_plugin_list(CURRENT_RELEASE)),
                _ok(_marketplace_list()),
                _fail(),
            ]
        )
        result = self._run(runner)
        self.assertEqual(result["status"], "upgrade_failed")
        self.assertEqual(result["step"], "marketplace_upgrade")
        self.assertEqual(
            runner.commands,
            [CLAUDE_LIST, CLAUDE_MARKETPLACE_LIST, CLAUDE_MARKETPLACE_UPDATE],
        )

    def test_claude_release_metadata_matches_manifest_and_syncs(self) -> None:
        manifest = json.loads(CLAUDE_MANIFEST_PATH.read_text(encoding="utf-8"))
        release = json.loads(CLAUDE_RELEASE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["version"],
            f"{release['version']}+{release['release_id']}",
        )
        self.assertEqual(release["tag_prefix"], TAG_PREFIX)
        self.assertFalse(
            release_sync.sync_release(check=True, platform="claude")
        )

        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "plugin.json"
            release_path = Path(tmp) / "plugin-release-claude.json"
            manifest_path.write_text(
                json.dumps({"version": TARGET_RELEASE}),
                encoding="utf-8",
            )
            stale = dict(release)
            stale["version"] = "0.6.0-dev.1"
            release_path.write_text(json.dumps(stale), encoding="utf-8")
            self.assertTrue(
                release_sync.sync_release(
                    check=False,
                    manifest_path=manifest_path,
                    release_path=release_path,
                    platform="claude",
                )
            )
            synced = json.loads(release_path.read_text(encoding="utf-8"))
            self.assertEqual(synced["version"], TARGET_VERSION)
            self.assertEqual(synced["release_id"], "claude.20260808120000")


class SharedBundleRegressionTest(unittest.TestCase):
    EXPECTED_SHA256 = {
        "plugins/anchises-analysis/.mcp.json": "0206a879a0161f76f354fbf8f160129735c9eec64da2cc28e46a972e52756dc7",
        "plugins/anchises-analysis/contracts/hosted-mcp-v1.json": "f52ff5598cf12c13958cbb6c33bc3bffd0770788b8c9383c552714b0895699c6",
    }
    EXPECTED_NORMALIZED_PROMPT_SHA256 = {
        "workflows/company-brief.md": "e3e50389698a81f343630803372098b013b5013c7fd54f7c7e4ad358d420f411",
        "workflows/company-comparison.md": "f45a87afd3f3c7a0769fee7a421bb23ca69b0fa8168f352a60fc20afd44b4bd8",
        "workflows/company-report.md": "aa837d7a6adf029afd9f8966890dd640b9f726b8d77c299881c7ba9e63ae7efb",
        "workflows/market-analysis.md": "6d45fec2ca851f9c063ce388bb727e186391cab0fca5a57553af157c1bedc847",
        "references/comparison-format.md": "b7d999cda0c5611a5f03f98e8012ebe1e879170aa49ca8d964979fc475532fd2",
        "references/comparison-workflow.md": "bba176cdeeb40cacc042a1a50bd062beb7c82b461834963168656f0f5608819e",
        "references/mining-report-quality.md": "30c52bb042c4fd5015bd6d196c0948295786e5dd35cd069b80b8252553f6da18",
        "references/report-format.md": "8d867da983a34139972508b27714616244595fc898f19df8e0d3f27f4f8d0ad5",
        "references/report-workflow.md": "aeaf7c5f13dbe94d0ef291e98748b2e5ae2ef6e60b6c53f093f6c75149fc3d38",
        "references/market-answer-format.md": "fea727da6b55886ae8a514c69a6cad683d84b9400a72d2c898a8c8f97521ba4f",
        "references/market-data-policy.md": "2a06f03087aaf72429efc24c23868153501a30269b8967f11a21e22faedea1cf",
        "references/market-workflow.md": "9f58fdd19d187e3d8d925362aa6efa0079a641fcfb8a7789c82ea6b6e4a83cdd",
    }

    def test_mcp_contract_is_byte_for_byte_unchanged(self) -> None:
        for relative in (
            "plugins/anchises-analysis/.mcp.json",
            "plugins/anchises-analysis/contracts/hosted-mcp-v1.json",
        ):
            expected = self.EXPECTED_SHA256[relative]
            with self.subTest(path=relative):
                digest = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
                self.assertEqual(digest, expected)

    def test_moved_business_prompts_change_only_internal_link_paths(self) -> None:
        def normalize_links(text: str) -> str:
            def replace(match: re.Match[str]) -> str:
                label, target = match.groups()
                normalized_label = Path(label).name if label.endswith(".md") else label
                return f"[{normalized_label}]({Path(target).name})"

            return re.sub(r"\[([^\]]+)\]\(([^)]+\.md)\)", replace, text)

        for relative, expected in self.EXPECTED_NORMALIZED_PROMPT_SHA256.items():
            with self.subTest(relative=relative):
                text = (CLAUDE_SKILL_ROOT / relative).read_text(encoding="utf-8")
                digest = hashlib.sha256(normalize_links(text).encode()).hexdigest()
                self.assertEqual(digest, expected)

    def test_business_workflows_are_present_in_the_self_contained_core(self) -> None:
        expected_fingerprints = {
            "company-brief.md": "exactly three or four prose sentences",
            "company-comparison.md": "Never silently compare only the first five",
            "company-report.md": "only plugin Skill allowed to call",
            "market-analysis.md": "complete matched range for server-side filtering",
        }
        workflow_root = CLAUDE_SKILL_ROOT / "workflows"
        for filename, expected in expected_fingerprints.items():
            with self.subTest(filename=filename):
                workflow = (workflow_root / filename).read_text(encoding="utf-8")
                if filename == "company-brief.md":
                    workflow += (CLAUDE_SKILL_ROOT / "references" / "company-introductions.md").read_text(encoding="utf-8")
                self.assertIn(expected, " ".join(workflow.split()))


if __name__ == "__main__":
    unittest.main()
