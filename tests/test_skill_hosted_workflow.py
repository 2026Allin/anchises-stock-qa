from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "anchises-stock-qa"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "anchises-stock-qa"
SKILL = SKILL_ROOT / "SKILL.md"
OPENAI_YAML = SKILL_ROOT / "agents" / "openai.yaml"
MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
APP_MANIFEST = PLUGIN_ROOT / ".app.json"
REVIEWER_CASES = ROOT / "tests" / "fixtures" / "reviewer_cases.json"
GOLDEN_CASES = ROOT / "tests" / "fixtures" / "golden_prompts.json"


EXPECTED_TOOLS = {
    "get_connection_status",
    "get_available_exchanges",
    "get_latest_dates",
    "get_stock_schema",
    "list_stock_tables",
    "get_table_schema",
    "screen_stocks",
    "validate_readonly_sql",
    "run_readonly_sql",
    "get_latest_company_report",
    "create_csv_export",
}


class SkillHostedWorkflowTest(unittest.TestCase):
    def test_single_skill_targets_all_eleven_hosted_tools(self) -> None:
        skill_dirs = [path for path in (PLUGIN_ROOT / "skills").iterdir() if path.is_dir()]
        self.assertEqual([path.name for path in skill_dirs], ["anchises-stock-qa"])
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("name: anchises-stock-qa", text)
        self.assertIn("anonymous_dev", text)
        self.assertIn("OAuth", text)
        self.assertIn("Work", text)
        self.assertIn("ChatGPT", text)
        self.assertIn("Codex", text)
        for tool in EXPECTED_TOOLS:
            self.assertIn(f"`{tool}`", text)

    def test_primary_skill_has_no_secret_or_local_runtime_setup(self) -> None:
        text = SKILL.read_text(encoding="utf-8").lower()
        for forbidden in (
            "config.toml",
            "mysql",
            "pandas",
            "setup_or_reset_token",
            "paste the api",
            "absolute csv path",
            "must perform at least one web search",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("never ask the user to paste passwords", text)
        self.assertIn("revoking or rotating", text)

    def test_company_report_routing_and_business_states_are_explicit(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for value in (
            "active",
            "expired",
            "not_found",
            "ondemand",
            "macmini",
            "pdf_range",
            "official annual reports",
            "live news",
            "never trigger report generation",
        ):
            self.assertIn(value, text)
        self.assertIn("Do not pass a language argument", text)
        self.assertIn("Do not repeat an identical successful tool call", text)
        self.assertIn("once before an access-sensitive workflow", text)

    def test_openai_metadata_matches_single_skill(self) -> None:
        text = OPENAI_YAML.read_text(encoding="utf-8")
        self.assertIn('display_name: "Anchises Stock QA"', text)
        self.assertIn("$anchises-stock-qa", text)
        self.assertIn("company report", text)
        self.assertIn("allow_implicit_invocation: true", text)

    def test_manifest_connects_real_app_and_keeps_legacy_rollback(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        app_manifest = json.loads(APP_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "anchises-stock-qa")
        self.assertEqual(manifest["apps"], "./.app.json")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertTrue((PLUGIN_ROOT / ".mcp.json").exists())
        self.assertTrue((PLUGIN_ROOT / "mcp" / "bootstrap.py").exists())
        self.assertEqual(set(app_manifest), {"apps"})
        self.assertEqual(set(app_manifest["apps"]), {"anchises_stock_qa"})
        app = app_manifest["apps"]["anchises_stock_qa"]
        self.assertEqual(set(app), {"id"})
        self.assertEqual(
            app["id"],
            "plugin_asdk_app_6a5754cdf4ac8191a27ec8854675482a",
        )
        serialized = json.dumps(app_manifest).lower()
        for forbidden in ("client_secret", "api_token", "authorization", "bearer"):
            self.assertNotIn(forbidden, serialized)

    def test_manifest_metadata_and_starter_prompts_match_phase_7a(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["homepage"], "https://anchisesdata.com/stock-qa")
        self.assertEqual(manifest["repository"], "https://github.com/2026Allin/anchises-stock-qa")
        interface = manifest["interface"]
        self.assertEqual(interface["privacyPolicyURL"], "https://anchisesdata.com/privacy")
        self.assertEqual(interface["termsOfServiceURL"], "https://anchisesdata.com/terms")
        self.assertEqual(len(interface["defaultPrompt"]), 3)
        self.assertTrue(any("Anchises AI report" in prompt for prompt in interface["defaultPrompt"]))
        self.assertTrue(all(len(prompt) <= 128 for prompt in interface["defaultPrompt"]))
        copy = json.dumps(manifest).lower()
        for stale in ("mysql", "api token", "pandas", "user-configured"):
            self.assertNotIn(stale, copy)

    def test_golden_prompts_cover_all_tools_and_report_boundaries(self) -> None:
        cases = json.loads(GOLDEN_CASES.read_text(encoding="utf-8"))
        positives = cases["positive"]
        negatives = cases["negative"]
        self.assertGreaterEqual(len(positives), 8)
        self.assertGreaterEqual(len(negatives), 6)
        covered = {
            tool
            for case in positives
            for tool in case.get("expected_tools", [])
        }
        self.assertEqual(covered, EXPECTED_TOOLS)
        categories = {case["category"] for case in positives + negatives}
        self.assertEqual(categories, {"direct", "indirect", "negative"})
        report_negative_ids = {
            case["id"]
            for case in negatives
            if "get_latest_company_report" in case.get("forbidden_tools", [])
        }
        self.assertEqual(
            report_negative_ids,
            {"official-filing-not-report", "live-news-not-report", "generation-not-read"},
        )
        language = next(case for case in negatives if case["id"] == "language-not-supported")
        self.assertIn("language", language["forbidden_arguments"])

    def test_submission_fixture_remains_five_positive_and_three_negative(self) -> None:
        cases = json.loads(REVIEWER_CASES.read_text(encoding="utf-8"))
        self.assertEqual(len(cases["positive"]), 5)
        self.assertEqual(len(cases["negative"]), 3)
        all_cases = cases["positive"] + cases["negative"]
        ids = [case["id"] for case in all_cases]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
