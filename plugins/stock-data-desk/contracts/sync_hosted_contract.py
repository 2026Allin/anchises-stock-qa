#!/usr/bin/env python3
"""Synchronize the checked-in Hosted MCP descriptor snapshot.

The command performs read-only JSON-RPC calls against the public Streamable HTTP
endpoint.  It never sends credentials and never mutates the Hosted MCP service.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from hosted_contract import ContractError, load_contract, validate_contract


DEFAULT_ENDPOINT = "https://mcp.anchisesdata.com/mcp"
DEFAULT_OUTPUT = Path(__file__).with_name("hosted-mcp-v1.json")
MCP_PROTOCOL_VERSION = "2025-06-18"
REQUEST_TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
EXPECTED_TOOLS = [
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
]
OAUTH_SCOPES = {
    "get_connection_status": [],
    "get_available_exchanges": ["stock.read"],
    "get_latest_dates": ["stock.read"],
    "get_stock_schema": ["schema.read"],
    "list_stock_tables": ["schema.read"],
    "get_table_schema": ["schema.read"],
    "screen_stocks": ["stock.read"],
    "validate_readonly_sql": ["stock.read"],
    "run_readonly_sql": ["stock.read"],
    "get_latest_company_report": ["stock.read"],
    "create_csv_export": ["export.create"],
}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _validated_endpoint(endpoint: str) -> str:
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError(f"invalid MCP endpoint: {exc}") from exc
    if not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError("MCP endpoint must have a hostname and no embedded credentials")
    if parsed.query or parsed.fragment:
        raise RuntimeError("MCP endpoint must not contain a query string or fragment")
    is_loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and is_loopback):
        raise RuntimeError("MCP endpoint must use HTTPS (HTTP is allowed only on loopback)")
    if port is not None and not 1 <= port <= 65535:
        raise RuntimeError("MCP endpoint port is out of range")
    return endpoint


def _read_limited(response: Any) -> str:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise RuntimeError("MCP response has an invalid Content-Length") from exc
        if declared_size > MAX_RESPONSE_BYTES:
            raise RuntimeError(
                f"MCP response exceeds {MAX_RESPONSE_BYTES} byte contract-sync limit"
            )
    body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError(
            f"MCP response exceeds {MAX_RESPONSE_BYTES} byte contract-sync limit"
        )
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("MCP response is not valid UTF-8") from exc


def _jsonrpc_messages(body: str) -> list[dict[str, Any]]:
    stripped = body.lstrip()
    if not stripped:
        return []

    raw_messages: list[Any]
    if stripped.startswith(("{", "[")):
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"MCP returned invalid JSON: {exc}") from exc
        raw_messages = payload if isinstance(payload, list) else [payload]
    else:
        raw_messages = []
        data_lines: list[str] = []

        def flush_event() -> None:
            if not data_lines:
                return
            data = "\n".join(data_lines)
            data_lines.clear()
            try:
                raw_messages.append(json.loads(data))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"MCP returned invalid SSE JSON data: {exc}") from exc

        for line in [*body.splitlines(), ""]:
            if not line:
                flush_event()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())

    if not raw_messages:
        raise RuntimeError("MCP response is neither JSON nor an SSE data event")
    messages: list[dict[str, Any]] = []
    for payload in raw_messages:
        if not isinstance(payload, dict):
            raise RuntimeError("MCP JSON-RPC response must contain only objects")
        messages.append(payload)
    return messages


class MCPHttpClient:
    """Small, credential-free Streamable HTTP client for contract discovery."""

    def __init__(self, endpoint: str) -> None:
        self.endpoint = _validated_endpoint(endpoint)
        self.session_id = ""
        self._opener = build_opener(_NoRedirect())

    def _post(self, payload: dict[str, Any]) -> str:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": "stock-data-desk-contract-sync/1.1",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = Request(
            self.endpoint,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            with self._opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                response_session = response.headers.get("Mcp-Session-Id", "").strip()
                if response_session:
                    self.session_id = response_session
                return _read_limited(response)
        except HTTPError as exc:
            try:
                details = exc.read(1024).decode("utf-8", errors="replace").strip()
            finally:
                exc.close()
            suffix = f": {details}" if details else ""
            raise RuntimeError(f"MCP HTTP {exc.code}{suffix}") from exc
        except URLError as exc:
            raise RuntimeError(f"MCP connection failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("MCP request timed out") from exc

    def call(
        self,
        method: str,
        params: dict[str, Any],
        request_id: int,
    ) -> dict[str, Any]:
        body = self._post(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        for message in _jsonrpc_messages(body):
            if message.get("id") != request_id:
                continue
            if message.get("jsonrpc") != "2.0":
                raise RuntimeError(f"MCP {method} returned an invalid JSON-RPC version")
            if "error" in message:
                raise RuntimeError(f"MCP {method} failed: {message['error']}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise RuntimeError(f"MCP {method} returned a non-object result")
            return result
        raise RuntimeError(f"MCP {method} returned no matching JSON-RPC response")

    def notify(self, method: str, params: dict[str, Any]) -> None:
        body = self._post({"jsonrpc": "2.0", "method": method, "params": params})
        for message in _jsonrpc_messages(body):
            if "error" in message:
                raise RuntimeError(f"MCP {method} failed: {message['error']}")


def _descriptor_sha256(tools: list[dict[str, Any]]) -> str:
    canonical = json.dumps(tools, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def fetch_contract(endpoint: str) -> dict[str, Any]:
    client = MCPHttpClient(endpoint)
    initialization = client.call(
        "initialize",
        {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "stock-data-desk-contract-sync", "version": "1.1.0"},
        },
        1,
    )
    client.notify("notifications/initialized", {})
    listed = client.call("tools/list", {}, 2)
    tools = listed.get("tools")
    if not isinstance(tools, list):
        raise RuntimeError("MCP tools/list result must contain a tools list")
    names = [tool["name"] for tool in tools]
    if names != EXPECTED_TOOLS:
        raise RuntimeError(f"unexpected Hosted MCP tools: {names}")

    contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "contract_version": "1.1.0-draft",
        "source": {
            "mcp_endpoint": endpoint,
            "access_mode": "anonymous_dev",
            "protocol_version": initialization["protocolVersion"],
            "server_name": initialization["serverInfo"]["name"],
            "server_version": initialization["serverInfo"]["version"],
            "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "descriptor_sha256": _descriptor_sha256(tools),
        },
        "production": {
            "mcp_endpoint": DEFAULT_ENDPOINT,
            "resource": "https://mcp.anchisesdata.com",
            "protected_resource_metadata": (
                "https://mcp.anchisesdata.com/.well-known/oauth-protected-resource"
            ),
            "issuer": "https://auth.anchisesdata.com/",
            "openid_configuration": (
                "https://auth.anchisesdata.com/.well-known/openid-configuration"
            ),
            "authorization_endpoint": "https://auth.anchisesdata.com/authorize",
            "token_endpoint": "https://auth.anchisesdata.com/oauth/token",
            "revocation_endpoint": "https://auth.anchisesdata.com/oauth/revoke",
            "jwks_uri": "https://auth.anchisesdata.com/.well-known/jwks.json",
            "product_page": "https://anchisesdata.com/stock-qa",
            "access_page": "https://account.anchisesdata.com/access",
        },
        "oauth": {
            "status": "future",
            "flow": "authorization_code",
            "pkce_methods_supported": ["S256"],
            "resource_parameter_required": True,
            "client_registration_preference": ["cimd", "predefined"],
            "scopes_supported": [
                "openid",
                "email",
                "profile",
                "stock.read",
                "schema.read",
                "export.create",
            ],
            "tool_scopes": OAUTH_SCOPES,
            "access_token": {
                "signature_algorithm": "RS256",
                "required_claims": ["iss", "aud", "sub", "exp", "iat"],
                "identity_key": ["iss", "sub"],
                "audience": "https://mcp.anchisesdata.com",
            },
        },
        "errors": {
            "invalid_scope": {"retryable": False},
            "access_pending": {"retryable": False},
            "access_denied": {"retryable": False},
            "usage_limit_exceeded": {"retryable": False},
            "rate_limited": {"retryable": True},
            "concurrency_limited": {"retryable": True},
            "query_rejected": {"retryable": False},
            "resource_not_found": {"retryable": False},
            "result_too_large": {"retryable": False},
            "temporarily_unavailable": {"retryable": True},
        },
        "tools": tools,
    }
    validate_contract(contract)
    return contract


def _without_sync_time(contract: dict[str, Any]) -> dict[str, Any]:
    comparable = copy.deepcopy(contract)
    comparable["source"].pop("synced_at", None)
    return comparable


def contracts_match(checked_in: dict[str, Any], live: dict[str, Any]) -> bool:
    """Return whether all stable contract fields match, ignoring only sync time."""

    validate_contract(checked_in)
    validate_contract(live)
    return _without_sync_time(checked_in) == _without_sync_time(live)


def write_contract(path: Path, contract: dict[str, Any]) -> None:
    """Validate and atomically replace a contract snapshot."""

    validate_contract(contract)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(contract, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare live descriptors with the checked-in snapshot without writing files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        live = fetch_contract(args.endpoint)
    except (ContractError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    if args.check:
        try:
            checked_in = load_contract(args.output)
        except ContractError as exc:
            raise SystemExit(str(exc)) from exc
        if not contracts_match(checked_in, live):
            raise SystemExit(
                "Hosted MCP contract changed: "
                f"checked-in={checked_in['source']['descriptor_sha256']} "
                f"live={live['source']['descriptor_sha256']}"
            )
        print(
            "Hosted MCP contract matches: "
            f"{live['source']['descriptor_sha256']}"
        )
        return

    write_contract(args.output, live)
    print(f"Wrote {len(live['tools'])} tools to {args.output}")
    print(f"descriptor_sha256={live['source']['descriptor_sha256']}")


if __name__ == "__main__":
    main()
