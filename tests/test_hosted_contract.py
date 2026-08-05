from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "anchises-analysis"
CONTRACTS = PLUGIN_ROOT / "contracts"
if str(CONTRACTS) not in sys.path:
    sys.path.insert(0, str(CONTRACTS))

from hosted_contract import (  # noqa: E402
    PROFILE_ANONYMOUS,
    PROFILE_AUTHENTICATED,
    PROFILE_UNAVAILABLE,
    ContractError,
    ServiceUnavailableModeError,
    descriptor_by_name,
    load_contract,
    mode_profile,
    mode_profiles,
    tool_descriptors,
    tool_names,
    validate_contract,
)


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
PAGE_TOOLS = {"list_stock_tables", "screen_stocks", "run_readonly_sql"}
POLICY_ERROR_CODES = {
    "export_requires_selective_query",
    "export_row_limit_exceeded",
    "export_column_limit_exceeded",
    "export_cell_limit_exceeded",
    "export_complete_partition_not_allowed",
    "export_top_n_limit_exceeded",
    "export_ticker_limit_exceeded",
    "query_not_exportable",
    "query_policy_expired",
    "query_partition_limit_exceeded",
}


def _property_schemas(schema: dict) -> list[dict]:
    found: list[dict] = []
    for child in schema.get("properties", {}).values():
        found.append(child)
        found.extend(_property_schemas(child))
    items = schema.get("items")
    if isinstance(items, dict):
        found.extend(_property_schemas(items))
    for key in ("oneOf", "anyOf", "allOf"):
        for child in schema.get(key, []):
            found.extend(_property_schemas(child))
    return found


