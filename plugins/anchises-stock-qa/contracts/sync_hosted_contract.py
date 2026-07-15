#!/usr/bin/env python3
"""Synchronize the checked-in Hosted MCP descriptor snapshot.

The command performs read-only JSON-RPC calls against the public Streamable HTTP
endpoint.  It never sends credentials and never mutates the Hosted MCP service.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "https://mcp.anchisesdata.com/mcp"
DEFAULT_OUTPUT = Path(__file__).with_name("hosted-mcp-v1.json")
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


def _rpc(endpoint: str, method: str, params: dict[str, Any], request_id: int) -> dict[str, Any]:
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
        separators=(",", ":"),
    ).encode("utf-8")
    request = Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": "anchises-stock-qa-contract-sync/1.0",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS endpoint by default
        body = response.read().decode("utf-8")

    messages: list[dict[str, Any]] = []
    if body.lstrip().startswith("{"):
        messages.append(json.loads(body))
    else:
        for line in body.splitlines():
            if line.startswith("data:"):
                messages.append(json.loads(line.removeprefix("data:").strip()))
    for message in messages:
        if message.get("id") == request_id:
            if "error" in message:
                raise RuntimeError(f"MCP {method} failed: {message['error']}")
            return message["result"]
    raise RuntimeError(f"MCP {method} returned no matching JSON-RPC response")


def _descriptor_sha256(tools: list[dict[str, Any]]) -> str:
    canonical = json.dumps(tools, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def fetch_contract(endpoint: str) -> dict[str, Any]:
    initialization = _rpc(
        endpoint,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "anchises-plugin-contract-sync", "version": "1.0.0"},
        },
        1,
    )
    tools = _rpc(endpoint, "tools/list", {}, 2)["tools"]
    names = [tool["name"] for tool in tools]
    if names != EXPECTED_TOOLS:
        raise RuntimeError(f"unexpected Hosted MCP tools: {names}")

    return {
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
    live = fetch_contract(args.endpoint)
    if args.check:
        checked_in = json.loads(args.output.read_text(encoding="utf-8"))
        expected_hash = checked_in["source"]["descriptor_sha256"]
        actual_hash = live["source"]["descriptor_sha256"]
        if actual_hash != expected_hash:
            raise SystemExit(
                f"Hosted MCP descriptors changed: checked-in={expected_hash} live={actual_hash}"
            )
        print(f"Hosted MCP descriptors match: {actual_hash}")
        return

    args.output.write_text(json.dumps(live, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(live['tools'])} tools to {args.output}")
    print(f"descriptor_sha256={live['source']['descriptor_sha256']}")


if __name__ == "__main__":
    main()
