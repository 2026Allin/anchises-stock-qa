from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "anchises-analysis"
PLUGIN_README = PLUGIN_ROOT / "README.md"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "anchises-analysis"
SKILL = SKILL_ROOT / "SKILL.md"
OPENAI_YAML = SKILL_ROOT / "agents" / "openai.yaml"
MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
APP_MANIFEST = PLUGIN_ROOT / ".app.json"
CONTRACT = PLUGIN_ROOT / "contracts" / "hosted-mcp-v1.json"
GOLDEN_CASES = ROOT / "tests" / "fixtures" / "golden_prompts.json"
REVIEWER_CASES = ROOT / "tests" / "fixtures" / "reviewer_cases.json"
REVIEWER_DOC = ROOT / "docs" / "anchises-analysis-reviewer-test-cases.md"


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
    "resolve_company_identity",
    "prepare_company_report_generation",
    "create_csv_export",
}

EXPECTED_SKILL_BUNDLE_FILES = {
    Path("SKILL.md"),
    Path("agents/openai.yaml"),
    Path("references/answer-format.md"),
    Path("references/company-report-workflow.md"),
    Path("references/company-resolution.md"),
    Path("references/market-data-policy.md"),
    Path("references/mining-report-quality.md"),
    Path("references/query-interpretation.md"),
    Path("references/workflow.md"),
}


def _skill_bundle_text() -> str:
    paths = [SKILL, *sorted((SKILL_ROOT / "references").glob("*.md"))]
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def _golden_cases() -> dict:
    return json.loads(GOLDEN_CASES.read_text(encoding="utf-8"))


