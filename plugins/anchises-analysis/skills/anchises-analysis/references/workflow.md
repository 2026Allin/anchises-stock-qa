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

`list_stock_tables`, `screen_stocks`, and `run_readonly_sql` also return:

```json
{
  "page": {
    "row_count": 20,
    "total_count": 125,
    "truncated": true,
    "next_cursor": "opaque-value"
  }
}
```

Treat `data_date` as source freshness, not the current date. Preserve warnings.
Use `next_cursor` unchanged only for the immediately preceding request shape.

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

`screen_stocks` accepts optional exchanges and date, zero to 30 AND-combined
filters, optional sort keys, an opaque cursor, and `page_size` up to 200. Use
only fields returned by `get_stock_schema`.

Use scalar values for `eq`, `ne`, `gt`, `gte`, `lt`, and `lte`; one to 100
values for `in`; and exactly two ordered values for `between`. Never pass an
object as a filter value.

## SQL fallback

Use SQL only when structured filters cannot represent the request. Generate one
bounded `SELECT` or `WITH ... SELECT`, call `validate_readonly_sql` with only
`sql`, and execute only after validation succeeds. `run_readonly_sql` may also
receive `max_rows`, `page_size`, and an opaque cursor.

## Exports

`create_csv_export` is the only non-read-only and non-idempotent tool. Pass only
a `query_id` returned by the current screen or SQL call. Omit
`expires_in_seconds` for the default 3600-second (60-minute) lifetime. If the
user requests another lifetime, pass an integer from 60 through 3600 seconds.
The HTTPS URL is a short-lived bearer capability; do not share it or call it a
permanent archive.

## Stable errors

| Code | Handling |
|---|---|
| `invalid_scope`, `access_pending`, `access_denied` | Unexpected for public access. Show only safe guidance and do not initiate sign-in. |
| `usage_limit_exceeded` | Show reset information; do not retry immediately. |
| `rate_limited` | Retry only after the returned delay. |
| `concurrency_limited` | Wait for an existing query to finish. |
| `query_rejected` | Narrow or safely rewrite the query. |
| `resource_not_found` | Do not probe or edit an opaque capability; rerun the original request if needed. |
| `result_too_large` | Narrow, paginate, or offer an allowed export. |
| `temporarily_unavailable` | Suggest retrying later. |
| `service_not_activated` or HTTP 503 | Stop without retrying. |