def _rehash(contract: dict) -> None:
    canonical = json.dumps(
        contract["tools"], sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    contract["source"]["descriptor_sha256"] = hashlib.sha256(canonical).hexdigest()


class HostedContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_contract()
        cls.descriptors = tool_descriptors(cls.contract)

    def test_live_snapshot_and_production_endpoints_are_frozen(self) -> None:
        self.assertEqual(self.contract["contract_version"], "1.8.0-draft")
        runtime = self.contract["runtime"]
        self.assertEqual(
            runtime["supported_modes"],
            ["closed", "public_noauth", "oauth"],
        )
        self.assertEqual(runtime["snapshot_mode"], "public_noauth")
        self.assertEqual(
            mode_profiles(self.contract),
            {
                "closed": PROFILE_UNAVAILABLE,
                "public_noauth": PROFILE_ANONYMOUS,
                "oauth": PROFILE_AUTHENTICATED,
            },
        )
        source = self.contract["source"]
        self.assertEqual(source["mcp_endpoint"], "https://mcp.anchisesdata.com/mcp")
        self.assertEqual(source["access_mode"], "public_noauth")
        self.assertEqual(source["server_name"], "Anchises Analysis")
        self.assertEqual(source["server_version"], "0.7.2")
        self.assertIn("limited to 200 rows per call", source["instructions"])
        self.assertIn("short-lived opaque cursor", source["instructions"])
        self.assertIn("User-authored SQL OFFSET remains forbidden", source["instructions"])
        self.assertIn("active server data policy", source["instructions"])
        self.assertIn("resolve a company name or ticker", source["instructions"])
        self.assertIn("Company-report requests always use", source["instructions"])
        self.assertIn("host must perform live web research", source["instructions"])
        self.assertEqual(source["sync_state"], "live")
        self.assertRegex(source["descriptor_sha256"], r"^[0-9a-f]{64}$")
        production = self.contract["production"]
        self.assertEqual(production["mcp_endpoint"], source["mcp_endpoint"])
        self.assertEqual(production["resource"], "https://mcp.anchisesdata.com")
        self.assertEqual(production["issuer"], "https://auth.anchisesdata.com/")
        self.assertEqual(
            production["protected_resource_metadata"],
            "https://mcp.anchisesdata.com/.well-known/oauth-protected-resource",
        )

    def test_tool_names_order_and_error_codes_are_stable(self) -> None:
        self.assertEqual([item["name"] for item in self.descriptors], EXPECTED_TOOLS)
        self.assertEqual(len(self.descriptors), 12)
        self.assertEqual(
            set(self.contract["errors"]),
            {
                "invalid_scope",
                "access_pending",
                "access_denied",
                "usage_limit_exceeded",
                "rate_limited",
                "concurrency_limited",
                "query_rejected",
                "query_requires_bounded_analysis",
                "resource_not_found",
                "result_too_large",
                "temporarily_unavailable",
            }
            | POLICY_ERROR_CODES,
        )

    def test_anonymous_descriptors_have_strict_schemas_metadata_and_annotations(self) -> None:
        for descriptor in self.descriptors:
            with self.subTest(tool=descriptor["name"]):
                Draft202012Validator.check_schema(descriptor["inputSchema"])
                Draft202012Validator.check_schema(descriptor["outputSchema"])
                self.assertEqual(descriptor["inputSchema"].get("additionalProperties"), False)
                self.assertEqual(descriptor["outputSchema"].get("additionalProperties"), False)
                self.assertTrue(descriptor["description"].startswith("Use this when"))
                self.assertEqual(descriptor["securitySchemes"], [{"type": "noauth"}])
                self.assertEqual(
                    descriptor["_meta"]["securitySchemes"],
                    descriptor["securitySchemes"],
                )
                self.assertEqual(
                    set(descriptor["annotations"]),
                    {
                        "title",
                        "readOnlyHint",
                        "destructiveHint",
                        "idempotentHint",
                        "openWorldHint",
                    },
                )
                self.assertFalse(descriptor["annotations"]["destructiveHint"])
                self.assertFalse(descriptor["annotations"]["openWorldHint"])
                for prop in _property_schemas(descriptor["inputSchema"]):
                    if set(prop) == {"type"}:
                        continue
                    self.assertIn("description", prop)

    def test_public_success_schemas_omit_internal_identifiers(self) -> None:
        forbidden = {
            "request_id",
            "user_id",
            "principal",
            "principal_id",
            "connection_id",
            "policy",
            "access_policy",
            "data_scope",
        }
        for descriptor in self.descriptors:
            property_names = {
                name
                for schema in _property_schemas(descriptor["outputSchema"])
                for name in schema.get("properties", {})
            }
            property_names.update(descriptor["outputSchema"].get("properties", {}))
            with self.subTest(tool=descriptor["name"]):
                self.assertFalse(forbidden & property_names)

    def test_future_oauth_security_is_materialized_at_top_level_and_meta(self) -> None:
        self.assertEqual(
            mode_profile(self.contract, "oauth"),
            PROFILE_AUTHENTICATED,
        )
        oauth = tool_descriptors(self.contract, access_mode="oauth")
        for descriptor in oauth:
            with self.subTest(tool=descriptor["name"]):
                scopes = self.contract["oauth"]["tool_scopes"][descriptor["name"]]
                expected = [{"type": "oauth2", "scopes": scopes}]
                self.assertEqual(descriptor["securitySchemes"], expected)
                self.assertEqual(descriptor["_meta"]["securitySchemes"], expected)

    def test_only_csv_export_is_not_read_only_or_idempotent(self) -> None:
        for descriptor in self.descriptors:
            expected = descriptor["name"] != "create_csv_export"
            self.assertEqual(descriptor["annotations"]["readOnlyHint"], expected)
            self.assertEqual(descriptor["annotations"]["idempotentHint"], expected)

    def test_page_tools_publish_complete_page_schema(self) -> None:
        for descriptor in self.descriptors:
            page = descriptor["outputSchema"]["properties"].get("page")
            if descriptor["name"] in PAGE_TOOLS:
                self.assertIsNotNone(page)
                self.assertEqual(
                    set(page["required"]),
                    {"row_count", "total_count", "truncated", "next_cursor"},
                )
            else:
                self.assertIsNone(page)

    def test_stock_row_pages_publish_opaque_nullable_cursor(self) -> None:
        for name in ("screen_stocks", "run_readonly_sql"):
            page = descriptor_by_name(name)["outputSchema"]["properties"]["page"]
            next_cursor = page["properties"]["next_cursor"]
            self.assertEqual(next_cursor["type"], ["string", "null"])
            self.assertEqual(next_cursor["maxLength"], 4096)

    def test_screen_0_7_inputs_analysis_and_export_policy_are_strict(self) -> None:
        descriptor = descriptor_by_name("screen_stocks")
        schema = descriptor["inputSchema"]
        properties = schema["properties"]
        self.assertEqual(
            set(properties),
            {
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
            },
        )
        self.assertNotIn("required", schema)
        self.assertEqual(properties["top_n"]["maximum"], 200000)
        self.assertEqual(properties["page_size"]["maximum"], 200)
        self.assertIn("Cannot be combined with as_of_date", properties["start_date"]["description"])
        self.assertIn("Cannot be combined with as_of_date", properties["end_date"]["description"])

        validator = Draft202012Validator(schema)
        valid = {
            "exchanges": ["NASDAQ"],
            "start_date": "2025-07-17",
            "end_date": "2026-07-17",
            "fields": ["Price_Close", "Volume"],
            "filters": [],
            "sort": [{"field": "Volume", "direction": "desc"}],
            "top_n": 100,
            "page_size": 100,
        }
        self.assertFalse(list(validator.iter_errors(valid)))
        self.assertFalse(list(validator.iter_errors({"cursor": "opaque", "page_size": 200})))

        data = descriptor["outputSchema"]["properties"]["data"]["properties"]
        analysis = data["analysis"]["properties"]
        self.assertEqual(analysis["display_row_limit"]["const"], 200)
        self.assertEqual(analysis["server_side_analysis_supported"]["const"], True)
        self.assertEqual(
            analysis["pagination_next_action"]["enum"],
            ["call_same_tool_with_cursor", "refine_query", "none"],
        )
        self.assertTrue(
            {
                "displayed_row_start",
                "displayed_row_end",
                "browsable_row_limit",
                "pagination_limit_reached",
                "pagination_next_action",
            }
            <= set(data["analysis"]["required"])
        )
        policy = data["export_policy"]["properties"]
        self.assertIn("eligible_by_query", policy)
        self.assertNotIn("eligible", policy)
        self.assertEqual(policy["mode"]["enum"], ["restricted", "bulk_enabled"])
        self.assertEqual(
            policy["source_tools_allowed"]["items"]["enum"],
            ["screen_stocks", "run_readonly_sql"],
        )
        limits = policy["limits"]["properties"]
        self.assertEqual(
            set(limits),
            {
                "max_rows",
                "max_columns",
                "max_cells",
                "max_bytes",
                "max_top_n",
                "max_explicit_tickers",
                "max_partitions",
                "complete_exchange_day_allowed",
                "sql_export_allowed",
            },
        )
        status_data = descriptor_by_name("get_connection_status")["outputSchema"][
            "properties"
        ]["data_policy"]["oneOf"][0]
        self.assertEqual(
            status_data["properties"]["mode"]["enum"],
            ["restricted", "bulk_enabled"],
        )
        self.assertEqual(
            set(status_data["properties"]["effective_limits"]["required"]),
            set(limits),
        )

    def test_sql_supports_cursor_pages_and_dynamic_exports(self) -> None:
        descriptor = descriptor_by_name("run_readonly_sql")
        schema = descriptor["inputSchema"]
        properties = schema["properties"]
        self.assertEqual(set(properties), {"sql", "max_rows", "cursor"})
        self.assertEqual(properties["max_rows"]["maximum"], 200)
        self.assertNotIn("page_size", properties)
        validator = Draft202012Validator(schema)
        for valid in (
            {"sql": "SELECT 1", "max_rows": 200},
            {"cursor": "opaque-next-page", "max_rows": 200},
        ):
            self.assertFalse(list(validator.iter_errors(valid)), valid)
        self.assertTrue(list(validator.iter_errors({"max_rows": 200})))
        self.assertIn("bulk-enabled server may export", schema["description"])
        policy = descriptor["outputSchema"]["properties"]["data"]["properties"][
            "export_policy"
        ]["properties"]
        self.assertIn("eligible_by_query", policy)
        self.assertIn("source_tools_allowed", policy)
        self.assertNotIn("eligible", policy)

    def test_screen_filter_value_is_strict_and_between_runtime_shape_is_documented(self) -> None:
        schema = descriptor_by_name("screen_stocks")["inputSchema"]
        validator = Draft202012Validator(schema)
        valid = {
            "filters": [
                {"field": "Price_Close", "operator": "between", "value": [10, 20]}
            ]
        }
        self.assertFalse(list(validator.iter_errors(valid)))
        invalid_object = {
            "filters": [{"field": "Price_Close", "operator": "eq", "value": {"x": 1}}]
        }
        self.assertTrue(list(validator.iter_errors(invalid_object)))
        too_many = {
            "filters": [
                {"field": "TICKER", "operator": "in", "value": list(range(101))}
            ]
        }
        self.assertTrue(list(validator.iter_errors(too_many)))

    def test_validate_sql_accepts_only_sql(self) -> None:
        validator = Draft202012Validator(
            descriptor_by_name("validate_readonly_sql")["inputSchema"]
        )
        self.assertFalse(list(validator.iter_errors({"sql": "SELECT 1"})))
        self.assertTrue(list(validator.iter_errors({"sql": "SELECT 1", "max_rows": 10})))

    def test_csv_export_lifetime_defaults_to_60_minutes_and_is_bounded(self) -> None:
        schema = descriptor_by_name("create_csv_export")["inputSchema"]
        lifetime = schema["properties"]["expires_in_seconds"]
        self.assertEqual(lifetime["minimum"], 60)
        self.assertEqual(lifetime["maximum"], 3600)
        self.assertEqual(lifetime["default"], 3600)
        self.assertEqual(lifetime["examples"], [60, 600, 3600])
        self.assertIn("60-minute", lifetime["description"])
        validator = Draft202012Validator(schema)
        query_id = "qry_screen_0001"
        for valid in (
            {"query_id": query_id},
            {"query_id": query_id, "expires_in_seconds": 60},
            {"query_id": query_id, "expires_in_seconds": 600},
            {"query_id": query_id, "expires_in_seconds": 3600},
        ):
            self.assertFalse(list(validator.iter_errors(valid)), valid)
        for invalid in (
            {"query_id": query_id, "expires_in_seconds": 59},
            {"query_id": query_id, "expires_in_seconds": 3601},
            {"query_id": query_id, "expires_in_seconds": 60.5},
        ):
            self.assertTrue(list(validator.iter_errors(invalid)), invalid)
        self.assertIn(
            "prior rowset",
            descriptor_by_name("create_csv_export")["description"],
        )

    def test_company_identity_resolution_contract_is_strict_and_bounded(self) -> None:
        descriptor = descriptor_by_name("resolve_company_identity")
        schema = descriptor["inputSchema"]
        validator = Draft202012Validator(schema)
        self.assertFalse(list(validator.iter_errors({"query": "Apple"})))
        self.assertFalse(
            list(
                validator.iter_errors(
                    {
                        "query": "Rio Tinto plc",
                        "exchange_hint": "LSE",
                        "purpose": "company_report",
                    }
                )
            )
        )
        for invalid in (
            {},
            {"query": ""},
            {"query": "AAPL", "purpose": "other"},
            {"query": "AAPL", "full_chat": "private transcript"},
            {"query": "x" * 501},
        ):
            self.assertTrue(list(validator.iter_errors(invalid)))
        data = descriptor["outputSchema"]["properties"]["data"]["properties"]
        self.assertEqual(
            data["status"]["enum"],
            ["resolved", "ambiguous", "not_found_in_supported_markets"],
        )
        self.assertEqual(
            data["purpose"]["enum"],
            ["stock_data", "company_report"],
        )
        company = data["company"]["oneOf"][0]
        self.assertEqual(
            set(company["required"]),
            {
                "exchange",
                "ticker",
                "company_name",
                "website",
                "is_active",
                "instrument_type",
                "match_type",
            },
        )
        self.assertEqual(data["candidates"]["maxItems"], 20)
        self.assertIn("six supported exchange", descriptor["description"])

    def test_company_report_generation_contract_is_host_side_and_bounded(self) -> None:
        descriptor = descriptor_by_name("prepare_company_report_generation")
        self.assertIn("always prepares", descriptor["description"])
        self.assertIn("external-market companies use Others", descriptor["description"])
        self.assertTrue(descriptor["annotations"]["readOnlyHint"])
        self.assertTrue(descriptor["annotations"]["idempotentHint"])
        self.assertFalse(descriptor["annotations"]["openWorldHint"])

        input_schema = descriptor["inputSchema"]
        validator = Draft202012Validator(input_schema)
        self.assertFalse(
            list(
                validator.iter_errors(
                    {
                        "exchange": "NASDAQ",
                        "ticker": "AAPL",
                        "company_name": "Apple Inc.",
                        "output_locale": "zh-CN",
                    }
                )
            )
        )
        for invalid in (
            {
                "exchange": "NASDAQ",
                "ticker": "AAPL",
                "output_locale": "zh-CN",
            },
            {
                "exchange": "NASDAQ",
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "output_locale": "zh_CN",
            },
            {
                "exchange": "NASDAQ",
                "ticker": "AAPL",
                "company_name": "",
                "output_locale": "zh-CN",
            },
        ):
            self.assertTrue(list(validator.iter_errors(invalid)), invalid)

        data = descriptor["outputSchema"]["properties"]["data"]["properties"]
        self.assertEqual(
            data["status"]["enum"],
            ["ready", "not_eligible"],
        )
        self.assertEqual(data["prompt_text"]["maxLength"], 25_000)
        self.assertEqual(data["prompt_version"]["enum"], ["5.1", None])
        self.assertEqual(
            data["identity_source"]["enum"],
            ["master", "host_supplied"],
        )
        self.assertEqual(
            set(input_schema["required"]),
            {"exchange", "ticker", "company_name", "output_locale"},
        )
        self.assertEqual(
            data["next_action"]["enum"],
            ["run_host_web_research", None],
        )

    def test_unknown_modes_tools_and_placeholder_credentials_are_rejected(self) -> None:
        with self.assertRaises(ContractError):
            descriptor_by_name("not-a-tool", self.contract)
        with self.assertRaises(ServiceUnavailableModeError):
            tool_descriptors(self.contract, access_mode="closed")
        serialized = json.dumps(self.contract).lower()
        for forbidden in (
            "replace_with_real",
            "client_secret",
            "refresh_token_value",
            "paste_your",
            "password123",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_invalid_contract_modes_scopes_and_error_metadata_are_rejected(self) -> None:
        invalid_mode = copy.deepcopy(self.contract)
        invalid_mode["source"]["access_mode"] = "public"
        invalid_mode["runtime"]["snapshot_mode"] = "public"
        with self.assertRaisesRegex(ContractError, "supported mode"):
            validate_contract(invalid_mode)

        invalid_profile = copy.deepcopy(self.contract)
        invalid_profile["runtime"]["profiles"]["public_noauth"] = "other"
        with self.assertRaisesRegex(ContractError, "unsupported profile"):
            validate_contract(invalid_profile)

        invalid_scope = copy.deepcopy(self.contract)
        invalid_scope["oauth"]["tool_scopes"]["screen_stocks"] = ["admin.write"]
        with self.assertRaisesRegex(ContractError, "unsupported scopes"):
            validate_contract(invalid_scope)

        invalid_error = copy.deepcopy(self.contract)
        invalid_error["errors"]["rate_limited"]["retryable"] = "yes"
        with self.assertRaisesRegex(ContractError, "retryable"):
            validate_contract(invalid_error)

        legacy_eligible = copy.deepcopy(self.contract)
        screen = next(
            tool for tool in legacy_eligible["tools"]
            if tool["name"] == "screen_stocks"
        )
        policy = screen["outputSchema"]["properties"]["data"]["properties"][
            "export_policy"
        ]["properties"]
        policy["eligible"] = policy.pop("eligible_by_query")
        _rehash(legacy_eligible)
        with self.assertRaisesRegex(ContractError, "eligible_by_query"):
            validate_contract(legacy_eligible)

    def test_anonymous_profile_is_independent_from_backend_mode_name(self) -> None:
        self.assertEqual(
            mode_profile(self.contract, "public_noauth"),
            PROFILE_ANONYMOUS,
        )
        with self.assertRaisesRegex(ContractError, "unsupported access mode"):
            mode_profile(self.contract, "anonymous_dev")

        renamed = copy.deepcopy(self.contract)
        renamed["runtime"]["supported_modes"].append("future_public_mode")
        renamed["runtime"]["profiles"]["future_public_mode"] = PROFILE_ANONYMOUS
        renamed["runtime"]["snapshot_mode"] = "future_public_mode"
        renamed["source"]["access_mode"] = "future_public_mode"
        validate_contract(renamed)
        self.assertEqual(
            mode_profile(renamed, "future_public_mode"),
            PROFILE_ANONYMOUS,
        )
        self.assertTrue(
            all(
                descriptor["securitySchemes"] == [{"type": "noauth"}]
                for descriptor in tool_descriptors(
                    renamed, access_mode="future_public_mode"
                )
            )
        )

    def test_invalid_tool_metadata_and_explicit_empty_contract_are_rejected(self) -> None:
        mismatched_title = copy.deepcopy(self.contract)
        mismatched_title["tools"][0]["annotations"]["title"] = "Different title"
        _rehash(mismatched_title)
        with self.assertRaisesRegex(ContractError, "annotation title"):
            validate_contract(mismatched_title)

        contradictory = copy.deepcopy(self.contract)
        contradictory["tools"][0]["annotations"]["destructiveHint"] = True
        _rehash(contradictory)
        with self.assertRaisesRegex(ContractError, "read-only and destructive"):
            validate_contract(contradictory)

        with self.assertRaises(ContractError):
            tool_descriptors({})
        with self.assertRaises(ContractError):
            tool_names({})

    def test_load_contract_wraps_invalid_json_with_path_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "not valid JSON") as ctx:
                load_contract(path)
        self.assertIn("broken.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
