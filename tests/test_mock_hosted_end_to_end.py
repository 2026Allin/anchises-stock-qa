from __future__ import annotations

import base64
import hashlib
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from jsonschema import Draft202012Validator, FormatChecker, ValidationError


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "plugins" / "anchises-analysis" / "contracts"
TESTS = ROOT / "tests"
if str(CONTRACTS) not in sys.path:
    sys.path.insert(0, str(CONTRACTS))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from hosted_contract import descriptor_by_name, load_contract  # noqa: E402
from mock_services import (  # noqa: E402
    ACTIVE_TOKEN,
    INTERNAL_TOKEN,
    PENDING_TOKEN,
    MockAnchisesAnalysisServices,
)
from sync_hosted_contract import (  # noqa: E402
    MCPServiceClosedError,
    fetch_contract,
)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _request(
    url: str,
    *,
    method: str = "GET",
    payload: Dict[str, Any] | None = None,
    form: Dict[str, str] | None = None,
    headers: Dict[str, str] | None = None,
    follow_redirects: bool = True,
) -> Tuple[int, Dict[str, Any] | str, Dict[str, str]]:
    request_headers = dict(headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    elif form is not None:
        data = urlencode(form).encode("utf-8")
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(url, data=data, headers=request_headers, method=method)
    opener = build_opener() if follow_redirects else build_opener(_NoRedirect())
    try:
        response = opener.open(request, timeout=5)
    except HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            parsed: Dict[str, Any] | str
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = body
            return exc.code, parsed, dict(exc.headers.items())
        finally:
            exc.close()
    body = response.read().decode("utf-8")
    content_type = response.headers.get("Content-Type", "")
    parsed = json.loads(body) if "application/json" in content_type else body
    return response.status, parsed, dict(response.headers.items())


class MockHostedEndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_contract()

    def setUp(self) -> None:
        self.services = MockAnchisesAnalysisServices().__enter__()

    def tearDown(self) -> None:
        self.services.__exit__(None, None, None)

    def _mcp_call(
        self,
        name: str,
        arguments: Dict[str, Any] | None = None,
        token: str = ACTIVE_TOKEN,
        request_id: int = 1,
        services: MockAnchisesAnalysisServices | None = None,
    ) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
        target = services or self.services
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        status, body, response_headers = _request(
            f"{target.base_url}/mcp",
            method="POST",
            headers=headers,
            payload={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            },
        )
        self.assertIsInstance(body, dict)
        return status, body, response_headers  # type: ignore[return-value]

    def _assert_success_schema(self, tool_name: str, body: Dict[str, Any]) -> Dict[str, Any]:
        result = body["result"]
        self.assertFalse(result["isError"])
        structured = result["structuredContent"]
        descriptor = descriptor_by_name(tool_name, self.contract)
        Draft202012Validator(
            descriptor["outputSchema"],
            format_checker=FormatChecker(),
        ).validate(structured)
        return structured

    def _oauth_token(self) -> str:
        verifier = "mock-verifier-with-sufficient-entropy-0123456789abcdef"
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")
        redirect_uri = "https://chatgpt.com/connector/oauth/mock-callback"
        state = "mock-state"
        query = urlencode(
            {
                "response_type": "code",
                "client_id": "https://chatgpt.com/oauth/mock/client.json",
                "redirect_uri": redirect_uri,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": f"{self.services.base_url}/mcp",
                "scope": "openid email profile stock.read schema.read export.create",
                "state": state,
            }
        )
        status, _, headers = _request(
            f"{self.services.base_url}/auth/authorize?{query}",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        callback = urlsplit(headers["Location"])
        callback_query = parse_qs(callback.query)
        self.assertEqual(callback_query["state"], [state])
        code = callback_query["code"][0]
        status, token, _ = _request(
            f"{self.services.base_url}/auth/oauth/token",
            method="POST",
            form={
                "grant_type": "authorization_code",
                "client_id": "https://chatgpt.com/oauth/mock/client.json",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": verifier,
                "resource": f"{self.services.base_url}/mcp",
            },
        )
        self.assertEqual(status, 200)
        self.assertIsInstance(token, dict)
        self.assertEqual(token["token_type"], "Bearer")
        return token["access_token"]

    def test_positive_1_auth0_discovery_pkce_and_connection_status(self) -> None:
        status, protected, _ = _request(
            f"{self.services.base_url}/mcp/.well-known/oauth-protected-resource"
        )
        self.assertEqual(status, 200)
        self.assertEqual(protected["resource"], f"{self.services.base_url}/mcp")
        status, discovery, _ = _request(
            f"{self.services.base_url}/auth/.well-known/openid-configuration"
        )
        self.assertEqual(status, 200)
        self.assertEqual(discovery["code_challenge_methods_supported"], ["S256"])
        self.assertTrue(discovery["client_id_metadata_document_supported"])
        status, jwks, _ = _request(discovery["jwks_uri"])
        self.assertEqual(status, 200)
        self.assertEqual(jwks["keys"][0]["alg"], "RS256")
        token = self._oauth_token()
        status, body, _ = self._mcp_call("get_connection_status", token=token)
        self.assertEqual(status, 200)
        structured = self._assert_success_schema("get_connection_status", body)
        self.assertEqual(structured["status"], "active")
        self.assertEqual(structured["authentication"], "oauth")
        self.assertEqual(structured["coverage"], "approved_stock_data")
        self.assertEqual(structured["data_policy"]["mode"], "restricted")
        self.assertEqual(
            structured["data_policy"]["policy_version"],
            "stock-data-access-v2",
        )

    def test_positive_2_market_discovery_and_latest_dates(self) -> None:
        status, body, _ = self._mcp_call("get_available_exchanges")
        self.assertEqual(status, 200)
        exchanges = self._assert_success_schema("get_available_exchanges", body)
        codes = [item["code"] for item in exchanges["data"]["exchanges"]]
        self.assertEqual(codes, ["ASX", "CSE", "NASDAQ", "NYSE", "TSX", "TSXV"])
        status, body, _ = self._mcp_call(
            "get_latest_dates", {"exchanges": ["NASDAQ", "ASX"]}
        )
        self.assertEqual(status, 200)
        dates = self._assert_success_schema("get_latest_dates", body)
        self.assertEqual(len(dates["data"]["latest_dates"]), 2)

    def test_positive_3_structured_momentum_screen(self) -> None:
        status, body, _ = self._mcp_call("get_stock_schema", {"exchange": "NASDAQ"})
        self.assertEqual(status, 200)
        schema = self._assert_success_schema("get_stock_schema", body)
        self.assertIn("price_change_pct_30day", [field["name"] for field in schema["data"]["fields"]])
        arguments = {
            "exchanges": ["NASDAQ", "ASX"],
            "fields": [
                "price_close",
                "price_change_pct_1day",
                "volume",
            ],
            "filters": [
                {"field": "volume", "operator": "gt", "value": 1000000},
                {"field": "price_change_pct_1day", "operator": "gt", "value": 5},
            ],
            "sort": [{"field": "price_change_pct_1day", "direction": "desc"}],
            "page_size": 20,
        }
        Draft202012Validator(
            descriptor_by_name("screen_stocks", self.contract)["inputSchema"]
        ).validate(arguments)
        status, body, _ = self._mcp_call("screen_stocks", arguments)
        self.assertEqual(status, 200)
        structured = self._assert_success_schema("screen_stocks", body)
        self.assertTrue(structured["data"]["query_id"].startswith("qry_screen_"))
        self.assertEqual(structured["page"]["row_count"], 2)
        self.assertFalse(structured["page"]["truncated"])
        self.assertIsNone(structured["page"]["next_cursor"])
        self.assertEqual(
            structured["data"]["analysis"]["query_classification"],
            "filtered",
        )
        self.assertTrue(structured["data"]["export_policy"]["eligible_by_query"])
        self.assertEqual(
            structured["data"]["export_policy"]["policy_version"],
            "stock-data-access-v2",
        )
        self.assertEqual(structured["data"]["export_policy"]["mode"], "restricted")

    def test_mock_tools_list_matches_materialized_contract(self) -> None:
        status, body, _ = _request(
            f"{self.services.base_url}/mcp",
            method="POST",
            payload={"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}},
        )
        self.assertEqual(status, 200)
        tools = body["result"]["tools"]
        self.assertEqual(len(tools), 12)
        self.assertFalse(
            {"get_cached_company_report", "read_company_report"}
            & {tool["name"] for tool in tools}
        )
        self.assertEqual(
            [tool["name"] for tool in tools],
            [tool["name"] for tool in self.contract["tools"]],
        )
        for tool in tools:
            Draft202012Validator.check_schema(tool["inputSchema"])
            Draft202012Validator.check_schema(tool["outputSchema"])
            self.assertEqual(tool["securitySchemes"][0]["type"], "oauth2")
            self.assertEqual(tool["_meta"]["securitySchemes"], tool["securitySchemes"])
        status, body, _ = _request(f"{self.services.base_url}/mcp-dev")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "not_found")

    def test_positive_4_historical_schema_validation_and_sql(self) -> None:
        status, body, _ = self._mcp_call(
            "list_stock_tables",
            {"exchanges": ["NASDAQ"], "start_date": "2026-06-01", "end_date": "2026-07-17"},
        )
        self.assertEqual(status, 200)
        coverage = self._assert_success_schema("list_stock_tables", body)
        table_names = coverage["data"]["tables"][:2]
        status, body, _ = self._mcp_call("get_table_schema", {"tables": table_names})
        self.assertEqual(status, 200)
        self._assert_success_schema("get_table_schema", body)
        sql = "SELECT ticker, price_close FROM daily_20260717_nasdaq LIMIT 50"
        status, body, _ = self._mcp_call("validate_readonly_sql", {"sql": sql})
        self.assertEqual(status, 200)
        validation = self._assert_success_schema("validate_readonly_sql", body)
        self.assertTrue(validation["data"]["valid"])
        status, body, _ = self._mcp_call("run_readonly_sql", {"sql": sql, "max_rows": 50})
        self.assertEqual(status, 200)
        result = self._assert_success_schema("run_readonly_sql", body)
        self.assertTrue(result["data"]["query_id"].startswith("qry_sql_"))
        self.assertIsNone(result["page"]["next_cursor"])
        self.assertEqual(
            result["data"]["analysis"]["query_classification"],
            "sql_analysis",
        )
        self.assertFalse(result["data"]["export_policy"]["eligible_by_query"])
        self.assertEqual(
            result["data"]["export_policy"]["reasons"],
            ["query_not_exportable"],
        )

    def test_positive_5_temporary_csv_export(self) -> None:
        status, body, _ = self._mcp_call(
            "screen_stocks",
            {
                "exchanges": ["NASDAQ"],
                "fields": ["price_close", "price_change_pct_30day", "volume"],
                "filters": [{"field": "ticker", "operator": "eq", "value": "AAPL"}],
                "sort": [{"field": "ticker", "direction": "asc"}],
                "page_size": 10,
            },
        )
        self.assertEqual(status, 200)
        screen = self._assert_success_schema("screen_stocks", body)
        self.assertTrue(screen["data"]["export_policy"]["eligible_by_query"])
        status, body, _ = self._mcp_call(
            "create_csv_export",
            {
                "query_id": screen["data"]["query_id"],
                "expires_in_seconds": 600,
            },
        )
        self.assertEqual(status, 200)
        export = self._assert_success_schema("create_csv_export", body)["data"]
        self.assertTrue(export["download_url"].startswith(self.services.base_url))
        self.assertEqual(export["expires_at"], "2026-07-14T12:10:00Z")
        status, csv_body, headers = _request(export["download_url"])
        self.assertEqual(status, 200)
        self.assertIn("text/csv", headers["Content-Type"])
        self.assertIn("AAPL,NASDAQ", csv_body)

    def test_screen_top_n_is_a_complete_logical_result_not_a_page_size(self) -> None:
        status, body, _ = self._mcp_call(
            "screen_stocks",
            {
                "exchanges": ["NASDAQ"],
                "fields": ["dollar_volume", "price_close"],
                "filters": [],
                "sort": [{"field": "dollar_volume", "direction": "desc"}],
                "top_n": 100,
                "page_size": 100,
            },
        )
        self.assertEqual(status, 200)
        ranked = self._assert_success_schema("screen_stocks", body)
        self.assertEqual(
            ranked["data"]["analysis"]["query_classification"],
            "bounded_top_n",
        )
        self.assertEqual(ranked["data"]["analysis"]["matched_row_count"], 100)
        self.assertFalse(ranked["data"]["analysis"]["result_is_preview"])
        self.assertFalse(
            ranked["data"]["analysis"]["row_pagination_available"]
        )
        self.assertIsNone(ranked["page"]["next_cursor"])
        self.assertTrue(ranked["data"]["export_policy"]["eligible_by_query"])

        tickers = [f"T{i:02d}" for i in range(40)]
        status, body, _ = self._mcp_call(
            "screen_stocks",
            {
                "exchanges": ["NASDAQ"],
                "fields": ["price_close", "volume"],
                "filters": [
                    {"field": "ticker", "operator": "in", "value": tickers}
                ],
                "sort": [{"field": "ticker", "direction": "asc"}],
                "page_size": 40,
            },
        )
        watchlist = self._assert_success_schema("screen_stocks", body)
        self.assertEqual(
            watchlist["data"]["analysis"]["query_classification"],
            "ticker_list",
        )
        self.assertTrue(watchlist["data"]["export_policy"]["eligible_by_query"])

        too_many = [f"T{i:02d}" for i in range(51)]
        status, body, _ = self._mcp_call(
            "screen_stocks",
            {
                "exchanges": ["NASDAQ"],
                "fields": ["price_close", "volume"],
                "filters": [
                    {"field": "ticker", "operator": "in", "value": too_many}
                ],
                "sort": [{"field": "ticker", "direction": "asc"}],
            },
        )
        oversized = self._assert_success_schema("screen_stocks", body)
        self.assertFalse(oversized["data"]["export_policy"]["eligible_by_query"])
        self.assertEqual(
            oversized["data"]["export_policy"]["reasons"],
            ["export_ticker_limit_exceeded"],
        )

    def test_bulk_top_500_and_sql_use_cursor_only_continuations_and_export(self) -> None:
        with MockAnchisesAnalysisServices(data_policy_mode="bulk_enabled") as services:
            status, body, _ = self._mcp_call(
                "get_connection_status", services=services
            )
            self.assertEqual(status, 200)
            connection = self._assert_success_schema(
                "get_connection_status", body
            )
            self.assertEqual(connection["data_policy"]["mode"], "bulk_enabled")
            self.assertTrue(
                connection["data_policy"]["effective_limits"]["sql_export_allowed"]
            )

            screen_arguments = {
                "exchanges": ["NASDAQ"],
                "fields": ["dollar_volume", "price_close"],
                "filters": [],
                "sort": [{"field": "dollar_volume", "direction": "desc"}],
                "top_n": 500,
                "page_size": 200,
            }
            status, body, _ = self._mcp_call(
                "screen_stocks", screen_arguments, services=services
            )
            self.assertEqual(status, 200)
            first = self._assert_success_schema("screen_stocks", body)
            self.assertEqual(first["page"]["row_count"], 200)
            self.assertEqual(first["page"]["total_count"], 500)
            self.assertEqual(first["data"]["analysis"]["displayed_row_start"], 1)
            self.assertEqual(first["data"]["analysis"]["displayed_row_end"], 200)
            self.assertEqual(
                first["data"]["analysis"]["pagination_next_action"],
                "call_same_tool_with_cursor",
            )
            cursor = first["page"]["next_cursor"]
            self.assertIsInstance(cursor, str)

            continuation = {"cursor": cursor, "page_size": 200}
            status, body, _ = self._mcp_call(
                "screen_stocks", continuation, services=services
            )
            second = self._assert_success_schema("screen_stocks", body)
            self.assertEqual(
                second["data"]["query_id"], first["data"]["query_id"]
            )
            self.assertEqual(second["data"]["analysis"]["displayed_row_start"], 201)
            self.assertEqual(second["data"]["analysis"]["displayed_row_end"], 400)
            self.assertEqual(services.tool_calls[-1]["arguments"], continuation)

            status, body, _ = self._mcp_call(
                "create_csv_export",
                {"query_id": first["data"]["query_id"]},
                services=services,
            )
            self._assert_success_schema("create_csv_export", body)
            self.assertEqual(
                services.httpd.queries[first["data"]["query_id"]]["matched"],  # type: ignore[attr-defined]
                500,
            )
            self.assertEqual(
                services.httpd.last_export_query_id,  # type: ignore[attr-defined]
                first["data"]["query_id"],
            )

            sql = (
                "SELECT ticker, price_close FROM daily_20260717_nasdaq "
                "ORDER BY ticker LIMIT 500"
            )
            self.assertNotIn("OFFSET", sql.upper())
            status, body, _ = self._mcp_call(
                "run_readonly_sql",
                {"sql": sql, "max_rows": 200},
                services=services,
            )
            sql_first = self._assert_success_schema("run_readonly_sql", body)
            self.assertTrue(sql_first["data"]["export_policy"]["eligible_by_query"])
            sql_continuation = {
                "cursor": sql_first["page"]["next_cursor"],
                "max_rows": 200,
            }
            status, body, _ = self._mcp_call(
                "run_readonly_sql", sql_continuation, services=services
            )
            sql_second = self._assert_success_schema("run_readonly_sql", body)
            self.assertEqual(sql_second["data"]["analysis"]["displayed_row_start"], 201)
            self.assertEqual(sql_second["data"]["analysis"]["displayed_row_end"], 400)
            self.assertEqual(services.tool_calls[-1]["arguments"], sql_continuation)
            self.assertNotIn("sql", services.tool_calls[-1]["arguments"])
            status, body, _ = self._mcp_call(
                "create_csv_export",
                {"query_id": sql_first["data"]["query_id"]},
                services=services,
            )
            self._assert_success_schema("create_csv_export", body)

    def test_restricted_over_limit_result_remains_analyzable(self) -> None:
        status, body, _ = self._mcp_call(
            "screen_stocks",
            {
                "exchanges": ["NASDAQ"],
                "fields": ["market_cap", "price_close"],
                "filters": [{"field": "market_cap", "operator": "gt", "value": 0}],
                "sort": [{"field": "market_cap", "direction": "desc"}],
                "page_size": 200,
            },
        )
        self.assertEqual(status, 200)
        result = self._assert_success_schema("screen_stocks", body)
        self.assertEqual(result["data"]["analysis"]["matched_row_count"], 1500)
        self.assertTrue(result["data"]["analysis"]["server_side_analysis_supported"])
        self.assertEqual(result["page"]["row_count"], 200)
        self.assertFalse(result["data"]["export_policy"]["eligible_by_query"])
        self.assertEqual(
            result["data"]["export_policy"]["reasons"],
            ["export_row_limit_exceeded"],
        )
        status, body, _ = self._mcp_call(
            "create_csv_export", {"query_id": result["data"]["query_id"]}
        )
        self.assertEqual(
            body["result"]["structuredContent"]["error"]["code"],
            "export_row_limit_exceeded",
        )

    def test_restricted_browse_limit_returns_refine_query(self) -> None:
        status, body, _ = self._mcp_call(
            "screen_stocks",
            {
                "fields": ["price_close"],
                "filters": [],
                "sort": [{"field": "ticker", "direction": "asc"}],
                "page_size": 200,
            },
        )
        page = self._assert_success_schema("screen_stocks", body)
        for _ in range(4):
            continuation = {
                "cursor": page["page"]["next_cursor"],
                "page_size": 200,
            }
            status, body, _ = self._mcp_call("screen_stocks", continuation)
            page = self._assert_success_schema("screen_stocks", body)
        analysis = page["data"]["analysis"]
        self.assertEqual(analysis["displayed_row_start"], 801)
        self.assertEqual(analysis["displayed_row_end"], 1000)
        self.assertEqual(analysis["browsable_row_limit"], 1000)
        self.assertTrue(analysis["pagination_limit_reached"])
        self.assertEqual(analysis["pagination_next_action"], "refine_query")
        self.assertIsNone(page["page"]["next_cursor"])

    def test_policy_change_invalidates_cursor_and_query_id_then_allows_requery(self) -> None:
        with MockAnchisesAnalysisServices(data_policy_mode="bulk_enabled") as services:
            original_arguments = {
                "exchanges": ["NASDAQ"],
                "fields": ["price_close", "volume"],
                "filters": [],
                "sort": [{"field": "ticker", "direction": "asc"}],
                "page_size": 200,
            }
            status, body, _ = self._mcp_call(
                "screen_stocks", original_arguments, services=services
            )
            original = self._assert_success_schema("screen_stocks", body)
            original_query_id = original["data"]["query_id"]
            old_cursor = original["page"]["next_cursor"]
            services.set_data_policy_mode("restricted")

            status, body, _ = self._mcp_call(
                "screen_stocks", {"cursor": old_cursor}, services=services
            )
            self.assertEqual(
                body["result"]["structuredContent"]["error"]["code"],
                "query_policy_expired",
            )
            status, body, _ = self._mcp_call(
                "create_csv_export",
                {"query_id": original_query_id},
                services=services,
            )
            self.assertEqual(
                body["result"]["structuredContent"]["error"]["code"],
                "query_policy_expired",
            )

            status, body, _ = self._mcp_call(
                "screen_stocks", original_arguments, services=services
            )
            refreshed = self._assert_success_schema("screen_stocks", body)
            self.assertNotEqual(refreshed["data"]["query_id"], original_query_id)
            self.assertEqual(refreshed["data"]["export_policy"]["mode"], "restricted")

    def test_complete_partition_remains_analyzable_but_not_exportable(self) -> None:
        status, body, _ = self._mcp_call(
            "screen_stocks",
            {
                "exchanges": ["NASDAQ"],
                "as_of_date": "2026-07-17",
                "fields": ["price_close", "volume"],
                "filters": [],
                "sort": [{"field": "ticker", "direction": "asc"}],
                "page_size": 200,
            },
        )
        broad = self._assert_success_schema("screen_stocks", body)
        self.assertEqual(
            broad["data"]["analysis"]["matched_row_count"],
            5000,
        )
        self.assertTrue(broad["data"]["analysis"]["server_side_analysis_supported"])
        self.assertFalse(broad["data"]["export_policy"]["eligible_by_query"])
        self.assertTrue(
            broad["data"]["export_policy"]["contains_complete_partition"]
        )
        self.assertEqual(
            broad["data"]["export_policy"]["reasons"],
            ["export_complete_partition_not_allowed"],
        )
        self.assertIsNotNone(broad["page"]["next_cursor"])
        self.assertEqual(
            broad["data"]["analysis"]["pagination_next_action"],
            "call_same_tool_with_cursor",
        )

        status, body, _ = self._mcp_call(
            "create_csv_export",
            {"query_id": broad["data"]["query_id"]},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["result"]["isError"])
        self.assertEqual(
            body["result"]["structuredContent"]["error"]["code"],
            "export_complete_partition_not_allowed",
        )

    def test_screen_runtime_rejects_invalid_range_top_n_and_legacy_cursor(self) -> None:
        cases = (
            {"filters": [], "start_date": "2026-01-01"},
            {"filters": [], "top_n": 10},
            {"filters": [], "cursor": "legacy-cursor"},
        )
        for arguments in cases:
            with self.subTest(arguments=arguments):
                status, body, _ = self._mcp_call("screen_stocks", arguments)
                self.assertEqual(status, 200)
                self.assertTrue(body["result"]["isError"])
                self.assertEqual(
                    body["result"]["structuredContent"]["error"]["code"],
                    "query_rejected",
                )

    def test_export_policy_errors_are_stable_and_safe(self) -> None:
        expected = {
            "qry_not_selective_0001": "export_requires_selective_query",
            "qry_row_limit_0001": "export_row_limit_exceeded",
            "qry_column_limit_0001": "export_column_limit_exceeded",
            "qry_cell_limit_0001": "export_cell_limit_exceeded",
            "qry_complete_partition_0001": "export_complete_partition_not_allowed",
            "qry_topn_limit_0001": "export_top_n_limit_exceeded",
            "qry_ticker_limit_0001": "export_ticker_limit_exceeded",
            "qry_expired_policy_0001": "query_policy_expired",
            "qry_partition_limit_0001": "query_partition_limit_exceeded",
            "qry_result_too_large_0001": "result_too_large",
            "qry_temp_unavailable_0001": "temporarily_unavailable",
        }
        for query_id, code in expected.items():
            with self.subTest(code=code):
                status, body, _ = self._mcp_call(
                    "create_csv_export",
                    {"query_id": query_id},
                )
                self.assertEqual(status, 200)
                self.assertTrue(body["result"]["isError"])
                error = body["result"]["structuredContent"]["error"]
                self.assertEqual(error["code"], code)
                self.assertNotIn(query_id, json.dumps(body))
                self.assertEqual(
                    error["retryable"],
                    code == "temporarily_unavailable",
                )

    def test_expired_policy_requires_a_fresh_screen_before_export(self) -> None:
        status, body, _ = self._mcp_call(
            "create_csv_export",
            {"query_id": "qry_expired_policy_0001"},
        )
        self.assertEqual(
            body["result"]["structuredContent"]["error"]["code"],
            "query_policy_expired",
        )

        status, body, _ = self._mcp_call(
            "screen_stocks",
            {
                "exchanges": ["NASDAQ"],
                "fields": ["price_close", "volume"],
                "filters": [{"field": "ticker", "operator": "eq", "value": "AAPL"}],
                "sort": [{"field": "ticker", "direction": "asc"}],
            },
        )
        refreshed = self._assert_success_schema("screen_stocks", body)
        self.assertTrue(refreshed["data"]["export_policy"]["eligible_by_query"])
        self.assertNotEqual(
            refreshed["data"]["query_id"],
            "qry_expired_policy_0001",
        )
        status, body, _ = self._mcp_call(
            "create_csv_export",
            {"query_id": refreshed["data"]["query_id"]},
        )
        self._assert_success_schema("create_csv_export", body)

    def test_positive_6_company_identity_resolution_states(self) -> None:
        status, body, _ = self._mcp_call(
            "resolve_company_identity",
            {"query": "Apple", "purpose": "company_report"},
        )
        self.assertEqual(status, 200)
        resolved = self._assert_success_schema("resolve_company_identity", body)["data"]
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(
            (resolved["company"]["exchange"], resolved["company"]["ticker"]),
            ("NASDAQ", "AAPL"),
        )

        status, body, _ = self._mcp_call(
            "resolve_company_identity",
            {"query": "RIO", "purpose": "company_report"},
        )
        ambiguous = self._assert_success_schema("resolve_company_identity", body)["data"]
        self.assertEqual(ambiguous["status"], "ambiguous")
        self.assertEqual({item["exchange"] for item in ambiguous["candidates"]}, {"ASX", "NYSE"})

        status, body, _ = self._mcp_call(
            "resolve_company_identity",
            {"query": "Alphabet", "exchange_hint": "NASDAQ", "purpose": "stock_data"},
        )
        share_classes = self._assert_success_schema("resolve_company_identity", body)["data"]
        self.assertEqual(share_classes["status"], "ambiguous")
        self.assertEqual({item["ticker"] for item in share_classes["candidates"]}, {"GOOG", "GOOGL"})

        status, body, _ = self._mcp_call(
            "resolve_company_identity",
            {"query": "Rio Tinto plc", "exchange_hint": "LSE", "purpose": "company_report"},
        )
        external = self._assert_success_schema("resolve_company_identity", body)["data"]
        self.assertEqual(external["status"], "not_found_in_supported_markets")
        self.assertIsNone(external["company"])

    def test_positive_7_prepare_company_report_generation_states(self) -> None:
        status, body, _ = self._mcp_call(
            "prepare_company_report_generation",
            {
                "exchange": "NASDAQ",
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "output_locale": "zh-CN",
            },
        )
        self.assertEqual(status, 200)
        ready = self._assert_success_schema(
            "prepare_company_report_generation", body
        )["data"]
        self.assertEqual(ready["status"], "ready")
        self.assertEqual(
            ready["selected_sector"],
            "Semiconductors, Compute & Advanced Hardware",
        )
        self.assertEqual(ready["identity_source"], "master")
        self.assertFalse(ready["listing_status_verification_required"])
        self.assertEqual(ready["prompt_version"], "5.1")
        self.assertEqual(ready["next_action"], "run_host_web_research")
        self.assertIn("Output locale: zh-CN", ready["prompt_text"])
        self.assertIn("**Summary:**", ready["prompt_text"])
        self.assertIn("warrants", ready["prompt_text"])
        self.assertLessEqual(len(ready["prompt_text"]), 25_000)

        status, body, _ = self._mcp_call(
            "prepare_company_report_generation",
            {
                "exchange": "ASX",
                "ticker": "OLD",
                "company_name": "Old Gold Limited",
                "output_locale": "en",
            },
        )
        others = self._assert_success_schema(
            "prepare_company_report_generation", body
        )
        self.assertEqual(others["data"]["selected_sector"], "Others")
        self.assertTrue(others["data"]["listing_status_verification_required"])
        self.assertEqual(others["warnings"], [])

        status, body, _ = self._mcp_call(
            "prepare_company_report_generation",
            {
                "exchange": "LSE",
                "ticker": "RIO",
                "company_name": "Rio Tinto plc",
                "output_locale": "en",
            },
        )
        external = self._assert_success_schema(
            "prepare_company_report_generation", body
        )["data"]
        self.assertEqual(external["status"], "ready")
        self.assertEqual(external["identity_source"], "host_supplied")
        self.assertTrue(external["listing_status_verification_required"])
        self.assertEqual(external["selected_sector"], "Others")

        status, body, _ = self._mcp_call(
            "prepare_company_report_generation",
            {
                "exchange": "ASX",
                "ticker": "VAS",
                "company_name": "Vanguard Australian Shares Index ETF",
                "output_locale": "en",
            },
        )
        ineligible = self._assert_success_schema(
            "prepare_company_report_generation", body
        )["data"]
        self.assertEqual(ineligible["status"], "not_eligible")
        self.assertIsNone(ineligible["prompt_text"])

    def test_prepare_requires_all_four_identity_and_locale_fields(self) -> None:
        schema = descriptor_by_name(
            "prepare_company_report_generation", self.contract
        )["inputSchema"]
        self.assertEqual(
            set(schema["required"]),
            {"exchange", "ticker", "company_name", "output_locale"},
        )
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(
                {"exchange": "NASDAQ", "ticker": "AAPL", "output_locale": "en"}
            )

    def test_negative_1_unauthenticated_call_returns_oauth_challenge(self) -> None:
        status, body, headers = self._mcp_call("get_connection_status", token="")
        self.assertEqual(status, 401)
        self.assertIn("resource_metadata=", headers["WWW-Authenticate"])
        challenges = body["result"]["_meta"]["mcp/www_authenticate"]
        self.assertIn("invalid_token", challenges[0])
        self.assertNotIn("access_token", json.dumps(body).lower())

    def test_negative_2_write_sql_sql_export_and_cross_user_export_are_safe(self) -> None:
        status, body, _ = self._mcp_call(
            "run_readonly_sql",
            {"sql": "UPDATE daily_20260717_nasdaq SET price_close = 0"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["result"]["isError"])
        self.assertEqual(
            body["result"]["structuredContent"]["error"]["code"],
            "query_rejected",
        )
        status, body, _ = self._mcp_call(
            "run_readonly_sql",
            {"sql": "SELECT COUNT(*) AS row_count FROM daily_20260717_nasdaq"},
        )
        sql_result = self._assert_success_schema("run_readonly_sql", body)
        status, body, _ = self._mcp_call(
            "create_csv_export",
            {"query_id": sql_result["data"]["query_id"]},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["result"]["isError"])
        self.assertEqual(
            body["result"]["structuredContent"]["error"]["code"],
            "query_not_exportable",
        )
        status, body, _ = self._mcp_call(
            "create_csv_export", {"query_id": "qry_owned_by_someone_else"}
        )
        self.assertEqual(status, 200)
        error = body["result"]["structuredContent"]["error"]
        self.assertEqual(error["code"], "resource_not_found")
        self.assertNotIn("someone_else", json.dumps(body))

        status, body, _ = self._mcp_call(
            "screen_stocks",
            {
                "filters": [
                    {"field": "Price_Close", "operator": "between", "value": [10]}
                ]
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["result"]["isError"])
        self.assertEqual(
            body["result"]["structuredContent"]["error"]["code"],
            "query_rejected",
        )

    def test_negative_3_pending_user_cannot_read_stock_data(self) -> None:
        status, body, _ = self._mcp_call(
            "get_connection_status", token=PENDING_TOKEN
        )
        self.assertEqual(status, 200)
        status_result = self._assert_success_schema("get_connection_status", body)
        self.assertEqual(status_result["status"], "pending")
        status, body, _ = self._mcp_call("screen_stocks", token=PENDING_TOKEN)
        self.assertEqual(status, 200)
        self.assertTrue(body["result"]["isError"])
        self.assertEqual(
            body["result"]["structuredContent"]["error"]["code"],
            "access_pending",
        )
        self.assertNotIn("rows", body["result"]["structuredContent"])

    def test_public_noauth_requires_no_token_and_publishes_noauth(self) -> None:
        with MockAnchisesAnalysisServices(access_mode="public_noauth") as services:
            refreshed = fetch_contract(
                f"{services.base_url}/mcp",
                base_contract=self.contract,
                expected_mode="public_noauth",
            )
            self.assertEqual(refreshed["source"]["sync_state"], "live")
            self.assertEqual(
                refreshed["source"]["instructions"],
                self.contract["source"]["instructions"],
            )
            self.assertEqual(len(refreshed["tools"]), 12)

            status, body, headers = _request(
                f"{services.base_url}/mcp",
                method="POST",
                payload={
                    "jsonrpc": "2.0",
                    "id": 20,
                    "method": "tools/call",
                    "params": {"name": "get_connection_status", "arguments": {}},
                },
            )
            self.assertEqual(status, 200)
            self.assertNotIn("WWW-Authenticate", headers)
            structured = body["result"]["structuredContent"]
            self.assertEqual(structured["status"], "active")
            self.assertEqual(structured["authentication"], "not_required")
            self.assertEqual(structured["coverage"], "all_supported_exchanges")
            self.assertEqual(structured["limits"]["rate"]["scope"], "global")

            status, listed, _ = _request(
                f"{services.base_url}/mcp",
                method="POST",
                payload={"jsonrpc": "2.0", "id": 21, "method": "tools/list", "params": {}},
            )
            self.assertEqual(status, 200)
            self.assertEqual(len(listed["result"]["tools"]), 12)
            for descriptor in listed["result"]["tools"]:
                self.assertEqual(descriptor["securitySchemes"], [{"type": "noauth"}])

            calls = [
                ("get_available_exchanges", {}),
                ("get_latest_dates", {"exchanges": ["NASDAQ", "ASX"]}),
                ("get_stock_schema", {"exchange": "NASDAQ"}),
                (
                    "list_stock_tables",
                    {
                        "exchanges": ["NASDAQ"],
                        "start_date": "2026-06-01",
                    "end_date": "2026-07-17",
                    },
                ),
                (
                    "get_table_schema",
                    {"tables": ["daily_20260717_nasdaq"]},
                ),
                ("screen_stocks", {"filters": []}),
                ("validate_readonly_sql", {"sql": "SELECT 1"}),
                (
                    "run_readonly_sql",
                    {
                        "sql": (
                            "SELECT ticker, price_close "
                            "FROM daily_20260717_nasdaq LIMIT 2"
                        )
                    },
                ),
                (
                    "resolve_company_identity",
                    {"query": "Apple", "purpose": "company_report"},
                ),
                (
                    "prepare_company_report_generation",
                    {
                        "exchange": "NASDAQ",
                        "ticker": "AAPL",
                        "company_name": "Apple Inc.",
                        "output_locale": "zh-CN",
                    },
                ),
                ("create_csv_export", {"query_id": "qry_screen_0001"}),
            ]
            for request_id, (tool_name, arguments) in enumerate(calls, start=22):
                with self.subTest(tool=tool_name):
                    status, body, headers = _request(
                        f"{services.base_url}/mcp",
                        method="POST",
                        payload={
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "method": "tools/call",
                            "params": {
                                "name": tool_name,
                                "arguments": arguments,
                            },
                        },
                    )
                    self.assertEqual(status, 200)
                    self.assertNotIn("WWW-Authenticate", headers)
                    self.assertFalse(body["result"]["isError"])
                    Draft202012Validator(
                        descriptor_by_name(tool_name, self.contract)["outputSchema"],
                        format_checker=FormatChecker(),
                    ).validate(body["result"]["structuredContent"])

    def test_closed_mode_returns_503_and_exposes_no_oauth_metadata(self) -> None:
        with MockAnchisesAnalysisServices(access_mode="closed") as services:
            with self.assertRaises(MCPServiceClosedError):
                fetch_contract(
                    f"{services.base_url}/mcp",
                    base_contract=self.contract,
                    expected_mode="closed",
                )

            status, body, _ = _request(
                f"{services.base_url}/mcp",
                method="POST",
                payload={
                    "jsonrpc": "2.0",
                    "id": 30,
                    "method": "initialize",
                    "params": {},
                },
            )
            self.assertEqual(status, 503)
            self.assertEqual(body["error"], "service_unavailable")

            status, body, _ = _request(
                f"{services.base_url}/mcp/.well-known/oauth-protected-resource"
            )
            self.assertEqual(status, 404)
            self.assertEqual(body["error"], "not_found")

            status, body, _ = _request(
                f"{services.base_url}/downloads/exp_mock.csv?sig=mock"
            )
            self.assertEqual(status, 404)
            self.assertEqual(body["error"], "not_found")

    def test_auth0_rejects_an_invalid_pkce_verifier(self) -> None:
        verifier = "correct-verifier-with-sufficient-entropy-0123456789"
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")
        redirect_uri = "https://chatgpt.com/connector/oauth/mock-callback"
        status, _, headers = _request(
            f"{self.services.base_url}/auth/authorize?"
            + urlencode(
                {
                    "response_type": "code",
                    "client_id": "https://chatgpt.com/oauth/mock/client.json",
                    "redirect_uri": redirect_uri,
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                    "resource": f"{self.services.base_url}/mcp",
                    "state": "pkce-negative",
                }
            ),
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        code = parse_qs(urlsplit(headers["Location"]).query)["code"][0]
        status, body, _ = _request(
            f"{self.services.base_url}/auth/oauth/token",
            method="POST",
            form={
                "grant_type": "authorization_code",
                "client_id": "https://chatgpt.com/oauth/mock/client.json",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": "wrong-verifier",
                "resource": f"{self.services.base_url}/mcp",
            },
        )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "invalid_grant")

    def test_internal_stock_api_accepts_only_backend_delegation(self) -> None:
        status, body, _ = _request(
            f"{self.services.base_url}/stock-api/v1/screen",
            method="POST",
            headers={"Authorization": f"Bearer {ACTIVE_TOKEN}"},
            payload={"request_id": "req_user_token"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "invalid_internal_token")
        status, body, _ = _request(
            f"{self.services.base_url}/stock-api/v1/screen",
            method="POST",
            headers={"Authorization": f"Bearer {INTERNAL_TOKEN}"},
            payload={"request_id": "req_internal_001"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["request_id"], "req_internal_001")
        self.assertEqual(len(body["data"]["rows"]), 2)
        status, body, _ = _request(
            f"{self.services.base_url}/stock-api/v1/exchanges",
            headers={"Authorization": f"Bearer {INTERNAL_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            [item["code"] for item in body["data"]["exchanges"]],
            ["ASX", "CSE", "NASDAQ", "NYSE", "TSX", "TSXV"],
        )


if __name__ == "__main__":
    unittest.main()
