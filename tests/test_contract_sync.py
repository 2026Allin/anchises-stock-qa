from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "plugins" / "anchises-analysis" / "contracts"
TESTS = ROOT / "tests"
if str(CONTRACTS) not in sys.path:
    sys.path.insert(0, str(CONTRACTS))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from hosted_contract import (  # noqa: E402
    ContractError,
    load_contract,
    tool_descriptors,
    validate_contract,
)
from sync_hosted_contract import (  # noqa: E402
    CONTRACT_SYNC_CLIENT_VERSION,
    EXPECTED_ERRORS,
    MAX_RESPONSE_BYTES,
    _jsonrpc_messages,
    _read_limited,
    _security_profile,
    _validated_endpoint,
    contracts_match,
    write_contract,
)


class _Response:
    def __init__(self, body: bytes, headers: dict[str, str] | None = None) -> None:
        self.body = body
        self.headers = headers or {}

    def read(self, limit: int) -> bytes:
        return self.body[:limit]


class ContractSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_contract()

    def test_endpoint_requires_https_except_for_loopback(self) -> None:
        self.assertEqual(
            _validated_endpoint("https://mcp.example.com/mcp"),
            "https://mcp.example.com/mcp",
        )
        self.assertEqual(
            _validated_endpoint("http://127.0.0.1:8765/mcp"),
            "http://127.0.0.1:8765/mcp",
        )
        for invalid in (
            "http://mcp.example.com/mcp",
            "https://user:secret@mcp.example.com/mcp",
            "https://mcp.example.com/mcp?token=secret",
            "file:///tmp/mcp",
        ):
            with self.subTest(endpoint=invalid), self.assertRaises(RuntimeError):
                _validated_endpoint(invalid)

    def test_sync_client_version_is_owned_by_the_plugin(self) -> None:
        self.assertEqual(CONTRACT_SYNC_CLIENT_VERSION, "1.0.0")

    def test_json_and_multiline_sse_responses_are_parsed(self) -> None:
        message = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
        self.assertEqual(_jsonrpc_messages(json.dumps(message)), [message])
        sse = (
            "event: message\n"
            'data: {"jsonrpc":"2.0",\n'
            'data: "id":1,"result":{"ok":true}}\n\n'
        )
        self.assertEqual(_jsonrpc_messages(sse), [message])

    def test_malformed_jsonrpc_payloads_are_rejected(self) -> None:
        for body in ("data: {not-json}\n\n", "[1]", '"text"'):
            with self.subTest(body=body), self.assertRaises(RuntimeError):
                _jsonrpc_messages(body)

    def test_response_limit_checks_declared_and_actual_sizes(self) -> None:
        declared = _Response(b"{}", {"Content-Length": str(MAX_RESPONSE_BYTES + 1)})
        with self.assertRaisesRegex(RuntimeError, "exceeds"):
            _read_limited(declared)
        actual = _Response(b"x" * (MAX_RESPONSE_BYTES + 1))
        with self.assertRaisesRegex(RuntimeError, "exceeds"):
            _read_limited(actual)

    def test_contract_match_ignores_runtime_version_and_sync_timestamp(self) -> None:
        for server_version in ("0.8.0", "0.8.1", "0.9.0"):
            with self.subTest(server_version=server_version):
                refreshed = copy.deepcopy(self.contract)
                refreshed["source"]["synced_at"] = "2099-01-01T00:00:00+00:00"
                refreshed["source"]["server_version"] = server_version
                self.assertTrue(contracts_match(self.contract, refreshed))

    def test_sync_owns_the_complete_export_policy_error_catalog(self) -> None:
        self.assertEqual(self.contract["errors"], EXPECTED_ERRORS)
        self.assertFalse(EXPECTED_ERRORS["query_policy_expired"]["retryable"])
        self.assertTrue(EXPECTED_ERRORS["temporarily_unavailable"]["retryable"])
        refreshed = copy.deepcopy(self.contract)
        refreshed["source"]["instructions"] += " drift"
        self.assertFalse(contracts_match(self.contract, refreshed))
        refreshed = copy.deepcopy(self.contract)
        refreshed["source"]["sync_state"] = "target_pending_mcp_publish"
        self.assertFalse(contracts_match(self.contract, refreshed))

    def test_security_profile_is_inferred_from_live_descriptors(self) -> None:
        self.assertEqual(
            _security_profile(tool_descriptors(self.contract)),
            "anonymous",
        )
        self.assertEqual(
            _security_profile(
                tool_descriptors(self.contract, access_mode="oauth")
            ),
            "authenticated",
        )

        mixed = tool_descriptors(self.contract)
        mixed[0] = tool_descriptors(
            self.contract, access_mode="oauth"
        )[0]
        with self.assertRaisesRegex(RuntimeError, "one consistent"):
            _security_profile(mixed)

        mismatched_meta = tool_descriptors(self.contract)
        mismatched_meta[0]["_meta"]["securitySchemes"] = []
        with self.assertRaisesRegex(RuntimeError, "do not match"):
            _security_profile(mismatched_meta)

    def test_contract_write_is_valid_atomic_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "contract.json"
            write_contract(path, self.contract)
            self.assertEqual(load_contract(path), self.contract)
            self.assertTrue(path.read_bytes().endswith(b"\n"))
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_validator_requires_service_only_connection_status(self) -> None:
        self.assertEqual(self.contract["contract_version"], "1.9.0-draft")
        validate_contract(self.contract)
        drifted = copy.deepcopy(self.contract)
        status = next(
            tool for tool in drifted["tools"] if tool["name"] == "get_connection_status"
        )
        status["outputSchema"]["properties"]["client_update"] = {"type": "null"}
        canonical = json.dumps(
            drifted["tools"], sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        drifted["source"]["descriptor_sha256"] = hashlib.sha256(canonical).hexdigest()
        with self.assertRaisesRegex(ContractError, "plugin release metadata"):
            validate_contract(drifted)

    def test_validator_rejects_non_semantic_observed_server_version(self) -> None:
        drifted = copy.deepcopy(self.contract)
        drifted["source"]["server_version"] = "release-current"
        with self.assertRaisesRegex(ContractError, "semantic version"):
            validate_contract(drifted)

    def test_version_independence_does_not_hide_missing_capabilities(self) -> None:
        drifted = copy.deepcopy(self.contract)
        screen = next(
            tool for tool in drifted["tools"] if tool["name"] == "screen_stocks"
        )
        del screen["inputSchema"]["properties"]["cursor"]
        canonical = json.dumps(
            drifted["tools"], sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        drifted["source"]["descriptor_sha256"] = hashlib.sha256(canonical).hexdigest()
        drifted["source"]["server_version"] = "0.9.0"
        with self.assertRaisesRegex(ContractError, "capability contract"):
            contracts_match(self.contract, drifted)


if __name__ == "__main__":
    unittest.main()
