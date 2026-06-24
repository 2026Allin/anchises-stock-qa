#!/usr/bin/env python3
"""Read-only Stocks_Tracker export tools for Codex analysis.

Codex writes and reasons about SQL. This module validates read-only SQL,
executes it against the configured MySQL database, and exports CSV files for
Codex to inspect with pandas or other local tools.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import shlex
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from config import (
    ConfigError,
    StockQAConfig,
    config_as_dict,
    config_path,
    load_config,
    redact_url,
    sanitize_error_text,
)
from output_cleanup import cleanup_outputs as run_cleanup_outputs
from output_cleanup import maybe_cleanup_outputs
from prompts import (
    get_prompt_catalog as run_get_prompt_catalog,
    get_prompt_bundle as load_prompt_bundle,
    initialize_custom_prompts as run_initialize_custom_prompts,
    list_custom_prompts as run_list_custom_prompts,
    preview_custom_prompt_update as run_preview_custom_prompt_update,
    read_custom_prompt as run_read_custom_prompt,
    reset_custom_prompt as run_reset_custom_prompt,
    write_custom_prompt as run_write_custom_prompt,
)
import remote_api


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
EXCHANGE_CODE_PATTERN = r"[a-z0-9]+"
DEFAULT_REMOTE_API_URL = "https://anchisesdata.com/anchises-stock-qa"
BUILTIN_EXCHANGE_ALIASES = {
    "asx": "asx",
    "asxexchange": "asx",
    "asx交易所": "asx",
    "australia": "asx",
    "australian": "asx",
    "澳洲": "asx",
    "澳大利亚": "asx",
    "tsxv": "tsxv",
    "tsxvexchange": "tsxv",
    "tsxv交易所": "tsxv",
    "tsxventure": "tsxv",
    "tsxventureexchange": "tsxv",
    "torontoventure": "tsxv",
    "canadianventure": "tsxv",
    "canadian": "tsxv",
    "toronto": "tsxv",
    "加拿大": "tsxv",
    "多伦多": "tsxv",
    "tsx": "tsx",
    "tsxexchange": "tsx",
    "tsx交易所": "tsx",
    "torontostockexchange": "tsx",
    "torontoexchange": "tsx",
    "多伦多证券交易所": "tsx",
    "多伦多股票交易所": "tsx",
    "cse": "cse",
    "cseexchange": "cse",
    "cse交易所": "cse",
    "canadiansecuritiesexchange": "cse",
    "canadiansecurities": "cse",
    "cnsx": "cse",
    "加拿大证券交易所": "cse",
    "nyse": "nyse",
    "nyseexchange": "nyse",
    "nyse交易所": "nyse",
    "newyorkstockexchange": "nyse",
    "纽交所": "nyse",
    "纽约证券交易所": "nyse",
    "nasdaq": "nasdaq",
    "nasdaqexchange": "nasdaq",
    "nasdaq交易所": "nasdaq",
    "nasdaqstockmarket": "nasdaq",
    "纳斯达克": "nasdaq",
}
DAILY_TABLE_RE = re.compile(rf"^daily_(\d{{8}})_({EXCHANGE_CODE_PATTERN})$", re.I)
MASTER_TABLE_RE = re.compile(rf"^exchange_({EXCHANGE_CODE_PATTERN})_master$", re.I)
METALS_TABLE_RE = re.compile(r"^metals$", re.I)
ALLOWED_TABLE_PATTERNS = [
    DAILY_TABLE_RE,
    MASTER_TABLE_RE,
    METALS_TABLE_RE,
]
SYSTEM_SCHEMAS = {"information_schema", "mysql", "performance_schema", "sys"}

DENIED_KEYWORD_PATTERNS = [
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\bcreate\b",
    r"\btruncate\b",
    r"\breplace\b",
    r"\bmerge\b",
    r"\bcall\b",
    r"\bexec(?:ute)?\b",
    r"\bgrant\b",
    r"\brevoke\b",
    r"\bset\b",
    r"\buse\b",
    r"\block\b",
    r"\bunlock\b",
    r"\bload\b",
    r"\bhandler\b",
    r"\banalyze\b",
    r"\boptimize\b",
    r"\brepair\b",
    r"\breset\b",
    r"\bkill\b",
    r"\bshutdown\b",
    r"\bprepare\b",
    r"\bdeallocate\b",
    r"\binto\b",
    r"\bfor\s+update\b",
    r"\block\s+in\s+share\s+mode\b",
    r"\boutfile\b",
    r"\binfile\b",
    r"\bdumpfile\b",
    r"\bload_file\s*\(",
    r"\bsleep\s*\(",
    r"\bbenchmark\s*\(",
    r"\bget_lock\s*\(",
    r"\brelease_lock\s*\(",
]

_ENGINE_CACHE: Dict[str, Any] = {}


class StockQAError(RuntimeError):
    pass


@dataclass
class SQLValidationResult:
    ok: bool
    normalized_sql: str
    errors: List[str]
    warnings: List[str]
    referenced_tables: List[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "normalized_sql": self.normalized_sql,
            "errors": self.errors,
            "warnings": self.warnings,
            "referenced_tables": self.referenced_tables,
        }


def _json_default(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _config_for_database() -> StockQAConfig:
    try:
        return load_config(require_database_url=True)
    except ConfigError as exc:
        raise StockQAError(str(exc)) from exc


def _setup_command(extra_args: List[str] | None = None) -> str:
    init_script = PLUGIN_ROOT / "scripts" / "init_config.sh"
    parts = ["bash", str(init_script)]
    parts.extend(extra_args or [])
    return " ".join(shlex.quote(part) for part in parts)


def get_setup_instructions() -> Dict[str, Any]:
    """Return first-time setup and token-reset instructions for the installed plugin."""
    init_script = PLUGIN_ROOT / "scripts" / "init_config.sh"
    readme_path = PLUGIN_ROOT / "README.md"
    config_exists = False
    api_token_configured = False
    api_base_url = ""
    backend_mode = "remote_api"
    errors: List[str] = []

    try:
        config = load_config(require_database_url=False)
        config_exists = config.config_exists
        api_base_url = (
            config_as_dict(config)["backend"]["api_base_url"]
            or DEFAULT_REMOTE_API_URL
        )
        api_token_configured = bool(config.backend.api_token)
        if not config.config_exists:
            errors.append(config.missing_config_message)
        if _is_remote(config):
            errors.extend(_remote_config_errors(config))
    except ConfigError as exc:
            errors.append(str(exc))
    if not api_base_url:
        api_base_url = DEFAULT_REMOTE_API_URL

    configured = config_exists and api_token_configured and not errors
    setup_command = _setup_command(["--prepare-runtime"])
    setup_without_runtime_command = _setup_command()
    force_recreate_command = _setup_command(["--force"])
    action = "reset_token" if api_token_configured else "first_time_setup"
    title = (
        "Anchises Stock QA is already configured"
        if configured
        else "Set up Anchises Stock QA"
    )
    summary = (
        "Run the reset command if you received a new API token."
        if api_token_configured
        else "Run the setup command and paste your API token when prompted."
    )

    return {
        "ok": True,
        "trigger_phrases": [
            "Set up Anchises Stock QA",
            "Reset Anchises Stock QA token",
            "Check the Anchises Stock QA connection",
        ],
        "title": title,
        "summary": summary,
        "action": action,
        "plugin_root": str(PLUGIN_ROOT),
        "readme_path": str(readme_path),
        "init_script": str(init_script),
        "config_path": str(config_path()),
        "config_exists": config_exists,
        "configured": configured,
        "runtime": {
            "prepare_runtime_on_setup": True,
            "venv_dir": str(PLUGIN_ROOT / ".venv"),
            "requirements": str(PLUGIN_ROOT / "requirements.txt"),
            "prepare_command": setup_command,
            "first_run_note": (
                "The setup command prepares the plugin Python runtime. "
                "The first run may take a few minutes while pandas and MCP dependencies install."
            ),
        },
        "backend": {
            "mode": backend_mode or "remote_api",
            "api_base_url": api_base_url,
            "api_token_configured": api_token_configured,
            "secrets_redacted": True,
        },
        "commands": {
            "setup_or_reset_token": setup_command,
            "setup_or_reset_token_without_runtime_prepare": setup_without_runtime_command,
            "force_recreate_config": force_recreate_command,
        },
        "instructions": [
            "Open Terminal.",
            "Run the setup_or_reset_token command exactly as shown.",
            "Paste your Anchises Stock QA API token when prompted; the token is hidden while typing.",
            "The first run may take a few minutes while Python dependencies are prepared.",
            "Run the same command again later to replace the token while keeping other settings.",
            "After setup, ask Codex: Check the Anchises Stock QA connection.",
        ],
        "errors": errors,
        "notes": [
            "Users do not need a database URL.",
            "Python dependencies are installed into the plugin-local .venv, not globally.",
            "The config file is outside the plugin install and is kept across plugin updates.",
            "Do not paste the API token into chat; enter it only in Terminal when the script prompts.",
        ],
    }


def _is_remote(config: StockQAConfig) -> bool:
    return config.backend.mode == "remote_api"


def _remote_config_errors(config: StockQAConfig) -> List[str]:
    errors: List[str] = []
    if not config.backend.api_base_url:
        errors.append("[backend].api_base_url is required for remote_api mode")
    if not config.backend.api_token:
        errors.append("[backend].api_token is required for remote_api mode")
    return errors


def _remote_request(
    config: StockQAConfig,
    method: str,
    path: str,
    payload: Dict[str, Any] | None = None,
    *,
    allow_ok_false: bool = False,
) -> Dict[str, Any]:
    try:
        return remote_api.request_json(
            config,
            method,
            path,
            payload,
            allow_ok_false=allow_ok_false,
        )
    except remote_api.RemoteAPIError as exc:
        raise StockQAError(sanitize_error_text(str(exc), config)) from exc


def _engine(config: StockQAConfig) -> Any:
    cache_key = config.database.url
    if cache_key not in _ENGINE_CACHE:
        _ENGINE_CACHE[cache_key] = create_engine(
            config.database.url,
            pool_pre_ping=True,
            pool_recycle=1800,
            future=True,
        )
    return _ENGINE_CACHE[cache_key]


def _exchange_alias_key(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", str(value or "")).lower()


def _exchange_aliases(config: StockQAConfig | None = None) -> Dict[str, str]:
    aliases = dict(BUILTIN_EXCHANGE_ALIASES)
    if config:
        aliases.update(
            {
                _exchange_alias_key(key): str(value).strip().lower()
                for key, value in config.exchanges.aliases.items()
            }
        )
    return aliases


def _canonical_exchange(
    value: Any,
    available_exchanges: Iterable[str],
    config: StockQAConfig | None = None,
) -> Optional[str]:
    raw = str(value or "").strip()
    if not raw:
        return None
    key = _exchange_alias_key(raw)
    if key in {"all", "any", "全部", "所有"}:
        return "*"
    available = {str(exchange).lower() for exchange in available_exchanges}
    if key in available:
        return key
    return _exchange_aliases(config).get(key)


def _normalize_exchanges(
    exchanges: Optional[List[str]],
    available_exchanges: Iterable[str],
    config: StockQAConfig | None = None,
) -> List[str]:
    available = sorted({str(exchange).lower() for exchange in available_exchanges})
    if not available:
        raise StockQAError(
            "No exchange tables were discovered in the configured database. "
            "Expected tables like daily_YYYYMMDD_<exchange>."
        )
    if not exchanges:
        return available

    normalized: List[str] = []
    invalid: List[str] = []
    for exchange in exchanges:
        canonical = _canonical_exchange(exchange, available, config)
        if canonical == "*":
            return available
        if canonical is None or canonical not in available:
            invalid.append(str(exchange))
            continue
        if canonical not in normalized:
            normalized.append(canonical)

    if invalid:
        supported = ", ".join(ex.upper() for ex in available)
        raise StockQAError(
            f"Unavailable exchange(s): {', '.join(invalid)}. "
            f"Available exchanges discovered from the database: {supported}"
        )
    return normalized or available


def _date_key_to_iso(date_key: str) -> str:
    return f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:]}"


def _parse_date_key(value: Any, field_name: str) -> Optional[str]:
    raw = str(value or "").strip()
    if not raw:
        return None
    date_key = raw.replace("-", "")
    if not re.fullmatch(r"\d{8}", date_key):
        raise StockQAError(f"{field_name} must use YYYY-MM-DD or YYYYMMDD")
    try:
        datetime.strptime(date_key, "%Y%m%d")
    except ValueError as exc:
        raise StockQAError(f"{field_name} is not a valid calendar date: {raw}") from exc
    return date_key


def _daily_table_info(table_name: Any) -> Optional[Dict[str, str]]:
    raw = str(table_name or "").strip()
    match = DAILY_TABLE_RE.match(raw)
    if not match:
        return None
    date_key = match.group(1)
    exchange_key = match.group(2).lower()
    return {
        "table_name": raw,
        "exchange": exchange_key.upper(),
        "exchange_key": exchange_key,
        "date": _date_key_to_iso(date_key),
        "date_key": date_key,
    }


def _master_table_exchange_key(table_name: Any) -> Optional[str]:
    match = MASTER_TABLE_RE.match(str(table_name or "").strip())
    if not match:
        return None
    return match.group(1).lower()


def _table_exchange_key(table_name: str) -> Optional[str]:
    daily_info = _daily_table_info(table_name)
    if daily_info:
        return daily_info["exchange_key"]
    return _master_table_exchange_key(table_name)


def _normalize_allowed_table_name(
    table_name: Any,
    available_exchanges: Iterable[str] | None = None,
) -> str:
    raw = str(table_name or "").strip().strip("`")
    if not raw:
        raise StockQAError("table name is required")
    if "." in raw:
        raise StockQAError("schema-qualified table names are not accepted here")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", raw):
        raise StockQAError(f"invalid table name: {raw}")
    normalized = raw.lower()
    if not any(pattern.match(normalized) for pattern in ALLOWED_TABLE_PATTERNS):
        raise StockQAError(f"table is outside allowed stock tables: {raw}")
    exchange_key = _table_exchange_key(normalized)
    if available_exchanges is not None and exchange_key:
        available = {str(exchange).lower() for exchange in available_exchanges}
        if exchange_key not in available:
            raise StockQAError(
                f"table uses exchange {exchange_key.upper()}, which was not "
                "discovered in the configured database"
            )
    return normalized


def _discover_exchange_inventory(config: StockQAConfig) -> Dict[str, Dict[str, Any]]:
    engine = _engine(config)
    inventory: Dict[str, Dict[str, Any]] = {}
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SHOW TABLES")).fetchall()
    except Exception as exc:
        raise StockQAError(sanitize_error_text(str(exc), config)) from exc

    for row in rows:
        table_name = str(row[0])
        daily_info = _daily_table_info(table_name)
        if daily_info:
            exchange_key = daily_info["exchange_key"]
            item = inventory.setdefault(
                exchange_key,
                {
                    "code": exchange_key.upper(),
                    "exchange_key": exchange_key,
                    "daily_table_count": 0,
                    "master_table": f"exchange_{exchange_key}_master",
                    "has_master_table": False,
                    "latest_table": None,
                    "latest_date": None,
                },
            )
            item["daily_table_count"] += 1
            if (
                item["latest_table"] is None
                or daily_info["date_key"] > item["latest_table"].split("_")[1]
            ):
                item["latest_table"] = daily_info["table_name"]
                item["latest_date"] = daily_info["date"]
            continue

        exchange_key = _master_table_exchange_key(table_name)
        if exchange_key:
            item = inventory.setdefault(
                exchange_key,
                {
                    "code": exchange_key.upper(),
                    "exchange_key": exchange_key,
                    "daily_table_count": 0,
                    "master_table": f"exchange_{exchange_key}_master",
                    "has_master_table": False,
                    "latest_table": None,
                    "latest_date": None,
                },
            )
            item["has_master_table"] = True

    return {key: inventory[key] for key in sorted(inventory)}


def _discover_exchange_codes(config: StockQAConfig) -> List[str]:
    return list(_discover_exchange_inventory(config))


def get_available_exchanges() -> Dict[str, Any]:
    config = _config_for_database()
    if _is_remote(config):
        return _remote_request(config, "GET", "/v1/exchanges")
    inventory = _discover_exchange_inventory(config)
    return {
        "ok": True,
        "source": "database table names",
        "table_patterns": [
            "daily_YYYYMMDD_<exchange>",
            "exchange_<exchange>_master",
        ],
        "count": len(inventory),
        "exchanges": [inventory[key] for key in sorted(inventory)],
        "aliases": {
            key: value
            for key, value in _exchange_aliases(config).items()
            if value in inventory
        },
    }


def get_stock_qa_config(redact_secrets: bool = True) -> Dict[str, Any]:
    try:
        config = load_config(require_database_url=False)
        data = config_as_dict(config, redact_secrets=redact_secrets)
        errors = []
        if not config.config_exists:
            errors.append(config.missing_config_message)
        if _is_remote(config):
            errors.extend(_remote_config_errors(config))
        elif not config.database.url:
            errors.append("[database].url is required")
        data["ok"] = not errors
        data["errors"] = errors
        return data
    except ConfigError as exc:
        return {
            "ok": False,
            "errors": [str(exc)],
            "backend": {"mode": "", "api_token_configured": False, "secrets_redacted": True},
            "database": {"url": "", "secrets_redacted": True},
        }


def get_prompt_bundle() -> Dict[str, Any]:
    return load_prompt_bundle()


def get_prompt_catalog(
    include_preview: bool = True,
    preview_chars: int = 500,
) -> Dict[str, Any]:
    return run_get_prompt_catalog(
        include_preview=include_preview,
        preview_chars=preview_chars,
    )


def list_custom_prompts() -> Dict[str, Any]:
    return run_list_custom_prompts()


def read_custom_prompt(prompt_name: str) -> Dict[str, Any]:
    try:
        return run_read_custom_prompt(prompt_name)
    except ValueError as exc:
        raise StockQAError(str(exc)) from exc


def preview_custom_prompt_update(prompt_name: str, content: str) -> Dict[str, Any]:
    try:
        return run_preview_custom_prompt_update(prompt_name, content)
    except ValueError as exc:
        raise StockQAError(str(exc)) from exc


def initialize_custom_prompts(
    prompt_names: Optional[List[str]] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    try:
        return run_initialize_custom_prompts(
            prompt_names,
            overwrite=overwrite,
        )
    except ValueError as exc:
        raise StockQAError(str(exc)) from exc


def write_custom_prompt(
    prompt_name: str,
    content: str,
    expected_current_hash: str = "",
) -> Dict[str, Any]:
    try:
        return run_write_custom_prompt(
            prompt_name,
            content,
            expected_current_hash=expected_current_hash,
        )
    except ValueError as exc:
        raise StockQAError(str(exc)) from exc


def reset_custom_prompt(prompt_name: str) -> Dict[str, Any]:
    try:
        return run_reset_custom_prompt(prompt_name)
    except ValueError as exc:
        raise StockQAError(str(exc)) from exc


def verify_environment() -> Dict[str, Any]:
    config_info = get_stock_qa_config(redact_secrets=True)
    return {
        "ok": bool(config_info.get("ok")),
        "config": config_info,
        "uses_openai_api": False,
        "exchange_source": "database table names via get_available_exchanges",
    }


def verify_database() -> Dict[str, Any]:
    config = _config_for_database()
    if _is_remote(config):
        health = _remote_request(config, "GET", "/v1/health")
        return {
            "ok": bool(health.get("ok", True)),
            "backend": {
                "mode": "remote_api",
                "api_base_url": config_as_dict(config)["backend"]["api_base_url"],
                "api_token_configured": bool(config.backend.api_token),
                "secrets_redacted": True,
            },
            "remote_health": health,
        }
    engine = _engine(config)
    try:
        with engine.connect() as conn:
            database = conn.execute(text("SELECT DATABASE()")).scalar()
            current_user = conn.execute(text("SELECT CURRENT_USER()")).scalar()
            ping = conn.execute(text("SELECT 1")).scalar()
    except Exception as exc:
        raise StockQAError(sanitize_error_text(str(exc), config)) from exc
    exchange_info = get_available_exchanges()

    return {
        "ok": True,
        "database": database,
        "current_user": current_user,
        "ping": ping,
        "configured_access_mode": config.database.access_mode,
        "database_url": redact_url(config.database.url),
        "available_exchanges": exchange_info["exchanges"],
    }


def _mask_comments_and_literals(sql: str) -> str:
    out: List[str] = []
    i = 0
    state = "normal"
    quote = ""
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""

        if state == "normal":
            if ch == "-" and nxt == "-":
                out.extend("  ")
                i += 2
                while i < len(sql) and sql[i] not in "\r\n":
                    out.append(" ")
                    i += 1
                continue
            if ch == "#":
                out.append(" ")
                i += 1
                while i < len(sql) and sql[i] not in "\r\n":
                    out.append(" ")
                    i += 1
                continue
            if ch == "/" and nxt == "*":
                out.extend("  ")
                i += 2
                while i < len(sql):
                    if sql[i] == "*" and i + 1 < len(sql) and sql[i + 1] == "/":
                        out.extend("  ")
                        i += 2
                        break
                    out.append(" ")
                    i += 1
                continue
            if ch in {"'", '"', "`"}:
                state = "literal"
                quote = ch
                out.append(ch if ch == "`" else " ")
                i += 1
                continue
            out.append(ch)
            i += 1
            continue

        if state == "literal":
            if ch == "\\":
                out.append(" ")
                if i + 1 < len(sql):
                    out.append(" ")
                    i += 2
                else:
                    i += 1
                continue
            if ch == quote:
                state = "normal"
                out.append(ch if quote == "`" else " ")
                i += 1
                continue
            out.append(ch if quote == "`" else " ")
            i += 1

    return "".join(out)


def _has_multiple_statements(masked_sql: str) -> bool:
    trimmed = masked_sql.strip()
    if trimmed.endswith(";"):
        trimmed = trimmed[:-1]
    return ";" in trimmed


def _normalize_identifier(identifier: str) -> str:
    parts = [p.strip().strip("`").lower() for p in identifier.split(".")]
    return ".".join(p for p in parts if p)


def _extract_cte_names(masked_sql: str) -> set[str]:
    if not re.match(r"^\s*with\b", masked_sql, re.I):
        return set()
    names: set[str] = set()
    pattern = (
        r"(?:\bwith\b|,)\s+([A-Za-z_][A-Za-z0-9_$]*)"
        r"\s*(?:\([^)]*\))?\s+as\s*\("
    )
    for match in re.finditer(pattern, masked_sql, re.I):
        names.add(match.group(1).lower())
    return names


def _extract_table_refs(masked_sql: str) -> List[str]:
    refs: List[str] = []
    table_expr = (
        r"(?:`[^`]+`|[A-Za-z_][A-Za-z0-9_$]*)"
        r"(?:\s*\.\s*(?:`[^`]+`|[A-Za-z_][A-Za-z0-9_$]*))?"
    )
    for match in re.finditer(rf"\b(?:from|join)\s+({table_expr})", masked_sql, re.I):
        raw = match.group(1)
        if raw.startswith("("):
            continue
        normalized = _normalize_identifier(re.sub(r"\s+", "", raw))
        if normalized and normalized not in refs:
            refs.append(normalized)
    return refs


def _is_allowed_table(
    ref: str,
    cte_names: set[str],
    available_exchanges: Iterable[str] | None = None,
) -> bool:
    parts = ref.split(".")
    if len(parts) > 2:
        return False
    if len(parts) == 2:
        schema, table = parts
        if schema in SYSTEM_SCHEMAS:
            return False
    else:
        table = parts[0]
        if table in cte_names:
            return True
    if not any(pattern.match(table) for pattern in ALLOWED_TABLE_PATTERNS):
        return False
    exchange_key = _table_exchange_key(table)
    if available_exchanges is None or not exchange_key:
        return True
    return exchange_key in {str(exchange).lower() for exchange in available_exchanges}


def _clean_sql(sql: str) -> str:
    cleaned = sql.strip()
    while cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    return cleaned


def validate_readonly_sql(sql: str) -> Dict[str, Any]:
    try:
        config = load_config(require_database_url=False)
        if config.config_exists and _is_remote(config):
            errors = _remote_config_errors(config)
            if errors:
                return {
                    "ok": False,
                    "normalized_sql": _clean_sql(sql or ""),
                    "errors": errors,
                    "warnings": [],
                    "referenced_tables": [],
                }
            return _remote_request(
                config,
                "POST",
                "/v1/validate-sql",
                {"sql": sql},
                allow_ok_false=True,
            )
    except ConfigError:
        pass
    result = _validate_readonly_sql(sql)
    return result.as_dict()


def _validate_readonly_sql(
    sql: str,
    available_exchanges: Iterable[str] | None = None,
) -> SQLValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    if not sql or not sql.strip():
        return SQLValidationResult(False, "", ["SQL is empty"], [], [])

    normalized_sql = _clean_sql(sql)
    masked = _mask_comments_and_literals(normalized_sql)
    masked_lower = masked.lower()

    if _has_multiple_statements(masked):
        errors.append("Only one SQL statement is allowed")

    if not re.match(r"^\s*(select|with)\b", masked_lower):
        errors.append("Only SELECT or WITH ... SELECT statements are allowed")

    for pattern in DENIED_KEYWORD_PATTERNS:
        if re.search(pattern, masked_lower, re.I):
            errors.append(f"Denied SQL construct matched: {pattern}")

    cte_names = _extract_cte_names(masked)
    table_refs = _extract_table_refs(masked)
    denied_refs = [
        ref
        for ref in table_refs
        if not _is_allowed_table(ref, cte_names, available_exchanges)
    ]
    if denied_refs:
        errors.append(
            "References to non-stock or system tables are not allowed: "
            + ", ".join(denied_refs)
        )

    if not table_refs:
        warnings.append("No table reference detected")

    if not re.search(r"\blimit\b", masked_lower):
        warnings.append(
            "No LIMIT detected; run_readonly_sql will enforce max_rows by wrapping the query"
        )

    return SQLValidationResult(not errors, normalized_sql, errors, warnings, table_refs)


def _safe_name(value: str, fallback: str) -> str:
    raw = (value or "").strip() or fallback
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-._")
    return safe[:80] or fallback


def _generate_conversation_id(outputs_root: Path) -> str:
    for _ in range(100):
        prefix = datetime.now().strftime("%Y%m%d-%H%M")
        suffix = f"{secrets.randbelow(1_000_000):06d}"
        candidate = f"{prefix}-{suffix}"
        if not (outputs_root / candidate).exists():
            return candidate
    return f"{datetime.now().strftime('%Y%m%d-%H%M')}-{uuid.uuid4().hex[:6]}"


def _conversation_id_for_output(
    outputs_root: Path,
    conversation_id: str = "",
) -> tuple[str, Optional[str]]:
    requested = (conversation_id or "").strip()
    if re.fullmatch(r"\d{8}-\d{4}-\d{6}", requested):
        return requested, None
    if requested:
        return _generate_conversation_id(outputs_root), requested
    return _generate_conversation_id(outputs_root), None


def _new_output_dir(
    outputs_root: Path,
    conversation_id: str = "",
    output_name: str = "query_result",
) -> tuple[str, Path, str, Optional[str]]:
    conv, requested_conv = _conversation_id_for_output(outputs_root, conversation_id)
    safe_conv = _safe_name(conv, "codex-thread")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"{ts}_{uuid.uuid4().hex[:8]}_{_safe_name(output_name, 'query')}"
    out_dir = outputs_root / safe_conv / run_id
    out_dir.mkdir(parents=True, exist_ok=False)
    return run_id, out_dir, safe_conv, requested_conv


def _bounded_max_rows(max_rows: Any, default: int = 200_000) -> int:
    if max_rows is None:
        parsed = default
    else:
        try:
            parsed = int(max_rows)
        except (TypeError, ValueError) as exc:
            raise StockQAError("max_rows must be an integer") from exc
    return max(1, min(parsed, 1_000_000))


def _remote_run_readonly_sql(
    config: StockQAConfig,
    sql: str,
    *,
    conversation_id: str = "",
    output_name: str = "query_result",
    max_rows: int = 200_000,
) -> Dict[str, Any]:
    cleanup_summary = maybe_cleanup_outputs(config.outputs)
    max_rows = _bounded_max_rows(max_rows)
    response = _remote_request(
        config,
        "POST",
        "/v1/run-sql",
        {
            "sql": sql,
            "output_name": output_name,
            "max_rows": max_rows,
        },
    )
    try:
        csv_bytes = remote_api.csv_bytes_from_response(response)
    except remote_api.RemoteAPIError as exc:
        raise StockQAError(sanitize_error_text(str(exc), config)) from exc
    run_id, out_dir, output_conversation_id, requested_conversation_id = _new_output_dir(
        config.outputs.dir,
        conversation_id,
        output_name,
    )
    csv_path = out_dir / f"{_safe_name(output_name, 'query_result')}.csv"
    sql_path = out_dir / "query.sql"
    metadata_path = out_dir / "metadata.json"
    csv_path.write_bytes(csv_bytes)

    remote_metadata = dict(response.get("metadata") or {})
    remote_columns = remote_metadata.get("columns") or response.get("columns") or []
    row_count = remote_metadata.get("row_count", response.get("row_count", 0))
    column_count = remote_metadata.get("column_count", len(remote_columns))
    metadata = {
        "run_id": run_id,
        "conversation_id": output_conversation_id,
        "requested_conversation_id": requested_conversation_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": int(row_count or 0),
        "column_count": int(column_count or 0),
        "columns": list(remote_columns),
        "max_rows": max_rows,
        "possibly_truncated": bool(
            remote_metadata.get("possibly_truncated", response.get("possibly_truncated", False))
        ),
        "output_csv": str(csv_path),
        "output_dir": str(out_dir),
        "query_sql": str(sql_path),
        "metadata_json": str(metadata_path),
        "analysis_python": sys.executable,
        "analysis_workdir": str(out_dir),
        "config": {
            "config_path": str(config.config_path),
            "backend_mode": config.backend.mode,
            "api_base_url": config_as_dict(config)["backend"]["api_base_url"],
            "api_token_configured": bool(config.backend.api_token),
            "outputs_root": str(config.outputs.dir),
            "secrets_redacted": True,
        },
        "cleanup": cleanup_summary,
        "validation": response.get("validation") or remote_metadata.get("validation") or {},
        "remote": {
            "request_id": response.get("request_id") or remote_metadata.get("request_id", ""),
            "metadata": remote_metadata,
        },
        "response_contract": {
            "prompt_bundle_tool": "get_prompt_bundle",
            "filtered_csv_required": True,
            "filtered_csv_filename": "filtered_results.csv",
            "filtered_csv_directory": str(out_dir),
            "primary_csv_path_rule": (
                "Save and cite filtered_results.csv under filtered_csv_directory; "
                "workspace copies are secondary only."
            ),
            "portable_file_write_rule": (
                "Write filtered_results.csv directly with pandas to the final absolute path. "
                "If copying is unavoidable, create the destination directory first and then copy; "
                "do not use GNU-only shell options such as install -D."
            ),
            "top_30_required_for_probability_rate_screening": True,
            "interpretation_must_include": [
                "Codex-derived screening/query rules",
                "exchange scope",
                "actual database date window",
                "event/filter definition",
                "financial filters and timing",
                "deduplication rule",
                "comparison and numerator/denominator logic",
                "missing-data handling",
                "output scoring/sorting rule",
            ],
            "required_sections": [
                "Interpretation",
                "Result",
                "Summary",
                "By exchange when more than one exchange is in scope",
                "Top 30 qualifying stocks",
                "Shell Risk Verification Notes",
                "Files",
                "Caveats",
                "Quick takeaways",
            ],
        },
        "analysis_instruction": (
            "Codex should read output_csv with analysis_python, use pandas as needed, "
            "perform required web searches, save final filtered/ranked/evidence rows as "
            "filtered_results.csv in analysis_workdir, and write the final answer using "
            "the prompt bundle returned by get_prompt_bundle. This tool does not call "
            "OpenAI APIs."
        ),
    }
    sql_path.write_text(_clean_sql(sql) + "\n", encoding="utf-8")
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    return metadata


def run_readonly_sql(
    sql: str,
    *,
    conversation_id: str = "",
    output_name: str = "query_result",
    max_rows: int = 200_000,
) -> Dict[str, Any]:
    config = _config_for_database()
    if _is_remote(config):
        return _remote_run_readonly_sql(
            config,
            sql,
            conversation_id=conversation_id,
            output_name=output_name,
            max_rows=max_rows,
        )
    available_exchanges = _discover_exchange_codes(config)
    validation = _validate_readonly_sql(sql, available_exchanges=available_exchanges)
    if not validation.ok:
        raise StockQAError("SQL safety validation failed: " + "; ".join(validation.errors))

    cleanup_summary = maybe_cleanup_outputs(config.outputs)
    max_rows = _bounded_max_rows(max_rows)
    engine = _engine(config)
    wrapped_sql = (
        f"SELECT * FROM ({validation.normalized_sql}) AS _anchises_safe_query "
        f"LIMIT {max_rows}"
    )
    run_id, out_dir, output_conversation_id, requested_conversation_id = _new_output_dir(
        config.outputs.dir,
        conversation_id,
        output_name,
    )
    csv_path = out_dir / f"{_safe_name(output_name, 'query_result')}.csv"
    sql_path = out_dir / "query.sql"
    metadata_path = out_dir / "metadata.json"

    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("START TRANSACTION READ ONLY")
            try:
                df = pd.read_sql(text(wrapped_sql), conn)
            finally:
                conn.exec_driver_sql("ROLLBACK")
    except Exception as exc:
        raise StockQAError(sanitize_error_text(str(exc), config)) from exc

    df.to_csv(csv_path, index=False)
    metadata = {
        "run_id": run_id,
        "conversation_id": output_conversation_id,
        "requested_conversation_id": requested_conversation_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "max_rows": max_rows,
        "possibly_truncated": len(df) >= max_rows,
        "output_csv": str(csv_path),
        "output_dir": str(out_dir),
        "query_sql": str(sql_path),
        "metadata_json": str(metadata_path),
        "analysis_python": sys.executable,
        "analysis_workdir": str(out_dir),
        "config": {
            "config_path": str(config.config_path),
            "database_url": redact_url(config.database.url),
            "database_access_mode": config.database.access_mode,
            "outputs_root": str(config.outputs.dir),
            "available_exchanges": [ex.upper() for ex in available_exchanges],
            "secrets_redacted": True,
        },
        "cleanup": cleanup_summary,
        "validation": validation.as_dict(),
        "response_contract": {
            "prompt_bundle_tool": "get_prompt_bundle",
            "filtered_csv_required": True,
            "filtered_csv_filename": "filtered_results.csv",
            "filtered_csv_directory": str(out_dir),
            "primary_csv_path_rule": (
                "Save and cite filtered_results.csv under filtered_csv_directory; "
                "workspace copies are secondary only."
            ),
            "portable_file_write_rule": (
                "Write filtered_results.csv directly with pandas to the final absolute path. "
                "If copying is unavoidable, create the destination directory first and then copy; "
                "do not use GNU-only shell options such as install -D."
            ),
            "top_30_required_for_probability_rate_screening": True,
            "interpretation_must_include": [
                "Codex-derived screening/query rules",
                "exchange scope",
                "actual database date window",
                "event/filter definition",
                "financial filters and timing",
                "deduplication rule",
                "comparison and numerator/denominator logic",
                "missing-data handling",
                "output scoring/sorting rule",
            ],
            "required_sections": [
                "Interpretation",
                "Result",
                "Summary",
                "By exchange when more than one exchange is in scope",
                "Top 30 qualifying stocks",
                "Shell Risk Verification Notes",
                "Files",
                "Caveats",
                "Quick takeaways",
            ],
        },
        "analysis_instruction": (
            "Codex should read output_csv with analysis_python, use pandas as needed, "
            "perform required web searches, save final filtered/ranked/evidence rows as "
            "filtered_results.csv in analysis_workdir, and write the final answer using "
            "the prompt bundle returned by get_prompt_bundle. This tool does not call "
            "OpenAI APIs."
        ),
    }
    sql_path.write_text(validation.normalized_sql + "\n", encoding="utf-8")
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    return metadata


def get_latest_dates(exchanges: Optional[List[str]] = None) -> Dict[str, Any]:
    config = _config_for_database()
    if _is_remote(config):
        return _remote_request(
            config,
            "POST",
            "/v1/latest-dates",
            {"exchanges": exchanges or []},
        )
    inventory = _discover_exchange_inventory(config)
    requested = _normalize_exchanges(exchanges, inventory, config)
    engine = _engine(config)
    out: Dict[str, Any] = {}
    try:
        with engine.connect() as conn:
            for ex in requested:
                rows = conn.execute(
                    text("SHOW TABLES LIKE :pattern"),
                    {"pattern": f"daily\\_%\\_{ex}"},
                ).fetchall()
                latest_table = None
                latest_date = None
                for row in rows:
                    table_info = _daily_table_info(row[0])
                    if not table_info:
                        continue
                    if latest_table is None or table_info["date_key"] > latest_table.split("_")[1]:
                        latest_table = table_info["table_name"]
                        latest_date = table_info["date"]
                out[ex.upper()] = {
                    "latest_table": latest_table,
                    "latest_date": latest_date,
                    "table_count": len(rows),
                }
    except Exception as exc:
        raise StockQAError(sanitize_error_text(str(exc), config)) from exc
    return out


def list_stock_tables(
    exchanges: Optional[List[str]] = None,
    date_start: str = "",
    date_end: str = "",
) -> Dict[str, Any]:
    start_key = _parse_date_key(date_start, "date_start")
    end_key = _parse_date_key(date_end, "date_end")
    if start_key and end_key and start_key > end_key:
        raise StockQAError("date_start must be on or before date_end")

    config = _config_for_database()
    if _is_remote(config):
        return _remote_request(
            config,
            "POST",
            "/v1/list-stock-tables",
            {
                "exchanges": exchanges or [],
                "date_start": date_start,
                "date_end": date_end,
            },
        )
    inventory = _discover_exchange_inventory(config)
    requested = _normalize_exchanges(exchanges, inventory, config)
    engine = _engine(config)
    tables: List[Dict[str, str]] = []
    by_exchange = {ex.upper(): 0 for ex in requested}
    try:
        with engine.connect() as conn:
            for ex in requested:
                rows = conn.execute(
                    text("SHOW TABLES LIKE :pattern"),
                    {"pattern": f"daily\\_%\\_{ex}"},
                ).fetchall()
                for row in rows:
                    info = _daily_table_info(row[0])
                    if not info or info["exchange_key"] != ex:
                        continue
                    if start_key and info["date_key"] < start_key:
                        continue
                    if end_key and info["date_key"] > end_key:
                        continue
                    by_exchange[ex.upper()] += 1
                    tables.append(
                        {
                            "table_name": info["table_name"],
                            "exchange": info["exchange"],
                            "date": info["date"],
                            "date_key": info["date_key"],
                        }
                    )
    except Exception as exc:
        raise StockQAError(sanitize_error_text(str(exc), config)) from exc

    tables.sort(key=lambda item: (item["exchange"], item["date_key"], item["table_name"]))
    return {
        "ok": True,
        "filters": {
            "exchanges": [ex.upper() for ex in requested],
            "date_start": _date_key_to_iso(start_key) if start_key else "",
            "date_end": _date_key_to_iso(end_key) if end_key else "",
        },
        "count": len(tables),
        "by_exchange": by_exchange,
        "tables": tables,
    }


def get_table_schema(table_names: List[str]) -> Dict[str, Any]:
    if isinstance(table_names, str):
        requested_names = [name.strip() for name in table_names.split(",") if name.strip()]
    else:
        requested_names = list(table_names or [])
    if not requested_names:
        raise StockQAError("table_names is required")
    if len(requested_names) > 250:
        raise StockQAError("table_names is limited to 250 tables per call")

    config = _config_for_database()
    if _is_remote(config):
        return _remote_request(
            config,
            "POST",
            "/v1/table-schema",
            {"table_names": requested_names},
        )
    available_exchanges = _discover_exchange_codes(config)
    engine = _engine(config)
    out: Dict[str, Any] = {"ok": True, "tables": {}, "errors": []}
    seen: set[str] = set()
    try:
        inspector = inspect(engine)
        for raw_name in requested_names:
            try:
                table_name = _normalize_allowed_table_name(
                    raw_name,
                    available_exchanges,
                )
            except StockQAError as exc:
                out["errors"].append({"table_name": str(raw_name), "error": str(exc)})
                continue
            if table_name in seen:
                continue
            seen.add(table_name)
            if not inspector.has_table(table_name):
                out["tables"][table_name] = {"exists": False, "columns": []}
                out["errors"].append(
                    {"table_name": table_name, "error": "table does not exist"}
                )
                continue
            out["tables"][table_name] = {
                "exists": True,
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col.get("type", "")),
                        "nullable": bool(col.get("nullable", True)),
                    }
                    for col in inspector.get_columns(table_name)
                ],
            }
    except Exception as exc:
        raise StockQAError(sanitize_error_text(str(exc), config)) from exc

    out["ok"] = not out["errors"]
    return out


def get_stock_schema(exchanges: Optional[List[str]] = None) -> Dict[str, Any]:
    config = _config_for_database()
    if _is_remote(config):
        latest = get_latest_dates(exchanges)
        table_names: List[str] = []
        for exchange, info in latest.items():
            if isinstance(info, dict):
                daily_table = info.get("latest_table")
                if daily_table:
                    table_names.append(str(daily_table))
                table_names.append(f"exchange_{str(exchange).lower()}_master")
        table_names.append("metals")
        schema_response = get_table_schema(table_names)
        tables = {
            table_name: {"columns": table_info.get("columns", [])}
            for table_name, table_info in schema_response.get("tables", {}).items()
            if table_info.get("exists", True)
        }
        return {"latest_dates": latest, "tables": tables}
    latest = get_latest_dates(exchanges)
    engine = _engine(config)
    schema: Dict[str, Any] = {"latest_dates": latest, "tables": {}}
    try:
        inspector = inspect(engine)
        for exchange, info in latest.items():
            daily_table = info.get("latest_table")
            master_table = f"exchange_{exchange.lower()}_master"
            for table_name in [daily_table, master_table, "metals"]:
                if not table_name or table_name in schema["tables"]:
                    continue
                if inspector.has_table(table_name):
                    schema["tables"][table_name] = {
                        "columns": [
                            {
                                "name": col["name"],
                                "type": str(col.get("type", "")),
                                "nullable": bool(col.get("nullable", True)),
                            }
                            for col in inspector.get_columns(table_name)
                        ]
                    }
    except Exception as exc:
        raise StockQAError(sanitize_error_text(str(exc), config)) from exc
    return schema


def _schema_snapshot_path(config: StockQAConfig) -> Path:
    return config.outputs.dir / ".schema_snapshot.json"


def _table_kind(table_name: str) -> str:
    if DAILY_TABLE_RE.match(table_name):
        return "daily"
    if MASTER_TABLE_RE.match(table_name):
        return "master"
    if METALS_TABLE_RE.match(table_name):
        return "metals"
    return "other"


def _column_signature(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "name": str(col.get("name", "")),
            "type": str(col.get("type", "")),
            "nullable": bool(col.get("nullable", True)),
        }
        for col in columns
    ]


def _schema_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=_json_default)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_schema_snapshot(config: StockQAConfig) -> Dict[str, Any]:
    engine = _engine(config)
    tables: Dict[str, Dict[str, Any]] = {}
    try:
        with engine.connect() as conn:
            database = conn.execute(text("SELECT DATABASE()")).scalar()
            rows = conn.execute(
                text(
                    """
                    SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, DATA_TYPE,
                           IS_NULLABLE, ORDINAL_POSITION
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = :schema_name
                    ORDER BY TABLE_NAME, ORDINAL_POSITION
                    """
                ),
                {"schema_name": database},
            ).mappings()
            for row in rows:
                actual_table_name = str(row["TABLE_NAME"])
                table_name = actual_table_name.lower()
                if not any(pattern.match(table_name) for pattern in ALLOWED_TABLE_PATTERNS):
                    continue
                table = tables.setdefault(
                    table_name,
                    {
                        "table_name": table_name,
                        "actual_table_name": actual_table_name,
                        "kind": _table_kind(table_name),
                        "columns": [],
                    },
                )
                table["columns"].append(
                    {
                        "name": str(row["COLUMN_NAME"]),
                        "type": str(row.get("COLUMN_TYPE") or row.get("DATA_TYPE") or ""),
                        "nullable": str(row["IS_NULLABLE"]).upper() == "YES",
                    }
                )
    except Exception as exc:
        raise StockQAError(sanitize_error_text(str(exc), config)) from exc

    table_names = sorted(tables)
    snapshot = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "database": database,
        "allowed_table_patterns": [
            "daily_YYYYMMDD_<exchange>",
            "exchange_<exchange>_master",
            "metals",
        ],
        "available_exchanges": sorted(
            {
                (_daily_table_info(name) or {}).get("exchange", "")
                or (_master_table_exchange_key(name) or "").upper()
                for name in tables
            }
            - {""}
        ),
        "inventory_hash": _schema_hash(table_names),
        "schema_hash": _schema_hash({name: tables[name] for name in table_names}),
        "tables": {name: tables[name] for name in table_names},
    }
    snapshot["summary"] = _summarize_schema_snapshot(snapshot)
    return snapshot


def _summarize_schema_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    tables = snapshot.get("tables", {})
    by_exchange_daily: Dict[str, int] = {}
    daily_table_count = 0
    master_table_count = 0
    metals_table_count = 0
    other_table_count = 0
    column_count = 0

    for table_name, table_info in tables.items():
        kind = table_info.get("kind") or _table_kind(table_name)
        column_count += len(table_info.get("columns", []))
        if kind == "daily":
            daily_table_count += 1
            daily_info = _daily_table_info(table_name)
            if daily_info:
                by_exchange_daily.setdefault(daily_info["exchange"], 0)
                by_exchange_daily[daily_info["exchange"]] += 1
        elif kind == "master":
            master_table_count += 1
        elif kind == "metals":
            metals_table_count += 1
        else:
            other_table_count += 1

    return {
        "table_count": len(tables),
        "daily_table_count": daily_table_count,
        "master_table_count": master_table_count,
        "metals_table_count": metals_table_count,
        "other_table_count": other_table_count,
        "column_count": column_count,
        "daily_tables_by_exchange": by_exchange_daily,
    }


def _table_column_diff(
    table_name: str,
    previous_columns: List[Dict[str, Any]],
    current_columns: List[Dict[str, Any]],
) -> Dict[str, Any]:
    previous_by_name = {col["name"]: col for col in _column_signature(previous_columns)}
    current_by_name = {col["name"]: col for col in _column_signature(current_columns)}
    previous_names = set(previous_by_name)
    current_names = set(current_by_name)
    changed_columns = []
    for name in sorted(previous_names & current_names):
        previous = previous_by_name[name]
        current = current_by_name[name]
        changes: Dict[str, Any] = {}
        if previous.get("type") != current.get("type"):
            changes["type"] = {
                "previous": previous.get("type", ""),
                "current": current.get("type", ""),
            }
        if previous.get("nullable") != current.get("nullable"):
            changes["nullable"] = {
                "previous": previous.get("nullable", True),
                "current": current.get("nullable", True),
            }
        if changes:
            changed_columns.append({"name": name, "changes": changes})

    return {
        "table_name": table_name,
        "added_columns": sorted(current_names - previous_names),
        "removed_columns": sorted(previous_names - current_names),
        "changed_columns": changed_columns,
    }


def _limit_list(items: List[Any], limit: int = 100) -> Dict[str, Any]:
    return {
        "items": items[:limit],
        "count": len(items),
        "truncated": len(items) > limit,
    }


def _diff_schema_snapshots(
    previous: Dict[str, Any],
    current: Dict[str, Any],
) -> Dict[str, Any]:
    previous_tables = previous.get("tables", {})
    current_tables = current.get("tables", {})
    previous_names = set(previous_tables)
    current_names = set(current_tables)
    added_tables = sorted(current_names - previous_names)
    removed_tables = sorted(previous_names - current_names)
    changed_tables = []

    for table_name in sorted(previous_names & current_names):
        previous_columns = previous_tables[table_name].get("columns", [])
        current_columns = current_tables[table_name].get("columns", [])
        if _column_signature(previous_columns) != _column_signature(current_columns):
            changed_tables.append(
                _table_column_diff(table_name, previous_columns, current_columns)
            )

    changed = bool(added_tables or removed_tables or changed_tables)
    return {
        "compared": True,
        "changed": changed,
        "previous_created_at_utc": previous.get("created_at_utc", ""),
        "current_created_at_utc": current.get("created_at_utc", ""),
        "previous_inventory_hash": previous.get("inventory_hash", ""),
        "current_inventory_hash": current.get("inventory_hash", ""),
        "previous_schema_hash": previous.get("schema_hash", ""),
        "current_schema_hash": current.get("schema_hash", ""),
        "added_tables": _limit_list(added_tables),
        "removed_tables": _limit_list(removed_tables),
        "changed_tables": _limit_list(changed_tables),
    }


def get_schema_snapshot(
    compare_to_last: bool = True,
    save_snapshot: bool = True,
) -> Dict[str, Any]:
    config = _config_for_database()
    if _is_remote(config):
        return _remote_request(
            config,
            "POST",
            "/v1/schema-snapshot",
            {
                "compare_to_last": compare_to_last,
                "save_snapshot": save_snapshot,
            },
        )
    snapshot = _build_schema_snapshot(config)
    snapshot_path = _schema_snapshot_path(config)
    diff: Dict[str, Any] = {
        "compared": False,
        "changed": False,
        "reason": "compare_to_last is false",
    }

    if compare_to_last:
        if snapshot_path.exists():
            try:
                previous = json.loads(snapshot_path.read_text(encoding="utf-8"))
                diff = _diff_schema_snapshots(previous, snapshot)
            except Exception as exc:
                diff = {
                    "compared": False,
                    "changed": False,
                    "reason": f"Could not read previous snapshot: {exc}",
                }
        else:
            diff = {
                "compared": False,
                "changed": False,
                "reason": "No previous snapshot exists yet",
            }

    saved = False
    if save_snapshot:
        config.outputs.dir.mkdir(parents=True, exist_ok=True)
        tmp_path = snapshot_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )
        tmp_path.replace(snapshot_path)
        saved = True

    sample_tables = sorted(snapshot["tables"])[:20]
    return {
        "ok": True,
        "created_at_utc": snapshot["created_at_utc"],
        "database": snapshot.get("database", ""),
        "snapshot_path": str(snapshot_path),
        "saved": saved,
        "summary": snapshot["summary"],
        "hashes": {
            "inventory_hash": snapshot["inventory_hash"],
            "schema_hash": snapshot["schema_hash"],
        },
        "diff": diff,
        "sample_tables": sample_tables,
        "sample_tables_truncated": len(snapshot["tables"]) > len(sample_tables),
        "next_step": (
            "Use get_table_schema(table_names=[...]) for exact columns on tables "
            "that changed or for the date range you plan to query."
        ),
    }


def _iter_output_metadata(outputs_root: Path) -> Iterable[Path]:
    if not outputs_root.exists():
        return []
    return outputs_root.glob("*/*/metadata.json")


def list_outputs(limit: int = 20, conversation_id: str = "") -> List[Dict[str, Any]]:
    config = load_config(require_database_url=False)
    outputs_root = config.outputs.dir
    limit = max(1, min(int(limit or 20), 200))
    items: List[Dict[str, Any]] = []
    for metadata_path in _iter_output_metadata(outputs_root):
        if conversation_id and metadata_path.parent.parent.name != _safe_name(
            conversation_id,
            "codex-thread",
        ):
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["_modified_at"] = metadata_path.stat().st_mtime
            items.append(metadata)
        except Exception:
            continue
    items.sort(key=lambda item: item.get("_modified_at", 0), reverse=True)
    for item in items:
        item.pop("_modified_at", None)
    return items[:limit]


def _resolve_csv(outputs_root: Path, path_or_run_id: str) -> Path:
    if not path_or_run_id:
        raise StockQAError("path_or_run_id is required")
    root = outputs_root.resolve()
    raw = Path(path_or_run_id).expanduser()
    if raw.exists():
        resolved = raw.resolve()
        if root not in resolved.parents and resolved != root:
            raise StockQAError(f"CSV path must be under {root}")
        if resolved.suffix.lower() != ".csv":
            raise StockQAError("Only CSV files can be read")
        return resolved

    matches = list(root.glob(f"*/*{path_or_run_id}*/*.csv"))
    matches += list(root.glob(f"*/*/{path_or_run_id}.csv"))
    if not matches:
        raise StockQAError(f"No CSV found for path/run id: {path_or_run_id}")
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0].resolve()


def read_output_csv(path_or_run_id: str, max_bytes: int = 200_000) -> Dict[str, Any]:
    config = load_config(require_database_url=False)
    path = _resolve_csv(config.outputs.dir, path_or_run_id)
    max_bytes = max(1, min(int(max_bytes or 200_000), 2_000_000))
    content = path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "content": content,
        "truncated": path.stat().st_size > max_bytes,
    }


def cleanup_outputs(dry_run: bool = True) -> Dict[str, Any]:
    config = load_config(require_database_url=False)
    return run_cleanup_outputs(config.outputs, dry_run=dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(description="Anchises Stock QA local DB tools")
    parser.add_argument("--verify-env", action="store_true")
    parser.add_argument("--verify-db", action="store_true")
    parser.add_argument("--setup-instructions", action="store_true")
    parser.add_argument("--get-config", action="store_true")
    parser.add_argument("--get-prompts", action="store_true")
    parser.add_argument("--get-prompt-catalog", action="store_true")
    parser.add_argument("--read-custom-prompt", action="store_true")
    parser.add_argument("--preview-custom-prompt-update", action="store_true")
    parser.add_argument("--list-custom-prompts", action="store_true")
    parser.add_argument("--init-custom-prompts", action="store_true")
    parser.add_argument("--write-custom-prompt", action="store_true")
    parser.add_argument("--reset-custom-prompt", action="store_true")
    parser.add_argument("--prompt-name", action="append", default=[])
    parser.add_argument("--prompt-content-file", default="")
    parser.add_argument("--expected-current-hash", default="")
    parser.add_argument("--no-prompt-preview", action="store_true")
    parser.add_argument("--prompt-preview-chars", type=int, default=500)
    parser.add_argument("--overwrite-custom-prompts", action="store_true")
    parser.add_argument("--cleanup-outputs", action="store_true")
    parser.add_argument("--cleanup-apply", action="store_true")
    parser.add_argument("--available-exchanges", action="store_true")
    parser.add_argument("--latest-dates", action="store_true")
    parser.add_argument("--schema", action="store_true")
    parser.add_argument("--list-stock-tables", action="store_true")
    parser.add_argument("--exchanges", default="")
    parser.add_argument("--date-start", default="")
    parser.add_argument("--date-end", default="")
    parser.add_argument("--table-schema", default="")
    parser.add_argument("--schema-snapshot", action="store_true")
    parser.add_argument("--no-compare-schema-snapshot", action="store_true")
    parser.add_argument("--no-save-schema-snapshot", action="store_true")
    parser.add_argument("--validate-sql")
    parser.add_argument("--run-sql")
    parser.add_argument("--conversation-id", default="")
    parser.add_argument("--output-name", default="query_result")
    parser.add_argument("--max-rows", type=int, default=200_000)
    parser.add_argument("--list-outputs", type=int)
    parser.add_argument("--read-output-csv")
    args = parser.parse_args()

    try:
        if args.verify_env:
            result = verify_environment()
        elif args.verify_db:
            result = verify_database()
        elif args.setup_instructions:
            result = get_setup_instructions()
        elif args.get_config:
            result = get_stock_qa_config(redact_secrets=True)
        elif args.get_prompts:
            result = get_prompt_bundle()
        elif args.get_prompt_catalog:
            result = get_prompt_catalog(
                include_preview=not args.no_prompt_preview,
                preview_chars=args.prompt_preview_chars,
            )
        elif args.read_custom_prompt:
            if len(args.prompt_name) != 1:
                raise StockQAError("--read-custom-prompt requires exactly one --prompt-name")
            result = read_custom_prompt(args.prompt_name[0])
        elif args.preview_custom_prompt_update:
            if len(args.prompt_name) != 1:
                raise StockQAError(
                    "--preview-custom-prompt-update requires exactly one --prompt-name"
                )
            if not args.prompt_content_file:
                raise StockQAError(
                    "--preview-custom-prompt-update requires --prompt-content-file"
                )
            content = Path(args.prompt_content_file).read_text(encoding="utf-8")
            result = preview_custom_prompt_update(args.prompt_name[0], content)
        elif args.list_custom_prompts:
            result = list_custom_prompts()
        elif args.init_custom_prompts:
            result = initialize_custom_prompts(
                args.prompt_name or None,
                overwrite=args.overwrite_custom_prompts,
            )
        elif args.write_custom_prompt:
            if len(args.prompt_name) != 1:
                raise StockQAError("--write-custom-prompt requires exactly one --prompt-name")
            if not args.prompt_content_file:
                raise StockQAError("--write-custom-prompt requires --prompt-content-file")
            content = Path(args.prompt_content_file).read_text(encoding="utf-8")
            result = write_custom_prompt(
                args.prompt_name[0],
                content,
                expected_current_hash=args.expected_current_hash,
            )
        elif args.reset_custom_prompt:
            if len(args.prompt_name) != 1:
                raise StockQAError("--reset-custom-prompt requires exactly one --prompt-name")
            result = reset_custom_prompt(args.prompt_name[0])
        elif args.cleanup_outputs:
            result = cleanup_outputs(dry_run=not args.cleanup_apply)
        elif args.available_exchanges:
            result = get_available_exchanges()
        elif args.latest_dates:
            result = get_latest_dates()
        elif args.schema:
            result = get_stock_schema()
        elif args.list_stock_tables:
            exchanges = [item.strip() for item in args.exchanges.split(",") if item.strip()]
            result = list_stock_tables(
                exchanges or None,
                date_start=args.date_start,
                date_end=args.date_end,
            )
        elif args.table_schema:
            result = get_table_schema(
                [item.strip() for item in args.table_schema.split(",") if item.strip()]
            )
        elif args.schema_snapshot:
            result = get_schema_snapshot(
                compare_to_last=not args.no_compare_schema_snapshot,
                save_snapshot=not args.no_save_schema_snapshot,
            )
        elif args.validate_sql:
            result = validate_readonly_sql(args.validate_sql)
        elif args.run_sql:
            result = run_readonly_sql(
                args.run_sql,
                conversation_id=args.conversation_id,
                output_name=args.output_name,
                max_rows=args.max_rows,
            )
        elif args.list_outputs is not None:
            result = list_outputs(args.list_outputs, conversation_id=args.conversation_id)
        elif args.read_output_csv:
            result = read_output_csv(args.read_output_csv)
        else:
            raise StockQAError("No action specified")
        print(json.dumps(result, ensure_ascii=False, default=_json_default))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {"error": str(exc), "type": type(exc).__name__},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
