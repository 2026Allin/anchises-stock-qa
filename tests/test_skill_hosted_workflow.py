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
BRIEF_SKILL_ROOT = PLUGIN_ROOT / "skills" / "company-brief"
BRIEF_SKILL = BRIEF_SKILL_ROOT / "SKILL.md"
BRIEF_OPENAI_YAML = BRIEF_SKILL_ROOT / "agents" / "openai.yaml"
REPORT_SKILL_ROOT = PLUGIN_ROOT / "skills" / "company-report"
REPORT_SKILL = REPORT_SKILL_ROOT / "SKILL.md"
REPORT_OPENAI_YAML = REPORT_SKILL_ROOT / "agents" / "openai.yaml"
COMPARISON_SKILL_ROOT = PLUGIN_ROOT / "skills" / "company-comparison"
COMPARISON_SKILL = COMPARISON_SKILL_ROOT / "SKILL.md"
COMPARISON_OPENAI_YAML = COMPARISON_SKILL_ROOT / "agents" / "openai.yaml"
MARKET_SKILL_ROOT = PLUGIN_ROOT / "skills" / "market-analysis"
MARKET_SKILL = MARKET_SKILL_ROOT / "SKILL.md"
MARKET_OPENAI_YAML = MARKET_SKILL_ROOT / "agents" / "openai.yaml"
MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
MCP_MANIFEST = PLUGIN_ROOT / ".mcp.json"
LEGACY_APP_MANIFEST = PLUGIN_ROOT / ".app.json"
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
    Path("references/common-errors.md"),
    Path("references/plugin-release.json"),
    Path("references/company-introductions.md"),
    Path("references/company-resolution.md"),
    Path("references/global-contract.md"),
    Path("references/query-interpretation.md"),
    Path("references/plugin-update.md"),
    Path("references/response-finalization.md"),
    Path("references/service-access.md"),
    Path("scripts/check_plugin_update.py"),
    Path("scripts/update_installed_plugin.py"),
}

EXPECTED_BRIEF_SKILL_BUNDLE_FILES = {
    Path("SKILL.md"),
    Path("agents/openai.yaml"),
}

EXPECTED_REPORT_SKILL_BUNDLE_FILES = {
    Path("SKILL.md"),
    Path("agents/openai.yaml"),
    Path("references/mining-report-quality.md"),
    Path("references/report-format.md"),
    Path("references/report-workflow.md"),
}

EXPECTED_COMPARISON_SKILL_BUNDLE_FILES = {
    Path("SKILL.md"),
    Path("agents/openai.yaml"),
    Path("references/comparison-format.md"),
    Path("references/comparison-workflow.md"),
}

EXPECTED_MARKET_SKILL_BUNDLE_FILES = {
    Path("SKILL.md"),
    Path("agents/openai.yaml"),
    Path("references/market-answer-format.md"),
    Path("references/market-data-policy.md"),
    Path("references/market-workflow.md"),
}

SKILL_ROOTS = {
    "anchises-analysis": SKILL_ROOT,
    "company-brief": BRIEF_SKILL_ROOT,
    "company-report": REPORT_SKILL_ROOT,
    "company-comparison": COMPARISON_SKILL_ROOT,
    "market-analysis": MARKET_SKILL_ROOT,
}

EXPECTED_BUNDLE_FILES = {
    "anchises-analysis": EXPECTED_SKILL_BUNDLE_FILES,
    "company-brief": EXPECTED_BRIEF_SKILL_BUNDLE_FILES,
    "company-report": EXPECTED_REPORT_SKILL_BUNDLE_FILES,
    "company-comparison": EXPECTED_COMPARISON_SKILL_BUNDLE_FILES,
    "market-analysis": EXPECTED_MARKET_SKILL_BUNDLE_FILES,
}


def _bundle_text(root: Path) -> str:
    paths = [root / "SKILL.md", *sorted((root / "references").glob("*.md"))]
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def _skill_bundle_text() -> str:
    return "\n".join(_bundle_text(root) for root in SKILL_ROOTS.values())


def _brief_skill_bundle_text() -> str:
    return _bundle_text(BRIEF_SKILL_ROOT)


def _golden_cases() -> dict:
    return json.loads(GOLDEN_CASES.read_text(encoding="utf-8"))


