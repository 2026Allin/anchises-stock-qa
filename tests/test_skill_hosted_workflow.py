from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "stock-data-desk"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "stock-data-desk"
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
        self.assertEqual([path.name for path in skill_dirs], ["stock-data-desk"])
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("name: stock-data-desk", text)
        self.assertIn("OAuth", text)
        self.assertIn("shared", text)
        self.assertIn("HTTP 503", text)
        self.assertIn("Work", text)
        self.assertIn("ChatGPT", text)
        self.assertIn("Codex", text)
        for tool in EXPECTED_TOOLS:
            self.assertIn(f"`{tool}`", text)

    def test_skill_uses_observable_access_behavior_not_backend_mode_names(self) -> None:
        paths = [SKILL, *sorted((SKILL_ROOT / "references").glob("*.md"))]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for internal_mode in ("anonymous_dev", "anonymous_dev_v1", "usr_anonymous_dev"):
            self.assertNotIn(internal_mode, combined)
        self.assertIn("OAuth challenge", combined)
        self.assertIn("shared limits", combined)
        self.assertIn("HTTP 503", combined)

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
            ".mcp.json",
            "stdio",
            "rollback",
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
        self.assertIn("Always identify the product as **Stock Data Desk**", text)
        self.assertIn("do not repeat", text)

    def test_openai_metadata_matches_single_skill(self) -> None:
        text = OPENAI_YAML.read_text(encoding="utf-8")
        self.assertIn('display_name: "Stock Data Desk"', text)
        self.assertIn("$stock-data-desk", text)
        self.assertIn("company report", text)
        self.assertIn("allow_implicit_invocation: true", text)

    def test_manifest_connects_real_app_without_local_mcp(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        app_manifest = json.loads(APP_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "stock-data-desk")
        self.assertEqual(manifest["apps"], "./.app.json")
        self.assertNotIn("mcpServers", manifest)
        for removed in (
            ".mcp.json",
            "config.example.toml",
            "requirements.txt",
            "mcp/bootstrap.py",
            "mcp/server.py",
            "scripts/ask_stock.py",
            "scripts/init_config.sh",
            "scripts/remote_api.py",
            "prompts/query-planning.md",
        ):
            self.assertFalse((PLUGIN_ROOT / removed).exists(), removed)
        self.assertEqual(set(app_manifest), {"apps"})
        self.assertEqual(set(app_manifest["apps"]), {"stock_data_desk"})
        app = app_manifest["apps"]["stock_data_desk"]
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
        self.assertTrue(any("cached AI company report" in prompt for prompt in interface["defaultPrompt"]))
        self.assertTrue(all(len(prompt) <= 128 for prompt in interface["defaultPrompt"]))
        self.assertEqual(interface["capabilities"], ["Interactive", "Read", "Write"])
        self.assertNotIn("developer mode", interface["longDescription"].lower())
        self.assertNotIn("anonymous_dev", interface["longDescription"])
        copy = json.dumps(manifest).lower()
        for stale in ("mysql", "api token", "pandas", "user-configured"):
            self.assertNotIn(stale, copy)

    def test_user_facing_brand_is_stock_data_desk(self) -> None:
        strict_files = [
            SKILL,
            OPENAI_YAML,
            *sorted((SKILL_ROOT / "references").glob("*.md")),
            GOLDEN_CASES,
            REVIEWER_CASES,
        ]
        for path in strict_files:
            self.assertNotIn(
                "anchises",
                path.read_text(encoding="utf-8").lower(),
                str(path),
            )

        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        user_facing = {
            "description": manifest["description"],
            "author": manifest["author"]["name"],
            "displayName": manifest["interface"]["displayName"],
            "shortDescription": manifest["interface"]["shortDescription"],
            "longDescription": manifest["interface"]["longDescription"],
            "developerName": manifest["interface"]["developerName"],
            "defaultPrompt": manifest["interface"]["defaultPrompt"],
        }
        self.assertNotIn("anchises", json.dumps(user_facing).lower())

    def test_old_brand_only_remains_in_approved_technical_metadata(self) -> None:
        excluded = {PLUGIN_ROOT / "contracts" / "hosted-mcp-v1.json"}
        allowed_line_markers = (
            "://",
            "ANCHISES_STOCK_QA_CONFIG",
            ".config/anchises-stock-qa",
            ".local/share/anchises-stock-qa",
            '".config" / "anchises-stock-qa"',
            '"share" / "anchises-stock-qa"',
        )
        unexpected: list[str] = []
        for path in PLUGIN_ROOT.rglob("*"):
            if not path.is_file() or path in excluded:
                continue
            if ".venv" in path.parts or "__pycache__" in path.parts:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, start=1):
                if "anchises" not in line.lower():
                    continue
                if not any(marker.lower() in line.lower() for marker in allowed_line_markers):
                    unexpected.append(
                        f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}"
                    )
        self.assertEqual(unexpected, [])

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
