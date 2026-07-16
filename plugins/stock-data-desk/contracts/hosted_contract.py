"""Load and validate the Stock Data Desk Hosted MCP descriptor snapshot."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List


CONTRACT_PATH = Path(__file__).with_name("hosted-mcp-v1.json")
SUPPORTED_ACCESS_MODES = {"anonymous_dev", "oauth"}
REQUIRED_TOOL_KEYS = {
    "name",
    "title",
    "description",
    "inputSchema",
    "outputSchema",
    "securitySchemes",
    "annotations",
    "_meta",
}
ANNOTATION_HINTS = (
    "readOnlyHint",
    "destructiveHint",
    "idempotentHint",
    "openWorldHint",
)


class ContractError(ValueError):
    """Raised when the checked-in Hosted MCP contract is inconsistent."""


def _descriptor_sha256(tools: List[Dict[str, Any]]) -> str:
    canonical = json.dumps(tools, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_contract(path: Path = CONTRACT_PATH) -> Dict[str, Any]:
    """Return the checked-in contract after validating structural invariants."""

    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError(f"could not read contract {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"contract {path} is not valid JSON: {exc}") from exc
    validate_contract(contract)
    return contract


def _object(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label} must be a non-empty string")
    return value


def _string_list(value: Any, label: str, *, allow_empty: bool = True) -> List[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        suffix = "non-empty " if not allow_empty else ""
        raise ContractError(f"{label} must be a {suffix}list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ContractError(f"{label} must contain only non-empty strings")
    if len(value) != len(set(value)):
        raise ContractError(f"{label} must not contain duplicates")
    return value


def validate_contract(contract: Dict[str, Any]) -> None:
    """Validate invariants that the individual JSON Schemas do not express."""

    contract = _object(contract, "contract")
    required = {"contract_version", "source", "production", "oauth", "errors", "tools"}
    missing = required - set(contract)
    if missing:
        raise ContractError(f"contract is missing keys: {sorted(missing)}")

    _nonempty_string(contract["contract_version"], "contract_version")
    source = _object(contract["source"], "source")
    _object(contract["production"], "production")
    oauth = _object(contract["oauth"], "oauth")
    errors = _object(contract["errors"], "errors")
    for key in (
        "mcp_endpoint",
        "access_mode",
        "protocol_version",
        "server_name",
        "server_version",
        "synced_at",
        "descriptor_sha256",
    ):
        _nonempty_string(source.get(key), f"source.{key}")
    access_mode = source["access_mode"]
    if access_mode not in SUPPORTED_ACCESS_MODES:
        raise ContractError(f"unsupported source access mode: {access_mode}")

    tools = contract["tools"]
    if not isinstance(tools, list) or not tools:
        raise ContractError("tools must be a non-empty list")
    expected_hash = source["descriptor_sha256"]
    actual_hash = _descriptor_sha256(tools)
    if expected_hash != actual_hash:
        raise ContractError(
            f"descriptor SHA-256 mismatch: expected={expected_hash} actual={actual_hash}"
        )

    names: List[str] = []
    for index, raw_tool in enumerate(tools):
        tool = _object(raw_tool, f"tools[{index}]")
        name = tool.get("name", f"tools[{index}]")
        missing_tool_keys = REQUIRED_TOOL_KEYS - set(tool)
        if missing_tool_keys:
            raise ContractError(
                f"tool is missing keys {sorted(missing_tool_keys)}: {name}"
            )
        name = _nonempty_string(tool["name"], f"tools[{index}].name")
        title = _nonempty_string(tool["title"], f"{name}.title")
        description = _nonempty_string(tool["description"], f"{name}.description")
        names.append(name)
        if not description.startswith("Use this when"):
            raise ContractError(f"{name} description must begin with 'Use this when'")
        input_schema = _object(tool["inputSchema"], f"{name}.inputSchema")
        output_schema = _object(tool["outputSchema"], f"{name}.outputSchema")
        if input_schema.get("type") != "object":
            raise ContractError(f"{name} inputSchema must be an object schema")
        if input_schema.get("additionalProperties") is not False:
            raise ContractError(f"{name} inputSchema must reject additional properties")
        if output_schema.get("type") != "object":
            raise ContractError(f"{name} outputSchema must be an object schema")
        if output_schema.get("additionalProperties") is not False:
            raise ContractError(f"{name} outputSchema must reject additional properties")
        security_schemes = tool["securitySchemes"]
        if not isinstance(security_schemes, list) or not security_schemes:
            raise ContractError(f"{name} securitySchemes must be a non-empty list")
        meta = _object(tool["_meta"], f"{name}._meta")
        if security_schemes != meta.get("securitySchemes"):
            raise ContractError(f"{name} top-level and _meta security schemes must match")
        annotations = _object(tool["annotations"], f"{name}.annotations")
        if annotations.get("title") != title:
            raise ContractError(f"{name} annotation title must match tool title")
        for hint in ANNOTATION_HINTS:
            if not isinstance(annotations.get(hint), bool):
                raise ContractError(f"{name} must declare boolean {hint}")
        if annotations["readOnlyHint"] and annotations["destructiveHint"]:
            raise ContractError(f"{name} cannot be both read-only and destructive")

    if len(names) != len(set(names)):
        raise ContractError("tool names must be unique")
    scopes_supported = _string_list(
        oauth.get("scopes_supported"),
        "oauth.scopes_supported",
        allow_empty=False,
    )
    tool_scopes = _object(oauth.get("tool_scopes"), "oauth.tool_scopes")
    if set(tool_scopes) != set(names):
        raise ContractError("oauth.tool_scopes must cover every tool exactly once")
    for name in names:
        scopes = _string_list(tool_scopes[name], f"oauth.tool_scopes.{name}")
        unknown_scopes = set(scopes) - set(scopes_supported)
        if unknown_scopes:
            raise ContractError(
                f"oauth.tool_scopes.{name} contains unsupported scopes: "
                f"{sorted(unknown_scopes)}"
            )

    for tool in tools:
        expected_schemes = _security_schemes(contract, tool["name"], access_mode)
        if tool["securitySchemes"] != expected_schemes:
            raise ContractError(
                f"{tool['name']} securitySchemes do not match source access mode "
                f"{access_mode}"
            )

    if not errors:
        raise ContractError("errors must be a non-empty object")
    for code, raw_details in errors.items():
        _nonempty_string(code, "error code")
        details = _object(raw_details, f"errors.{code}")
        if not isinstance(details.get("retryable"), bool):
            raise ContractError(f"errors.{code}.retryable must be a boolean")


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

    if contract is None:
        source = load_contract()
    else:
        validate_contract(contract)
        source = contract
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


def tool_names(contract: Dict[str, Any] | None = None) -> tuple[str, ...]:
    """Return stable tool names in discovery order."""

    if contract is None:
        source = load_contract()
    else:
        validate_contract(contract)
        source = contract
    return tuple(tool["name"] for tool in source["tools"])
