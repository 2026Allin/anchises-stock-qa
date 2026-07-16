from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "plugins" / "stock-data-desk" / "contracts"
if str(CONTRACTS) not in sys.path:
    sys.path.insert(0, str(CONTRACTS))

from hosted_contract import (  # noqa: E402
    PROFILE_ANONYMOUS,
    descriptor_by_name,
    load_contract,
    mode_profile,
)
from sync_hosted_contract import (  # noqa: E402
    DEFAULT_ENDPOINT,
    MCP_PROTOCOL_VERSION,
    MCPHttpClient,
    contracts_match,
    fetch_contract,
)


RUN_LIVE = os.environ.get("RUN_LIVE_MCP_TESTS") == "1"


@unittest.skipUnless(
    RUN_LIVE,
    "set RUN_LIVE_MCP_TESTS=1 to run credential-free production checks",
)
class LiveHostedContractTest(unittest.TestCase):
    """Opt-in, read-only checks against the real Hosted MCP endpoint."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.checked_in = load_contract()
        cls.endpoint = os.environ.get("MCP_LIVE_ENDPOINT", DEFAULT_ENDPOINT)
        cls.expected_mode = os.environ.get(
            "MCP_EXPECT_MODE",
            cls.checked_in["runtime"]["snapshot_mode"],
        )
        cls.live = fetch_contract(
            cls.endpoint,
            base_contract=cls.checked_in,
            expected_mode=cls.expected_mode,
        )

    def test_live_tools_match_checked_in_snapshot(self) -> None:
        self.assertTrue(contracts_match(self.checked_in, self.live))
        self.assertEqual(len(self.live["tools"]), 11)

    def test_current_anonymous_status_is_readable_without_credentials(self) -> None:
        if mode_profile(self.checked_in, self.expected_mode) != PROFILE_ANONYMOUS:
            self.skipTest("the active mode is not credential-free")

        client = MCPHttpClient(self.endpoint)
        client.call(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "stock-data-desk-live-test",
                    "version": "1.0.0",
                },
            },
            1,
        )
        client.notify("notifications/initialized", {})
        result = client.call(
            "tools/call",
            {
                "name": "get_connection_status",
                "arguments": {},
            },
            2,
        )
        self.assertFalse(result["isError"])
        structured = result["structuredContent"]
        Draft202012Validator(
            descriptor_by_name("get_connection_status")["outputSchema"],
            format_checker=FormatChecker(),
        ).validate(structured)
        self.assertEqual(structured["status"], "active")
        self.assertIn("global quota", structured["message"].lower())


if __name__ == "__main__":
    unittest.main()
