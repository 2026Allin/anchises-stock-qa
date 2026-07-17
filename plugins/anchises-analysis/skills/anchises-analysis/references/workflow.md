# Hosted App workflow reference

## Tool selection

Use the smallest sequence that answers the request:

1. `get_connection_status` for public service state.
2. `resolve_company_identity` for any single-company name, ticker, or contextual
   reference.
3. `prepare_company_report_generation` for every explicit company-research or
   company-report request after all three identity fields are established.
4. `get_available_exchanges` for authoritative structured-data markets.
5. `get_latest_dates` for market-data freshness.
6. `get_stock_schema` before structured field selection.
7. `list_stock_tables` and `get_table_schema` for historical coverage.
8. `screen_stocks` for ordinary filters and rankings.
9. `validate_readonly_sql` and `run_readonly_sql` for complex fallback queries.
10. `create_csv_export` only for an explicit CSV download of a prior query.

Every company report is prepared for live Host research. Do not query a prior
stored report or add a separate generation-confirmation state machine.

## Result envelopes

Data tools return `data_date`, `data`, `warnings`, and `quota`. Public success
responses omit internal request, principal, connection, and policy identifiers.
Quota reports its scope, remaining amount, limit, period, and reset time.

`list_stock_tables`, `screen_stocks`, and `run_readonly_sql` also return a
`page` object. For stock-row tools in the current contract:

```json
{
  "page": {
    "row_count": 200,
    "total_count": 4125,
    "truncated": true,
    "next_cursor": null
  }
}
```

Treat `data_date` as source freshness, not the current date. Preserve warnings.
`screen_stocks` and `run_readonly_sql` never provide stock-row pagination.
`list_stock_tables` remains a metadata-listing workflow and may have its own
opaque cursor according to its descriptor.

## Company identity

`resolve_company_identity` searches only ASX, CSE, NASDAQ, NYSE, TSX, and TSXV
masters. It returns `resolved`, `ambiguous`, or
`not_found_in_supported_markets`. Read
[company-resolution.md](company-resolution.md) for candidate handling,
external markets, share classes, and privacy.

## Live company research

`prepare_company_report_generation` requires `exchange`, `ticker`,
`company_name`, and `output_locale`. A `ready` result must provide a non-empty
`prompt_text`, `prompt_version=5.1`, and
`next_action=run_host_web_research`. The Host performs web research and writing;
MCP does neither and does not persist the final response. Read
[company-report-workflow.md](company-report-workflow.md).

## Structured screens

`screen_stocks` requires a filters array and accepts optional exchanges,
`as_of_date`, a paired `start_date` plus `end_date`, selected fields, zero
to 30 AND-combined filters, sort keys, `top_n`, `base_query_id`, and
`page_size` up to 200. Never combine an exact date with a range, send only one
range boundary, or send a cursor. Use only fields returned by
`get_stock_schema`.

Use scalar values for `eq`, `ne`, `gt`, `gte`, `lt`, and `lte`; one to 100
values for `in`; and exactly two ordered values for `between`. Never pass an
object as a filter value. Use `top_n` only with a non-empty explicit sort.

The result includes:

- `data.analysis`: matched and displayed counts, preview state, display limit,
  row-pagination availability, server-side-analysis support, and query
  classification.
- `data.export_policy`: `eligible_by_query`, classification, complete
  partition state, reasons, policy version, required source tool, and limits.

Use `eligible_by_query` exactly. Do not read a legacy `eligible` field.

## SQL fallback

Use SQL only when structured filters cannot represent a server-side statistic
or aggregation, or for at most 50 explicitly named tickers. Generate one
bounded `SELECT` or `WITH ... SELECT`, call `validate_readonly_sql` with only
`sql`, and execute only after validation succeeds. `run_readonly_sql` accepts
only `sql` and optional `max_rows` up to 200. It has no cursor or OFFSET.

Do not construct UNION, JOIN, Boolean OR, ticker-letter range, date-slice, or
sort-direction schemes for enumerating market rows. SQL query IDs are
analysis-only.

## Exports

`create_csv_export` is the only non-read-only and non-idempotent tool. Pass
only the current `query_id` from a preceding `screen_stocks` result whose
`export_policy.eligible_by_query` is true. Never pass a SQL query ID. The
screen must explicitly select research-relevant fields.

One file is limited to 1,000 rows, 25 total columns, 20,000 cells, Top-N 200,
or 50 exact tickers, and it can never contain a complete exchange-day
partition. `EXCHANGE`, `Date`, and `TICKER` are automatically included and
count toward the column limit.

Omit `expires_in_seconds` for the default 3600-second (60-minute) lifetime. If
the user requests another lifetime, pass an integer from 60 through 3600
seconds. The HTTPS URL is a short-lived bearer capability; do not share it or
call it a permanent archive. Read
[market-data-policy.md](market-data-policy.md) for non-circumvention and
recovery rules.

## Stable errors

| Code | Handling |
|---|---|
| `invalid_scope`, `access_pending`, `access_denied` | Unexpected for public access. Show only safe guidance and do not initiate sign-in. |
| `usage_limit_exceeded` | Show reset information; do not retry immediately. |
| `rate_limited` | Retry only after the returned delay. |
| `concurrency_limited` | Wait for an existing query to finish. |
| `query_rejected` | Narrow or safely rewrite the query. |
| `query_requires_bounded_analysis` | Use a server-side aggregate or no more than 50 exact tickers; do not enumerate raw rows. |
| `resource_not_found` | Do not probe or edit an opaque capability; rerun the original request if needed. |
| `export_requires_selective_query` | Continue analysis and offer a selective research subset. |
| `export_row_limit_exceeded` | Reduce the single result's rows without splitting files. |
| `export_column_limit_exceeded` | Select fewer relevant fields; automatic identity fields count. |
| `export_cell_limit_exceeded` | Reduce rows or fields in one research subset. |
| `export_complete_partition_not_allowed` | Analyze the full partition in-session; offer a selective subset. |
| `export_top_n_limit_exceeded` | Use one explicitly sorted Top-N of at most 200. |
| `export_ticker_limit_exceeded` | Reduce the exact watchlist to at most 50 tickers. |
| `query_not_exportable` | Do not export SQL; restate an eligible request as `screen_stocks`. |
| `query_policy_expired` | Rerun the original screen and inspect its new policy and query ID. |
| `query_partition_limit_exceeded` | Narrow or aggregate; do not split partitions. |
| `result_too_large` | Narrow or aggregate; do not paginate stock rows. |
| `temporarily_unavailable` | If only CSV failed, preserve analysis and state that download is temporarily unavailable. |
| `service_not_activated` or HTTP 503 | Stop without retrying. |
