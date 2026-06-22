from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ask_stock import validate_readonly_sql


class SqlSafetyTest(unittest.TestCase):
    def test_valid_select_is_allowed(self) -> None:
        result = validate_readonly_sql(
            "SELECT TICKER, Price_Close FROM daily_20260612_asx LIMIT 10"
        )

        self.assertTrue(result["ok"], result)

    def test_valid_select_for_future_exchange_code_is_allowed_by_pattern(self) -> None:
        result = validate_readonly_sql(
            "SELECT TICKER, Price_Close FROM daily_20260612_lse LIMIT 10"
        )

        self.assertTrue(result["ok"], result)

    def test_valid_cte_is_allowed(self) -> None:
        result = validate_readonly_sql(
            "WITH latest AS (SELECT TICKER FROM daily_20260612_tsxv) "
            "SELECT * FROM latest LIMIT 5"
        )

        self.assertTrue(result["ok"], result)

    def test_write_statement_is_rejected(self) -> None:
        result = validate_readonly_sql("UPDATE daily_20260612_asx SET Price_Close = 0")

        self.assertFalse(result["ok"])
        self.assertTrue(any("Only SELECT" in error for error in result["errors"]))

    def test_dangerous_function_is_rejected(self) -> None:
        result = validate_readonly_sql("SELECT SLEEP(1) FROM daily_20260612_asx")

        self.assertFalse(result["ok"])
        self.assertTrue(any("sleep" in error.lower() for error in result["errors"]))

    def test_system_schema_is_rejected(self) -> None:
        result = validate_readonly_sql("SELECT * FROM information_schema.tables")

        self.assertFalse(result["ok"])
        self.assertTrue(any("non-stock" in error for error in result["errors"]))

    def test_non_stock_table_is_rejected(self) -> None:
        result = validate_readonly_sql("SELECT * FROM users")

        self.assertFalse(result["ok"])
        self.assertTrue(any("non-stock" in error for error in result["errors"]))

    def test_missing_limit_warns(self) -> None:
        result = validate_readonly_sql("SELECT TICKER FROM daily_20260612_nasdaq")

        self.assertTrue(result["ok"], result)
        self.assertTrue(any("No LIMIT" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
