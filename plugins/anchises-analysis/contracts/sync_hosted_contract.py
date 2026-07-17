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

from hosted_contract import (
    PROFILE_ANONYMOUS,
    PROFILE_AUTHENTICATED,
    PROFILE_UNAVAILABLE,
    ContractError,
    load_contract,
    mode_profile,
    validate_contract,
)


DEFAULT_ENDPOINT = "https://mcp.anchisesdata.com/mcp"
DEFAULT_OUTPUT = Path(__file__).with_name("hosted-mcp-v1.json")
MCP_PROTOCOL_VERSION = "2025-06-18"
REQUEST_TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
CONTRACT_VERSION = "1.5.0-draft"
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
    "resolve_company_identity",
    "prepare_company_report_generation",
    "create_csv_export",
]
EXPECTED_OAUTH_TOOL_SCOPES = {
    "get_connection_status": [],
    "get_available_exchanges": ["stock.read"],
    "get_latest_dates": ["stock.read"],
    "get_stock_schema": ["schema.read"],
    "list_stock_tables": ["schema.read"],
    "get_table_schema": ["schema.read"],
    "screen_stocks": ["stock.read"],
    "validate_readonly_sql": ["stock.read"],
    "run_readonly_sql": ["stock.read"],
    "resolve_company_identity": ["stock.read"],
    "prepare_company_report_generation": ["stock.read"],
    "create_csv_export": ["export.create"],
}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class MCPHTTPError(RuntimeError):
    """HTTP failure carrying a status code for access-mode detection."""

    def __init__(self, status: int, details: str = "") -> None:
        self.status = status
        self.details = details
        suffix = f": {details}" if details else ""
        super().__init__(f"MCP HTTP {status}{suffix}")


class MCPServiceClosedError(RuntimeError):
    """The MCP endpoint is intentionally unavailable in its closed mode."""


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
            "User-Agent": "anchises-analysis-contract-sync/1.5",
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
            raise MCPHTTPError(exc.code, details) from exc
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


def _security_profile(tools: list[dict[str, Any]]) -> str:
    """Classify one live tools/list response without depending on mode names."""

    profiles: set[str] = set()
    for tool in tools:
        name = tool.get("name", "<unknown>")
        schemes = tool.get("securitySchemes")
        meta = tool.get("_meta")
        meta_schemes = meta.get("securitySchemes") if isinstance(meta, dict) else None
        if schemes != meta_schemes:
            raise RuntimeError(
                f"{name} top-level and _meta security schemes do not match"
            )
        if schemes == [{"type": "noauth"}]:
            profiles.add(PROFILE_ANONYMOUS)
            continue
        if (
            isinstance(schemes, list)
            and len(schemes) == 1
            and isinstance(schemes[0], dict)
            and schemes[0].get("type") == "oauth2"
            and isinstance(schemes[0].get("scopes"), list)
        ):
            profiles.add(PROFILE_AUTHENTICATED)
            continue
        raise RuntimeError(f"{name} publishes an unsupported security scheme")
    if len(profiles) != 1:
        raise RuntimeError(
            "Hosted MCP tools must publish one consistent security profile"
        )
    return profiles.pop()


def fetch_contract(
    endpoint: str,
    *,
    base_contract: dict[str, Any] | None = None,
    expected_mode: str | None = None,
) -> dict[str, Any]:
    """Fetch the live descriptor set using a checked-in contract as metadata."""

    base = copy.deepcopy(base_contract if base_contract is not None else load_contract())
    validate_contract(base)
    mode = expected_mode or base["runtime"]["snapshot_mode"]
    expected_profile = mode_profile(base, mode)
    client = MCPHttpClient(endpoint)
    try:
        initialization = client.call(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "anchises-analysis-contract-sync",
                    "version": "1.5.0",
                },
            },
            1,
        )
        client.notify("notifications/initialized", {})
        listed = client.call("tools/list", {}, 2)
    except MCPHTTPError as exc:
        if exc.status == 503:
            raise MCPServiceClosedError("Hosted MCP is in closed mode") from exc
        raise
    tools = listed.get("tools")
    if not isinstance(tools, list):
        raise RuntimeError("MCP tools/list result must contain a tools list")
    names = [tool["name"] for tool in tools]
    if names != EXPECTED_TOOLS:
        raise RuntimeError(f"unexpected Hosted MCP tools: {names}")
    actual_profile = _security_profile(tools)
    if expected_profile == PROFILE_UNAVAILABLE:
        raise RuntimeError(
            f"expected mode {mode!r} to be closed, but the endpoint exposes tools"
        )
    if actual_profile != expected_profile:
        raise RuntimeError(
            f"Hosted MCP security profile mismatch: mode={mode!r} "
            f"expected={expected_profile} actual={actual_profile}"
        )
    instructions = initialization.get("instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        raise RuntimeError("MCP initialize result must publish non-empty instructions")

    contract = base
    contract["contract_version"] = CONTRACT_VERSION
    contract["oauth"]["tool_scopes"] = copy.deepcopy(
        EXPECTED_OAUTH_TOOL_SCOPES
    )
    contract["runtime"]["snapshot_mode"] = mode
    contract["source"].update(
        {
            "mcp_endpoint": endpoint,
            "access_mode": mode,
            "protocol_version": initialization["protocolVersion"],
            "server_name": initialization["serverInfo"]["name"],
            "server_version": initialization["serverInfo"]["version"],
            "instructions": instructions,
            "sync_state": "live",
            "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "descriptor_sha256": _descriptor_sha256(tools),
        }
    )
    contract["tools"] = tools
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
        "--expect-mode",
        help=(
            "Expected backend runtime mode. Defaults to runtime.snapshot_mode "
            "from the checked-in contract."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare live descriptors with the checked-in snapshot without writing files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        base_path = args.output if args.output.exists() else DEFAULT_OUTPUT
        base = load_contract(base_path)
        expected_mode = args.expect_mode or base["runtime"]["snapshot_mode"]
        expected_profile = mode_profile(base, expected_mode)
        live = fetch_contract(
            args.endpoint,
            base_contract=base,
            expected_mode=expected_mode,
        )
    except MCPServiceClosedError as exc:
        if "expected_profile" in locals() and expected_profile == PROFILE_UNAVAILABLE:
            print(f"Hosted MCP mode matches: {expected_mode} (closed)")
            return
        raise SystemExit(
            f"Hosted MCP is closed; expected mode was {expected_mode!r}"
        ) from exc
    except (ContractError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    if args.check:
        if not contracts_match(base, live):
            raise SystemExit(
                "Hosted MCP contract changed: "
                f"checked-in={base['source']['descriptor_sha256']} "
                f"live={live['source']['descriptor_sha256']}"
            )
        print(
            f"Hosted MCP contract matches ({expected_mode}): "
            f"{live['source']['descriptor_sha256']}"
        )
        return

    write_contract(args.output, live)
    print(f"Wrote {len(live['tools'])} tools to {args.output}")
    print(f"descriptor_sha256={live['source']['descriptor_sha256']}")


if __name__ == "__main__":
    main()
