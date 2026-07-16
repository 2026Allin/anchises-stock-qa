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

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "plugins" / "stock-data-desk" / "contracts"
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
    MockStockDataDeskServices,
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
        self.services = MockStockDataDeskServices().__enter__()

    def tearDown(self) -> None:
        self.services.__exit__(None, None, None)

    def _mcp_call(
        self,
        name: str,
        arguments: Dict[str, Any] | None = None,
        token: str = ACTIVE_TOKEN,
        request_id: int = 1,
    ) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        status, body, response_headers = _request(
            f"{self.services.base_url}/mcp",
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
        self.assertEqual(structured["access_policy"], "full_v1")

    def test_positive_2_market_discovery_and_latest_dates(self) -> None:
        status, body, _ = self._mcp_call("get_available_exchanges")
        self.assertEqual(status, 200)
        exchanges = self._assert_success_schema("get_available_exchanges", body)
        codes = [item["code"] for item in exchanges["data"]["exchanges"]]
        self.assertEqual(codes, ["NASDAQ", "ASX"])
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
            "filters": [
                {"field": "price_change_pct_30day", "operator": "gt", "value": 10}
            ],
            "sort": [{"field": "price_change_pct_30day", "direction": "desc"}],
            "page_size": 20,
        }
        Draft202012Validator(
            descriptor_by_name("screen_stocks", self.contract)["inputSchema"]
        ).validate(arguments)
        status, body, _ = self._mcp_call("screen_stocks", arguments)
        self.assertEqual(status, 200)
        structured = self._assert_success_schema("screen_stocks", body)
        self.assertEqual(structured["data"]["query_id"], "qry_screen_0001")
        self.assertEqual(structured["page"]["row_count"], 2)
        self.assertFalse(structured["page"]["truncated"])

    def test_mock_tools_list_matches_materialized_contract(self) -> None:
        status, body, _ = _request(
            f"{self.services.base_url}/mcp",
            method="POST",
            payload={"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}},
        )
        self.assertEqual(status, 200)
        tools = body["result"]["tools"]
        self.assertEqual(
            [tool["name"] for tool in tools],
            [tool["name"] for tool in self.contract["tools"]],
        )
        for tool in tools:
            Draft202012Validator.check_schema(tool["inputSchema"])
            Draft202012Validator.check_schema(tool["outputSchema"])
            self.assertEqual(tool["securitySchemes"][0]["type"], "oauth2")
            self.assertEqual(tool["_meta"]["securitySchemes"], tool["securitySchemes"])

    def test_positive_4_historical_schema_validation_and_sql(self) -> None:
        status, body, _ = self._mcp_call(
            "list_stock_tables",
            {"exchanges": ["NASDAQ"], "start_date": "2026-06-01", "end_date": "2026-07-10"},
        )
        self.assertEqual(status, 200)
        coverage = self._assert_success_schema("list_stock_tables", body)
        table_names = coverage["data"]["tables"][:2]
        status, body, _ = self._mcp_call("get_table_schema", {"tables": table_names})
        self.assertEqual(status, 200)
        self._assert_success_schema("get_table_schema", body)
        sql = "SELECT ticker, price_close FROM daily_20260710_nasdaq LIMIT 50"
        status, body, _ = self._mcp_call("validate_readonly_sql", {"sql": sql})
        self.assertEqual(status, 200)
        validation = self._assert_success_schema("validate_readonly_sql", body)
        self.assertTrue(validation["data"]["valid"])
        status, body, _ = self._mcp_call("run_readonly_sql", {"sql": sql, "max_rows": 50})
        self.assertEqual(status, 200)
        result = self._assert_success_schema("run_readonly_sql", body)
        self.assertEqual(result["data"]["query_id"], "qry_sql_0001")

    def test_positive_5_temporary_csv_export(self) -> None:
        status, body, _ = self._mcp_call(
            "create_csv_export",
            {"query_id": "qry_screen_0001", "expires_in_seconds": 600},
        )
        self.assertEqual(status, 200)
        export = self._assert_success_schema("create_csv_export", body)["data"]
        self.assertTrue(export["download_url"].startswith(self.services.base_url))
        status, csv_body, headers = _request(export["download_url"])
        self.assertEqual(status, 200)
        self.assertIn("text/csv", headers["Content-Type"])
        self.assertIn("MOCK,NASDAQ", csv_body)

    def test_positive_6_company_report_active_expired_not_found_and_pdf(self) -> None:
        status, body, _ = self._mcp_call(
            "get_latest_company_report",
            {"exchange": "ASX", "ticker": "BGL", "source": "auto", "pdf_range": "1Y"},
        )
        self.assertEqual(status, 200)
        active = self._assert_success_schema("get_latest_company_report", body)
        self.assertEqual(active["data"]["status"], "active")
        self.assertEqual(active["data"]["report"]["lang"], "en")
        self.assertEqual(active["data"]["report"]["source"], "macmini")
        self.assertFalse(active["data"]["content_truncated"])
        status, pdf, headers = _request(active["data"]["pdf_download_url"])
        self.assertEqual(status, 200)
        self.assertIn("application/pdf", headers["Content-Type"])
        self.assertTrue(pdf.startswith("%PDF"))

        status, body, _ = self._mcp_call(
            "get_latest_company_report", {"exchange": "ASX", "ticker": "OLD"}
        )
        expired = self._assert_success_schema("get_latest_company_report", body)
        self.assertEqual(expired["data"]["status"], "expired")
        self.assertTrue(expired["data"]["report"]["is_expired"])
        self.assertTrue(expired["warnings"])
        self.assertIsNotNone(expired["data"]["pdf_download_url"])

        status, body, _ = self._mcp_call(
            "get_latest_company_report", {"exchange": "ASX", "ticker": "NONE"}
        )
        missing = self._assert_success_schema("get_latest_company_report", body)
        self.assertEqual(missing["data"]["status"], "not_found")
        self.assertIsNone(missing["data"]["report"])
        self.assertIsNone(missing["data"]["pdf_download_url"])

    def test_company_report_truncation_is_explicit_and_projection_is_safe(self) -> None:
        status, body, _ = self._mcp_call(
            "get_latest_company_report", {"exchange": "ASX", "ticker": "LONG"}
        )
        self.assertEqual(status, 200)
        structured = self._assert_success_schema("get_latest_company_report", body)
        self.assertTrue(structured["data"]["content_truncated"])
        report = structured["data"]["report"]
        content_chars = len(report["summary"]) + sum(
            len(section["body"]) for section in report["sections"]
        )
        self.assertEqual(content_chars, 50_000)
        serialized = json.dumps(structured["data"]["report"]).lower()
        for forbidden in ("raw_markdown", "model_usage", "search_events", "127.0.0.1"):
            self.assertNotIn(forbidden, serialized)

    def test_negative_1_unauthenticated_call_returns_oauth_challenge(self) -> None:
        status, body, headers = self._mcp_call("get_connection_status", token="")
        self.assertEqual(status, 401)
        self.assertIn("resource_metadata=", headers["WWW-Authenticate"])
        challenges = body["result"]["_meta"]["mcp/www_authenticate"]
        self.assertIn("invalid_token", challenges[0])
        self.assertNotIn("access_token", json.dumps(body).lower())

    def test_negative_2_write_sql_and_cross_user_export_are_safe(self) -> None:
        status, body, _ = self._mcp_call(
            "run_readonly_sql",
            {"sql": "UPDATE daily_20260710_nasdaq SET price_close = 0"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["result"]["isError"])
        self.assertEqual(
            body["result"]["structuredContent"]["error"]["code"],
            "query_rejected",
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

    def test_anonymous_dev_requires_no_token_and_publishes_noauth(self) -> None:
        with MockStockDataDeskServices(access_mode="anonymous_dev") as services:
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
            self.assertEqual(structured["access_policy"], "anonymous_dev_v1")

            status, listed, _ = _request(
                f"{services.base_url}/mcp",
                method="POST",
                payload={"jsonrpc": "2.0", "id": 21, "method": "tools/list", "params": {}},
            )
            self.assertEqual(status, 200)
            self.assertEqual(len(listed["result"]["tools"]), 11)
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
                        "end_date": "2026-07-10",
                    },
                ),
                (
                    "get_table_schema",
                    {"tables": ["daily_20260710_nasdaq"]},
                ),
                ("screen_stocks", {"filters": []}),
                ("validate_readonly_sql", {"sql": "SELECT 1"}),
                (
                    "run_readonly_sql",
                    {
                        "sql": (
                            "SELECT ticker, price_close "
                            "FROM daily_20260710_nasdaq LIMIT 2"
                        )
                    },
                ),
                (
                    "get_latest_company_report",
                    {"exchange": "ASX", "ticker": "BGL"},
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
        with MockStockDataDeskServices(access_mode="closed") as services:
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
        self.assertEqual([item["code"] for item in body["data"]["exchanges"]], ["NASDAQ", "ASX"])


if __name__ == "__main__":
    unittest.main()
