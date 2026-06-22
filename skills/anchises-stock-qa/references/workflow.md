# Anchises Stock QA Workflow

Configuration:
- Default config path: `~/.config/anchises-stock-qa/config.toml`
- Override config path: `ANCHISES_STOCK_QA_CONFIG`
- Example config: `config.example.toml`
- Database URL setting: `[database].url`
- Required database mode: `[database].access_mode = "readonly"`
- Output root setting: `[outputs].dir`
- Prompt override setting: `[prompts].override_dir`

MCP tools:
- `get_stock_qa_config`
- `get_prompt_bundle`
- `cleanup_outputs`
- `verify_stock_qa_environment`
- `verify_stock_qa_database`
- `get_available_exchanges`
- `get_latest_dates`
- `get_stock_schema`
- `list_stock_tables`
- `get_table_schema`
- `get_schema_snapshot`
- `validate_readonly_sql`
- `run_readonly_sql`
- `list_outputs`
- `read_output_csv`

Codex-owned analysis:
- Codex interprets user intent.
- Codex calls `get_prompt_bundle` and follows the returned prompt markdown.
- Codex writes SQL.
- The MCP server validates SQL, runs it in a read-only transaction, and exports CSV only.
- Codex reads CSV and performs analysis with pandas or other local tools using the returned `analysis_python` when needed.
- Codex must perform at least one relevant web search before the final stock answer for external/current context, company/background checks, or validation.
- Numeric probabilities, rankings, and filters from `Stocks_Tracker` must remain grounded in the exported CSV.
- The user should be able to ask in natural language. Do not require the user to say `run_readonly_sql`, provide `conversation_id`, or request CSV explicitly.

Default prompt handling:
- Discover exchange codes from the configured database with `get_available_exchanges`.
- If no exchange is specified, use all discovered exchanges.
- If the user mentions an exchange that is not discovered, refuse that exchange and state the discovered list.
- If the user says "latest", use `get_latest_dates`.
- If the user asks for a date range, call `list_stock_tables` and union only the returned daily tables.
- If historical daily tables may have different columns, call `get_table_schema` for the selected tables and use a shared column set in SQL.
- If the user asks whether table structure changed, or a column unexpectedly fails, call `get_schema_snapshot`.
- If the user asks a probability/rate question, export row-level evidence, then calculate numerator/denominator with pandas.
- Probability/rate questions still require a Top 30 evidence table in the final markdown when qualifying rows exist.
- Derive `output_name` from the question, for example `price_spike_probability`, `latest_momentum`, or `unusual_volume`.
- Omit `conversation_id` by default and let the tool generate one.

SQL safety:
- The validator allows only one `SELECT` or `WITH ... SELECT` statement.
- The validator rejects write/DDL/admin/session/procedure/file/lock/time-wasting constructs.
- The validator rejects system schemas and non-stock tables.
- The executor wraps accepted SQL with `LIMIT max_rows`, starts `START TRANSACTION READ ONLY`, and then rolls back.

Allowed table patterns:
- `daily_YYYYMMDD_<exchange>`
- `exchange_<exchange>_master`
- `metals`

Exchange discovery:
- `<exchange>` is not hard-coded in the prompt.
- The MCP server discovers exchange codes from `daily_YYYYMMDD_<exchange>` and `exchange_<exchange>_master` table names.
- Users can optionally add natural-language aliases in `[exchanges.aliases]` inside `config.toml`; aliases must point to discovered exchange codes.

Output naming:
- `run_readonly_sql` writes under `[outputs].dir`:
  - `<conversation_id>/<timestamp>_<uuid>_<output_name>/<output_name>.csv`
  - `query.sql`
  - `metadata.json`
- If `conversation_id` is unavailable, the tool generates an id in the form `YYYYMMDD-HHMM-123456`.
- If a supplied `conversation_id` does not match `YYYYMMDD-HHMM-123456`, the tool generates a valid id and records the supplied value as `requested_conversation_id`.

Cleanup:
- Automatic cleanup is controlled by `[outputs].cleanup_enabled`.
- Cleanup checks at most once per `[outputs].cleanup_interval_days`.
- Expired run directories older than `[outputs].retention_days` are deleted only if they match the MCP output structure and contain `metadata.json`.
- `cleanup_outputs(dry_run=true)` previews deletions without removing files.

Final answer format:
- Use the prompt bundle returned by `get_prompt_bundle`.
- `Interpretation` must show Codex's final derived screening/query rules.
- Include the exact `**Full results saved to filtered_results.csv**` line.
- Do not use a Codex workspace copy as the primary CSV path. Save `filtered_results.csv` beside the MCP `output_csv`; mention any workspace copy only after the primary path.

Common failures:
- The config file is missing.
- `[database].url` is missing or points at the wrong MySQL host/socket.
- `[database].access_mode` is not `readonly`.
- MySQL is not listening on the configured host/socket.
- SQL references a blocked table or includes blocked constructs.
- The requested daily table/date does not exist.
