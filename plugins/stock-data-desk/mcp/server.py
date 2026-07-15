#!/usr/bin/env python3
"""MCP server for Stock Data Desk read-only exports."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ask_stock import (  # noqa: E402
    cleanup_outputs as run_cleanup_outputs,
    get_available_exchanges as run_get_available_exchanges,
    get_latest_dates as run_get_latest_dates,
    get_prompt_catalog as run_get_prompt_catalog,
    get_prompt_bundle as run_get_prompt_bundle,
    get_schema_snapshot as run_get_schema_snapshot,
    get_setup_instructions as run_get_setup_instructions,
    get_stock_qa_config as run_get_stock_qa_config,
    get_stock_schema as run_get_stock_schema,
    get_table_schema as run_get_table_schema,
    initialize_custom_prompts as run_initialize_custom_prompts,
    list_custom_prompts as run_list_custom_prompts,
    list_stock_tables as run_list_stock_tables,
    list_outputs as run_list_outputs,
    preview_custom_prompt_update as run_preview_custom_prompt_update,
    read_output_csv as run_read_output_csv,
    read_custom_prompt as run_read_custom_prompt,
    reset_custom_prompt as run_reset_custom_prompt,
    run_readonly_sql as run_run_readonly_sql,
    validate_readonly_sql as run_validate_readonly_sql,
    verify_database,
    verify_environment,
    write_custom_prompt as run_write_custom_prompt,
)


mcp = FastMCP(
    "stock-data-desk",
    instructions=(
        "Stock Data Desk exposes read-only Stocks_Tracker tools. "
        "Configuration is loaded from ~/.config/anchises-stock-qa/config.toml "
        "or ANCHISES_STOCK_QA_CONFIG. Shared users configure remote_api with "
        "an API URL and token; all secrets are treated as private. For setup "
        "or token reset requests, Codex should call get_setup_instructions and "
        "show the returned setup_or_reset_token command. For natural-language "
        "stock questions, Codex should call get_prompt_bundle, discover exchanges with "
        "get_available_exchanges, inspect latest dates/schema, use list_stock_tables "
        "and get_table_schema for date ranges, interpret query dimensions, write "
        "safe SELECT/WITH SQL, call run_readonly_sql, "
        "read the exported CSV with pandas using the returned analysis_python, perform "
        "at least one relevant web search for current/external context, and return "
        "markdown using the prompt bundle. For requests to customize prompt behavior, "
        "Codex should first use get_prompt_catalog, then read_custom_prompt, "
        "preview_custom_prompt_update, and only after user confirmation "
        "write_custom_prompt; these tools edit only "
        "the user's fixed prompt directory so plugin upgrades do not overwrite "
        "custom prompts. The MCP server validates SQL, uses the "
        "configured backend, exports CSV files, and may clean old outputs according "
        "to config. It does not call OpenAI APIs or perform the final pandas "
        "analysis itself."
    ),
)


@mcp.tool()
def get_setup_instructions() -> Dict[str, Any]:
    """Return first-time setup and API token reset instructions for this plugin install."""
    return run_get_setup_instructions()


@mcp.tool()
def get_stock_qa_config(redact_secrets: bool = True) -> Dict[str, Any]:
    """Return effective plugin configuration with database secrets redacted."""
    return run_get_stock_qa_config(redact_secrets=redact_secrets)


@mcp.tool()
def get_prompt_bundle() -> Dict[str, Any]:
    """Return built-in and user-customized prompt markdown for Codex analysis."""
    return run_get_prompt_bundle()


@mcp.tool()
def get_prompt_catalog(
    include_preview: bool = True,
    preview_chars: int = 500,
) -> Dict[str, Any]:
    """Return editable prompt names, purposes, paths, active sources, hashes, and optional previews."""
    return run_get_prompt_catalog(
        include_preview=include_preview,
        preview_chars=preview_chars,
    )


@mcp.tool()
def list_custom_prompts() -> Dict[str, Any]:
    """List editable prompt files and whether each one currently uses a user file."""
    return run_list_custom_prompts()


@mcp.tool()
def read_custom_prompt(prompt_name: str) -> Dict[str, Any]:
    """Read one active prompt, including built-in and user file content plus hashes."""
    return run_read_custom_prompt(prompt_name=prompt_name)


@mcp.tool()
def preview_custom_prompt_update(prompt_name: str, content: str) -> Dict[str, Any]:
    """Preview a proposed full prompt update with a diff and hash without writing it."""
    return run_preview_custom_prompt_update(
        prompt_name=prompt_name,
        content=content,
    )


@mcp.tool()
def initialize_custom_prompts(
    prompt_names: Optional[List[str]] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Copy selected built-in prompt files into the user's upgrade-safe prompt directory."""
    return run_initialize_custom_prompts(
        prompt_names=prompt_names,
        overwrite=overwrite,
    )


