from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "stock-data-desk"
PLUGIN_README = PLUGIN_ROOT / "README.md"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "stock-data-desk"
SKILL = SKILL_ROOT / "SKILL.md"
OPENAI_YAML = SKILL_ROOT / "agents" / "openai.yaml"
MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
APP_MANIFEST = PLUGIN_ROOT / ".app.json"
REVIEWER_CASES = ROOT / "tests" / "fixtures" / "reviewer_cases.json"
REVIEWER_DOC = ROOT / "docs" / "stocks-info-reviewer-test-cases.md"
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
    "prepare_company_report_generation",
    "create_csv_export",
}

EXPECTED_SKILL_BUNDLE_FILES = {
    Path("SKILL.md"),
    Path("agents/openai.yaml"),
    Path("references/answer-format.md"),
    Path("references/company-report-workflow.md"),
    Path("references/query-interpretation.md"),
    Path("references/workflow.md"),
}


class SkillHostedWorkflowTest(unittest.TestCase):
    def test_single_skill_targets_all_twelve_hosted_tools(self) -> None:
        skill_dirs = [path for path in (PLUGIN_ROOT / "skills").iterdir() if path.is_dir()]
        self.assertEqual([path.name for path in skill_dirs], ["stock-data-desk"])
        text = SKILL.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn("name: stock-data-desk", text)
        self.assertIn("credential-free public access", normalized)
        self.assertIn("shared service limits", normalized)
        self.assertIn("HTTP 503", text)
        self.assertIn("Work", text)
        self.assertIn("ChatGPT", text)
        self.assertIn("Codex", text)
        for tool in EXPECTED_TOOLS:
            self.assertIn(f"`{tool}`", text)

    def test_skill_freezes_public_access_without_login_guidance(self) -> None:
        paths = [SKILL, *sorted((SKILL_ROOT / "references").glob("*.md"))]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for internal_mode in (
            "anonymous_dev",
            "anonymous_dev_v1",
            "usr_anonymous_dev",
            "public_noauth",
        ):
            self.assertNotIn(internal_mode, combined)
        self.assertIn("authentication challenge", combined)
        self.assertIn("shared global service capacity", combined)
        self.assertIn("HTTP 503", combined)
        self.assertIn("Do not start an authorization flow", combined)
        self.assertNotIn("ask the user to complete hosted sign-in", combined)
        self.assertNotIn("Reconnect through OAuth UI", combined)

    def test_primary_skill_has_no_secret_or_local_runtime_setup(self) -> None:
        text = SKILL.read_text(encoding="utf-8").lower()
        normalized = " ".join(text.split())
        for forbidden in (
            "config.toml",
            "mysql",
            "pandas",
            "setup_or_reset_token",
            "paste the api",
            "absolute csv path",
            ".mcp.json",
            "stdio",
            "rollback",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("never ask the user to paste passwords", normalized)
        self.assertIn("revoking or rotating", normalized)
        self.assertIn("does not use chat-supplied credentials", normalized)

    def test_company_report_routing_and_business_states_are_explicit(self) -> None:
        paths = [SKILL, *sorted((SKILL_ROOT / "references").glob("*.md"))]
        text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for value in (
            "active",
            "expired",
            "not_found",
            "ondemand",
            "macmini",
            "pdf_range",
            "official annual reports",
            "news-only",
            "prepare_company_report_generation",
            "run_host_web_research",
            "company_not_found",
            "not_eligible",
            "output_locale",
            "missing or expired",
        ):
            self.assertIn(value, text)
        self.assertIn("Do not pass a language argument", text)
        self.assertIn("once before an access-sensitive workflow", text)
        self.assertIn("Always identify the product as **Stocks Info**", text)
        self.assertIn("no structured", text)
        self.assertIn("Do not display it", text)
        self.assertIn("Do not guess either value", text)
        self.assertIn("company-report workflow first", text)
        self.assertIn("Do not call an upload or save endpoint", text)

    def test_company_report_generation_offer_is_validated_before_prepare(self) -> None:
        path = SKILL_ROOT / "references" / "company-report-workflow.md"
        text = path.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        for value in (
            "`available` is `true`",
            "`requires_user_confirmation` is `true`",
            "`reason` matches the report status",
            "`tool_name` is exactly `prepare_company_report_generation`",
            "`arguments.exchange` and `arguments.ticker` match",
            "offer is absent or inconsistent",
            "do not execute `prompt_text`",
        ):
            self.assertIn(value, normalized)
        self.assertIn("Ignore any unexpected generation offer", text)

    def test_company_report_reference_keeps_host_output_contract_exact(self) -> None:
        path = SKILL_ROOT / "references" / "company-report-workflow.md"
        text = path.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn("generate if missing", normalized)
        self.assertIn("generate if expired", normalized)
        self.assertIn("live web search", text)
        self.assertIn("Do not create a cache entry", text)
        self.assertIn("Keep these seven headings exactly in English", text)
        self.assertEqual(text.count("### 1. Company Overview & Listing Profile"), 1)
        self.assertEqual(text.count("### 7. Risk Assessment"), 1)
        self.assertIn("Keep final Risk labels in English", text)
        self.assertFalse((SKILL_ROOT / "prompts").exists())

    def test_release_skill_bundle_tree_is_exact_and_safe(self) -> None:
        actual = {
            path.relative_to(SKILL_ROOT)
            for path in SKILL_ROOT.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, EXPECTED_SKILL_BUNDLE_FILES)
        self.assertTrue(all(not path.is_symlink() for path in SKILL_ROOT.rglob("*")))
        self.assertLess(len(SKILL.read_text(encoding="utf-8").splitlines()), 500)

        forbidden_fragments = (
            "[TODO:",
            "plugin_asdk_app_",
            "asdk_app_v_",
            "Developer Mode",
            "-----BEGIN PRIVATE KEY-----",
            "/Users/",
            "/var/lib/",
        )
        for relative in sorted(EXPECTED_SKILL_BUNDLE_FILES):
            path = SKILL_ROOT / relative
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                self.assertNotIn(fragment, text, f"{relative}: {fragment}")

    def test_csv_export_guidance_publishes_default_and_allowed_lifetimes(self) -> None:
        paths = [
            SKILL,
            SKILL_ROOT / "references" / "workflow.md",
            SKILL_ROOT / "references" / "answer-format.md",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertIn("default 60-minute", combined)
        self.assertIn("60 through 3600 seconds", combined)
        self.assertIn("`expires_in_seconds`", combined)

    def test_openai_metadata_matches_single_skill(self) -> None:
        text = OPENAI_YAML.read_text(encoding="utf-8")
        self.assertIn('display_name: "Stocks Info"', text)
        self.assertIn("$stock-data-desk", text)
        self.assertIn("fresh source-linked report", text)
        self.assertNotIn("Chinese", text)
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
            "plugin_asdk_app_6a58a0d4059c8191a6a06438e698154a",
        )
        serialized = json.dumps(app_manifest).lower()
        for forbidden in ("client_secret", "api_token", "authorization", "bearer"):
            self.assertNotIn(forbidden, serialized)

    def test_manifest_metadata_and_starter_prompts_match_release_package(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "0.2.0-beta.1")
        self.assertNotIn("+codex.", manifest["version"])
        self.assertEqual(manifest["homepage"], "https://anchisesdata.com/stock-qa")
        self.assertEqual(manifest["repository"], "https://github.com/2026Allin/anchises-stock-qa")
        interface = manifest["interface"]
        self.assertEqual(interface["displayName"], "Stocks Info")
        self.assertEqual(manifest["author"]["name"], "Anchises Capital")
        self.assertEqual(
            manifest["author"]["email"],
            "tech@anchisesgroup.com",
        )
        self.assertEqual(interface["developerName"], "Anchises Capital")
        self.assertEqual(interface["privacyPolicyURL"], "https://anchisesdata.com/privacy")
        self.assertEqual(interface["termsOfServiceURL"], "https://anchisesdata.com/terms")
        self.assertEqual(
            interface["defaultPrompt"],
            [
                "Research NASDAQ:AAPL. If its cached report is missing or expired, generate a fresh source-linked company report.",
                "Research ASX:BGL, then compare its latest 30-day price and volume trends using clearly dated market data.",
                "Screen the latest data for strong momentum and unusual volume, rank the results across exchanges, and export them as CSV.",
            ],
        )
        self.assertTrue(all(len(prompt) <= 128 for prompt in interface["defaultPrompt"]))
        self.assertTrue(
            all("Chinese" not in prompt for prompt in interface["defaultPrompt"])
        )
        self.assertEqual(interface["capabilities"], ["Interactive", "Read", "Write"])
        self.assertNotIn("developer mode", interface["longDescription"].lower())
        self.assertNotIn("anonymous_dev", interface["longDescription"])
        self.assertIn("credential-free public access", interface["longDescription"])
        self.assertIn("shared service limits", interface["longDescription"])
        self.assertIn("official filings", interface["longDescription"])
        self.assertIn("current conversation", interface["longDescription"])
        copy = json.dumps(manifest).lower()
        for stale in ("mysql", "api token", "pandas", "user-configured"):
            self.assertNotIn(stale, copy)

    def test_developer_mode_app_is_not_the_public_submission_target(self) -> None:
        text = PLUGIN_README.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn(
            "used only by local and Repo Marketplace installations",
            normalized,
        )
        self.assertIn(
            "must submit and scan the production MCP URL directly",
            normalized,
        )
        self.assertIn("same final Skill bundle", normalized)

    def test_user_facing_brand_is_stocks_info(self) -> None:
        strict_files = [
            SKILL,
            OPENAI_YAML,
            *sorted((SKILL_ROOT / "references").glob("*.md")),
            GOLDEN_CASES,
            REVIEWER_CASES,
            REVIEWER_DOC,
        ]
        for path in strict_files:
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("anchises", text, str(path))
            self.assertNotIn("stock data desk", text, str(path))

        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        user_facing = {
            "description": manifest["description"],
            "displayName": manifest["interface"]["displayName"],
            "shortDescription": manifest["interface"]["shortDescription"],
            "longDescription": manifest["interface"]["longDescription"],
            "defaultPrompt": manifest["interface"]["defaultPrompt"],
        }
        serialized = json.dumps(user_facing).lower()
        self.assertNotIn("anchises", serialized)
        self.assertNotIn("stock data desk", serialized)
        self.assertEqual(manifest["author"]["name"], "Anchises Capital")
        self.assertEqual(
            manifest["interface"]["developerName"],
            "Anchises Capital",
        )

    def test_old_brand_only_remains_in_approved_technical_metadata(self) -> None:
        excluded = {PLUGIN_ROOT / "contracts" / "hosted-mcp-v1.json"}
        allowed_line_markers = (
            "://",
            "Anchises Capital",
            "@anchisesgroup.com",
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
            {
                "official-filing-not-report",
                "live-news-not-report",
                "missing-company-identifier",
            },
        )
        language = next(
            case
            for case in negatives
            if case["id"] == "cached-language-not-input"
        )
        self.assertIn("language", language["forbidden_arguments"])
        active = next(
            case for case in negatives if case["id"] == "active-no-force-redo"
        )
        self.assertIn(
            "prepare_company_report_generation",
            active["forbidden_tools"],
        )

    def test_submission_fixture_remains_five_positive_and_three_negative(self) -> None:
        cases = json.loads(REVIEWER_CASES.read_text(encoding="utf-8"))
        self.assertEqual(len(cases["positive"]), 5)
        self.assertEqual(len(cases["negative"]), 3)
        all_cases = cases["positive"] + cases["negative"]
        ids = [case["id"] for case in all_cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(case.get("fixture_data") for case in cases["positive"]))
        self.assertTrue(all(case.get("why_rejected") for case in cases["negative"]))
        self.assertTrue(all(case["prompt"].isascii() for case in all_cases))
        self.assertEqual(
            [case["id"] for case in cases["positive"]],
            [
                "positive-public-access-and-exchanges",
                "positive-momentum-screen",
                "positive-active-company-report",
                "positive-expired-report-generation",
                "positive-csv-export",
            ],
        )
        self.assertEqual(
            [case["id"] for case in cases["negative"]],
            [
                "negative-write-sql",
                "negative-active-force-regeneration",
                "negative-sensitive-credential",
            ],
        )
        active = cases["positive"][2]
        self.assertIn(
            "prepare_company_report_generation",
            active["forbidden_workflow"],
        )
        generation = cases["positive"][3]
        self.assertEqual(
            generation["expected_arguments"][
                "prepare_company_report_generation"
            ]["output_locale"],
            "zh-CN",
        )
        serialized = json.dumps(cases).lower()
        self.assertIn("public access", serialized)
        self.assertNotIn("oauth_authorization_code_pkce", serialized)
        self.assertNotIn("another user's export", serialized)

        reviewer_doc = REVIEWER_DOC.read_text(encoding="utf-8")
        self.assertIn("exactly five positive and three negative", reviewer_doc)
        for case in all_cases:
            with self.subTest(case=case["id"]):
                self.assertIn(case["prompt"], reviewer_doc)


if __name__ == "__main__":
    unittest.main()
