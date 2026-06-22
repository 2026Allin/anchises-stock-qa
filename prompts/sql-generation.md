# SQL Generation Prompt

Write SQL only after calling `get_latest_dates` and `get_stock_schema`.
For historical date ranges, also call `list_stock_tables`; when schemas may differ,
call `get_table_schema` for the selected tables.

Hard safety rules:
- Use exactly one statement.
- Use only `SELECT` or `WITH ... SELECT`.
- Never use writes, DDL, session changes, stored procedures, admin commands, locks, file access, or time-wasting functions.
- Do not use `INTO OUTFILE`, `LOAD_FILE`, `SLEEP`, `BENCHMARK`, `FOR UPDATE`, or `LOCK IN SHARE MODE`.
- Do not query system schemas.

Allowed table patterns:
- `daily_YYYYMMDD_<exchange>`
- `exchange_<exchange>_master`
- `metals`

Generation rules:
- Use the latest table names returned by `get_latest_dates` for latest-data questions.
- For date ranges, union only the daily tables returned by `list_stock_tables` with `UNION ALL`.
- When unioning historical tables, select a stable shared column set. If needed, use `NULL AS column_name` for fields missing from older tables.
- Select only columns needed for the analysis and final evidence tables.
- Include row-level evidence for screening, ranking, persistence, probability, and rate questions.
- If the query may be large, still preserve evidence fields and rely on `run_readonly_sql(max_rows=...)` for the outer cap.
- Pass candidate SQL to `validate_readonly_sql`; if validation fails, revise the SQL rather than asking the user to debug it.

Execution:
- Call `run_readonly_sql` with a short, descriptive `output_name`.
- Omit `conversation_id` by default so the MCP tool can generate one.
