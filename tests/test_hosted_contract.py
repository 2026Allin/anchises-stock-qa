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
PLUGIN_ROOT = ROOT / "plugins" / "stock-data-desk"
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
    "get_latest_company_report",
    "create_csv_export",
]
PAGINATED_TOOLS = {"list_stock_tables", "screen_stocks", "run_readonly_sql"}


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
        self.assertEqual(self.contract["contract_version"], "1.2.0-draft")
        runtime = self.contract["runtime"]
        self.assertEqual(
            runtime["supported_modes"],
            ["closed", "anonymous_dev", "oauth"],
        )
        self.assertEqual(runtime["snapshot_mode"], "anonymous_dev")
        self.assertEqual(
            mode_profiles(self.contract),
            {
                "closed": PROFILE_UNAVAILABLE,
                "anonymous_dev": PROFILE_ANONYMOUS,
                "oauth": PROFILE_AUTHENTICATED,
            },
        )
        source = self.contract["source"]
        self.assertEqual(source["mcp_endpoint"], "https://mcp.anchisesdata.com/mcp")
        self.assertEqual(source["access_mode"], "anonymous_dev")
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
        self.assertEqual(len(self.descriptors), 11)
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
                "resource_not_found",
                "result_too_large",
                "temporarily_unavailable",
            },
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
                    self.assertIn("description", prop)

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

    def test_only_paginated_tools_publish_complete_page_schema(self) -> None:
        for descriptor in self.descriptors:
            page = descriptor["outputSchema"]["properties"].get("page")
            if descriptor["name"] in PAGINATED_TOOLS:
                self.assertIsNotNone(page)
                self.assertEqual(
                    set(page["required"]),
                    {"row_count", "total_count", "truncated", "next_cursor"},
                )
            else:
                self.assertIsNone(page)

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

    def test_company_report_contract_and_projection_are_bounded(self) -> None:
        descriptor = descriptor_by_name("get_latest_company_report")
        schema = descriptor["inputSchema"]
        validator = Draft202012Validator(schema)
        self.assertFalse(
            list(
                validator.iter_errors(
                    {
                        "exchange": "ASX",
                        "ticker": "BGL",
                        "source": "auto",
                        "pdf_range": "1Y",
                    }
                )
            )
        )
        for invalid in (
            {"exchange": "asx", "ticker": "BGL"},
            {"exchange": "ASX", "ticker": "BGL", "language": "en"},
            {"exchange": "ASX", "ticker": "BGL", "source": "other"},
            {"exchange": "ASX", "ticker": "BGL", "pdf_range": "5Y"},
        ):
            self.assertTrue(list(validator.iter_errors(invalid)))
        serialized = json.dumps(descriptor["outputSchema"]).lower()
        for forbidden in (
            "raw_markdown",
            "section_blocks",
            "sections_legacy",
            "model_usage",
            "cost",
            "search_events",
            "internal_id",
        ):
            self.assertNotIn(forbidden, serialized)

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
        invalid_profile["runtime"]["profiles"]["anonymous_dev"] = "other"
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

    def test_future_anonymous_mode_name_is_one_mapping_change(self) -> None:
        renamed = copy.deepcopy(self.contract)
        renamed["runtime"]["supported_modes"].append("public_noauth")
        renamed["runtime"]["profiles"]["public_noauth"] = PROFILE_ANONYMOUS
        renamed["runtime"]["snapshot_mode"] = "public_noauth"
        renamed["source"]["access_mode"] = "public_noauth"
        validate_contract(renamed)
        self.assertEqual(
            mode_profile(renamed, "public_noauth"),
            PROFILE_ANONYMOUS,
        )
        self.assertTrue(
            all(
                descriptor["securitySchemes"] == [{"type": "noauth"}]
                for descriptor in tool_descriptors(
                    renamed, access_mode="public_noauth"
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