@mcp.tool()
def write_custom_prompt(
    prompt_name: str,
    content: str,
    expected_current_hash: str = "",
) -> Dict[str, Any]:
    """Write one user prompt file after Codex has prepared the revised markdown."""
    return run_write_custom_prompt(
        prompt_name=prompt_name,
        content=content,
        expected_current_hash=expected_current_hash,
    )


@mcp.tool()
def reset_custom_prompt(prompt_name: str) -> Dict[str, Any]:
    """Delete one user prompt file so the built-in prompt is used again."""
    return run_reset_custom_prompt(prompt_name=prompt_name)


@mcp.tool()
def cleanup_outputs(dry_run: bool = True) -> Dict[str, Any]:
    """Preview or delete expired output run directories according to config."""
    return run_cleanup_outputs(dry_run=dry_run)


@mcp.tool()
def verify_stock_qa_environment() -> Dict[str, Any]:
    """Check configuration, output path, and DB URL setup."""
    return verify_environment()


@mcp.tool()
def verify_stock_qa_database() -> Dict[str, Any]:
    """Check whether the configured read-only Stocks_Tracker database can be reached."""
    return verify_database()


@mcp.tool()
def get_available_exchanges() -> Dict[str, Any]:
    """Discover current exchange codes from Stocks_Tracker table names."""
    return run_get_available_exchanges()


@mcp.tool()
def get_latest_dates(exchanges: Optional[List[str]] = None) -> Dict[str, Any]:
    """Return latest daily table/date per requested discovered exchange."""
    return run_get_latest_dates(exchanges)


@mcp.tool()
def get_stock_schema(exchanges: Optional[List[str]] = None) -> Dict[str, Any]:
    """Return column schema for requested discovered exchanges' latest daily and master tables."""
    return run_get_stock_schema(exchanges)


@mcp.tool()
def list_stock_tables(
    exchanges: Optional[List[str]] = None,
    date_start: str = "",
    date_end: str = "",
) -> Dict[str, Any]:
    """List available daily tables by exchange and optional date range."""
    return run_list_stock_tables(
        exchanges,
        date_start=date_start,
        date_end=date_end,
    )


@mcp.tool()
def get_table_schema(table_names: List[str]) -> Dict[str, Any]:
    """Return exact column schema for specific allowed stock tables."""
    return run_get_table_schema(table_names)


@mcp.tool()
def get_schema_snapshot(
    compare_to_last: bool = True,
    save_snapshot: bool = True,
) -> Dict[str, Any]:
    """Create a compact stock-table schema snapshot and compare it with the last saved one."""
    return run_get_schema_snapshot(
        compare_to_last=compare_to_last,
        save_snapshot=save_snapshot,
    )


@mcp.tool()
def validate_readonly_sql(sql: str) -> Dict[str, Any]:
    """Validate that SQL is a single safe read-only SELECT over allowed stock tables."""
    return run_validate_readonly_sql(sql)


@mcp.tool()
def run_readonly_sql(
    sql: str,
    conversation_id: str = "",
    output_name: str = "query_result",
    max_rows: int = 200000,
) -> Dict[str, Any]:
    """Validate and execute read-only SQL, then export the result CSV under the configured outputs directory."""
    return run_run_readonly_sql(
        sql,
        conversation_id=conversation_id,
        output_name=output_name,
        max_rows=max_rows,
    )


@mcp.tool()
def list_outputs(limit: int = 20, conversation_id: str = "") -> List[Dict[str, Any]]:
    """List recent CSV exports produced by Stock Data Desk."""
    return run_list_outputs(limit, conversation_id=conversation_id)


@mcp.tool()
def read_output_csv(path_or_run_id: str) -> Dict[str, Any]:
    """Read an exported CSV by absolute path or run id."""
    return run_read_output_csv(path_or_run_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
