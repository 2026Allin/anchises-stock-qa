from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "anchises-analysis"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "anchises-analysis"
REFERENCE_ROOT = SKILL_ROOT / "references"
DIAGNOSTICS = REFERENCE_ROOT / "diagnostics.md"
CHECKER_PATH = SKILL_ROOT / "scripts" / "check_plugin_update.py"
GOLDEN_CASES = ROOT / "tests" / "fixtures" / "golden_prompts.json"
RESULT_CASES = ROOT / "tests" / "fixtures" / "diagnostics_results.json"
REPOSITORY = "https://github.com/2026Allin/anchises-stock-qa.git"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


checker = _load_module("anchises_diagnostics_checker", CHECKER_PATH)


def _golden_by_id() -> dict[str, dict[str, Any]]:
    payload = json.loads(GOLDEN_CASES.read_text(encoding="utf-8"))
    return {
        case["id"]: case
        for group in payload.values()
        for case in group
    }


class DiagnosticsRoutingTest(unittest.TestCase):
    def test_status_routes_before_business_and_uses_only_the_connection_tool(self) -> None:
        cases = _golden_by_id()
        for case_id in (
            "status-direct",
            "status-force-refresh",
            "status-check-update-only",
        ):
            case = cases[case_id]
            self.assertEqual(case["expected_primary_task"], "diagnostics")
            self.assertEqual(case["expected_skill"], "anchises-analysis")
            self.assertEqual(case["expected_tools"], ["get_connection_status"])
            self.assertLessEqual(
                case["expected_release_check"]["max_git_queries"],
                1,
            )

        force = cases["status-force-refresh"]["expected_release_check"]
        self.assertEqual(force["mode"], "fresh")
        self.assertTrue(force["skip_cache_read"])
        check_only = cases["status-check-update-only"]
        self.assertIn("plugin_install", check_only["forbidden_operations"])

    def test_check_and_install_uses_plugin_update_without_mcp(self) -> None:
        case = _golden_by_id()["check-and-install-update"]
        self.assertEqual(case["expected_primary_task"], "plugin_update")
        self.assertEqual(case["expected_tools"], [])
        self.assertIn("get_connection_status", case["forbidden_tools"])
        self.assertEqual(case["expected_release_check"]["mode"], "fresh")

    def test_incidental_health_and_status_words_do_not_trigger_diagnostics(self) -> None:
        case = _golden_by_id()["incidental-health-status-not-diagnostics"]
        self.assertEqual(case["expected_primary_task"], "comparison")
        self.assertEqual(case["expected_skill"], "company-comparison")
        self.assertIn("diagnostics", case["forbidden_operations"])

    def test_prompt_contract_freezes_diagnostic_execution_and_privacy(self) -> None:
        diagnostics = " ".join(DIAGNOSTICS.read_text(encoding="utf-8").split())
        coordinator = " ".join(
            (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").split()
        )
        shared = " ".join(
            (REFERENCE_ROOT / "plugin-update.md").read_text(encoding="utf-8").split()
        )
        for expected in (
            "`primary_task=diagnostics`",
            "`anchises_analysis:get_connection_status` exactly once with `{}`",
            "Do not call HTTP `/health`",
            "Run the service check and selected-platform plugin check independently",
            "skip the cache-only probe",
            "exactly one fixed-repository `git ls-remote`",
            "`anchises-analysis/codex/v*`",
            "`anchises-analysis/claude/v*`",
            "插件版本暂时无法确认",
            "Do not add an investment disclaimer",
        ):
            self.assertIn(expected, diagnostics)
        self.assertIn("bypasses `query-interpretation.md`", coordinator)
        self.assertIn("`plugin_update`, not `diagnostics`", coordinator)
        self.assertIn("must not call MCP", coordinator)
        self.assertIn("An explicit “check updates only; do not install”", shared)
        self.assertIn("must not call `get_connection_status`", shared)

    def test_coordinator_contains_the_claude_safe_diagnostic_completion_gate(self) -> None:
        coordinator = " ".join(
            (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").split()
        )
        for expected in (
            "`anchises_analysis:get_connection_status` exactly once with `{}`",
            "A successful service call never permits skipping the plugin check",
            "Populate both `diagnostic_service_check` and `diagnostic_plugin_check`",
            "- 插件：<Codex 或 Claude>，当前版本 <x>",
            "- 更新：<已是最新版 / 可更新到 y / 插件版本暂时无法确认>",
            "- 检查来源：<最近有效结果 / 刚刚重新检查>",
            "still return all receipt lines",
        ):
            self.assertIn(expected, coordinator)

    def test_description_activates_the_full_diagnostic_on_claude_web(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        description = next(
            line.removeprefix("description: ")
            for line in skill.splitlines()
            if line.startswith("description: ")
        )
        self.assertLessEqual(len(description), 1024)
        for expected in (
            "For any Anchises status request, run unified diagnostics",
            "anchises_analysis:get_connection_status once",
            "active host's bundled release metadata",
            "never stop after service status",
            "platform/current version",
            "check source",
            "without business advice or follow-up",
        ):
            self.assertIn(expected, description)


class DiagnosticsResultContractTest(unittest.TestCase):
    def test_six_required_result_combinations_are_closed_and_safe(self) -> None:
        cases = json.loads(RESULT_CASES.read_text(encoding="utf-8"))
        self.assertEqual(
            [case["id"] for case in cases],
            [
                "active-current",
                "active-update-available",
                "inactive-current",
                "mcp-503-current",
                "active-plugin-unknown",
                "both-unknown",
            ],
        )
        for case in cases:
            expected = case["expected"]
            receipt = "\n".join(
                (
                    "Anchises Analysis 状态",
                    f"- 服务：{expected['service']}",
                    f"- 访问：{expected['access']}",
                    f"- 更新：{expected['update']}",
                    f"- 检查来源：{expected['source']}",
                )
            )
            self.assertIn(expected["response_status"], {"mechanical_result", "failed"})
            self.assertNotIn("?", receipt)
            self.assertNotIn("投资", receipt)
            for forbidden in case.get("forbidden_output", []):
                self.assertNotIn(forbidden, receipt)
            if expected["notice"]:
                self.assertTrue(expected["update"].startswith("可更新到 "))
            else:
                self.assertFalse(
                    expected["update"].startswith("可更新到 "),
                    case["id"],
                )

    def test_direct_remote_ingest_bypasses_a_cached_value_and_writes_new_cache(self) -> None:
        metadata = REFERENCE_ROOT / "plugin-release.json"
        main_commit = "a" * 40
        target = "0.6.0-dev.9"
        refs_with_update = "\n".join(
            (
                f"{main_commit}\tHEAD",
                f"{main_commit}\trefs/heads/main",
                f"{main_commit}\trefs/tags/anchises-analysis/codex/v{target}",
                "",
            )
        )
        refs_current = "\n".join(
            (
                f"{main_commit}\tHEAD",
                f"{main_commit}\trefs/heads/main",
                "",
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "release-cache.json"
            first = checker.check_remote_refs(
                refs_with_update,
                metadata_path=metadata,
                cache_path=cache,
                now=1000,
            )
            self.assertEqual(first["status"], "update_available")
            cached = checker.check_cached_result(
                metadata_path=metadata,
                cache_path=cache,
                now=1001,
            )
            self.assertEqual(cached["status"], "update_available")
            self.assertEqual(cached["cache"], "hit")

            forced = checker.check_remote_refs(
                refs_current,
                metadata_path=metadata,
                cache_path=cache,
                now=1002,
            )
            self.assertEqual(forced["status"], "current")
            refreshed = checker.check_cached_result(
                metadata_path=metadata,
                cache_path=cache,
                now=1003,
            )
            self.assertEqual(refreshed["status"], "current")
            self.assertEqual(refreshed["cache"], "hit")

    def test_platform_metadata_keeps_fixed_repository_and_separate_namespaces(self) -> None:
        codex = json.loads(
            (REFERENCE_ROOT / "plugin-release.json").read_text(encoding="utf-8")
        )
        claude = json.loads(
            (REFERENCE_ROOT / "plugin-release-claude.json").read_text(encoding="utf-8")
        )
        self.assertEqual(codex["repository"], REPOSITORY)
        self.assertEqual(claude["repository"], REPOSITORY)
        self.assertEqual(codex["tag_prefix"], "anchises-analysis/codex/v")
        self.assertEqual(claude["tag_prefix"], "anchises-analysis/claude/v")
        self.assertNotEqual(codex["version"], claude["version"])


if __name__ == "__main__":
    unittest.main()