class SkillHostedWorkflowTest(unittest.TestCase):
    def test_five_skills_share_the_existing_hosted_mcp_contract(self) -> None:
        skill_dirs = sorted(
            path.name
            for path in (PLUGIN_ROOT / "skills").iterdir()
            if path.is_dir()
        )
        self.assertEqual(
            skill_dirs,
            [
                "anchises-analysis",
                "company-brief",
                "company-comparison",
                "company-report",
                "market-analysis",
            ],
        )
        combined = _skill_bundle_text()
        self.assertIn("credential-free public service", " ".join(combined.split()))
        for tool in EXPECTED_TOOLS:
            self.assertIn(f"`{tool}`", combined)

        for name, root in SKILL_ROOTS.items():
            self.assertIn(
                f"name: {name}",
                (root / "SKILL.md").read_text(encoding="utf-8"),
            )

        brief = BRIEF_SKILL.read_text(encoding="utf-8")
        intro_component = (
            SKILL_ROOT / "references" / "company-introductions.md"
        ).read_text(encoding="utf-8")
        brief_normalized = " ".join((brief + intro_component).split())
        self.assertIn("`get_connection_status`", brief)
        self.assertIn("`resolve_company_identity`", intro_component)
        self.assertIn(
            "Do not call `prepare_company_report_generation`",
            brief_normalized,
        )
        self.assertIn(
            "only plugin Skill allowed to call `prepare_company_report_generation`",
            " ".join(REPORT_SKILL.read_text(encoding="utf-8").split()),
        )
        self.assertIn(
            "must never call that tool",
            " ".join(COMPARISON_SKILL.read_text(encoding="utf-8").split()),
        )
        self.assertIn(
            "Never call `prepare_company_report_generation`",
            _bundle_text(MARKET_SKILL_ROOT),
        )

    def test_release_skill_bundle_trees_are_exact_and_safe(self) -> None:
        forbidden_fragments = (
            "[TODO:",
            "plugin_asdk_app_",
            "asdk_app_v_",
            "Developer Mode",
            "-----BEGIN PRIVATE KEY-----",
            "/Users/",
            "/var/lib/",
        )
        for name, root in SKILL_ROOTS.items():
            expected = EXPECTED_BUNDLE_FILES[name]
            actual = {
                path.relative_to(root)
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(actual, expected)
            self.assertTrue(all(not path.is_symlink() for path in root.rglob("*")))
            self.assertLess(
                len((root / "SKILL.md").read_text(encoding="utf-8").splitlines()),
                500,
            )
            for relative in sorted(expected):
                text = (root / relative).read_text(encoding="utf-8")
                for fragment in forbidden_fragments:
                    self.assertNotIn(
                        fragment,
                        text,
                        f"{root.name}/{relative}: {fragment}",
                    )

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
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                SKILL,
                *sorted(
                    path
                    for path in (SKILL_ROOT / "references").glob("*.md")
                    if path.name != "plugin-update.md"
                ),
            ]
        ).lower()
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

    def test_all_five_skills_share_one_tag_based_update_protocol(self) -> None:
        for name, root in SKILL_ROOTS.items():
            skill = (root / "SKILL.md").read_text(encoding="utf-8")
            normalized = " ".join(skill.split())
            self.assertIn("plugin-update.md", skill, name)
            self.assertIn("get_connection_status", skill, name)
            self.assertIn("tag checker", normalized, name)
            self.assertIn("exactly once", normalized, name)
            self.assertIn("plugin_update_check", skill, name)
            self.assertIn("with `{}`", skill, name)
            self.assertNotIn("client_update", skill, name)

        protocol = (
            SKILL_ROOT / "references" / "plugin-update.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(protocol.split())
        for transition in (
            "idle",
            "tag_check",
            "update_available",
            "explicit_authorization",
            "tag_recheck",
            "preflight",
            "marketplace_upgrade",
            "plugin_install",
            "verification",
            "new_task_required",
        ):
            self.assertIn(transition, protocol)
        self.assertIn("请为我安装 Anchises Analysis 更新。", protocol)
        self.assertIn("A bare “是”", normalized)
        self.assertIn("Silence never authorizes work", normalized)
        self.assertIn("A message unrelated to Anchises Analysis", normalized)
        self.assertIn("Do not persist an ignored release", normalized)
        self.assertIn("anchises-analysis/codex/v*", protocol)
        self.assertIn("remote `main` head", protocol)
        for command in (
            "codex plugin list --json",
            "codex plugin marketplace list --json",
            "codex plugin marketplace upgrade Anchises-Analysis --json",
            "codex plugin add anchises-analysis@Anchises-Analysis --json",
        ):
            self.assertIn(command, protocol)
        for forbidden_method in (
            "`git pull`",
            "`git clone`",
            "uninstall-first",
            "`config.toml`",
            "rollback",
        ):
            self.assertIn(forbidden_method, protocol)

        finalizer = (
            SKILL_ROOT / "references" / "response-finalization.md"
        ).read_text(encoding="utf-8")
        self.assertIn("operational update footer", finalizer)
        self.assertIn("final sentence of the business answer", finalizer)

    def test_plugin_release_metadata_is_closed_and_distribution_allowlisted(self) -> None:
        release = json.loads(
            (
                SKILL_ROOT / "references" / "plugin-release.json"
            ).read_text(encoding="utf-8")
        )
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
        self.assertEqual(release["version"], "0.6.0-dev.6")
        self.assertRegex(release["release_id"], r"^codex\.\d{14}$")
        self.assertEqual(release["git_ref"], "main")
        self.assertEqual(release["tag_prefix"], "anchises-analysis/codex/v")
        self.assertEqual(release["marketplace"], "Anchises-Analysis")
        self.assertEqual(
            release["repository"],
            "https://github.com/2026Allin/anchises-stock-qa.git",
        )
        protocol = (
            SKILL_ROOT / "references" / "plugin-update.md"
        ).read_text(encoding="utf-8")
        self.assertIn(release["repository"], protocol)
        self.assertIn(release["tag_prefix"], protocol)

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
        text = _bundle_text(REPORT_SKILL_ROOT)
        normalized = " ".join(text.split())
        self.assertIn("explicit report request authorizes immediate live research", normalized)
        self.assertIn("do not ask whether to generate it", normalized)
        self.assertIn("Do not read a prior stored report first", normalized)
        self.assertIn("The MCP returns a research prompt", normalized)
        self.assertIn("The Host must execute", normalized)
        self.assertIn("Do not send the report back to MCP", normalized)

    def test_primary_task_arbitration_is_canonical_and_one_way(self) -> None:
        interpretation = (
            SKILL_ROOT / "references" / "query-interpretation.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(interpretation.split())
        self.assertIn("Classify an in-scope request into exactly one `primary_task`", normalized)
        for task in (
            "company_brief",
            "full_report",
            "news",
            "comparison",
            "market_data",
            "discovery",
            "ambiguous",
        ):
            self.assertIn(task, interpretation)
        self.assertIn("only source of task arbitration", normalized)
        self.assertIn("do not reclassify", normalized.lower())
        self.assertIn("modifiers", interpretation)
        self.assertIn("entities", interpretation)
        self.assertIn("presentation policies", interpretation)
        self.assertIn("finalize the response", interpretation)

        main = " ".join(SKILL.read_text(encoding="utf-8").split())
        market_workflow = " ".join(
            (MARKET_SKILL_ROOT / "references" / "market-workflow.md")
            .read_text(encoding="utf-8")
            .split()
        )
        report = " ".join(
            (REPORT_SKILL_ROOT / "references" / "report-workflow.md")
            .read_text(encoding="utf-8")
            .split()
        )
        brief = " ".join(BRIEF_SKILL.read_text(encoding="utf-8").split())
        comparison = " ".join(COMPARISON_SKILL.read_text(encoding="utf-8").split())
        market = " ".join(MARKET_SKILL.read_text(encoding="utf-8").split())
        self.assertIn("references/query-interpretation.md", main)
        self.assertIn("Do not reclassify the request here", market_workflow)
        self.assertIn("Do not reclassify it here", report)
        for specialist in (brief, comparison, market):
            self.assertIn(
                "../anchises-analysis/references/query-interpretation.md",
                specialist,
            )
        for root in SKILL_ROOTS.values():
            skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
            if root == SKILL_ROOT:
                self.assertIn("references/global-contract.md", skill_text)
            else:
                self.assertIn(
                    "../anchises-analysis/references/global-contract.md",
                    skill_text,
                )
        self.assertNotIn("company profiles", SKILL.read_text(encoding="utf-8").lower())

    def test_specialized_skills_have_disjoint_execution_ownership(self) -> None:
        report = " ".join(_bundle_text(REPORT_SKILL_ROOT).split())
        comparison = " ".join(_bundle_text(COMPARISON_SKILL_ROOT).split())
        market = " ".join(_bundle_text(MARKET_SKILL_ROOT).split())
        brief = " ".join(_bundle_text(BRIEF_SKILL_ROOT).split())

        self.assertIn("Proceed only when `primary_task=full_report`", report)
        self.assertIn("Proceed only when `primary_task=comparison`", comparison)
        self.assertIn("`primary_task=market_data`", market)
        self.assertIn("`primary_task` is `company_brief`", brief)

        self.assertIn("Call `prepare_company_report_generation` directly", report)
        self.assertNotIn(
            "Call `prepare_company_report_generation` directly",
            "\n".join((brief, comparison, market)),
        )
        self.assertIn("must never call that tool", comparison)
        self.assertIn(
            "Never call `prepare_company_report_generation`",
            market,
        )

    def test_core_is_a_thin_coordinator_not_a_specialist_executor(self) -> None:
        core = " ".join(SKILL.read_text(encoding="utf-8").split())
        self.assertIn("thin coordination entry", core)
        self.assertIn("This Skill coordinates", core)
        self.assertIn("does not duplicate the specialized delivery workflows", core)
        self.assertNotIn("## Generate a live company report", core)
        self.assertNotIn("## Analyze stock data", core)

    def test_shared_company_introduction_contract_is_bounded_and_non_recursive(self) -> None:
        text = (
            SKILL_ROOT / "references" / "company-introductions.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        for value in (
            "current_intro_batch = ordered_intro_entities[0:5]",
            "remaining_intro_entities = ordered_intro_entities[5:]",
            "Research and write introductions only for `current_intro_batch`",
            "exactly three or four prose sentences",
            "most recent 90 days",
            "most recent 12 months",
            "material independent news item",
            "Do not reorder by perceived importance",
            "Do not scan the full conversation",
            "Do not add customers, suppliers, competitors",
            "does not authorize `prepare_company_report_generation`",
        ):
            self.assertIn(value, normalized)

    def test_global_finalization_contract_handles_all_response_states(self) -> None:
        text = " ".join(
            (
                SKILL_ROOT / "references" / "response-finalization.md"
            ).read_text(encoding="utf-8").split()
        )
        self.assertIn(
            "one continuation question, then one semantic question",
            text,
        )
        self.assertIn(
            "exactly one semantic question",
            text,
        )
        self.assertIn("may concern only `current_intro_batch`", text)
        self.assertIn("two most recent assistant messages", text)
        self.assertIn("suggestions_allowed=false", text)
        self.assertIn("no semantic question; give safe recovery guidance", text)
        self.assertIn("`mechanical_result`", text)
        self.assertIn("must be the final sentence", text)

    def test_global_policies_have_single_canonical_sources(self) -> None:
        combined = _skill_bundle_text()
        self.assertEqual(
            combined.count(
                "current_intro_batch = ordered_intro_entities[0:5]"
            ),
            1,
        )
        self.assertEqual(
            combined.count(
                "remaining_intro_entities = ordered_intro_entities[5:]"
            ),
            1,
        )
        self.assertFalse(
            (SKILL_ROOT / "references" / "common-follow-up.md").exists()
        )
        for root in SKILL_ROOTS.values():
            skill = (root / "SKILL.md").read_text(encoding="utf-8")
            if root == SKILL_ROOT:
                self.assertIn("references/response-finalization.md", skill)
            else:
                self.assertIn(
                    "../anchises-analysis/references/response-finalization.md",
                    skill,
                )

    def test_removed_report_state_machine_is_absent_from_skill_tests_and_examples(self) -> None:
        paths = [
            *[
                path
                for root in SKILL_ROOTS.values()
                for path in (
                    root / "SKILL.md",
                    *sorted((root / "references").glob("*.md")),
                )
            ],
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

    def test_company_brief_golden_cases_cover_scope_batching_and_modifiers(self) -> None:
        cases = _golden_cases()
        all_cases = cases["positive"] + cases["negative"]
        by_id = {case["id"]: case for case in all_cases}

        brief_ids = {
            "company-brief-three",
            "company-brief-context-reference",
            "company-brief-eight",
            "company-brief-user-priority",
            "company-brief-news-modifier",
            "company-brief-no-suggestions-with-remaining",
            "company-brief-no-suggestions-complete",
        }
        for case_id in brief_ids:
            case = by_id[case_id]
            self.assertEqual(case["expected_primary_task"], "company_brief")
            self.assertIn("resolve_company_identity", case["expected_tools"])
            self.assertIn(
                "prepare_company_report_generation",
                case["forbidden_tools"],
            )

        eight = by_id["company-brief-eight"]["expected_behavior"]
        for company in (
            "Apple",
            "NVIDIA",
            "AMD",
            "Intel",
            "TSMC",
            "ASML",
            "Broadcom",
            "Qualcomm",
        ):
            self.assertIn(company, eight)
        self.assertIn("exactly one continuation question", eight)
        self.assertIn("one semantic question", eight)
        self.assertIn(
            "omit the optional semantic question",
            by_id["company-brief-no-suggestions-with-remaining"][
                "expected_behavior"
            ],
        )
        self.assertEqual(
            by_id["company-brief-no-suggestions-complete"][
                "expected_output_contract"
            ]["semantic_questions"],
            0,
        )
        self.assertIn(
            "AMD, Apple, then NVIDIA",
            by_id["company-brief-user-priority"]["expected_behavior"],
        )
        self.assertIn(
            "rather than reclassifying the request as news-only",
            by_id["company-brief-news-modifier"]["expected_behavior"],
        )

    def test_context_and_incidental_mentions_do_not_force_company_briefs(self) -> None:
        cases = _golden_cases()
        all_cases = cases["positive"] + cases["negative"]
        by_id = {case["id"]: case for case in all_cases}
        comparison = by_id["context-comparison-not-brief"]
        discovery = by_id["incidental-company-list-not-brief"]
        self.assertEqual(comparison["expected_primary_task"], "comparison")
        self.assertEqual(discovery["expected_primary_task"], "discovery")
        self.assertIn(
            "prepare_company_report_generation",
            comparison["forbidden_tools"],
        )
        self.assertIn(
            "prepare_company_report_generation",
            discovery["forbidden_tools"],
        )
        self.assertIn(
            "contextual reference as the entity source",
            comparison["expected_behavior"],
        )
        self.assertIn(
            "without automatically expanding every company",
            discovery["expected_behavior"],
        )

    def test_golden_routes_cover_all_five_skill_entries(self) -> None:
        cases = _golden_cases()
        by_id = {
            case["id"]: case
            for case in cases["positive"] + cases["negative"]
        }
        expected_routes = {
            "ambiguous-company-request-routes-to-core": "anchises-analysis",
            "company-brief-three": "company-brief",
            "company-name-live-report": "company-report",
            "company-comparison-business-context": "company-comparison",
            "structured-screen": "market-analysis",
        }
        for case_id, expected_skill in expected_routes.items():
            self.assertEqual(by_id[case_id]["expected_skill"], expected_skill)

        self.assertEqual(
            by_id["mixed-company-and-market-analysis"]["expected_primary_task"],
            "full_report",
        )
        self.assertEqual(
            by_id["mixed-company-and-market-analysis"]["expected_skill"],
            "company-report",
        )
        self.assertEqual(
            by_id["market-discovery"]["expected_skill"],
            "market-analysis",
        )

    def test_comparison_set_does_not_inherit_introduction_window(self) -> None:
        case = next(
            item
            for item in _golden_cases()["positive"]
            if item["id"] == "company-comparison-six-no-brief-window"
        )
        self.assertEqual(case["expected_primary_task"], "comparison")
        self.assertEqual(case["expected_skill"], "company-comparison")
        self.assertIn(
            "Do not apply the standalone introduction window",
            case["expected_behavior"],
        )
        comparison = " ".join(COMPARISON_SKILL.read_text(encoding="utf-8").split())
        self.assertIn(
            "standalone company-introduction window does not limit",
            comparison,
        )
        self.assertIn("Never silently compare only the first five", comparison)

    def test_market_screen_with_introductions_keeps_table_and_batches_profiles(self) -> None:
        by_id = {
            case["id"]: case
            for cases in _golden_cases().values()
            for case in cases
        }
        case = by_id["market-screen-with-company-introductions"]
        self.assertEqual(case["expected_primary_task"], "market_data")
        self.assertEqual(case["expected_skill"], "market-analysis")
        self.assertIn("screen_stocks", case["expected_tools"])
        self.assertIn("resolve_company_identity", case["expected_tools"])
        contract = case["expected_output_contract"]
        self.assertTrue(contract["quantitative_result_not_capped"])
        self.assertEqual(contract["max_introduction_blocks"], 5)
        self.assertEqual(contract["continuation_questions"], 1)
        self.assertEqual(contract["semantic_questions"], 1)

        market = " ".join(MARKET_SKILL.read_text(encoding="utf-8").split())
        self.assertIn("company_introductions=true", market)
        self.assertIn("Keep the full quantitative result", market)
        self.assertIn("five-company window only to the standalone introduction section", market)
        self.assertIn("Do not rerun the screen", market)

    def test_comparison_with_standalone_introductions_has_two_scopes(self) -> None:
        case = next(
            item
            for item in _golden_cases()["positive"]
            if item["id"] == "company-comparison-with-standalone-introductions"
        )
        contract = case["expected_output_contract"]
        self.assertEqual(contract["comparison_entities"], "all")
        self.assertEqual(contract["max_introduction_blocks"], 5)
        self.assertEqual(contract["continuation_questions"], 1)
        self.assertIn("current_intro_batch", COMPARISON_SKILL.read_text(encoding="utf-8"))

    def test_market_introduction_continuation_reuses_prior_result(self) -> None:
        case = next(
            item
            for item in _golden_cases()["positive"]
            if item["id"] == "market-introduction-continuation"
        )
        self.assertIn("resolve_company_identity", case["expected_tools"])
        self.assertIn("screen_stocks", case["forbidden_tools"])
        self.assertIn("data_date", case["expected_behavior"])

    def test_direct_specialist_invocation_cannot_bypass_global_contract(self) -> None:
        case = next(
            item
            for item in _golden_cases()["positive"]
            if item["id"] == "direct-market-skill-with-company-introductions"
        )
        self.assertEqual(case["expected_skill"], "market-analysis")
        self.assertEqual(
            case["expected_output_contract"]["max_introduction_blocks"],
            5,
        )
        self.assertIn(
            "../anchises-analysis/references/global-contract.md",
            MARKET_SKILL.read_text(encoding="utf-8"),
        )

    def test_disclaimer_and_report_risk_label_precede_final_questions(self) -> None:
        market_format = (
            MARKET_SKILL_ROOT / "references" / "market-answer-format.md"
        ).read_text(encoding="utf-8")
        report_format = (
            REPORT_SKILL_ROOT / "references" / "report-format.md"
        ).read_text(encoding="utf-8")
        finalizer = (
            SKILL_ROOT / "references" / "response-finalization.md"
        ).read_text(encoding="utf-8")
        self.assertIn("immediately before any continuation or semantic", market_format)
        self.assertIn("placed before any question", report_format)
        self.assertIn("analytical-information disclaimer", finalizer)
        self.assertIn("semantic question, when required", finalizer)

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
        report = (REPORT_SKILL_ROOT / "references" / "report-workflow.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join(report.split())
        self.assertIn("Return the completed report, not the prompt", normalized)
        self.assertIn("Do not expose `prompt_text`", normalized)
        self.assertIn("live web search", normalized)
        self.assertEqual(report.count("### 1. Company Overview & Listing Profile"), 1)
        self.assertEqual(report.count("### 7. Risk Assessment"), 1)
        self.assertIn("`**Summary:**`", report)
        self.assertIn("`**[Risk: Low]**`", report)

    def test_no_web_search_never_falls_back_to_model_memory(self) -> None:
        combined = " ".join(_bundle_text(REPORT_SKILL_ROOT).split())
        self.assertIn("If live web search is unavailable", combined)
        self.assertIn("do not generate current research from model memory", combined)
        self.assertIn("do not rely on model memory", combined)
        case = next(
            item for item in _golden_cases()["negative"]
            if item["id"] == "external-no-web-verification"
        )
        self.assertIn("invent the exchange, ticker, or company name", case["expected_behavior"])

    def test_report_is_not_persisted_or_written_back(self) -> None:
        combined = " ".join(_bundle_text(REPORT_SKILL_ROOT).split())
        self.assertIn("Return the completed source-linked report only in the current conversation", combined)
        self.assertIn("Do not send the report back to MCP", combined)
        self.assertIn("Do not send it back to MCP", combined)
        self.assertIn("claim it was saved, uploaded, or published", combined)

    def test_mining_quality_covers_cash_debt_and_warrants(self) -> None:
        text = (REPORT_SKILL_ROOT / "references" / "mining-report-quality.md").read_text(
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
        self.assertEqual(contract["contract_version"], "1.8.0-draft")
        self.assertEqual(contract["source"]["server_version"], "0.7.2")
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

    def test_csv_export_guidance_uses_dynamic_policy_and_allowed_lifetimes(self) -> None:
        combined = " ".join(_bundle_text(MARKET_SKILL_ROOT).split())
        self.assertIn("default 60-minute", combined)
        self.assertIn("60 through 3,600 seconds", combined)
        self.assertIn("`expires_in_seconds`", combined)
        self.assertIn("`get_connection_status.data_policy`", combined)
        self.assertIn("`restricted`", combined)
        self.assertIn("`bulk_enabled`", combined)
        self.assertIn("`source_tools_allowed`", combined)
        self.assertIn("dynamic `limits`", combined)

    def test_user_facing_export_copy_is_question_led_without_limit_recital(self) -> None:
        answer_format = (
            MARKET_SKILL_ROOT / "references" / "market-answer-format.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(answer_format.split())
        for threshold in (
            "1,000 rows",
            "25 total columns",
            "20,000 cells",
            "Top-N 200",
            "50 exact tickers",
        ):
            self.assertNotIn(threshold, normalized)
        self.assertIn("Tailor suggested fields to the user's question", normalized)
        self.assertIn("confirm them with `get_stock_schema`", normalized)
        self.assertIn("verify their current official documentation", normalized)
        self.assertNotIn(
            "Ticker, Company, Exchange, Open, High, Low, Close",
            normalized,
        )

    def test_market_data_policy_uses_cursor_and_dynamic_export_contract(self) -> None:
        combined = " ".join(_bundle_text(MARKET_SKILL_ROOT).split())
        self.assertIn("data.export_policy.eligible_by_query", combined)
        self.assertIn("never infer eligibility from a legacy field", combined)
        self.assertIn("`data.export_policy.source_tools_allowed`", combined)
        self.assertIn("`pagination_next_action=call_same_tool_with_cursor`", combined)
        self.assertIn("only the unmodified `page.next_cursor`", combined)
        self.assertIn("Never resend or rewrite the SQL", combined)
        self.assertIn("never add or use SQL `OFFSET`", combined)
        self.assertIn("never split filters, fields, tickers, dates", combined)

    def test_policy_errors_have_safe_recovery_instructions(self) -> None:
        combined = " ".join(_bundle_text(MARKET_SKILL_ROOT).split())
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
        self.assertIn("rerun the original intent", combined)
        self.assertIn("download is temporarily unavailable", combined)

    def test_restricted_export_refusal_is_courteous_and_policy_specific(self) -> None:
        combined = " ".join(_bundle_text(MARKET_SKILL_ROOT).split())
        self.assertIn("When restricted mode refuses", combined)
        self.assertIn("licensed exchange-data vendor", combined)
        self.assertIn("Tailor suggested fields to the user's question", combined)
        self.assertIn("complete matched range can still be analyzed", combined)
        self.assertIn("Do not use this restricted-mode wording when bulk mode", combined)
        self.assertNotIn("connector has reached its monthly call limit", combined)

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
            "liquidity-fields-from-question",
            "historical-fields-from-question",
            "bulk-liquidity-provider-alternative",
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
        self.assertIn("offer the next page", by_id["broad-result-preview"]["expected_behavior"])
        self.assertIn(
            "price, volume, dollar volume, and price change",
            by_id["liquidity-fields-from-question"]["expected_behavior"],
        )
        self.assertIn(
            "OHLC, adjusted close, and volume",
            by_id["historical-fields-from-question"]["expected_behavior"],
        )
        self.assertNotEqual(
            by_id["liquidity-fields-from-question"]["expected_behavior"],
            by_id["historical-fields-from-question"]["expected_behavior"],
        )

    def test_openai_metadata_matches_all_five_skills(self) -> None:
        expected = {
            OPENAI_YAML: ("Anchises Analysis", "$anchises-analysis"),
            BRIEF_OPENAI_YAML: ("Company Brief", "$company-brief"),
            REPORT_OPENAI_YAML: ("Company Report", "$company-report"),
            COMPARISON_OPENAI_YAML: (
                "Company Comparison",
                "$company-comparison",
            ),
            MARKET_OPENAI_YAML: ("Market Analysis", "$market-analysis"),
        }
        for path, (display_name, invocation) in expected.items():
            text = path.read_text(encoding="utf-8")
            self.assertIn(f'display_name: "{display_name}"', text)
            self.assertIn(invocation, text)
            self.assertIn("allow_implicit_invocation: true", text)

    def test_manifest_bundles_cross_workspace_remote_mcp(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        mcp_manifest = json.loads(MCP_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "anchises-analysis")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertNotIn("apps", manifest)
        self.assertFalse(LEGACY_APP_MANIFEST.exists())
        self.assertEqual(set(mcp_manifest), {"mcpServers"})
        self.assertEqual(set(mcp_manifest["mcpServers"]), {"anchises_analysis"})
        server = mcp_manifest["mcpServers"]["anchises_analysis"]
        self.assertEqual(server["type"], "http")
        self.assertEqual(server["url"], "https://mcp.anchisesdata.com/mcp")
        self.assertEqual(set(server), {"type", "url"})
        serialized = json.dumps(mcp_manifest).lower()
        for forbidden in (
            "client_secret",
            "api_token",
            "authorization",
            "bearer",
            "headers",
            "oauth",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_manifest_metadata_and_starter_prompts_match_release(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"].split("+", 1)[0], "0.6.0-dev.6")
        self.assertRegex(
            manifest["version"],
            r"^0\.6\.0-dev\.6(?:\+codex\.[0-9A-Za-z][0-9A-Za-z.-]*)?$",
        )
        self.assertLessEqual(manifest["version"].count("+codex."), 1)
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
        self.assertIn("at most 200 rows", interface["longDescription"])
        self.assertIn("opaque cursor", interface["longDescription"])
        self.assertIn("Top-N bounds the complete logical ranked result", interface["longDescription"])
        self.assertIn("restricted or bulk-enabled data policy", interface["longDescription"])
        self.assertIn("allowed screen or SQL source tools", interface["longDescription"])
        self.assertIn("no account-linked cross-session cumulative budget", interface["longDescription"])

    def test_repo_distribution_uses_bundled_mcp_and_keeps_directory_separate(self) -> None:
        normalized = " ".join(PLUGIN_README.read_text(encoding="utf-8").split())
        self.assertIn("does not depend on a Developer Mode App ID", normalized)
        self.assertIn("Local and cross-workspace Repo Marketplace installations", normalized)
        self.assertIn("must submit and scan the production MCP URL directly", normalized)
        self.assertIn("same five-Skill bundle", normalized)

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
            "company-brief-three",
            "company-brief-context-reference",
            "company-brief-eight",
            "company-brief-user-priority",
            "company-brief-news-modifier",
            "company-brief-no-suggestions-with-remaining",
            "company-brief-no-suggestions-complete",
            "company-comparison-business-context",
            "company-comparison-six-no-brief-window",
            "company-comparison-with-standalone-introductions",
            "market-screen-with-company-introductions",
            "market-introduction-continuation",
            "direct-market-skill-with-company-introductions",
            "context-comparison-not-brief",
            "incidental-company-list-not-brief",
            "ambiguous-company-request-routes-to-core",
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
            "liquidity-fields-from-question",
            "historical-fields-from-question",
            "bulk-liquidity-provider-alternative",
        }
        self.assertTrue(required_ids.issubset({case["id"] for case in all_cases}))


if __name__ == "__main__":
    unittest.main()