class SkillHostedWorkflowTest(unittest.TestCase):
    def test_single_skill_targets_all_twelve_hosted_tools(self) -> None:
        skill_dirs = [path for path in (PLUGIN_ROOT / "skills").iterdir() if path.is_dir()]
        self.assertEqual([path.name for path in skill_dirs], ["anchises-analysis"])
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("name: anchises-analysis", text)
        self.assertIn("credential-free public access", " ".join(text.split()))
        for tool in EXPECTED_TOOLS:
            self.assertIn(f"`{tool}`", text)

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
            text = (SKILL_ROOT / relative).read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                self.assertNotIn(fragment, text, f"{relative}: {fragment}")

    def test_skill_freezes_public_access_without_login_guidance(self) -> None:
        combined = " ".join(_skill_bundle_text().split())
        for internal_mode in (
            "anonymous_dev",
            "anonymous_dev_v1",
            "usr_anonymous_dev",
            "public_noauth",
        ):
            self.assertNotIn(internal_mode, combined)
        self.assertIn("authentication challenge", combined)
        self.assertIn("shared global service capacity", combined)
        self.assertIn("Do not start an authorization flow", combined)
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
            ".mcp.json",
            "stdio",
            "rollback",
        ):
            self.assertNotIn(forbidden, text)
        normalized = " ".join(text.split())
        self.assertIn("never ask the user to paste passwords", normalized)
        self.assertIn("revoking or rotating", normalized)
        self.assertIn("does not use chat-supplied credentials", normalized)

    def test_company_resolution_reference_is_complete_and_private(self) -> None:
        text = (SKILL_ROOT / "references" / "company-resolution.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join(text.split())
        for value in (
            "current request",
            "chat history",
            "the second company above",
            "Exchange issuer or instrument pages",
            "Securities-regulator records",
            "Company investor-relations pages",
            '"query": "company name or ticker"',
            '"exchange_hint": "optional exchange"',
            '"purpose": "stock_data or company_report"',
            "resolved",
            "ambiguous",
            "not_found_in_supported_markets",
            "same ticker on different exchanges",
            "share class",
            "full chat history",
        ):
            self.assertIn(value, normalized)

    def test_company_report_requests_start_live_research_without_confirmation(self) -> None:
        text = _skill_bundle_text()
        normalized = " ".join(text.split())
        self.assertIn("request itself authorizes immediate live research", normalized)
        self.assertIn("do not ask whether to generate it", normalized)
        self.assertIn("Do not read a prior stored report first", normalized)
        self.assertIn("The MCP returns a research prompt", normalized)
        self.assertIn("The Host must execute", normalized)
        self.assertIn("Do not send it back to MCP", normalized)

    def test_removed_report_state_machine_is_absent_from_skill_tests_and_examples(self) -> None:
        paths = [
            SKILL,
            *sorted((SKILL_ROOT / "references").glob("*.md")),
            GOLDEN_CASES,
            REVIEWER_CASES,
            REVIEWER_DOC,
            ROOT / "tests" / "mock_services.py",
            ROOT / "tests" / "test_mock_hosted_end_to_end.py",
            ROOT / "tests" / "test_live_hosted_contract.py",
        ]
        forbidden = (
            "get_latest_" + "company_report",
            "generation" + "_offer",
            "MCP_" + "EXPIRED_REPORT_SAMPLE",
            "pdf_" + "range",
            "pdf_" + "download_url",
            "seven-day report",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for value in forbidden:
                self.assertNotIn(value, text, f"{path.relative_to(ROOT)}: {value}")

    def test_only_company_name_can_generate_a_report(self) -> None:
        case = next(
            item for item in _golden_cases()["positive"]
            if item["id"] == "company-name-live-report"
        )
        self.assertEqual(
            case["expected_arguments"]["resolve_company_identity"],
            {"query": "Apple", "purpose": "company_report"},
        )
        self.assertEqual(
            case["expected_arguments"]["prepare_company_report_generation"],
            {
                "exchange": "NASDAQ",
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "output_locale": "zh-CN",
            },
        )

    def test_only_ticker_can_generate_a_report(self) -> None:
        case = next(
            item for item in _golden_cases()["positive"]
            if item["id"] == "ticker-only-live-report"
        )
        self.assertEqual(
            case["expected_arguments"]["resolve_company_identity"]["query"],
            "AAPL",
        )
        self.assertIn("company_name", case["expected_arguments"]["prepare_company_report_generation"])

    def test_prior_chat_reference_can_generate_a_report(self) -> None:
        case = next(
            item for item in _golden_cases()["positive"]
            if item["id"] == "context-reference-live-report"
        )
        self.assertIn("resolve_company_identity", case["expected_tools"])
        self.assertIn("never send the full conversation", case["expected_behavior"])
        self.assertIn("this company", _skill_bundle_text())

    def test_company_name_resolves_before_stock_data(self) -> None:
        case = next(
            item for item in _golden_cases()["positive"]
            if item["id"] == "company-name-stock-data"
        )
        self.assertEqual(case["expected_tools"][0], "resolve_company_identity")
        self.assertIn("canonical NASDAQ and AAPL", case["expected_behavior"])

    def test_cross_market_ticker_does_not_silently_resolve(self) -> None:
        case = next(
            item for item in _golden_cases()["negative"]
            if item["id"] == "cross-market-ticker-ambiguous"
        )
        self.assertEqual(case["expected_tools"], ["resolve_company_identity"])
        self.assertIn("screen_stocks", case["forbidden_tools"])
        self.assertIn("ASX and NYSE", case["expected_behavior"])

    def test_multiple_share_classes_do_not_silently_resolve(self) -> None:
        case = next(
            item for item in _golden_cases()["negative"]
            if item["id"] == "share-class-ambiguous"
        )
        self.assertIn("GOOG or GOOGL", case["expected_behavior"])
        self.assertIn("screen_stocks", case["forbidden_tools"])

    def test_external_market_company_can_receive_live_report(self) -> None:
        case = next(
            item for item in _golden_cases()["positive"]
            if item["id"] == "external-market-live-report"
        )
        prepare = case["expected_arguments"]["prepare_company_report_generation"]
        self.assertEqual(
            prepare,
            {
                "exchange": "LSE",
                "ticker": "RIO",
                "company_name": "Rio Tinto plc",
                "output_locale": "en",
            },
        )
        self.assertIn("identity_source=host_supplied", case["expected_behavior"])

    def test_external_market_stock_data_states_coverage_limit(self) -> None:
        case = next(
            item for item in _golden_cases()["negative"]
            if item["id"] == "external-market-stock-data-limit"
        )
        self.assertIn("run_readonly_sql", case["forbidden_tools"])
        self.assertIn("ASX, CSE, NASDAQ, NYSE, TSX, and TSXV", case["expected_behavior"])

    def test_inactive_or_delisted_company_still_uses_live_research(self) -> None:
        case = next(
            item for item in _golden_cases()["positive"]
            if item["id"] == "inactive-company-live-report"
        )
        self.assertIn("prepare_company_report_generation", case["expected_tools"])
        self.assertIn("delisting status", case["expected_behavior"])
        self.assertIn("selected_sector=Others", _skill_bundle_text())

    def test_fund_stops_on_not_eligible(self) -> None:
        case = next(
            item for item in _golden_cases()["negative"]
            if item["id"] == "fund-not-eligible"
        )
        self.assertIn("not_eligible", case["expected_behavior"])
        self.assertIn("do not execute prompt_text", case["expected_behavior"])

    def test_ready_executes_hidden_prompt_instead_of_returning_it(self) -> None:
        report = (SKILL_ROOT / "references" / "company-report-workflow.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("return the completed report, not the prompt", report)
        self.assertIn("Do not expose `prompt_text`", report)
        self.assertIn("live web search", report)
        self.assertEqual(report.count("### 1. Company Overview & Listing Profile"), 1)
        self.assertEqual(report.count("### 7. Risk Assessment"), 1)
        self.assertIn("`**Summary:**`", report)
        self.assertIn("`**[Risk: Low]**`", report)

    def test_no_web_search_never_falls_back_to_model_memory(self) -> None:
        combined = " ".join(_skill_bundle_text().split())
        self.assertIn("If live web search is unavailable", combined)
        self.assertIn("do not generate from model memory", combined)
        self.assertIn("do not rely on model memory", combined)
        case = next(
            item for item in _golden_cases()["negative"]
            if item["id"] == "external-no-web-verification"
        )
        self.assertIn("invent the exchange, ticker, or company name", case["expected_behavior"])

    def test_report_is_not_persisted_or_written_back(self) -> None:
        combined = " ".join(_skill_bundle_text().split())
        self.assertIn("Return the finished report only in the current conversation", combined)
        self.assertIn("Do not send it back to MCP", combined)
        self.assertIn("Do not send the result to MCP", combined)
        self.assertIn("claim it was saved, uploaded, or published", combined)

    def test_mining_quality_covers_cash_debt_and_warrants(self) -> None:
        text = (SKILL_ROOT / "references" / "mining-report-quality.md").read_text(
            encoding="utf-8"
        )
        text = " ".join(text.split())
        for value in (
            "cash and cash equivalents",
            "short- and long-term debt",
            "net cash or net debt",
            "estimated runway",
            "fully diluted share count",
            "warrants outstanding and exercisable",
            "expiry ladder",
            "potential exercise proceeds",
            "funding gap",
            "12 to 24 months",
            "Do not double-count",
        ):
            self.assertIn(value, text)

    def test_contract_snapshot_has_new_twelve_tool_shape(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        names = [tool["name"] for tool in contract["tools"]]
        self.assertEqual(len(names), 12)
        self.assertEqual(set(names), EXPECTED_TOOLS)
        self.assertEqual(contract["source"]["server_name"], "Anchises Analysis")
        self.assertEqual(contract["contract_version"], "1.6.0-draft")
        self.assertEqual(contract["source"]["server_version"], "0.6.0")
        self.assertEqual(contract["source"]["sync_state"], "live")
        self.assertRegex(contract["source"]["descriptor_sha256"], r"^[0-9a-f]{64}$")

    def test_prepare_snapshot_requires_four_fields_and_prompt_5_1(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        tool = next(
            item for item in contract["tools"]
            if item["name"] == "prepare_company_report_generation"
        )
        self.assertEqual(
            set(tool["inputSchema"]["required"]),
            {"exchange", "ticker", "company_name", "output_locale"},
        )
        data = tool["outputSchema"]["properties"]["data"]["properties"]
        self.assertEqual(data["prompt_version"]["enum"], ["5.1", None])
        self.assertEqual(data["identity_source"]["enum"], ["master", "host_supplied"])
        self.assertEqual(
            data["next_action"]["enum"],
            ["run_host_web_research", None],
        )

    def test_csv_export_guidance_publishes_default_and_allowed_lifetimes(self) -> None:
        combined = " ".join(_skill_bundle_text().split())
        self.assertIn("default 60-minute", combined)
        self.assertIn("60 through 3600 seconds", combined)
        self.assertIn("`expires_in_seconds`", combined)
        self.assertIn("1,000 rows", combined)
        self.assertIn("25 total columns", combined)
        self.assertIn("20,000", combined)
        self.assertIn("50 tickers", combined)
        self.assertIn("at most 22 additional fields", combined)

    def test_market_data_policy_uses_only_the_new_export_gate(self) -> None:
        combined = " ".join(_skill_bundle_text().split())
        self.assertIn("data.export_policy.eligible_by_query", combined)
        self.assertIn("Never read or infer eligibility from a legacy `eligible` field", combined)
        self.assertNotIn("current screen or SQL workflow", combined)
        self.assertIn("Never export a SQL query ID", combined)
        self.assertIn("page.next_cursor` is always null", combined)
        self.assertIn("Do not retrieve row 201 onward", combined)
        self.assertIn("Do not evade a refusal by splitting fields", combined)

    def test_policy_errors_have_safe_recovery_instructions(self) -> None:
        combined = _skill_bundle_text()
        for code in (
            "export_requires_selective_query",
            "export_row_limit_exceeded",
            "export_column_limit_exceeded",
            "export_cell_limit_exceeded",
            "export_complete_partition_not_allowed",
            "export_top_n_limit_exceeded",
            "export_ticker_limit_exceeded",
            "query_not_exportable",
            "query_policy_expired",
            "query_partition_limit_exceeded",
            "query_requires_bounded_analysis",
            "result_too_large",
            "temporarily_unavailable",
        ):
            self.assertIn(f"`{code}`", combined)
        self.assertIn("rerun the original structured screen", combined)
        self.assertIn("download is temporarily unavailable", combined)

    def test_normal_analyst_requests_are_policy_transparent(self) -> None:
        cases = _golden_cases()
        all_cases = cases["positive"] + cases["negative"]
        by_id = {case["id"]: case for case in all_cases}
        required = {
            "structured-screen",
            "nasdaq-dollar-volume-top-100",
            "watchlist-40-tickers",
            "single-stock-one-year",
            "historical-sql-fallback",
            "broad-result-preview",
            "csv-export",
            "complete-row-table-no-pagination",
            "complete-partition-export-rejected",
            "sql-query-not-exportable",
            "query-policy-expired",
        }
        self.assertTrue(required.issubset(by_id))
        self.assertIn("without leading with export-policy language", by_id["structured-screen"]["expected_behavior"])
        self.assertEqual(
            by_id["nasdaq-dollar-volume-top-100"]["expected_arguments"][
                "screen_stocks"
            ]["top_n"],
            100,
        )
        self.assertIn("40 values", by_id["watchlist-40-tickers"]["expected_behavior"])
        self.assertIn("paired start_date and end_date", by_id["single-stock-one-year"]["expected_behavior"])
        self.assertIn("no next page", by_id["broad-result-preview"]["expected_behavior"])

    def test_openai_metadata_matches_renamed_skill(self) -> None:
        text = OPENAI_YAML.read_text(encoding="utf-8")
        self.assertIn('display_name: "Anchises Analysis"', text)
        self.assertIn("$anchises-analysis", text)
        self.assertIn("NASDAQ Top 100 by dollar volume", text)
        self.assertIn("field-selected research subset", text)
        self.assertIn("allow_implicit_invocation: true", text)

    def test_manifest_connects_same_app_id_with_renamed_key(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        app_manifest = json.loads(APP_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "anchises-analysis")
        self.assertEqual(manifest["apps"], "./.app.json")
        self.assertNotIn("mcpServers", manifest)
        self.assertEqual(set(app_manifest["apps"]), {"anchises_analysis"})
        self.assertEqual(
            app_manifest["apps"]["anchises_analysis"]["id"],
            "plugin_asdk_app_6a58a0d4059c8191a6a06438e698154a",
        )
        serialized = json.dumps(app_manifest).lower()
        for forbidden in ("client_secret", "api_token", "authorization", "bearer"):
            self.assertNotIn(forbidden, serialized)

    def test_manifest_metadata_and_starter_prompts_match_release(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "0.4.0-beta.1")
        self.assertNotIn("+codex.", manifest["version"])
        self.assertEqual(manifest["author"]["name"], "Anchises Capital")
        interface = manifest["interface"]
        self.assertEqual(interface["displayName"], "Anchises Analysis")
        self.assertEqual(interface["developerName"], "Anchises Capital")
        self.assertEqual(
            interface["defaultPrompt"],
            [
                "Research Apple, verify its primary listing, and generate a fresh source-linked company report.",
                "Analyze NYSE advance/decline counts, averages, and distributions using the full market.",
                "Rank the NASDAQ Top 100 by dollar volume and export only the key research fields as CSV.",
            ],
        )
        self.assertTrue(all(len(prompt) <= 128 for prompt in interface["defaultPrompt"]))
        self.assertIn("ASX, CSE, NASDAQ, NYSE, TSX, and TSXV", interface["longDescription"])
        self.assertIn("does not persist", interface["longDescription"])
        self.assertIn("first 200 rows", interface["longDescription"])
        self.assertIn("no subsequent row-level pages", interface["longDescription"])
        self.assertIn("selective small research subsets", interface["longDescription"])
        self.assertIn("rather than a market-percentage limit", interface["longDescription"])
        self.assertIn("no account-linked cross-session cumulative budget", interface["longDescription"])

    def test_developer_mode_app_is_not_public_submission_target(self) -> None:
        normalized = " ".join(PLUGIN_README.read_text(encoding="utf-8").split())
        self.assertIn("used only by local and Repo Marketplace installations", normalized)
        self.assertIn("must submit and scan the production MCP URL directly", normalized)
        self.assertIn("same final Skill bundle", normalized)

    def test_submission_fixture_remains_five_positive_and_three_negative(self) -> None:
        cases = json.loads(REVIEWER_CASES.read_text(encoding="utf-8"))
        self.assertEqual(len(cases["positive"]), 5)
        self.assertEqual(len(cases["negative"]), 3)
        all_cases = cases["positive"] + cases["negative"]
        self.assertEqual(len({case["id"] for case in all_cases}), 8)
        self.assertTrue(all(case["prompt"].isascii() for case in all_cases))
        self.assertTrue(all(case.get("fixture_data") for case in cases["positive"]))
        self.assertTrue(all(case.get("why_rejected") for case in cases["negative"]))
        reviewer_doc = REVIEWER_DOC.read_text(encoding="utf-8")
        self.assertIn("exactly five positive and three negative", reviewer_doc)
        for case in all_cases:
            self.assertIn(case["prompt"], reviewer_doc)

    def test_golden_prompts_cover_all_tools_and_required_scenarios(self) -> None:
        cases = _golden_cases()
        all_cases = cases["positive"] + cases["negative"]
        covered = {
            tool
            for case in all_cases
            for tool in case.get("expected_tools", [])
        }
        self.assertEqual(covered, EXPECTED_TOOLS)
        self.assertEqual({case["category"] for case in all_cases}, {"direct", "indirect", "negative"})
        required_ids = {
            "company-name-live-report",
            "ticker-only-live-report",
            "context-reference-live-report",
            "company-name-stock-data",
            "cross-market-ticker-ambiguous",
            "share-class-ambiguous",
            "external-market-live-report",
            "external-market-stock-data-limit",
            "inactive-company-live-report",
            "fund-not-eligible",
            "external-no-web-verification",
            "mining-financial-quality",
            "nasdaq-dollar-volume-top-100",
            "watchlist-40-tickers",
            "single-stock-one-year",
            "broad-result-preview",
            "complete-row-table-no-pagination",
            "complete-partition-export-rejected",
            "sql-query-not-exportable",
            "query-policy-expired",
        }
        self.assertTrue(required_ids.issubset({case["id"] for case in all_cases}))


if __name__ == "__main__":
    unittest.main()
