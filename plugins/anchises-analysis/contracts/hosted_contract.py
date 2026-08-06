"""Load and validate the Anchises Analysis Hosted MCP descriptor snapshot."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List


CONTRACT_PATH = Path(__file__).with_name("hosted-mcp-v1.json")
CONTRACT_PROFILE_VERSION = "1.9.0-draft"
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
PROFILE_UNAVAILABLE = "unavailable"
PROFILE_ANONYMOUS = "anonymous"
PROFILE_AUTHENTICATED = "authenticated"
SUPPORTED_MODE_PROFILES = {
    PROFILE_UNAVAILABLE,
    PROFILE_ANONYMOUS,
    PROFILE_AUTHENTICATED,
}
DISCOVERABLE_MODE_PROFILES = {PROFILE_ANONYMOUS, PROFILE_AUTHENTICATED}
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


class ServiceUnavailableModeError(ContractError):
    """Raised when a runtime mode intentionally exposes no MCP tools."""


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


def _semantic_version(value: Any, label: str) -> str:
    version = _nonempty_string(value, label)
    if not SEMVER_PATTERN.fullmatch(version):
        raise ContractError(f"{label} must be a semantic version")
    return version


def _string_list(value: Any, label: str, *, allow_empty: bool = True) -> List[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        suffix = "non-empty " if not allow_empty else ""
        raise ContractError(f"{label} must be a {suffix}list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ContractError(f"{label} must contain only non-empty strings")
    if len(value) != len(set(value)):
        raise ContractError(f"{label} must not contain duplicates")
    return value


def _schema_properties(schema: Dict[str, Any], label: str) -> Dict[str, Any]:
    return _object(schema.get("properties"), f"{label}.properties")


def _validate_dynamic_stock_access_policy(
    by_name: Dict[str, Dict[str, Any]],
) -> None:
    """Validate the current cursor pagination and dynamic export capabilities."""

    required_tools = {
        "get_connection_status",
        "screen_stocks",
        "run_readonly_sql",
        "create_csv_export",
    }
    missing = required_tools - set(by_name)
    if missing:
        raise ContractError(
            f"stock access policy tools are missing: {sorted(missing)}"
        )

    status_output = _schema_properties(
        by_name["get_connection_status"]["outputSchema"],
        "get_connection_status.outputSchema",
    )
    if "data_policy" not in status_output:
        raise ContractError("get_connection_status must publish data_policy")
    if "data_policy" not in set(
        by_name["get_connection_status"]["outputSchema"].get("required", [])
    ):
        raise ContractError("get_connection_status must require data_policy")
    data_policy_union = _object(
        status_output["data_policy"], "get_connection_status.data_policy"
    )
    data_policy_objects = [
        branch
        for branch in data_policy_union.get("oneOf", [])
        if isinstance(branch, dict) and branch.get("type") == "object"
    ]
    if len(data_policy_objects) != 1:
        raise ContractError("get_connection_status data_policy must allow one object shape")
    data_policy = data_policy_objects[0]
    expected_data_policy = {
        "mode",
        "restrictions",
        "policy_version",
        "effective_limits",
    }
    data_policy_properties = _schema_properties(
        data_policy, "get_connection_status.data_policy"
    )
    if (
        set(data_policy_properties) != expected_data_policy
        or set(data_policy.get("required", [])) != expected_data_policy
    ):
        raise ContractError("get_connection_status data_policy schema is incomplete")
    if data_policy_properties["mode"].get("enum") != [
        "restricted",
        "bulk_enabled",
    ]:
        raise ContractError("get_connection_status data_policy modes are incomplete")

    screen = by_name["screen_stocks"]
    screen_input = _schema_properties(
        screen["inputSchema"], "screen_stocks.inputSchema"
    )
    expected_screen_inputs = {
        "exchanges",
        "as_of_date",
        "start_date",
        "end_date",
        "fields",
        "filters",
        "sort",
        "top_n",
        "base_query_id",
        "cursor",
        "page_size",
    }
    if set(screen_input) != expected_screen_inputs:
        raise ContractError(
            "screen_stocks input properties do not match the capability contract"
        )
    if screen["inputSchema"].get("required"):
        raise ContractError("screen_stocks inputs must not be globally required")
    if screen_input["top_n"].get("maximum") != 200_000:
        raise ContractError("screen_stocks top_n maximum must be 200000")
    if screen_input["page_size"].get("maximum") != 200:
        raise ContractError("screen_stocks page_size maximum must be 200")
    if screen_input["cursor"].get("type") != ["string", "null"]:
        raise ContractError("screen_stocks cursor must allow string or null")
    if screen_input["cursor"].get("maxLength") != 4096:
        raise ContractError("screen_stocks cursor must be bounded")

    sql = by_name["run_readonly_sql"]
    sql_input = _schema_properties(sql["inputSchema"], "run_readonly_sql.inputSchema")
    if set(sql_input) != {"sql", "max_rows", "cursor"}:
        raise ContractError(
            "run_readonly_sql must accept sql, max_rows, and cursor"
        )
    if sql_input["max_rows"].get("maximum") != 200:
        raise ContractError("run_readonly_sql max_rows maximum must be 200")
    if sql_input["cursor"].get("type") != ["string", "null"]:
        raise ContractError("run_readonly_sql cursor must allow string or null")
    if sql_input["cursor"].get("maxLength") != 4096:
        raise ContractError("run_readonly_sql cursor must be bounded")
    continuation_requirements = {
        frozenset(branch.get("required", []))
        for branch in sql["inputSchema"].get("anyOf", [])
    }
    if continuation_requirements != {frozenset({"sql"}), frozenset({"cursor"})}:
        raise ContractError("run_readonly_sql must require sql or cursor")

    expected_analysis = {
        "matched_row_count",
        "displayed_row_count",
        "display_row_limit",
        "result_is_preview",
        "row_pagination_available",
        "displayed_row_start",
        "displayed_row_end",
        "browsable_row_limit",
        "pagination_limit_reached",
        "pagination_next_action",
        "server_side_analysis_supported",
        "query_classification",
    }
    expected_policy = {
        "mode",
        "policy_version",
        "eligible_by_query",
        "classification",
        "contains_complete_partition",
        "reasons",
        "source_tools_allowed",
        "limits",
    }
    expected_limits = {
        "max_rows",
        "max_columns",
        "max_cells",
        "max_bytes",
        "max_top_n",
        "max_explicit_tickers",
        "max_partitions",
        "complete_exchange_day_allowed",
        "sql_export_allowed",
    }
    effective_limits = _object(
        data_policy_properties["effective_limits"],
        "get_connection_status.data_policy.effective_limits",
    )
    effective_limit_properties = _schema_properties(
        effective_limits,
        "get_connection_status.data_policy.effective_limits",
    )
    if (
        set(effective_limit_properties) != expected_limits
        or set(effective_limits.get("required", [])) != expected_limits
    ):
        raise ContractError("get_connection_status effective limits are incomplete")
    if any("const" in schema for schema in effective_limit_properties.values()):
        raise ContractError("get_connection_status effective limits must be dynamic")

    for tool_name in ("screen_stocks", "run_readonly_sql"):
        output = by_name[tool_name]["outputSchema"]
        output_properties = _schema_properties(output, f"{tool_name}.outputSchema")
        page = _object(output_properties.get("page"), f"{tool_name}.page")
        page_properties = _schema_properties(page, f"{tool_name}.page")
        next_cursor = page_properties.get("next_cursor", {})
        if set(page.get("required", [])) != {
            "row_count",
            "total_count",
            "truncated",
            "next_cursor",
        }:
            raise ContractError(f"{tool_name} page schema is incomplete")
        if next_cursor.get("type") != ["string", "null"]:
            raise ContractError(
                f"{tool_name} next_cursor must allow string or null"
            )
        if next_cursor.get("maxLength") != 4096:
            raise ContractError(f"{tool_name} next_cursor must be bounded")

        data = _object(output_properties.get("data"), f"{tool_name}.data")
        data_properties = _schema_properties(data, f"{tool_name}.data")
        analysis = _object(data_properties.get("analysis"), f"{tool_name}.analysis")
        analysis_properties = _schema_properties(
            analysis, f"{tool_name}.analysis"
        )
        if set(analysis_properties) != expected_analysis:
            raise ContractError(f"{tool_name} analysis schema is incomplete")
        if set(analysis.get("required", [])) != expected_analysis:
            raise ContractError(f"{tool_name} analysis fields must all be required")
        if analysis_properties["display_row_limit"].get("const") != 200:
            raise ContractError(f"{tool_name} display row limit must be 200")
        if analysis_properties["pagination_next_action"].get("enum") != [
            "call_same_tool_with_cursor",
            "refine_query",
            "none",
        ]:
            raise ContractError(
                f"{tool_name} pagination_next_action enum is incomplete"
            )

        policy = _object(
            data_properties.get("export_policy"),
            f"{tool_name}.export_policy",
        )
        policy_properties = _schema_properties(
            policy, f"{tool_name}.export_policy"
        )
        if set(policy_properties) != expected_policy or "eligible" in policy_properties:
            raise ContractError(
                f"{tool_name} must publish eligible_by_query and the dynamic "
                "export policy contract"
            )
        if set(policy.get("required", [])) != expected_policy:
            raise ContractError(f"{tool_name} export policy fields must all be required")
        if policy_properties["mode"].get("enum") != [
            "restricted",
            "bulk_enabled",
        ]:
            raise ContractError(f"{tool_name} export policy modes are incomplete")
        allowed_sources = policy_properties["source_tools_allowed"].get("items", {})
        if set(allowed_sources.get("enum", [])) != {
            "screen_stocks",
            "run_readonly_sql",
        }:
            raise ContractError(
                f"{tool_name} export policy must describe both rowset sources"
            )
        limits = _schema_properties(
            _object(policy_properties["limits"], f"{tool_name}.export_policy.limits"),
            f"{tool_name}.export_policy.limits",
        )
        if set(limits) != expected_limits:
            raise ContractError(f"{tool_name} export policy limits are incomplete")
        if set(policy_properties["limits"].get("required", [])) != expected_limits:
            raise ContractError(f"{tool_name} export policy limits must all be required")
        if any("const" in schema for schema in limits.values()):
            raise ContractError(f"{tool_name} export policy limits must be dynamic")

    export = by_name["create_csv_export"]
    export_input = _schema_properties(
        export["inputSchema"], "create_csv_export.inputSchema"
    )
    if set(export_input) != {"query_id", "expires_in_seconds"}:
        raise ContractError(
            "create_csv_export must accept only query_id and expires_in_seconds"
        )
    if set(export["inputSchema"].get("required", [])) != {"query_id"}:
        raise ContractError("create_csv_export must require query_id")


def _validate_connection_status_schema(
    by_name: Dict[str, Dict[str, Any]],
) -> None:
    """Keep service access separate from plugin release discovery."""

    status = by_name.get("get_connection_status")
    if status is None:
        raise ContractError("get_connection_status is required")
    status_input = status["inputSchema"]
    input_properties = _schema_properties(
        status_input, "get_connection_status.inputSchema"
    )
    status_output = status["outputSchema"]
    output_properties = _schema_properties(
        status_output, "get_connection_status.outputSchema"
    )

    if input_properties or status_input.get("required"):
        raise ContractError("get_connection_status must accept only empty arguments")
    if "client_update" in output_properties:
        raise ContractError(
            "get_connection_status must not publish plugin release metadata"
        )


def _validate_stock_access_policy(
    tools: List[Dict[str, Any]], contract_version: str
) -> None:
    """Validate the current capability profile without gating on MCP SemVer."""

    if contract_version != CONTRACT_PROFILE_VERSION:
        raise ContractError(f"unsupported contract version: {contract_version}")
    by_name = {tool["name"]: tool for tool in tools}
    _validate_dynamic_stock_access_policy(by_name)
    _validate_connection_status_schema(by_name)


def mode_profiles(contract: Dict[str, Any]) -> Dict[str, str]:
    """Return backend mode names mapped to stable plugin behavior profiles."""

    runtime = _object(contract.get("runtime"), "runtime")
    profiles = _object(runtime.get("profiles"), "runtime.profiles")
    return {
        _nonempty_string(mode, "runtime.profiles mode"): _nonempty_string(
            profile, f"runtime.profiles.{mode}"
        )
        for mode, profile in profiles.items()
    }


def mode_profile(contract: Dict[str, Any], access_mode: str) -> str:
    """Resolve a mutable backend mode name to a stable behavior profile."""

    mode = _nonempty_string(access_mode, "access mode")
    profiles = mode_profiles(contract)
    try:
        return profiles[mode]
    except KeyError as exc:
        raise ContractError(f"unsupported access mode: {mode}") from exc


def validate_contract(contract: Dict[str, Any]) -> None:
    """Validate invariants that the individual JSON Schemas do not express."""

    contract = _object(contract, "contract")
    required = {
        "contract_version",
        "runtime",
        "source",
        "production",
        "oauth",
        "errors",
        "tools",
    }
    missing = required - set(contract)
    if missing:
        raise ContractError(f"contract is missing keys: {sorted(missing)}")

    contract_version = _nonempty_string(
        contract["contract_version"], "contract_version"
    )
    if contract_version != CONTRACT_PROFILE_VERSION:
        raise ContractError(f"unsupported contract version: {contract_version}")
    runtime = _object(contract["runtime"], "runtime")
    source = _object(contract["source"], "source")
    _object(contract["production"], "production")
    oauth = _object(contract["oauth"], "oauth")
    errors = _object(contract["errors"], "errors")
    for key in (
        "mcp_endpoint",
        "access_mode",
        "protocol_version",
        "server_name",
        "instructions",
        "sync_state",
        "synced_at",
        "descriptor_sha256",
    ):
        _nonempty_string(source.get(key), f"source.{key}")
    _semantic_version(source.get("server_version"), "source.server_version")
    if source["sync_state"] not in {"live", "target_pending_mcp_publish"}:
        raise ContractError("source.sync_state must be live or target_pending_mcp_publish")
    supported_modes = _string_list(
        runtime.get("supported_modes"),
        "runtime.supported_modes",
        allow_empty=False,
    )
    snapshot_mode = _nonempty_string(
        runtime.get("snapshot_mode"), "runtime.snapshot_mode"
    )
    profiles = mode_profiles(contract)
    if set(profiles) != set(supported_modes):
        raise ContractError(
            "runtime.profiles must cover runtime.supported_modes exactly"
        )
    for mode, profile in profiles.items():
        if profile not in SUPPORTED_MODE_PROFILES:
            raise ContractError(
                f"runtime.profiles.{mode} has unsupported profile: {profile}"
            )
    if snapshot_mode not in profiles:
        raise ContractError("runtime.snapshot_mode must be a supported mode")

    access_mode = source["access_mode"]
    if access_mode != snapshot_mode:
        raise ContractError(
            "source.access_mode must match runtime.snapshot_mode"
        )
    source_profile = mode_profile(contract, access_mode)
    if source_profile not in DISCOVERABLE_MODE_PROFILES:
        raise ContractError(
            "the checked-in descriptor snapshot must use a discoverable mode"
        )

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
    _validate_stock_access_policy(tools, contract["contract_version"])
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
        expected_schemes = _security_schemes(
            contract, tool["name"], source_profile
        )
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


def _security_schemes(contract: Dict[str, Any], tool_name: str, profile: str) -> list:
    if profile == PROFILE_ANONYMOUS:
        return [{"type": "noauth"}]
    if profile == PROFILE_AUTHENTICATED:
        return [
            {
                "type": "oauth2",
                "scopes": copy.deepcopy(contract["oauth"]["tool_scopes"][tool_name]),
            }
        ]
    if profile == PROFILE_UNAVAILABLE:
        raise ServiceUnavailableModeError(
            "the selected runtime mode does not expose MCP tools"
        )
    raise ContractError(f"unsupported mode profile: {profile}")


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
    profile = mode_profile(source, mode)
    if profile not in DISCOVERABLE_MODE_PROFILES:
        raise ServiceUnavailableModeError(
            f"runtime mode {mode!r} does not expose MCP tools"
        )
    descriptors = copy.deepcopy(source["tools"])
    for descriptor in descriptors:
        schemes = _security_schemes(source, descriptor["name"], profile)
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
