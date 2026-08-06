from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
CROSS_WORKSPACE_GUIDE = (
    ROOT / "docs" / "anchises-analysis-codex-cross-workspace-install.md"
)


class MarketplaceManifestTest(unittest.TestCase):
    def test_marketplace_points_to_plugin_package(self) -> None:
        data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "Anchises-Analysis")
        self.assertEqual(data["interface"]["displayName"], "Anchises Analysis")
        plugins = {plugin["name"]: plugin for plugin in data["plugins"]}

        plugin = plugins["anchises-analysis"]
        self.assertEqual(plugin["source"]["source"], "local")
        self.assertEqual(plugin["source"]["path"], "./plugins/anchises-analysis")
        self.assertEqual(plugin["policy"]["installation"], "AVAILABLE")
        self.assertEqual(plugin["policy"]["authentication"], "ON_USE")

        plugin_root = ROOT / plugin["source"]["path"]
        self.assertTrue((plugin_root / ".codex-plugin" / "plugin.json").exists())
        self.assertFalse((plugin_root / ".app.json").exists())
        self.assertTrue((plugin_root / ".mcp.json").exists())
        self.assertTrue((plugin_root / "skills" / "anchises-analysis").is_dir())
        self.assertTrue((plugin_root / "skills" / "company-brief").is_dir())
        self.assertTrue((plugin_root / "skills" / "company-report").is_dir())
        self.assertTrue((plugin_root / "skills" / "company-comparison").is_dir())
        self.assertTrue((plugin_root / "skills" / "market-analysis").is_dir())

        manifest = json.loads(
            (plugin_root / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        mcp_manifest = json.loads(
            (plugin_root / ".mcp.json").read_text(encoding="utf-8")
        )
        contract = json.loads(
            (plugin_root / "contracts" / "hosted-mcp-v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertNotIn("apps", manifest)
        self.assertEqual(
            mcp_manifest,
            {
                "mcpServers": {
                    "anchises_analysis": {
                        "type": "http",
                        "url": "https://mcp.anchisesdata.com/mcp",
                    }
                }
            },
        )
        self.assertEqual(manifest["version"].split("+", 1)[0], "0.6.0-dev.6")
        self.assertRegex(
            manifest["version"],
            r"^0\.6\.0-dev\.6(?:\+codex\.[0-9A-Za-z][0-9A-Za-z.-]*)?$",
        )
        self.assertLessEqual(manifest["version"].count("+codex."), 1)
        self.assertEqual(contract["contract_version"], "1.9.0-draft")
        self.assertRegex(
            contract["source"]["server_version"],
            r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)",
        )
        self.assertEqual(contract["source"]["access_mode"], "public_noauth")

    def test_cross_workspace_install_uses_git_and_bundled_mcp(self) -> None:
        guide = CROSS_WORKSPACE_GUIDE.read_text(encoding="utf-8")
        normalized = " ".join(guide.split())
        for expected in (
            "https://github.com/2026Allin/anchises-stock-qa.git",
            "--ref main",
            "--sparse .agents/plugins",
            "--sparse plugins/anchises-analysis",
            "codex plugin add anchises-analysis@Anchises-Analysis",
            "https://mcp.anchisesdata.com/mcp",
            "all five Skills",
            "exactly 12 tools",
        ):
            self.assertIn(expected, normalized)
        self.assertNotIn("plugin_asdk_app", guide)


if __name__ == "__main__":
    unittest.main()
