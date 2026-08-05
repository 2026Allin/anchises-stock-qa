"""In-process Auth0, Hosted MCP, and internal Stock Data API test doubles."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import threading
from contextlib import AbstractContextManager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import parse_qs, urlencode, urlsplit


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "plugins" / "anchises-analysis" / "contracts"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "mock_backend_data.json"
CLIENT_RELEASE_PATH = (
    ROOT
    / "plugins"
    / "anchises-analysis"
    / "skills"
    / "anchises-analysis"
    / "references"
    / "client-release.json"
)

import sys

if str(CONTRACTS) not in sys.path:
    sys.path.insert(0, str(CONTRACTS))

from hosted_contract import (  # noqa: E402
    PROFILE_AUTHENTICATED,
    PROFILE_UNAVAILABLE,
    ContractError,
    load_contract,
    mode_profile,
    tool_descriptors,
)


ACTIVE_TOKEN = "mock-access-token-active"
PENDING_TOKEN = "mock-access-token-pending"
INTERNAL_TOKEN = "mock-internal-delegation"
AUTHORIZATION_CODE = "mock-authorization-code"


def _rehash_contract(contract: Dict[str, Any]) -> None:
    canonical = json.dumps(
        contract["tools"], sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    contract["source"]["descriptor_sha256"] = hashlib.sha256(canonical).hexdigest()


def _with_client_update_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    """Return an in-memory MCP 0.7.2 / contract 1.8 mock descriptor."""

    future = copy.deepcopy(contract)
    future["contract_version"] = "1.8.0-draft"
    future["source"]["server_version"] = "0.7.2"
    status = next(
        tool for tool in future["tools"] if tool["name"] == "get_connection_status"
    )
    status["inputSchema"] = {
        "type": "object",
        "properties": {
            "client": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "minLength": 1, "maxLength": 128},
                    "platform": {"type": "string", "minLength": 1, "maxLength": 128},
                    "version": {"type": "string", "minLength": 1, "maxLength": 128},
                    "release_id": {"type": "string", "minLength": 1, "maxLength": 128},
                    "channel": {"type": "string", "minLength": 1, "maxLength": 128},
                },
                "additionalProperties": False,
                "required": [
                    "name",
                    "platform",
                    "version",
                    "release_id",
                    "channel",
                ],
            }
        },
        "additionalProperties": False,
        "description": (
            "Optionally publish the installed Anchises Analysis client release. "
            "Missing or unrecognized client metadata returns update status unknown."
        ),
    }
    update_fields = {
        "installed_version",
        "installed_release_id",
        "latest_version",
        "latest_release_id",
        "minimum_supported_version",
        "channel",
        "summary",
    }
    client_update = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": [
                    "current",
                    "update_available",
                    "unsupported",
                    "unknown",
                ],
            },
            **{
                field: {"type": ["string", "null"]}
                for field in sorted(update_fields)
            },
        },
        "additionalProperties": False,
        "required": ["status", *sorted(update_fields)],
    }
    status["outputSchema"]["properties"]["client_update"] = client_update
    status["outputSchema"]["required"].append("client_update")
    _rehash_contract(future)
    return future


def _base64url_sha256(value: str) -> str:
    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


class MockServiceHandler(BaseHTTPRequestHandler):
    server_version = "AnchisesAnalysisMock/0.7.1"

    @property
    def base_url(self) -> str:
        return self.server.base_url  # type: ignore[attr-defined]

    @property
    def fixture(self) -> Dict[str, Any]:
        return self.server.fixture  # type: ignore[attr-defined]

    @property
    def access_mode(self) -> str:
        return self.server.access_mode  # type: ignore[attr-defined]

    @property
    def data_policy_mode(self) -> str:
        return self.server.data_policy_mode  # type: ignore[attr-defined]

    @property
    def access_profile(self) -> str:
        return mode_profile(
            self.server.contract,  # type: ignore[attr-defined]
            self.access_mode,
        )

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(
        self,
        status: int,
        payload: Dict[str, Any],
        *,
        headers: Dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _text(
        self,
        status: int,
        body: str,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8") or "{}")

    def _read_form(self) -> Dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        parsed = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}

    def _token(self) -> str:
        value = self.headers.get("Authorization", "")
        return value[7:] if value.startswith("Bearer ") else ""

    def _protected_resource(self) -> Dict[str, Any]:
        return {
            "resource": f"{self.base_url}/mcp",
            "authorization_servers": [f"{self.base_url}/auth/"],
            "scopes_supported": ["stock.read", "schema.read", "export.create"],
            "resource_documentation": "https://anchisesdata.com/stock-qa",
        }

    def _discovery(self) -> Dict[str, Any]:
        return {
            "issuer": f"{self.base_url}/auth/",
            "authorization_endpoint": f"{self.base_url}/auth/authorize",
            "token_endpoint": f"{self.base_url}/auth/oauth/token",
            "jwks_uri": f"{self.base_url}/auth/.well-known/jwks.json",
            "client_id_metadata_document_supported": True,
            "token_endpoint_auth_methods_supported": ["none", "private_key_jwt"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": [
                "openid",
                "email",
                "profile",
                "stock.read",
                "schema.read",
                "export.create",
            ],
        }

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        path = parsed.path

        if path == "/mcp/.well-known/oauth-protected-resource":
            if self.access_profile != PROFILE_AUTHENTICATED:
                self._json(404, {"error": "not_found"})
                return
            self._json(200, self._protected_resource())
            return
        if path in {
            "/auth/.well-known/openid-configuration",
            "/auth/.well-known/oauth-authorization-server",
        }:
            self._json(200, self._discovery())
            return
        if path == "/auth/.well-known/jwks.json":
            self._json(
                200,
                {
                    "keys": [
                        {
                            "kty": "RSA",
                            "use": "sig",
                            "alg": "RS256",
                            "kid": "mock-key-1",
                            "n": "sXchMockPublicModulusForContractTestsOnly",
                            "e": "AQAB",
                        }
                    ]
                },
            )
            return
        if path == "/auth/authorize":
            query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
            required = {
                "response_type",
                "client_id",
                "redirect_uri",
                "code_challenge",
                "code_challenge_method",
                "resource",
                "state",
            }
            if required - set(query) or query.get("response_type") != "code":
                self._json(400, {"error": "invalid_request"})
                return
            if query.get("code_challenge_method") != "S256":
                self._json(400, {"error": "invalid_request", "error_description": "S256 required"})
                return
            self.server.authorization_codes[AUTHORIZATION_CODE] = {  # type: ignore[attr-defined]
                "challenge": query["code_challenge"],
                "resource": query["resource"],
                "redirect_uri": query["redirect_uri"],
            }
            location = query["redirect_uri"] + "?" + urlencode(
                {"code": AUTHORIZATION_CODE, "state": query["state"]}
            )
            self.send_response(302)
            self.send_header("Location", location)
            self.end_headers()
            return
        if path == "/stock-api/v1/exchanges":
            if self._token() != INTERNAL_TOKEN:
                self._json(401, {"error": "invalid_internal_token"})
                return
            self._json(200, {"ok": True, "data": {"exchanges": self.fixture["exchanges"]}})
            return
        if path == "/downloads/exp_mock.csv":
            if self.access_profile == PROFILE_UNAVAILABLE:
                self._json(404, {"error": "not_found"})
                return
            self._text(
                200,
                "ticker,exchange,price_close\nAAPL,NASDAQ,212.5\nBGL,ASX,1.52\n",
                "text/csv; charset=utf-8",
            )
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        if parsed.path == "/auth/oauth/token":
            self._handle_token()
            return
        if parsed.path == "/mcp":
            self._handle_mcp()
            return
        if parsed.path == "/stock-api/v1/screen":
            if self._token() != INTERNAL_TOKEN:
                self._json(401, {"error": "invalid_internal_token"})
                return
            payload = self._read_json()
            self._json(
                200,
                {
                    "ok": True,
                    "request_id": payload.get("request_id", "req_internal_001"),
                    "data": {"rows": self.fixture["screen_rows"]},
                },
            )
            return
        self._json(404, {"error": "not_found"})

    def _handle_token(self) -> None:
        form = self._read_form()
        code = self.server.authorization_codes.get(form.get("code", ""))  # type: ignore[attr-defined]
        if (
            form.get("grant_type") != "authorization_code"
            or not code
            or form.get("redirect_uri") != code["redirect_uri"]
            or form.get("resource") != code["resource"]
            or _base64url_sha256(form.get("code_verifier", "")) != code["challenge"]
        ):
            self._json(400, {"error": "invalid_grant"})
            return
        self._json(
            200,
            {
                "access_token": ACTIVE_TOKEN,
                "token_type": "Bearer",
                "expires_in": 1800,
                "scope": "openid email profile stock.read schema.read export.create",
                "id_token": "mock-id-token",
            },
        )

    def _auth_challenge(self, request_id: Any) -> None:
        challenge = (
            f'Bearer resource_metadata="{self.base_url}/mcp/.well-known/oauth-protected-resource", '
            'error="invalid_token", error_description="Sign in to Anchises Analysis"'
        )
        self._json(
            401,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": "Authentication required."}],
                    "isError": True,
                    "_meta": {"mcp/www_authenticate": [challenge]},
                },
            },
            headers={"WWW-Authenticate": challenge},
        )

    def _handle_mcp(self) -> None:
        request = self._read_json()
        request_id = request.get("id")
        if self.access_profile == PROFILE_UNAVAILABLE:
            self._json(503, {"error": "service_unavailable"})
            return
        method = request.get("method")
        if method == "initialize":
            contract = self.server.contract  # type: ignore[attr-defined]
            self._json(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {
                            "name": contract["source"]["server_name"],
                            "version": contract["source"]["server_version"],
                        },
                        "instructions": contract["source"]["instructions"],
                    },
                },
            )
            return
        if method == "tools/list":
            self._json(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": tool_descriptors(
                            self.server.contract,  # type: ignore[attr-defined]
                            access_mode=self.access_mode,
                        )
                    },
                },
            )
            return
        if method == "notifications/initialized":
            self._json(200, {})
            return
        if method != "tools/call":
            self._json(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": "Method not found"},
                },
            )
            return

        token = self._token()
        if self.access_mode == "oauth" and token not in {ACTIVE_TOKEN, PENDING_TOKEN}:
            self._auth_challenge(request_id)
            return
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        self.server.tool_calls.append(  # type: ignore[attr-defined]
            {"name": tool_name, "arguments": copy.deepcopy(arguments)}
        )
        if self.access_mode == "oauth" and token == PENDING_TOKEN and tool_name != "get_connection_status":
            self._tool_error(request_id, "access_pending", "Access approval is pending.")
            return
        response = self._tool_response(tool_name, arguments, token)
        if isinstance(response, tuple):
            code, message = response
            self._tool_error(request_id, code, message)
            return
        self._json(
            200,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": f"{tool_name} completed."}],
                    "structuredContent": response,
                    "isError": False,
                },
            },
        )

    def _envelope(
        self,
        data: Dict[str, Any],
        *,
        page: Dict[str, Any] | None = None,
        data_date: str | None = None,
    ) -> Dict[str, Any]:
        result = {
            "data_date": data_date if data_date is not None else self.fixture["data_date"],
            "data": data,
            "warnings": [],
            "quota": {
                "scope": (
                    "global" if self.access_mode == "public_noauth" else "user"
                ),
                "remaining": 59,
                "limit": 60,
                "period_seconds": 60,
                "reset_at": "2026-07-16T07:00:00Z",
            },
        }
        if page is not None:
            result["page"] = page
        return result

    @staticmethod
    def _policy_limits(mode: str) -> Dict[str, Any]:
        if mode == "bulk_enabled":
            return {
                "max_rows": 200000,
                "max_columns": 100,
                "max_cells": 20000000,
                "max_bytes": 50000000,
                "max_top_n": None,
                "max_explicit_tickers": None,
                "max_partitions": 1000,
                "complete_exchange_day_allowed": True,
                "sql_export_allowed": True,
            }
        return {
            "max_rows": 1000,
            "max_columns": 25,
            "max_cells": 20000,
            "max_bytes": 30000000,
            "max_top_n": 200,
            "max_explicit_tickers": 50,
            "max_partitions": 1000,
            "complete_exchange_day_allowed": False,
            "sql_export_allowed": False,
        }

    def _data_policy(self) -> Dict[str, Any]:
        return {
            "mode": self.data_policy_mode,
            "restrictions": (
                "disabled" if self.data_policy_mode == "bulk_enabled" else "enabled"
            ),
            "policy_version": "stock-data-access-v2",
            "effective_limits": self._policy_limits(self.data_policy_mode),
        }

    def _client_update(self, arguments: Dict[str, Any]) -> Dict[str, Any] | None:
        if not self.server.client_update_enabled:  # type: ignore[attr-defined]
            return None
        client = arguments.get("client")
        valid = (
            isinstance(client, dict)
            and set(client)
            == {"name", "platform", "version", "release_id", "channel"}
            and client.get("name") == "anchises-analysis"
            and client.get("platform") == "codex"
            and isinstance(client.get("version"), str)
            and re.fullmatch(
                r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
                r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?",
                client["version"],
            )
            is not None
            and isinstance(client.get("release_id"), str)
            and re.fullmatch(r"codex\.\d{14}", client["release_id"]) is not None
            and client.get("channel") == "qa-v2-auth"
        )
        if not valid:
            return {
                "status": "unknown",
                "installed_version": None,
                "installed_release_id": None,
                "latest_version": None,
                "latest_release_id": None,
                "minimum_supported_version": None,
                "channel": None,
                "summary": None,
            }
        return {
            "status": self.server.client_update_status,  # type: ignore[attr-defined]
            "installed_version": client["version"],
            "installed_release_id": client["release_id"],
            "latest_version": self.server.latest_client_version,  # type: ignore[attr-defined]
            "latest_release_id": self.server.latest_client_release_id,  # type: ignore[attr-defined]
            "minimum_supported_version": self.server.minimum_client_version,  # type: ignore[attr-defined]
            "channel": client["channel"],
            "summary": self.server.client_update_summary,  # type: ignore[attr-defined]
        }

    @staticmethod
    def _analysis(
        matched: int | None,
        displayed: int,
        classification: str,
        *,
        offset: int,
        browsable_limit: int,
    ) -> Dict[str, Any]:
        displayed_start = offset + 1 if displayed else 0
        displayed_end = offset + displayed
        more_rows = matched is None or displayed_end < matched
        pagination_limit_reached = more_rows and displayed_end >= browsable_limit
        row_pagination_available = more_rows and not pagination_limit_reached
        if row_pagination_available:
            next_action = "call_same_tool_with_cursor"
        elif pagination_limit_reached:
            next_action = "refine_query"
        else:
            next_action = "none"
        return {
            "matched_row_count": matched,
            "displayed_row_count": displayed,
            "display_row_limit": 200,
            "result_is_preview": more_rows,
            "row_pagination_available": row_pagination_available,
            "displayed_row_start": displayed_start,
            "displayed_row_end": displayed_end,
            "browsable_row_limit": browsable_limit,
            "pagination_limit_reached": pagination_limit_reached,
            "pagination_next_action": next_action,
            "server_side_analysis_supported": True,
            "query_classification": classification,
        }

    @staticmethod
    def _export_policy(
        *,
        mode: str,
        eligible: bool,
        classification: str,
        contains_complete_partition: bool | None,
        reasons: list[str],
    ) -> Dict[str, Any]:
        return {
            "mode": mode,
            "policy_version": "stock-data-access-v2",
            "eligible_by_query": eligible,
            "classification": classification,
            "contains_complete_partition": contains_complete_partition,
            "reasons": reasons,
            "source_tools_allowed": (
                ["screen_stocks", "run_readonly_sql"]
                if mode == "bulk_enabled"
                else ["screen_stocks"]
            ),
            "limits": MockServiceHandler._policy_limits(mode),
        }

    def _query_id(self, source_tool: str) -> str:
        self.server.query_counter += 1  # type: ignore[attr-defined]
        source = "screen" if source_tool == "screen_stocks" else "sql"
        return f"qry_{source}_{self.server.query_counter:08d}"  # type: ignore[attr-defined]

    def _encode_cursor(self, query_id: str, source_tool: str, offset: int) -> str:
        payload = json.dumps(
            {
                "epoch": self.server.policy_epoch,  # type: ignore[attr-defined]
                "offset": offset,
                "query_id": query_id,
                "source_tool": source_tool,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        signature = hashlib.sha256(
            payload + self.server.cursor_secret  # type: ignore[attr-defined]
        ).hexdigest()[:24]
        return f"cur_{encoded}.{signature}"

    def _decode_cursor(
        self,
        cursor: Any,
        source_tool: str,
    ) -> Dict[str, Any] | Tuple[str, str]:
        try:
            prefix, signature = str(cursor).split(".", 1)
            if not prefix.startswith("cur_"):
                raise ValueError
            encoded = prefix[4:]
            payload = base64.urlsafe_b64decode(
                encoded + "=" * (-len(encoded) % 4)
            )
            expected = hashlib.sha256(
                payload + self.server.cursor_secret  # type: ignore[attr-defined]
            ).hexdigest()[:24]
            if signature != expected:
                raise ValueError
            decoded = json.loads(payload.decode("utf-8"))
        except (ValueError, TypeError, json.JSONDecodeError):
            return "query_rejected", "The opaque cursor is invalid."
        if decoded.get("source_tool") != source_tool:
            return "query_rejected", "The cursor belongs to another tool."
        if decoded.get("epoch") != self.server.policy_epoch:  # type: ignore[attr-defined]
            return "query_policy_expired", "The query policy changed; rerun the original query."
        query = self.server.queries.get(decoded.get("query_id"))  # type: ignore[attr-defined]
        if query is None or query.get("epoch") != self.server.policy_epoch:  # type: ignore[attr-defined]
            return "query_policy_expired", "The query policy changed; rerun the original query."
        decoded["query"] = query
        return decoded

    @staticmethod
    def _repeat_rows(source_rows: list[Dict[str, Any]], total: int) -> list[Dict[str, Any]]:
        rows: list[Dict[str, Any]] = []
        for index in range(total):
            row = copy.deepcopy(source_rows[index % len(source_rows)])
            if index >= len(source_rows):
                row["ticker"] = f"MOCK{index + 1:06d}"
                if "name" in row:
                    row["name"] = f"Mock Company {index + 1}"
            rows.append(row)
        return rows

    def _render_query_page(
        self,
        query: Dict[str, Any],
        *,
        offset: int,
        page_size: int,
    ) -> Dict[str, Any]:
        browsable_limit = int(query["browsable_limit"])
        page_end = min(offset + page_size, len(query["rows"]), browsable_limit)
        page_rows = query["rows"][offset:page_end]
        analysis = self._analysis(
            query["matched"],
            len(page_rows),
            query["classification"],
            offset=offset,
            browsable_limit=browsable_limit,
        )
        next_cursor = None
        if analysis["pagination_next_action"] == "call_same_tool_with_cursor":
            next_cursor = self._encode_cursor(
                query["query_id"],
                query["source_tool"],
                page_end,
            )
        return self._envelope(
            {
                "query_id": query["query_id"],
                "columns": query["columns"],
                "rows": page_rows,
                "analysis": analysis,
                "export_policy": query["policy"],
            },
            page={
                "row_count": len(page_rows),
                "next_cursor": next_cursor,
                "total_count": query["matched"],
                "truncated": analysis["result_is_preview"],
            },
        )

    def _tool_response(
        self,
        name: str,
        arguments: Dict[str, Any],
        token: str,
    ) -> Dict[str, Any] | Tuple[str, str]:
        if name == "get_connection_status":
            if not self.server.client_update_enabled and arguments:  # type: ignore[attr-defined]
                return "query_rejected", "This contract accepts no status arguments."
            client_update = self._client_update(arguments)
            if self.access_mode == "public_noauth":
                result = {
                    "status": "active",
                    "message": "Public access is available. No sign-in is required.",
                    "access_request_url": None,
                    "authentication": "not_required",
                    "coverage": "all_supported_exchanges",
                    "limits": {
                        "rate": {
                            "scope": "global",
                            "limit": 60,
                            "period_seconds": 60,
                        },
                        "concurrency": {"scope": "global", "limit": 2},
                        "query": {"timeout_seconds": 200, "max_rows": 200000},
                        "csv": {"max_bytes": 50000000},
                    },
                    "data_policy": self._data_policy(),
                }
                if client_update is not None:
                    result["client_update"] = client_update
                return result
            status = "active" if token == ACTIVE_TOKEN else "pending"
            result = {
                "status": status,
                "message": "Access is active." if status == "active" else "Approval is pending.",
                "access_request_url": (
                    None if status == "active" else "https://account.anchisesdata.com/access"
                ),
                "authentication": "oauth",
                "coverage": "approved_stock_data" if status == "active" else None,
                "limits": (
                    {
                        "rate": {
                            "scope": "user",
                            "limit": 60,
                            "period_seconds": 60,
                        },
                            "concurrency": {"scope": "user", "limit": 2},
                            "query": {"timeout_seconds": 200, "max_rows": 200000},
                            "csv": {"max_bytes": 50000000},
                        }
                    if status == "active"
                    else None
                ),
                "data_policy": self._data_policy() if status == "active" else None,
            }
            if client_update is not None:
                result["client_update"] = client_update
            return result
        if name == "get_available_exchanges":
            return self._envelope({"exchanges": self.fixture["exchanges"]})
        if name == "get_latest_dates":
            requested = set(arguments.get("exchanges") or [])
            latest_dates = {
                item["exchange"]: item["latest_date"]
                for item in self.fixture["latest_dates"]
                if not requested or item["exchange"] in requested
            }
            return self._envelope({"latest_dates": latest_dates})
        if name == "get_stock_schema":
            return self._envelope({"fields": self.fixture["fields"]})
        if name == "list_stock_tables":
            tables = [item["table_name"] for item in self.fixture["tables"]]
            return self._envelope(
                {"tables": tables},
                page={
                    "row_count": len(tables),
                    "next_cursor": None,
                    "total_count": len(tables),
                    "truncated": False,
                },
            )
        if name == "get_table_schema":
            allowed = {item["table_name"] for item in self.fixture["tables"]}
            requested = arguments.get("tables") or []
            if any(table not in allowed for table in requested):
                return "resource_not_found", "Requested table is unavailable."
            return self._envelope(
                {
                    "tables": {
                        table: {"columns": self.fixture["table_columns"]}
                        for table in requested
                    }
                }
            )
        if name == "screen_stocks":
            cursor = arguments.get("cursor")
            if cursor:
                if set(arguments) - {"cursor", "page_size"}:
                    return (
                        "query_rejected",
                        "A continuation call accepts only cursor and page_size.",
                    )
                decoded = self._decode_cursor(cursor, "screen_stocks")
                if isinstance(decoded, tuple):
                    return decoded
                page_size = int(arguments.get("page_size", 200))
                if not 1 <= page_size <= 200:
                    return "query_rejected", "page_size must be between 1 and 200."
                return self._render_query_page(
                    decoded["query"],
                    offset=int(decoded["offset"]),
                    page_size=page_size,
                )

            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            as_of_date = arguments.get("as_of_date")
            if bool(start_date) != bool(end_date):
                return "query_rejected", "start_date and end_date must be provided together."
            if as_of_date and (start_date or end_date):
                return "query_rejected", "as_of_date cannot be combined with a date range."
            base_query_id = arguments.get("base_query_id")
            if base_query_id:
                base_query = self.server.queries.get(base_query_id)  # type: ignore[attr-defined]
                if (
                    base_query is None
                    or base_query.get("epoch") != self.server.policy_epoch  # type: ignore[attr-defined]
                ):
                    return (
                        "query_policy_expired",
                        "The base query policy changed; rerun the original query.",
                    )
            top_n = arguments.get("top_n")
            if top_n is not None and not arguments.get("sort"):
                return "query_rejected", "top_n requires an explicit sort."
            max_top_n = self._policy_limits(self.data_policy_mode)["max_top_n"]
            if top_n is not None and not 1 <= int(top_n) <= 200000:
                return "query_rejected", "top_n must be between 1 and 200000."
            if top_n is not None and max_top_n is not None and int(top_n) > max_top_n:
                return "query_rejected", "top_n exceeds the active data policy."
            page_size = int(arguments.get("page_size", 200))
            if not 1 <= page_size <= 200:
                return "query_rejected", "page_size must be between 1 and 200."

            filters = arguments.get("filters", [])
            for item in filters:
                if item.get("operator") == "between" and len(item.get("value", [])) != 2:
                    return "query_rejected", "between requires exactly two ordered values."

            ticker_count = 0
            for item in filters:
                if str(item.get("field", "")).casefold() != "ticker":
                    continue
                value = item.get("value")
                if item.get("operator") == "in" and isinstance(value, list):
                    ticker_count = len(value)
                elif item.get("operator") == "eq":
                    ticker_count = 1

            if top_n is not None:
                classification = "bounded_top_n"
                matched = int(top_n)
            elif ticker_count:
                classification = "ticker_list"
                matched = ticker_count
            elif filters:
                classification = "filtered"
                matched = (
                    1500
                    if any(
                        str(item.get("field", "")).casefold() == "market_cap"
                        for item in filters
                    )
                    else len(self.fixture["screen_rows"])
                )
            else:
                classification = "broad_preview"
                matched = 5000
            query_id = self._query_id("screen_stocks")

            exchanges = arguments.get("exchanges") or []
            contains_complete_partition = bool(
                len(exchanges) == 1
                and as_of_date
                and not filters
                and top_n is None
            )
            fields = arguments.get("fields") or []
            total_columns = len(fields) + 3
            reasons: list[str] = []
            limits = self._policy_limits(self.data_policy_mode)
            if self.data_policy_mode == "restricted":
                if contains_complete_partition:
                    reasons.append("export_complete_partition_not_allowed")
                elif classification == "broad_preview" or not fields:
                    reasons.append("export_requires_selective_query")
                elif ticker_count > int(limits["max_explicit_tickers"]):
                    reasons.append("export_ticker_limit_exceeded")
            if not reasons and total_columns > int(limits["max_columns"]):
                reasons.append("export_column_limit_exceeded")
            if not reasons and matched > int(limits["max_rows"]):
                reasons.append("export_row_limit_exceeded")
            if not reasons and matched * total_columns > int(limits["max_cells"]):
                reasons.append("export_cell_limit_exceeded")
            eligible = not reasons
            policy = self._export_policy(
                mode=self.data_policy_mode,
                eligible=eligible,
                classification=classification,
                contains_complete_partition=contains_complete_partition,
                reasons=reasons,
            )
            self.server.query_policies[query_id] = policy  # type: ignore[attr-defined]

            source_rows = self._repeat_rows(self.fixture["screen_rows"], matched)
            automatic_fields = ["exchange", "date", "ticker"]
            selected_fields = fields or [
                key for key in source_rows[0] if key not in automatic_fields
            ]
            columns = list(dict.fromkeys([*automatic_fields, *selected_fields]))
            projected_rows = [
                {key: row.get(key) for key in columns}
                for row in source_rows
            ]
            query = {
                "query_id": query_id,
                "source_tool": "screen_stocks",
                "rows": projected_rows,
                "columns": columns,
                "matched": matched,
                "classification": classification,
                "policy": policy,
                "epoch": self.server.policy_epoch,  # type: ignore[attr-defined]
                "browsable_limit": (
                    200000 if self.data_policy_mode == "bulk_enabled" else 1000
                ),
            }
            self.server.queries[query_id] = query  # type: ignore[attr-defined]
            return self._render_query_page(query, offset=0, page_size=page_size)
        if name == "validate_readonly_sql":
            sql = str(arguments.get("sql", "")).strip()
            denied = any(keyword in sql.lower() for keyword in ("update ", "delete ", "drop ", "insert "))
            return self._envelope(
                {
                    "valid": not denied,
                    "normalized_sql": sql if not denied else None,
                    "errors": ["Only SELECT or WITH...SELECT is allowed."] if denied else [],
                    "warnings": [],
                }
            )
        if name == "run_readonly_sql":
            cursor = arguments.get("cursor")
            if cursor:
                if set(arguments) - {"cursor", "max_rows"}:
                    return (
                        "query_rejected",
                        "A continuation call accepts only cursor and max_rows.",
                    )
                decoded = self._decode_cursor(cursor, "run_readonly_sql")
                if isinstance(decoded, tuple):
                    return decoded
                max_rows = int(arguments.get("max_rows", 200))
                if not 1 <= max_rows <= 200:
                    return "query_rejected", "max_rows must be between 1 and 200."
                return self._render_query_page(
                    decoded["query"],
                    offset=int(decoded["offset"]),
                    page_size=max_rows,
                )

            sql = str(arguments.get("sql", "")).strip()
            if not sql:
                return "query_rejected", "sql is required on the first call."
            if any(keyword in sql.lower() for keyword in ("update ", "delete ", "drop ", "insert ")):
                return "query_rejected", "Only bounded read-only stock queries are allowed."
            if re.search(r"\boffset\b", sql, flags=re.IGNORECASE):
                return "query_rejected", "SQL OFFSET is not allowed; use the opaque cursor."
            max_rows = int(arguments.get("max_rows", 200))
            if not 1 <= max_rows <= 200:
                return "query_rejected", "max_rows must be between 1 and 200."

            limit_match = re.search(r"\blimit\s+(\d+)\b", sql, flags=re.IGNORECASE)
            if "count(" in sql.casefold():
                matched = 1
            elif limit_match:
                matched = min(int(limit_match.group(1)), 200000)
            else:
                matched = len(self.fixture["sql_rows"])
            rows = self._repeat_rows(self.fixture["sql_rows"], matched)
            query_id = self._query_id("run_readonly_sql")
            limits = self._policy_limits(self.data_policy_mode)
            reasons: list[str] = []
            if not limits["sql_export_allowed"]:
                reasons.append("query_not_exportable")
            elif matched > int(limits["max_rows"]):
                reasons.append("export_row_limit_exceeded")
            elif matched * len(rows[0]) > int(limits["max_cells"]):
                reasons.append("export_cell_limit_exceeded")
            policy = self._export_policy(
                mode=self.data_policy_mode,
                eligible=not reasons,
                classification="sql_analysis",
                contains_complete_partition=None,
                reasons=reasons,
            )
            self.server.query_policies[query_id] = policy  # type: ignore[attr-defined]
            has_stable_order = bool(re.search(r"\border\s+by\b", sql, flags=re.IGNORECASE))
            query = {
                "query_id": query_id,
                "source_tool": "run_readonly_sql",
                "rows": rows,
                "columns": list(rows[0]),
                "matched": matched,
                "classification": "sql_analysis",
                "policy": policy,
                "epoch": self.server.policy_epoch,  # type: ignore[attr-defined]
                "browsable_limit": (
                    200000
                    if self.data_policy_mode == "bulk_enabled" and has_stable_order
                    else 1000
                    if has_stable_order
                    else max_rows
                ),
            }
            self.server.queries[query_id] = query  # type: ignore[attr-defined]
            return self._render_query_page(query, offset=0, page_size=max_rows)
        if name == "resolve_company_identity":
            query = str(arguments.get("query", "")).strip()
            if not query:
                return "query_rejected", "query is required."
            purpose = str(arguments.get("purpose", "stock_data"))
            exchange_hint = str(arguments.get("exchange_hint") or "").upper()
            supported = {item["code"] for item in self.fixture["exchanges"]}
            matches: list[Dict[str, Any]] = []
            query_folded = query.casefold().rstrip(".")
            if not exchange_hint or exchange_hint in supported:
                for raw_company in self.fixture["companies"]:
                    company = copy.deepcopy(raw_company)
                    aliases = {
                        str(value).casefold().rstrip(".")
                        for value in company.pop("aliases", [])
                    }
                    ticker_folded = company["ticker"].casefold()
                    name_folded = company["company_name"].casefold().rstrip(".")
                    if exchange_hint and company["exchange"] != exchange_hint:
                        continue
                    if query_folded == ticker_folded:
                        match_type = "exact_ticker"
                    elif query_folded == name_folded:
                        match_type = "exact_name"
                    elif query_folded in aliases:
                        match_type = "normalized_name"
                    elif name_folded.startswith(query_folded):
                        match_type = "prefix_name"
                    elif query_folded in name_folded:
                        match_type = "contains_name"
                    else:
                        continue
                    matches.append(
                        {
                            "exchange": company["exchange"],
                            "ticker": company["ticker"],
                            "company_name": company["company_name"],
                            "website": company["website"],
                            "is_active": company["is_active"],
                            "instrument_type": company["instrument_type"],
                            "match_type": match_type,
                        }
                    )
            if len(matches) == 1:
                status = "resolved"
                company = matches[0]
                candidates: list[Dict[str, Any]] = []
                message = "A unique supported-market company identity was resolved."
            elif matches:
                status = "ambiguous"
                company = None
                candidates = matches
                message = "Multiple supported-market securities match the query."
            else:
                status = "not_found_in_supported_markets"
                company = None
                candidates = []
                message = "No match was found in the six supported exchange masters."
            return self._envelope(
                {
                    "status": status,
                    "query": query,
                    "purpose": purpose,
                    "company": company,
                    "candidates": candidates,
                    "message": message,
                }
            )
        if name == "prepare_company_report_generation":
            exchange = str(arguments.get("exchange", "")).upper()
            ticker = str(arguments.get("ticker", "")).upper()
            company_name = str(arguments.get("company_name", "")).strip()
            output_locale = str(arguments.get("output_locale", ""))
            if not all((exchange, ticker, company_name, output_locale)):
                return "query_rejected", "All four company-report fields are required."
            fixture = next(
                (
                    copy.deepcopy(item)
                    for item in self.fixture["companies"]
                    if item["exchange"] == exchange and item["ticker"] == ticker
                ),
                None,
            )
            if fixture is None:
                company = {
                    "exchange": exchange,
                    "ticker": ticker,
                    "company_name": company_name,
                    "website": None,
                    "is_active": True,
                    "instrument_type": "unknown",
                    "company_type": "Operating Company",
                    "classifier_sector": None,
                    "classifier_industry": None,
                    "classifier_sector_updated_at": None,
                    "classifier_sector_source": None,
                    "instrument_verification_required": True,
                }
                identity_source = "host_supplied"
                listing_verification = True
                selected_sector = "Others"
            else:
                fixture.pop("aliases", None)
                company = fixture
                identity_source = "master"
                listing_verification = bool(
                    company["instrument_verification_required"]
                    or not company["is_active"]
                )
                selected_sector = (
                    company["classifier_sector"]
                    if company["is_active"] and company["classifier_sector"]
                    else "Others"
                )
            if company["company_type"] == "Fund" or company["instrument_type"] in {
                "ETF",
                "Fund",
            }:
                return self._envelope(
                    {
                        "status": "not_eligible",
                        "message": "ETF and Fund records are not eligible for an operating-company report.",
                        "company": company,
                        "identity_source": identity_source,
                        "listing_status_verification_required": listing_verification,
                        "selected_sector": None,
                        "prompt_id": None,
                        "prompt_version": None,
                        "prompt_text": None,
                        "next_action": None,
                    }
                )
            prompt_id = (
                "mining_metals_exploration_company_search"
                if selected_sector == "Mining / Metals / Exploration"
                else "others_generic_company_search"
                if selected_sector == "Others"
                else "semiconductors_compute_advanced_hardware_company_search"
            )
            prompt_text = (
                "Use live web research and primary sources to prepare the report. "
                f"Company: {company['company_name']}. Exchange: {exchange}. "
                f"Ticker: {ticker}. Output locale: {output_locale}. Start with "
                "**Summary:** and use exactly these headings: "
                "### 1. Company Overview & Listing Profile; "
                "### 2. Business, Assets, Products or Operating Footprint; "
                "### 3. Market, Customers, Competitive Position & Regulatory Context; "
                "### 4. Recent Developments & Newsflow; "
                "### 5. Financial Position, Capital Structure & Trading Profile; "
                "### 6. Forward Plans, Catalysts & Execution Milestones; "
                "### 7. Risk Assessment. Cover cash, debt, warrants, dilution, and "
                "runway when material. End with **[Risk: Low]**, **[Risk: Medium]**, "
                "or **[Risk: High]**. Return the report only in this conversation and "
                "do not persist or publish it."
            )
            return self._envelope(
                {
                    "status": "ready",
                    "message": "The sector-specific host research prompt is ready.",
                    "company": company,
                    "identity_source": identity_source,
                    "listing_status_verification_required": listing_verification,
                    "selected_sector": selected_sector,
                    "prompt_id": prompt_id,
                    "prompt_version": "5.1",
                    "prompt_text": prompt_text,
                    "next_action": "run_host_web_research",
                }
            )
        if name == "create_csv_export":
            query_id = arguments.get("query_id")
            special_error = self.server.special_query_errors.get(query_id)  # type: ignore[attr-defined]
            if special_error:
                return special_error, "The export request does not satisfy the current query policy."
            policy = self.server.query_policies.get(query_id)  # type: ignore[attr-defined]
            if policy is None:
                return "resource_not_found", "Export source is unavailable."
            query = self.server.queries.get(query_id)  # type: ignore[attr-defined]
            if query is not None and query.get("epoch") != self.server.policy_epoch:  # type: ignore[attr-defined]
                return "query_policy_expired", "The query policy changed; rerun the original query."
            if (
                query is not None
                and query.get("source_tool") not in policy["source_tools_allowed"]
            ):
                return "query_not_exportable", "The active policy does not allow this source tool."
            if not policy["eligible_by_query"]:
                code = (
                    policy["reasons"][0]
                    if policy["reasons"]
                    else "export_requires_selective_query"
                )
                return code, "The result is still available for analysis but is not an exportable research subset."
            expires_in_seconds = arguments.get("expires_in_seconds", 3600)
            self.server.last_export_query_id = query_id  # type: ignore[attr-defined]
            expires_at = datetime(
                2026, 7, 14, 12, tzinfo=timezone.utc
            ) + timedelta(seconds=expires_in_seconds)
            return self._envelope(
                {
                    "export_id": "exp_mock",
                    "download_url": f"{self.base_url}/downloads/exp_mock.csv?sig=mock",
                    "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
                    "bytes": 62,
                }
            )
        return "resource_not_found", "Unknown tool."

    def _tool_error(self, request_id: Any, code: str, message: str) -> None:
        self._json(
            200,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": message}],
                    "structuredContent": {
                        "error": {
                            "code": code,
                            "message": message,
                            "retryable": code in {"rate_limited", "concurrency_limited", "temporarily_unavailable"},
                            "request_id": "req_mock_error_001",
                        }
                    },
                    "isError": True,
                },
            },
        )


class MockAnchisesAnalysisServices(AbstractContextManager["MockAnchisesAnalysisServices"]):
    """Run all external dependencies on one loopback HTTP server."""

    def __init__(
        self,
        *,
        access_mode: str = "oauth",
        data_policy_mode: str = "restricted",
        client_update_enabled: bool = False,
        client_update_status: str = "current",
        latest_client_version: str | None = None,
        latest_client_release_id: str | None = None,
        minimum_client_version: str | None = None,
        client_update_summary: str | None = None,
    ) -> None:
        contract = load_contract()
        if client_update_enabled:
            contract = _with_client_update_contract(contract)
        try:
            mode_profile(contract, access_mode)
        except ContractError as exc:
            raise ValueError(f"unsupported mock access mode: {access_mode}") from exc
        if data_policy_mode not in {"restricted", "bulk_enabled"}:
            raise ValueError(f"unsupported mock data policy mode: {data_policy_mode}")
        if client_update_status not in {
            "current",
            "update_available",
            "unsupported",
            "unknown",
        }:
            raise ValueError(f"unsupported client update status: {client_update_status}")
        client_release = json.loads(CLIENT_RELEASE_PATH.read_text(encoding="utf-8"))
        latest_client_version = latest_client_version or client_release["version"]
        latest_client_release_id = (
            latest_client_release_id or client_release["release_id"]
        )
        minimum_client_version = minimum_client_version or client_release["version"]
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), MockServiceHandler)
        host, port = self.httpd.server_address
        self.base_url = f"http://{host}:{port}"
        self.httpd.base_url = self.base_url  # type: ignore[attr-defined]
        self.httpd.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))  # type: ignore[attr-defined]
        self.httpd.contract = contract  # type: ignore[attr-defined]
        self.httpd.access_mode = access_mode  # type: ignore[attr-defined]
        self.httpd.data_policy_mode = data_policy_mode  # type: ignore[attr-defined]
        self.httpd.client_update_enabled = client_update_enabled  # type: ignore[attr-defined]
        self.httpd.client_update_status = client_update_status  # type: ignore[attr-defined]
        self.httpd.latest_client_version = latest_client_version  # type: ignore[attr-defined]
        self.httpd.latest_client_release_id = latest_client_release_id  # type: ignore[attr-defined]
        self.httpd.minimum_client_version = minimum_client_version  # type: ignore[attr-defined]
        self.httpd.client_update_summary = client_update_summary  # type: ignore[attr-defined]
        self.httpd.policy_epoch = 1  # type: ignore[attr-defined]
        self.httpd.cursor_secret = b"mock-cursor-secret"  # type: ignore[attr-defined]
        self.httpd.query_counter = 0  # type: ignore[attr-defined]
        self.httpd.queries = {}  # type: ignore[attr-defined]
        self.httpd.tool_calls = []  # type: ignore[attr-defined]
        self.httpd.last_export_query_id = None  # type: ignore[attr-defined]
        self.httpd.authorization_codes = {}  # type: ignore[attr-defined]
        self.httpd.query_policies = {  # type: ignore[attr-defined]
            "qry_screen_0001": MockServiceHandler._export_policy(
                mode=data_policy_mode,
                eligible=True,
                classification="filtered",
                contains_complete_partition=False,
                reasons=[],
            )
        }
        self.httpd.special_query_errors = {  # type: ignore[attr-defined]
            "qry_expired_policy_0001": "query_policy_expired",
            "qry_row_limit_0001": "export_row_limit_exceeded",
            "qry_column_limit_0001": "export_column_limit_exceeded",
            "qry_cell_limit_0001": "export_cell_limit_exceeded",
            "qry_complete_partition_0001": "export_complete_partition_not_allowed",
            "qry_topn_limit_0001": "export_top_n_limit_exceeded",
            "qry_ticker_limit_0001": "export_ticker_limit_exceeded",
            "qry_not_selective_0001": "export_requires_selective_query",
            "qry_partition_limit_0001": "query_partition_limit_exceeded",
            "qry_result_too_large_0001": "result_too_large",
            "qry_temp_unavailable_0001": "temporarily_unavailable",
        }
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def tool_calls(self) -> list[Dict[str, Any]]:
        return self.httpd.tool_calls  # type: ignore[attr-defined]

    def set_data_policy_mode(self, mode: str) -> None:
        if mode not in {"restricted", "bulk_enabled"}:
            raise ValueError(f"unsupported mock data policy mode: {mode}")
        if mode != self.httpd.data_policy_mode:  # type: ignore[attr-defined]
            self.httpd.data_policy_mode = mode  # type: ignore[attr-defined]
            self.httpd.policy_epoch += 1  # type: ignore[attr-defined]

    def __enter__(self) -> "MockAnchisesAnalysisServices":
        self.thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.httpd.shutdown()
        self.thread.join(timeout=5)
        self.httpd.server_close()
