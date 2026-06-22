from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ask_stock import (  # noqa: E402
    StockQAError,
    _daily_table_info,
    _diff_schema_snapshots,
    _normalize_allowed_table_name,
    _normalize_exchanges,
    _parse_date_key,
)


class TableDiscoveryTest(unittest.TestCase):
    def test_parse_date_key_accepts_iso_and_compact(self) -> None:
        self.assertEqual(_parse_date_key("2026-06-22", "date_start"), "20260622")
        self.assertEqual(_parse_date_key("20260622", "date_end"), "20260622")

    def test_parse_date_key_rejects_invalid_date(self) -> None:
        with self.assertRaises(StockQAError):
            _parse_date_key("2026-02-30", "date_start")

    def test_daily_table_info_extracts_exchange_and_date(self) -> None:
        info = _daily_table_info("daily_20260622_asx")

        self.assertIsNotNone(info)
        self.assertEqual(info["exchange"], "ASX")
        self.assertEqual(info["date"], "2026-06-22")

    def test_dynamic_exchange_code_is_allowed_by_table_pattern(self) -> None:
        info = _daily_table_info("daily_20260622_lse")

        self.assertIsNotNone(info)
        self.assertEqual(info["exchange"], "LSE")
        self.assertEqual(
            _normalize_allowed_table_name("daily_20260622_lse"),
            "daily_20260622_lse",
        )

    def test_available_exchange_list_controls_requested_exchanges(self) -> None:
        self.assertEqual(_normalize_exchanges(["LSE"], ["asx", "lse"]), ["lse"])
        self.assertEqual(_normalize_exchanges(None, ["asx", "lse"]), ["asx", "lse"])
        with self.assertRaises(StockQAError):
            _normalize_exchanges(["NYSE"], ["asx", "lse"])

    def test_allowed_table_name_blocks_schema_and_non_stock_table(self) -> None:
        self.assertEqual(
            _normalize_allowed_table_name("daily_20260622_nasdaq"),
            "daily_20260622_nasdaq",
        )
        with self.assertRaises(StockQAError):
            _normalize_allowed_table_name("daily_20260622_lse", ["asx"])
        with self.assertRaises(StockQAError):
            _normalize_allowed_table_name("information_schema.tables")
        with self.assertRaises(StockQAError):
            _normalize_allowed_table_name("users")

    def test_schema_snapshot_diff_reports_table_and_column_changes(self) -> None:
        previous = {
            "created_at_utc": "2026-06-01T00:00:00+00:00",
            "inventory_hash": "old-inventory",
            "schema_hash": "old-schema",
            "tables": {
                "daily_20260620_asx": {
                    "columns": [
                        {"name": "TICKER", "type": "varchar(32)", "nullable": False},
                        {"name": "Price_Close", "type": "double", "nullable": True},
                    ]
                },
                "daily_20260620_tsx": {"columns": []},
            },
        }
        current = {
            "created_at_utc": "2026-06-22T00:00:00+00:00",
            "inventory_hash": "new-inventory",
            "schema_hash": "new-schema",
            "tables": {
                "daily_20260620_asx": {
                    "columns": [
                        {"name": "TICKER", "type": "varchar(64)", "nullable": False},
                        {"name": "Volume_Traded", "type": "bigint", "nullable": True},
                    ]
                },
                "daily_20260622_asx": {"columns": []},
            },
        }

        diff = _diff_schema_snapshots(previous, current)

        self.assertTrue(diff["changed"])
        self.assertEqual(diff["added_tables"]["items"], ["daily_20260622_asx"])
        self.assertEqual(diff["removed_tables"]["items"], ["daily_20260620_tsx"])
        changed_table = diff["changed_tables"]["items"][0]
        self.assertEqual(changed_table["table_name"], "daily_20260620_asx")
        self.assertEqual(changed_table["added_columns"], ["Volume_Traded"])
        self.assertEqual(changed_table["removed_columns"], ["Price_Close"])
        self.assertEqual(changed_table["changed_columns"][0]["name"], "TICKER")


if __name__ == "__main__":
    unittest.main()
