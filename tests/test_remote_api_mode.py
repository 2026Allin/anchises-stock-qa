from __future__ import annotations

import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import sys

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "stock-data-desk"
SCRIPTS = PLUGIN_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import remote_api
from ask_stock import run_readonly_sql, validate_readonly_sql, verify_database
from config import load_config


class RemoteAPIModeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_config = os.environ.get("ANCHISES_STOCK_QA_CONFIG")

    def tearDown(self) -> None:
        if self._old_config is None:
            os.environ.pop("ANCHISES_STOCK_QA_CONFIG", None)
        else:
            os.environ["ANCHISES_STOCK_QA_CONFIG"] = self._old_config

    def _write_remote_config(self, root: Path) -> Path:
        outputs = root / "outputs"
        config_path = root / "config.toml"
        config_path.write_text(
            "\n".join(
                [
                    "[backend]",
                    'mode = "remote_api"',
                    'api_base_url = "https://api.example.com/anchises-stock-qa"',
                    'api_token = "secret-token"',
                    "[database]",
                    'url = ""',
                    'access_mode = "readonly"',
                    "[outputs]",
                    f'dir = "{outputs}"',
                ]
            ),
            encoding="utf-8",
        )
        os.environ["ANCHISES_STOCK_QA_CONFIG"] = str(config_path)
        return outputs

    def test_validate_sql_uses_remote_api_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_remote_config(Path(tmp))

            with patch("ask_stock.remote_api.request_json") as request_json:
                request_json.return_value = {
                    "ok": True,
                    "normalized_sql": "SELECT 1",
                    "errors": [],
                    "warnings": [],
                    "referenced_tables": [],
                }
                result = validate_readonly_sql("SELECT 1")

        self.assertTrue(result["ok"])
        request_json.assert_called_once()
        _, method, path, payload = request_json.call_args.args
        self.assertEqual(method, "POST")
        self.assertEqual(path, "/v1/validate-sql")
        self.assertEqual(payload["sql"], "SELECT 1")

    def test_validate_sql_allows_remote_ok_false_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_remote_config(Path(tmp))

            with patch("ask_stock.remote_api.request_json") as request_json:
                request_json.return_value = {
                    "ok": False,
                    "normalized_sql": "SELECT * FROM users",
                    "errors": ["table not in white-list"],
                    "warnings": [],
                    "referenced_tables": ["users"],
                }
                result = validate_readonly_sql("SELECT * FROM users")

        self.assertFalse(result["ok"])
        request_json.assert_called_once()
        self.assertTrue(request_json.call_args.kwargs.get("allow_ok_false"))

    def test_verify_database_uses_remote_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_remote_config(Path(tmp))

            with patch("ask_stock.remote_api.request_json") as request_json:
                request_json.return_value = {"ok": True, "service": "stock-qa-api"}
                result = verify_database()

        self.assertTrue(result["ok"])
        self.assertEqual(result["backend"]["mode"], "remote_api")
        self.assertTrue(result["backend"]["api_token_configured"])
        self.assertNotIn("secret-token", json.dumps(result))
        request_json.assert_called_once()
        _, method, path = request_json.call_args.args[:3]
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/v1/health")

    def test_run_readonly_sql_writes_remote_csv_locally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outputs = self._write_remote_config(Path(tmp))

            with patch("ask_stock.remote_api.request_json") as request_json:
                request_json.return_value = {
                    "ok": True,
                    "csv_text": "Ticker,Score\nABC,1\n",
                    "metadata": {
                        "row_count": 1,
                        "column_count": 2,
                        "columns": ["Ticker", "Score"],
                    },
                    "validation": {"ok": True},
                    "request_id": "req-123",
                }
                result = run_readonly_sql(
                    "SELECT Ticker, Score FROM daily_20260622_asx",
                    output_name="remote_result",
                    max_rows=50,
                )

            csv_path = Path(result["output_csv"])
            metadata_path = Path(result["metadata_json"])

            self.assertTrue(str(csv_path.resolve()).startswith(str(outputs.resolve())))
            self.assertEqual(
                csv_path.read_text(encoding="utf-8"),
                "Ticker,Score\nABC,1\n",
            )
            self.assertTrue(metadata_path.exists())
            metadata_text = metadata_path.read_text(encoding="utf-8")
            self.assertNotIn("secret-token", metadata_text)
            metadata = json.loads(metadata_text)
            self.assertEqual(metadata["config"]["backend_mode"], "remote_api")
            self.assertEqual(metadata["row_count"], 1)
            self.assertEqual(metadata["remote"]["request_id"], "req-123")
            self.assertEqual(
                Path(result["query_sql"]).read_text(encoding="utf-8").strip(),
                "SELECT Ticker, Score FROM daily_20260622_asx",
            )
            request_json.assert_called_once()
            _, method, path, payload = request_json.call_args.args
            self.assertEqual(method, "POST")
            self.assertEqual(path, "/v1/run-sql")
            self.assertEqual(payload["max_rows"], 50)

    def test_run_readonly_sql_clamps_zero_max_rows_before_remote_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_remote_config(Path(tmp))

            with patch("ask_stock.remote_api.request_json") as request_json:
                request_json.return_value = {
                    "ok": True,
                    "csv_text": "Ticker\nABC\n",
                    "metadata": {
                        "row_count": 1,
                        "column_count": 1,
                        "columns": ["Ticker"],
                    },
                    "validation": {"ok": True},
                    "request_id": "req-rows",
                }
                run_readonly_sql(
                    "SELECT Ticker FROM daily_20260622_asx",
                    output_name="remote_result",
                    max_rows=0,
                )

            _, _, _, payload = request_json.call_args.args
            self.assertEqual(payload["max_rows"], 1)

    def test_remote_http_error_redacts_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_remote_config(Path(tmp))
            config = load_config(require_database_url=True)

            def raise_http_error(request, timeout):
                raise HTTPError(
                    request.full_url,
                    401,
                    "Unauthorized",
                    {},
                    BytesIO(b'{"error":"bad token secret-token"}'),
                )

            with patch("remote_api.urlopen", side_effect=raise_http_error):
                with self.assertRaises(remote_api.RemoteAPIError) as ctx:
                    remote_api.request_json(config, "GET", "/v1/health")

        self.assertIn("HTTP 401", str(ctx.exception))
        self.assertNotIn("secret-token", str(ctx.exception))

    def test_remote_invalid_json_is_reported(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return b"not-json"

        with tempfile.TemporaryDirectory() as tmp:
            self._write_remote_config(Path(tmp))
            config = load_config(require_database_url=True)

            with patch("remote_api.urlopen", return_value=FakeResponse()):
                with self.assertRaises(remote_api.RemoteAPIError) as ctx:
                    remote_api.request_json(config, "GET", "/v1/health")

        self.assertIn("invalid JSON", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
