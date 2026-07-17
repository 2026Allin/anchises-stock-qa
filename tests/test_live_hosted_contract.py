from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "plugins" / "stock-data-desk" / "contracts"
if str(CONTRACTS) not in sys.path:
    sys.path.insert(0, str(CONTRACTS))

from hosted_contract import (  # noqa: E402
    PROFILE_ANONYMOUS,
    descriptor_by_name,
    load_contract,
    mode_profile,
)
from sync_hosted_contract import (  # noqa: E402
    DEFAULT_ENDPOINT,
    MCP_PROTOCOL_VERSION,
    MCPHttpClient,
    contracts_match,
    fetch_contract,
)


RUN_LIVE = os.environ.get("RUN_LIVE_MCP_TESTS") == "1"


@unittest.skipUnless(
    RUN_LIVE,
    "set RUN_LIVE_MCP_TESTS=1 to run credential-free production checks",
)
class LiveHostedContractTest(unittest.TestCase):
    """Opt-in, read-only checks against the real Hosted MCP endpoint."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.checked_in = load_contract()
        cls.endpoint = os.environ.get("MCP_LIVE_ENDPOINT", DEFAULT_ENDPOINT)
        cls.expected_mode = os.environ.get(
            "MCP_EXPECT_MODE",
            cls.checked_in["runtime"]["snapshot_mode"],
        )
        cls.live = fetch_contract(
            cls.endpoint,
            base_contract=cls.checked_in,
            expected_mode=cls.expected_mode,
        )

    def test_live_tools_match_checked_in_snapshot(self) -> None:
        self.assertTrue(contracts_match(self.checked_in, self.live))
        self.assertEqual(len(self.live["tools"]), 12)

    def test_current_anonymous_status_is_readable_without_credentials(self) -> None:
        if mode_profile(self.checked_in, self.expected_mode) != PROFILE_ANONYMOUS:
            self.skipTest("the active mode is not credential-free")

        client = MCPHttpClient(self.endpoint)
        client.call(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "stock-data-desk-live-test",
                    "version": "1.0.0",
                },
            },
            1,
        )
        client.notify("notifications/initialized", {})
        result = client.call(
            "tools/call",
            {
                "name": "get_connection_status",
                "arguments": {},
            },
            2,
        )
        self.assertFalse(result["isError"])
        structured = result["structuredContent"]
        Draft202012Validator(
            descriptor_by_name("get_connection_status")["outputSchema"],
            format_checker=FormatChecker(),
        ).validate(structured)
        self.assertEqual(structured["status"], "active")
        self.assertEqual(structured["authentication"], "not_required")
        self.assertEqual(structured["coverage"], "all_supported_exchanges")
        self.assertEqual(structured["limits"]["rate"]["scope"], "global")
        self.assertEqual(structured["limits"]["concurrency"]["scope"], "global")
        for forbidden in (
            "request_id",
            "user_id",
            "principal",
            "connection_id",
            "policy",
        ):
            self.assertNotIn(forbidden, structured)

    def test_public_negative_calls_are_safe_and_do_not_echo_inputs(self) -> None:
        if mode_profile(self.checked_in, self.expected_mode) != PROFILE_ANONYMOUS:
            self.skipTest("the active mode is not credential-free")

        client = MCPHttpClient(self.endpoint)
        client.call(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "stock-data-desk-live-negative-test",
                    "version": "1.0.0",
                },
            },
            1,
        )
        client.notify("notifications/initialized", {})
        cases = [
            (
                "run_readonly_sql",
                {"sql": "DROP TABLE daily_20260715_asx"},
                "rejected",
            ),
            (
                "create_csv_export",
                {"query_id": "qry_tampered_public_review"},
                "invalid",
            ),
            (
                "get_connection_status",
                {"api_token": "REDACTED_TEST_VALUE"},
                "additional properties",
            ),
        ]
        for request_id, (tool_name, arguments, expected_text) in enumerate(
            cases, start=2
        ):
            with self.subTest(tool=tool_name):
                result = client.call(
                    "tools/call",
                    {"name": tool_name, "arguments": arguments},
                    request_id,
                )
                self.assertTrue(result["isError"])
                text = " ".join(
                    item.get("text", "")
                    for item in result.get("content", [])
                    if isinstance(item, dict)
                )
                self.assertIn(expected_text, text.lower())
                self.assertNotIn("REDACTED_TEST_VALUE", json.dumps(result))

    def test_all_twelve_tools_complete_a_production_smoke(self) -> None:
        if mode_profile(self.checked_in, self.expected_mode) != PROFILE_ANONYMOUS:
            self.skipTest("the active mode is not credential-free")

        client = MCPHttpClient(self.endpoint)
        client.call(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "stocks-info-live-all-tools-test",
                    "version": "1.0.0",
                },
            },
            1,
        )
        client.notify("notifications/initialized", {})
        request_id = 1

        def call(name: str, arguments: dict) -> dict:
            nonlocal request_id
            request_id += 1
            result = client.call(
                "tools/call",
                {"name": name, "arguments": arguments},
                request_id,
            )
            self.assertFalse(result["isError"], name)
            structured = result["structuredContent"]
            Draft202012Validator(
                descriptor_by_name(name, self.checked_in)["outputSchema"],
                format_checker=FormatChecker(),
            ).validate(structured)
            return structured

        status = call("get_connection_status", {})
        self.assertEqual(status["status"], "active")
        exchanges = call("get_available_exchanges", {})
        self.assertIn(
            "ASX",
            [item["code"] for item in exchanges["data"]["exchanges"]],
        )
        dates = call("get_latest_dates", {"exchanges": ["ASX"]})
        latest = dates["data"]["latest_dates"]["ASX"]
        latest_date = latest["latest_date"]
        call("get_stock_schema", {"exchange": "ASX"})
        tables = call(
            "list_stock_tables",
            {
                "exchanges": ["ASX"],
                "start_date": latest_date,
                "end_date": latest_date,
                "page_size": 10,
            },
        )
        table = tables["data"]["tables"][0]
        call("get_table_schema", {"tables": [table]})
        screen = call(
            "screen_stocks",
            {"exchanges": ["ASX"], "filters": [], "page_size": 1},
        )
        query_id = screen["data"]["query_id"]
        sql = f"SELECT * FROM {table} LIMIT 1"
        validation = call("validate_readonly_sql", {"sql": sql})
        self.assertTrue(validation["data"]["valid"])
        call(
            "run_readonly_sql",
            {"sql": sql, "max_rows": 1, "page_size": 1},
        )
        report = call(
            "get_latest_company_report",
            {"exchange": "ASX", "ticker": "BGL", "pdf_range": "1Y"},
        )
        self.assertEqual(report["data"]["status"], "active")
        call(
            "prepare_company_report_generation",
            {
                "exchange": "NASDAQ",
                "ticker": "AAPL",
                "output_locale": "zh-CN",
            },
        )
        export = call(
            "create_csv_export",
            {"query_id": query_id, "expires_in_seconds": 60},
        )
        request = Request(
            export["data"]["download_url"],
            headers={"User-Agent": "stocks-info-live-all-tools-test/1.0"},
        )
        with urlopen(request, timeout=30) as response:
            self.assertIn("csv", response.headers.get("Content-Type", "").lower())
            self.assertTrue(response.read(1024))

    def test_company_report_generation_business_states(self) -> None:
        if mode_profile(self.checked_in, self.expected_mode) != PROFILE_ANONYMOUS:
            self.skipTest("the active mode is not credential-free")

        client = MCPHttpClient(self.endpoint)
        client.call(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "stocks-info-live-company-report-test",
                    "version": "1.0.0",
                },
            },
            1,
        )
        client.notify("notifications/initialized", {})
        request_id = 1

        def call(name: str, arguments: dict) -> dict:
            nonlocal request_id
            request_id += 1
            result = client.call(
                "tools/call",
                {"name": name, "arguments": arguments},
                request_id,
            )
            self.assertFalse(result["isError"], name)
            structured = result["structuredContent"]
            Draft202012Validator(
                descriptor_by_name(name, self.checked_in)["outputSchema"],
                format_checker=FormatChecker(),
            ).validate(structured)
            return structured

        active = call(
            "get_latest_company_report",
            {"exchange": "ASX", "ticker": "BGL"},
        )
        self.assertEqual(active["data"]["status"], "active")
        self.assertNotIn("generation_offer", active["data"])

        active_prepare = call(
            "prepare_company_report_generation",
            {
                "exchange": "ASX",
                "ticker": "BGL",
                "output_locale": "en",
            },
        )
        self.assertEqual(active_prepare["data"]["status"], "not_eligible")
        self.assertIsNone(active_prepare["data"]["prompt_text"])

        missing = call(
            "get_latest_company_report",
            {"exchange": "NASDAQ", "ticker": "AAPL"},
        )
        self.assertEqual(missing["data"]["status"], "not_found")
        self.assertEqual(
            missing["data"]["generation_offer"]["reason"],
            "not_found",
        )
        ready = call(
            "prepare_company_report_generation",
            {
                "exchange": "NASDAQ",
                "ticker": "AAPL",
                "output_locale": "zh-CN",
            },
        )
        self.assertEqual(ready["data"]["status"], "ready")
        self.assertEqual(
            ready["data"]["next_action"],
            "run_host_web_research",
        )
        self.assertLessEqual(len(ready["data"]["prompt_text"]), 25_000)
        self.assertIn(
            "### 1. Company Overview & Listing Profile",
            ready["data"]["prompt_text"],
        )
        self.assertIn(
            "### 7. Risk Assessment",
            ready["data"]["prompt_text"],
        )

        others = call(
            "prepare_company_report_generation",
            {
                "exchange": "ASX",
                "ticker": "AIA",
                "output_locale": "en",
            },
        )
        self.assertEqual(others["data"]["selected_sector"], "Others")
        self.assertEqual(others["warnings"], [])

        ineligible = call(
            "prepare_company_report_generation",
            {
                "exchange": "ASX",
                "ticker": "1TTDB",
                "output_locale": "en",
            },
        )
        self.assertEqual(ineligible["data"]["status"], "not_eligible")
        self.assertIsNone(ineligible["data"]["prompt_text"])

        company_missing = call(
            "prepare_company_report_generation",
            {
                "exchange": "NASDAQ",
                "ticker": "ZZZZNOTREAL",
                "output_locale": "en",
            },
        )
        self.assertEqual(company_missing["data"]["status"], "company_not_found")
        self.assertIsNone(company_missing["data"]["company"])

    def test_expired_report_offer_when_sample_is_configured(self) -> None:
        sample = os.environ.get("MCP_EXPIRED_REPORT_SAMPLE", "")
        if ":" not in sample:
            self.skipTest(
                "set MCP_EXPIRED_REPORT_SAMPLE=EXCHANGE:TICKER when an expired "
                "production report is available"
            )
        exchange, ticker = sample.split(":", 1)
        client = MCPHttpClient(self.endpoint)
        client.call(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "stocks-info-live-expired-report-test",
                    "version": "1.0.0",
                },
            },
            1,
        )
        client.notify("notifications/initialized", {})
        result = client.call(
            "tools/call",
            {
                "name": "get_latest_company_report",
                "arguments": {
                    "exchange": exchange.upper(),
                    "ticker": ticker.upper(),
                },
            },
            2,
        )
        self.assertFalse(result["isError"])
        structured = result["structuredContent"]
        Draft202012Validator(
            descriptor_by_name(
                "get_latest_company_report",
                self.checked_in,
            )["outputSchema"],
            format_checker=FormatChecker(),
        ).validate(structured)
        self.assertEqual(structured["data"]["status"], "expired")
        self.assertIsNotNone(structured["data"]["report"])
        self.assertTrue(structured["data"]["report"]["is_expired"])
        self.assertIsNotNone(structured["data"]["pdf_download_url"])
        offer = structured["data"]["generation_offer"]
        self.assertTrue(offer["available"])
        self.assertTrue(offer["requires_user_confirmation"])
        self.assertEqual(offer["reason"], "expired")
        self.assertEqual(
            offer["tool_name"],
            "prepare_company_report_generation",
        )
        self.assertEqual(
            offer["arguments"],
            {"exchange": exchange.upper(), "ticker": ticker.upper()},
        )
        self.assertTrue(structured["warnings"])

        prepared_result = client.call(
            "tools/call",
            {
                "name": "prepare_company_report_generation",
                "arguments": {
                    "exchange": exchange.upper(),
                    "ticker": ticker.upper(),
                    "output_locale": "en",
                },
            },
            3,
        )
        self.assertFalse(prepared_result["isError"])
        prepared = prepared_result["structuredContent"]
        Draft202012Validator(
            descriptor_by_name(
                "prepare_company_report_generation",
                self.checked_in,
            )["outputSchema"],
            format_checker=FormatChecker(),
        ).validate(prepared)
        self.assertEqual(prepared["data"]["status"], "ready")
        self.assertEqual(
            prepared["data"]["next_action"],
            "run_host_web_research",
        )
        self.assertTrue(prepared["data"]["prompt_text"])
        self.assertLessEqual(len(prepared["data"]["prompt_text"]), 25_000)


if __name__ == "__main__":
    unittest.main()
