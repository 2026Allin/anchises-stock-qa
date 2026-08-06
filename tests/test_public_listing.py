from __future__ import annotations

import hashlib
import json
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "anchises-analysis"
MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
LISTING = ROOT / "docs" / "anchises-analysis-plugin-directory-listing.md"
AVAILABILITY = (
    ROOT / "docs" / "openai-plugin-availability-regions-2026-07-16.md"
)


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise AssertionError(f"{path} is not a valid PNG")
    return struct.unpack(">II", data[16:24])


class PublicListingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.listing = LISTING.read_text(encoding="utf-8")
        cls.availability = AVAILABILITY.read_text(encoding="utf-8")

    def test_listing_matches_manifest_metadata(self) -> None:
        interface = self.manifest["interface"]
        for value in (
            interface["displayName"],
            interface["shortDescription"],
            interface["longDescription"],
            self.manifest["author"]["name"],
            self.manifest["author"]["email"],
            interface["websiteURL"],
            interface["privacyPolicyURL"],
            interface["termsOfServiceURL"],
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.listing)

        self.assertIn("https://anchisesdata.com/support", self.listing)
        self.assertIn("Primary listing locale: English (en)", self.listing)
        self.assertIn("Category: Productivity", self.listing)
        self.assertIn("Version: 0.6.0-dev.9", self.listing)
        self.assertIn(
            "MCP version: discovered dynamically at connection time",
            self.listing,
        )
        self.assertIn("Data API version: 0.3.0", self.listing)
        self.assertIn("Contract version: `1.9.0-draft`", self.listing)
        self.assertIn("server-enforced query and export capabilities", self.listing)

    def test_listing_uses_the_exact_starter_prompts(self) -> None:
        prompts = self.manifest["interface"]["defaultPrompt"]
        self.assertEqual(len(prompts), 3)
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertTrue(prompt.isascii())
                self.assertLessEqual(len(prompt), 128)
                self.assertIn(prompt, self.listing)

    def test_long_description_contains_release_disclosures(self) -> None:
        description = self.manifest["interface"]["longDescription"]
        for disclosure in (
            "resolves a company name or ticker",
            "live web search",
            "current conversation",
            "does not persist",
            "official filings or investment advice",
            "no Anchises Analysis account or credentials",
            "shared short-term service limits",
            "short-lived bearer links",
            "ASX, CSE, NASDAQ, NYSE, TSX, and TSXV",
            "at most 200 rows",
            "opaque cursor",
            "Top-N bounds the complete logical ranked result",
            "server-enforced query and export capabilities",
            "allowed screen or SQL source tools",
            "no account-linked cross-session cumulative budget",
        ):
            with self.subTest(disclosure=disclosure):
                self.assertIn(disclosure, description)

    def test_public_copy_describes_server_analysis_pagination_and_dynamic_exports(self) -> None:
        normalized_listing = " ".join(self.listing.split())
        for expected in (
            "Full matched stock-data ranges may be analyzed",
            "at most 200 rows per call",
            "opaque cursor",
            "Top-N controls the complete logical result",
            "allowed screen or SQL source tools",
            "Policy changes invalidate old cursors and query IDs",
            "rather than from a fixed template",
            "no account-linked cross-session cumulative budget",
        ):
            self.assertIn(expected, normalized_listing)

        release_surfaces = [
            self.manifest["interface"]["longDescription"],
            self.listing,
            (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "anchises-analysis-marketplace-release-plan.md").read_text(
                encoding="utf-8"
            ),
        ]
        forbidden = (
            "no subsequent row-level pages",
            "does not provide later row-level pages",
            "sql results cannot be exported",
            "complete exchange-day partitions and sql results cannot be exported",
            "stock-row cursors are not supported",
        )
        for text in release_surfaces:
            lowered = text.lower()
            for phrase in forbidden:
                self.assertNotIn(phrase.lower(), lowered)

        public_threshold_recitals = (
            "1,000 rows",
            "25 total columns",
            "20,000 cells",
            "Top-N 200",
            "50 exact tickers",
        )
        for text in release_surfaces:
            for phrase in public_threshold_recitals:
                self.assertNotIn(phrase, text)

    def test_production_logo_assets_are_frozen(self) -> None:
        expected = {
            "logo.png": (
                (512, 512),
                "3eef3b9fcb0b64e9d6168a47363fdd65e09f368e2dfc3adced04cde683580c6d",
            ),
            "composer-icon.png": (
                (512, 512),
                "3eef3b9fcb0b64e9d6168a47363fdd65e09f368e2dfc3adced04cde683580c6d",
            ),
        }
        for filename, (dimensions, digest) in expected.items():
            path = PLUGIN_ROOT / "assets" / filename
            with self.subTest(filename=filename):
                self.assertEqual(png_dimensions(path), dimensions)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

    def test_no_ui_submission_omits_screenshots(self) -> None:
        interface = self.manifest["interface"]
        self.assertNotIn("screenshots", interface)
        self.assertIn("Custom UI: None", self.listing)
        self.assertIn("Screenshots: None", self.listing)
        self.assertIn("Do not submit", self.listing)

    def test_external_submission_blockers_are_explicit(self) -> None:
        for blocker in (
            "exact CSP validation",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, self.listing)

        self.assertIn(
            "- [x] Confirm `Anchises Capital` is selectable",
            self.listing,
        )
        self.assertIn(
            "- [x] Confirm the submitter has `Apps Management: Write`.",
            self.listing,
        )
        self.assertIn(
            "- [x] Select broad public availability",
            self.listing,
        )
        self.assertIn(
            "- [x] Deploy and verify the Terms and Product-page changes",
            self.listing,
        )

    def test_availability_snapshot_is_complete_and_clearly_dated(self) -> None:
        snapshot = self.availability.split(
            "## Current public planning snapshot (208)",
            1,
        )[1].split("## Approved release decision for Anchises Analysis", 1)[0]
        entries = [
            line.removeprefix("- ")
            for line in snapshot.splitlines()
            if line.startswith("- ")
        ]
        self.assertEqual(len(entries), 208)
        self.assertEqual(entries[0], "Albania")
        self.assertEqual(entries[-1], "Zimbabwe")
        for location in (
            "Australia",
            "Canada",
            "Singapore",
            "United Kingdom",
            "United States of America",
        ):
            with self.subTest(location=location):
                self.assertIn(location, entries)

        self.assertIn("live `Global` tab is the source of truth", self.availability)
        self.assertIn(
            "select every country or region offered by the live plugin "
            "submission portal",
            self.availability,
        )


if __name__ == "__main__":
    unittest.main()
