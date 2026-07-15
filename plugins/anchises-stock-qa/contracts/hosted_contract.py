"""Load and validate the Anchises Hosted MCP descriptor snapshot."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


CONTRACT_PATH = Path(__file__).with_name("hosted-mcp-v1.json")
SUPPORTED_ACCESS_MODES = {"anonymous_dev", "oauth"}


class ContractError(ValueError):
    """Raised when the checked-in Hosted MCP contract is inconsistent."""


def _descriptor_sha256(tools: List[Dict[str, Any]]) -> str:
    canonical = json.dumps(tools, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_contract(path: Path = CONTRACT_PATH) -> Dict[str, Any]:
    """Return the checked-in contract after validating structural invariants."""

    contract = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract: Dict[str, Any]) -> None:
    """Validate invariants that the individual JSON Schemas do not express."""

    required = {"contract_version", "source", "production", "oauth", "errors", "tools"}
    missing = required - set(contract)
    if missing:
        raise ContractError(f"contract is missing keys: {sorted(missing)}")

    tools = contract["tools"]
    if not isinstance(tools, list) or not tools:
        raise ContractError("tools must be a non-empty list")
    expected_hash = contract["source"].get("descriptor_sha256")
    actual_hash = _descriptor_sha256(tools)
    if expected_hash != actual_hash:
        raise ContractError(
            f"descriptor SHA-256 mismatch: expected={expected_hash} actual={actual_hash}"
        )

    names: List[str] = []
    for tool in tools:
        name = tool.get("name", "<unknown>")
        for key in (
            "name",
            "title",
            "description",
            "inputSchema",
            "outputSchema",
            "securitySchemes",
            "annotations",
            "_meta",
        ):
            if key not in tool:
                raise ContractError(f"tool is missing {key}: {name}")
        names.append(name)
        if not tool["description"].startswith("Use this when"):
            raise ContractError(f"{name} description must begin with 'Use this when'")
        if tool["inputSchema"].get("type") != "object":
            raise ContractError(f"{name} inputSchema must be an object schema")
        if tool["inputSchema"].get("additionalProperties") is not False:
            raise ContractError(f"{name} inputSchema must reject additional properties")
        if tool["outputSchema"].get("type") != "object":
            raise ContractError(f"{name} outputSchema must be an object schema")
        if tool["outputSchema"].get("additionalProperties") is not False:
            raise ContractError(f"{name} outputSchema must reject additional properties")
        if tool["securitySchemes"] != tool["_meta"].get("securitySchemes"):
            raise ContractError(f"{name} top-level and _meta security schemes must match")
        annotations = tool["annotations"]
        for hint in (
            "readOnlyHint",
            "destructiveHint",
            "idempotentHint",
            "openWorldHint",
        ):
            if not isinstance(annotations.get(hint), bool):
                raise ContractError(f"{name} must declare boolean {hint}")

    if len(names) != len(set(names)):
        raise ContractError("tool names must be unique")
    tool_scopes = contract["oauth"].get("tool_scopes", {})
    if set(tool_scopes) != set(names):
        raise ContractError("oauth.tool_scopes must cover every tool exactly once")


def _security_schemes(contract: Dict[str, Any], tool_name: str, access_mode: str) -> list:
    if access_mode == "anonymous_dev":
        return [{"type": "noauth"}]
    if access_mode == "oauth":
        return [
            {
                "type": "oauth2",
                "scopes": copy.deepcopy(contract["oauth"]["tool_scopes"][tool_name]),
            }
        ]
    raise ContractError(f"unsupported access mode: {access_mode}")


def tool_descriptors(
    contract: Dict[str, Any] | None = None,
    *,
    access_mode: str | None = None,
) -> List[Dict[str, Any]]:
    """Return self-contained tools/list descriptors for one security mode."""

    source = contract or load_contract()
    mode = access_mode or source["source"]["access_mode"]
    if mode not in SUPPORTED_ACCESS_MODES:
        raise ContractError(f"unsupported access mode: {mode}")
    descriptors = copy.deepcopy(source["tools"])
    for descriptor in descriptors:
        schemes = _security_schemes(source, descriptor["name"], mode)
        descriptor["securitySchemes"] = schemes
        descriptor["_meta"]["securitySchemes"] = copy.deepcopy(schemes)
    return descriptors


def descriptor_by_name(
    name: str,
    contract: Dict[str, Any] | None = None,
    *,
    access_mode: str | None = None,
) -> Dict[str, Any]:
    """Return one materialized descriptor by stable tool name."""

    for descriptor in tool_descriptors(contract, access_mode=access_mode):
        if descriptor["name"] == name:
            return descriptor
    raise ContractError(f"unknown Hosted MCP tool: {name}")


def tool_names(contract: Dict[str, Any] | None = None) -> Iterable[str]:
    """Yield stable tool names in discovery order."""

    source = contract or load_contract()
    return (tool["name"] for tool in source["tools"])
