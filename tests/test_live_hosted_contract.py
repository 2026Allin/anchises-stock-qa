from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "plugins" / "anchises-analysis" / "contracts"
if str(CONTRACTS) not in sys.path:
    sys.path.insert(0, str(CONTRACTS))

from hosted_contract import descriptor_by_name, load_contract  # noqa: E402
from sync_hosted_contract import (  # noqa: E402
    MCPHttpClient,
    contracts_match,
    fetch_contract,
)


RUN_LIVE = os.environ.get("RUN_LIVE_MCP_TESTS") == "1"
ENDPOINT = "https://mcp.anchisesdata.com/mcp"
HEALTH = "https://mcp.anchisesdata.com/health"


@unittest.skipUnless(
    RUN_LIVE,
    "set RUN_LIVE_MCP_TESTS=1 to run credential-free production checks",
)
class LiveHostedContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_contract()

    def _client(self, label: str) -> tuple[MCPHttpClient, dict]:
        client = MCPHttpClient(ENDPOINT)
        initialized = client.call(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {
                    "name": f"anchises-analysis-{label}",
                    "version": "0.7.1",
                },
            },
            1,
        )
        client.notify("notifications/initialized", {})
        return client, initialized

    def _tool_call(
        self,
        client: MCPHttpClient,
        request_id: int,
        name: str,
        arguments: dict,
    ) -> dict:
        result = client.call(
            "tools/call",
            {"name": name, "arguments": arguments},
            request_id,
        )
        self.assertFalse(result.get("isError"), result)
        structured = result.get("structuredContent")
        self.assertIsInstance(structured, dict)
        Draft202012Validator(
            descriptor_by_name(name, self.contract)["outputSchema"],
            format_checker=FormatChecker(),
        ).validate(structured)
        return structured

    def test_health_and_handshake_publish_0_7_1(self) -> None:
        request = Request(
            HEALTH,
            headers={"User-Agent": "anchises-analysis-live-health/0.7.1"},
        )
        with urlopen(request, timeout=20) as response:
            health = json.loads(response.read().decode("utf-8"))
        self.assertTrue(health["ok"])
        self.assertEqual(health["version"], "0.7.1")
        self.assertEqual(health["status"], "ready")
        self.assertEqual(health["access_mode"], "public_noauth")
        self.assertEqual(health["authentication"], "not_required")

        _, initialized = self._client("handshake")
        self.assertEqual(
            initialized["serverInfo"],
            {
                "name": "Anchises Analysis",
                "version": "0.7.1",
                "websiteUrl": "https://anchisesdata.com/stock-qa",
            },
        )

    def test_live_tools_match_checked_in_snapshot(self) -> None:
        live = fetch_contract(
            ENDPOINT,
            base_contract=self.contract,
            expected_mode="public_noauth",
        )
        self.assertTrue(contracts_match(self.contract, live))
        self.assertEqual(len(live["tools"]), 12)
        names = [tool["name"] for tool in live["tools"]]
        self.assertIn("resolve_company_identity", names)
        self.assertFalse(
            {"get_cached_company_report", "read_company_report"} & set(names)
        )

    def test_current_anonymous_status_is_readable_without_credentials(self) -> None:
        client, _ = self._client("status")
        result = self._tool_call(client, 2, "get_connection_status", {})
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["authentication"], "not_required")
        self.assertEqual(result["coverage"], "all_supported_exchanges")
        self.assertEqual(result["limits"]["rate"]["scope"], "global")
        self.assertIn(result["data_policy"]["mode"], {"restricted", "bulk_enabled"})
        self.assertEqual(result["data_policy"]["policy_version"], "stock-data-access-v2")

    def test_all_twelve_tools_complete_a_production_smoke(self) -> None:
        client, _ = self._client("all-tools")
        request_id = 2

        status = self._tool_call(client, request_id, "get_connection_status", {})
        request_id += 1
        self.assertEqual(status["status"], "active")

        exchanges = self._tool_call(client, request_id, "get_available_exchanges", {})
        request_id += 1
        codes = [item["code"] for item in exchanges["data"]["exchanges"]]
        self.assertEqual(codes, ["ASX", "CSE", "NASDAQ", "NYSE", "TSX", "TSXV"])

        latest = self._tool_call(
            client,
            request_id,
            "get_latest_dates",
            {"exchanges": ["NASDAQ"]},
        )
        request_id += 1
        schema = self._tool_call(
            client,
            request_id,
            "get_stock_schema",
            {"exchange": "NASDAQ"},
        )
        request_id += 1
        field_names = [item["name"] for item in schema["data"]["fields"]]
        ticker_field = next(name for name in field_names if name.casefold() == "ticker")
        price_field = next(
            name for name in field_names
            if name.casefold() in {"price_close", "close"}
        )

        tables = self._tool_call(
            client,
            request_id,
            "list_stock_tables",
            {"exchanges": ["NASDAQ"], "page_size": 1},
        )
        request_id += 1
        table_name = tables["data"]["tables"][0]
        self._tool_call(
            client,
            request_id,
            "get_table_schema",
            {"tables": [table_name]},
        )
        request_id += 1

        screen = self._tool_call(
            client,
            request_id,
            "screen_stocks",
            {
                "exchanges": ["NASDAQ"],
                "fields": [price_field],
                "filters": [
                    {
                        "field": ticker_field,
                        "operator": "eq",
                        "value": "AAPL",
                    }
                ],
                "sort": [{"field": ticker_field, "direction": "asc"}],
                "top_n": 1,
                "page_size": 1,
            },
        )
        request_id += 1
        self.assertIsNone(screen["page"]["next_cursor"])
        self.assertTrue(screen["data"]["export_policy"]["eligible_by_query"])
        self.assertEqual(
            screen["data"]["export_policy"]["policy_version"],
            "stock-data-access-v2",
        )
        aggregate_sql = f'SELECT COUNT(*) AS "row_count" FROM "{table_name}"'
        self._tool_call(
            client,
            request_id,
            "validate_readonly_sql",
            {"sql": aggregate_sql},
        )
        request_id += 1
        sql_result = self._tool_call(
            client,
            request_id,
            "run_readonly_sql",
            {"sql": aggregate_sql, "max_rows": 1},
        )
        request_id += 1
        self.assertIsNone(sql_result["page"]["next_cursor"])
        self.assertEqual(
            sql_result["data"]["export_policy"]["mode"],
            status["data_policy"]["mode"],
        )
        if status["data_policy"]["effective_limits"]["sql_export_allowed"]:
            self.assertTrue(sql_result["data"]["export_policy"]["eligible_by_query"])
            self.assertIn(
                "run_readonly_sql",
                sql_result["data"]["export_policy"]["source_tools_allowed"],
            )
        else:
            self.assertFalse(sql_result["data"]["export_policy"]["eligible_by_query"])

        resolved = self._tool_call(
            client,
            request_id,
            "resolve_company_identity",
            {"query": "AAPL", "exchange_hint": "NASDAQ", "purpose": "company_report"},
        )
        request_id += 1
        company = resolved["data"]["company"]
        self.assertEqual(resolved["data"]["status"], "resolved")

        prepared = self._tool_call(
            client,
            request_id,
            "prepare_company_report_generation",
            {
                "exchange": company["exchange"],
                "ticker": company["ticker"],
                "company_name": company["company_name"],
                "output_locale": "en",
            },
        )
        request_id += 1
        self.assertEqual(prepared["data"]["status"], "ready")

        export = self._tool_call(
            client,
            request_id,
            "create_csv_export",
            {
                "query_id": screen["data"]["query_id"],
                "expires_in_seconds": 60,
            },
        )
        self.assertTrue(export["data"]["download_url"].startswith("https://"))
        download = Request(
            export["data"]["download_url"],
            headers={"User-Agent": "anchises-analysis-live-csv/0.7.1"},
        )
        with urlopen(download, timeout=30) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
        self.assertTrue(body)
        self.assertIn("text/csv", content_type)

        latest_value = latest["data"]["latest_dates"]["NASDAQ"]
        latest_date = (
            latest_value["latest_date"]
            if isinstance(latest_value, dict)
            else latest_value
        )
        broad = self._tool_call(
            client,
            request_id + 1,
            "screen_stocks",
            {
                "exchanges": ["NASDAQ"],
                "as_of_date": latest_date,
                "fields": [price_field],
                "filters": [],
                "sort": [{"field": ticker_field, "direction": "asc"}],
                "page_size": 1,
            },
        )
        self.assertIsInstance(broad["page"]["next_cursor"], str)
        self.assertEqual(
            broad["data"]["analysis"]["pagination_next_action"],
            "call_same_tool_with_cursor",
        )
        self.assertEqual(broad["data"]["analysis"]["displayed_row_start"], 1)
        self.assertEqual(broad["data"]["analysis"]["displayed_row_end"], 1)
        self.assertTrue(
            broad["data"]["export_policy"]["contains_complete_partition"]
        )
        continued = self._tool_call(
            client,
            request_id + 2,
            "screen_stocks",
            {"cursor": broad["page"]["next_cursor"], "page_size": 1},
        )
        self.assertEqual(continued["data"]["query_id"], broad["data"]["query_id"])
        self.assertEqual(continued["data"]["analysis"]["displayed_row_start"], 2)
        self.assertEqual(continued["data"]["analysis"]["displayed_row_end"], 2)

    def test_screen_runtime_rejects_one_sided_range_unsorted_top_n_and_cursor(self) -> None:
        client, _ = self._client("screen-invalid")
        cases = (
            {"filters": [], "start_date": "2026-07-01", "page_size": 1},
            {"filters": [], "top_n": 10, "page_size": 1},
            {"filters": [], "cursor": "legacy", "page_size": 1},
        )
        for request_id, arguments in enumerate(cases, 2):
            with self.subTest(arguments=arguments):
                result = client.call(
                    "tools/call",
                    {"name": "screen_stocks", "arguments": arguments},
                    request_id,
                )
                self.assertTrue(result["isError"])
                self.assertNotIn("data", result.get("structuredContent", {}))

    def test_company_identity_resolution_business_states(self) -> None:
        client, _ = self._client("identity")
        resolved = self._tool_call(
            client,
            2,
            "resolve_company_identity",
            {"query": "AAPL", "exchange_hint": "NASDAQ", "purpose": "stock_data"},
        )["data"]
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(
            (
                resolved["company"]["exchange"],
                resolved["company"]["ticker"],
                resolved["company"]["company_name"],
            ),
            ("NASDAQ", "AAPL", "Apple Inc."),
        )

        company_name = self._tool_call(
            client,
            3,
            "resolve_company_identity",
            {"query": "Apple", "purpose": "company_report"},
        )["data"]
        self.assertIn(company_name["status"], {"resolved", "ambiguous"})
        if company_name["status"] == "ambiguous":
            self.assertTrue(
                any(item["ticker"] == "AAPL" for item in company_name["candidates"])
            )

        cross_market = self._tool_call(
            client,
            4,
            "resolve_company_identity",
            {"query": "RIO", "purpose": "company_report"},
        )["data"]
        self.assertEqual(cross_market["status"], "ambiguous")
        self.assertGreaterEqual(len({item["exchange"] for item in cross_market["candidates"]}), 2)

        external = self._tool_call(
            client,
            5,
            "resolve_company_identity",
            {
                "query": "Rio Tinto plc",
                "exchange_hint": "LSE",
                "purpose": "company_report",
            },
        )["data"]
        self.assertEqual(external["status"], "not_found_in_supported_markets")

    def test_company_report_preparation_ready_external_and_inactive(self) -> None:
        client, _ = self._client("report-states")
        ready = self._tool_call(
            client,
            2,
            "prepare_company_report_generation",
            {
                "exchange": "NASDAQ",
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "output_locale": "zh-CN",
            },
        )["data"]
        self.assertEqual(ready["status"], "ready")
        self.assertEqual(ready["identity_source"], "master")
        self.assertFalse(ready["listing_status_verification_required"])
        self.assertEqual(ready["prompt_version"], "5.1")
        self.assertEqual(ready["next_action"], "run_host_web_research")
        self.assertIn("**Summary:**", ready["prompt_text"])
        self.assertIn("**[Risk:", ready["prompt_text"])
        self.assertIn("warrant", ready["prompt_text"].lower())
        for number in range(1, 8):
            self.assertIn(f"### {number}.", ready["prompt_text"])

        inactive = self._tool_call(
            client,
            3,
            "prepare_company_report_generation",
            {
                "exchange": "ASX",
                "ticker": "1TTDB",
                "company_name": "1TTDB",
                "output_locale": "en",
            },
        )["data"]
        self.assertEqual(inactive["status"], "ready")
        self.assertEqual(inactive["selected_sector"], "Others")
        self.assertTrue(inactive["listing_status_verification_required"])

        external = self._tool_call(
            client,
            4,
            "prepare_company_report_generation",
            {
                "exchange": "LSE",
                "ticker": "RIO",
                "company_name": "Rio Tinto plc",
                "output_locale": "en",
            },
        )["data"]
        self.assertEqual(external["status"], "ready")
        self.assertEqual(external["identity_source"], "host_supplied")
        self.assertTrue(external["listing_status_verification_required"])
        self.assertEqual(external["selected_sector"], "Others")

    def test_invalid_inputs_are_rejected_without_echoing_secrets(self) -> None:
        client, _ = self._client("negative")
        prepare_error = client.call(
            "tools/call",
            {
                "name": "prepare_company_report_generation",
                "arguments": {
                    "exchange": "NASDAQ",
                    "ticker": "AAPL",
                    "output_locale": "en",
                },
            },
            2,
        )
        self.assertTrue(prepare_error["isError"])
        self.assertNotIn("Apple Inc.", json.dumps(prepare_error))

        secret = "secret-value-that-must-not-be-reflected"
        resolver_error = client.call(
            "tools/call",
            {
                "name": "resolve_company_identity",
                "arguments": {"query": "AAPL", "full_chat": secret},
            },
            3,
        )
        self.assertTrue(resolver_error["isError"])
        self.assertNotIn(secret, json.dumps(resolver_error))

        rejected = client.call(
            "tools/call",
            {
                "name": "run_readonly_sql",
                "arguments": {"sql": "DROP TABLE stock_data"},
            },
            4,
        )
        self.assertTrue(rejected["isError"])
        serialized = json.dumps(rejected)
        self.assertNotIn("DROP TABLE stock_data", serialized)

        for metadata_url in (
            "https://mcp.anchisesdata.com/.well-known/oauth-protected-resource",
            "https://mcp.anchisesdata.com/mcp/.well-known/oauth-protected-resource",
        ):
            with self.subTest(url=metadata_url):
                try:
                    urlopen(Request(metadata_url), timeout=20)
                except HTTPError as error:
                    try:
                        self.assertEqual(error.code, 404)
                    finally:
                        error.close()
                else:
                    self.fail("public access unexpectedly exposed OAuth metadata")


if __name__ == "__main__":
    unittest.main()
