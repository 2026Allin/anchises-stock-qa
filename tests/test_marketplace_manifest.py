from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"


class MarketplaceManifestTest(unittest.TestCase):
    def test_marketplace_points_to_plugin_package(self) -> None:
        data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "Anchises-Tech")
        plugins = {plugin["name"]: plugin for plugin in data["plugins"]}

        plugin = plugins["anchises-stock-qa"]
        self.assertEqual(plugin["source"]["source"], "local")
        self.assertEqual(plugin["source"]["path"], "./plugins/anchises-stock-qa")
        self.assertEqual(plugin["policy"]["installation"], "AVAILABLE")
        self.assertEqual(plugin["policy"]["authentication"], "ON_INSTALL")

        plugin_root = ROOT / plugin["source"]["path"]
        self.assertTrue((plugin_root / ".codex-plugin" / "plugin.json").exists())
        self.assertTrue((plugin_root / ".mcp.json").exists())
        self.assertTrue((plugin_root / "skills" / "anchises-stock-qa").is_dir())


if __name__ == "__main__":
    unittest.main()
