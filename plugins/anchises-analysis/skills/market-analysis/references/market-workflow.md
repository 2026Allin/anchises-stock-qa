# Structured market workflow

The request's `primary_task`, modifiers, and ordered entities must already be
set by
[the canonical arbitration reference](../../anchises-analysis/references/query-interpretation.md).
This file defines tool execution only. Do not reclassify the request here.

## Choose the smallest tool sequence

1. `get_connection_status` for the public service state.
2. `resolve_company_identity` for a single-company market-data request.
3. `get_available_exchanges` for authoritative structured-data markets.
4. `get_latest_dates` for market-data freshness.
5. `get_stock_schema` before selecting screen or export fields.
6. `list_stock_tables` and `get_table_schema` for historical coverage.
7. `screen_stocks` for ordinary filters, rankings, and latest snapshots.
8. `validate_readonly_sql` and then `run_readonly_sql` for complex aggregate
   fallback queries.
9. `create_csv_export` only for an explicit CSV request backed by an eligible
   preceding screen.

Never call `prepare_company_report_generation` in this workflow.

## Result envelopes

Data tools return `data_date`, `data`, `warnings`, and `quota`. Public success
responses omit internal request, principal, connection, and policy identifiers.
Quota reports its scope, remaining amount, limit, period, and reset time.

`list_stock_tables`, `screen_stocks`, and `run_readonly_sql` also return a
`page` object. Stock-row results use a bounded non-pageable preview:

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
`list_stock_tables` is metadata listing and may use its own opaque cursor.

## Company identity

`resolve_company_identity` searches ASX, CSE, NASDAQ, NYSE, TSX, and TSXV
masters. It returns `resolved`, `ambiguous`, or
`not_found_in_supported_markets`.

For `resolved`, use the canonical exchange, ticker, and share class. For
`ambiguous`, use candidates and primary sources, then ask one concise identity
question only if needed. For `not_found_in_supported_markets`, state the
coverage boundary and do not run a structured screen or SQL query for that
listing.

## Structured screens

`screen_stocks` requires a filters array and accepts optional exchanges,
`as_of_date`, a paired `start_date` plus `end_date`, selected fields, zero to
30 AND-combined filters, sort keys, `top_n`, `base_query_id`, and `page_size`
up to 200.

- Never combine an exact date with a range or send only one range boundary.
- Use only fields returned by `get_stock_schema`.
- Use scalar values for `eq`, `ne`, `gt`, `gte`, `lt`, and `lte`; one to 100
  values for `in`; and exactly two ordered values for `between`.
- Never pass an object as a filter value.
- Use `top_n` only with a non-empty explicit sort.
- Never send a stock-row cursor.

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
`sql`, and execute only after validation succeeds.

`run_readonly_sql` accepts only `sql` and optional `max_rows` up to 200. It has
no cursor or OFFSET. Do not construct UNION, JOIN, Boolean OR, ticker-letter
range, date-slice, or sort-direction schemes for enumerating market rows. SQL
query IDs are analysis-only.

## Exports

`create_csv_export` is the only non-read-only and non-idempotent tool. Pass
only the current `query_id` from an immediately preceding `screen_stocks`
result whose `export_policy.eligible_by_query` is true. Never pass a SQL query
ID.

The screen must explicitly select fields derived from the user's analytical
question and verified with `get_stock_schema`; never use a fixed universal CSV
schema. If a broad download is ineligible, preserve the analysis and offer a
focused research subset or a suitable verified bulk-market-data API or
licensed exchange-data vendor.

One file is limited to 1,000 rows, 25 total columns, 20,000 cells, Top-N 200,
or 50 exact tickers, and it can never contain a complete exchange-day
partition. `EXCHANGE`, `Date`, and `TICKER` are automatically included and
count toward the column limit.

These numeric limits are tool-construction guardrails, not an ordinary refusal
script. When the user asks for an exact applicable threshold, use the value
returned by the current `data.export_policy.limits`.

Omit `expires_in_seconds` for the default 3,600-second lifetime. If the user
requests another lifetime, pass an integer from 60 through 3,600 seconds. The
HTTPS URL is a temporary bearer capability, not a permanent archive.

## Stable errors

| Code | Handling |
|---|---|
| `query_rejected` | Narrow or safely rewrite the query. |
| `query_requires_bounded_analysis` | Use a server-side aggregate or no more than 50 exact tickers. |
| `resource_not_found` | Rerun the original request if needed; do not edit an opaque capability. |
| `export_requires_selective_query` | Continue analysis and offer a selective research subset. |
| `export_row_limit_exceeded` | Reduce rows without splitting files. |
| `export_column_limit_exceeded` | Select fewer relevant fields; identity fields count. |
| `export_cell_limit_exceeded` | Reduce rows or fields in one subset. |
| `export_complete_partition_not_allowed` | Analyze in-session; offer a selective subset. |
| `export_top_n_limit_exceeded` | Use one explicitly sorted Top-N of at most 200. |
| `export_ticker_limit_exceeded` | Reduce the exact watchlist to at most 50 tickers. |
| `query_not_exportable` | Do not export SQL; restate an eligible request as a screen. |
| `query_policy_expired` | Rerun the original screen and inspect the new policy and query ID. |
| `query_partition_limit_exceeded` or `result_too_large` | Narrow or aggregate; do not partition or paginate. |
| `temporarily_unavailable` | If only CSV failed, preserve analysis and state that download is unavailable. |
