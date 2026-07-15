# Hosted App workflow reference

## Tool selection

Use the smallest sequence that answers the question:

1. `get_connection_status` for access state.
2. `get_available_exchanges` for authoritative exchange codes.
3. `get_latest_company_report` for one latest cached English cached AI company report.
4. `get_latest_dates` for stock-data freshness.
5. `get_stock_schema` before structured field selection.
6. `screen_stocks` for ordinary filters and rankings.
7. `list_stock_tables` and `get_table_schema` for historical coverage.
8. `validate_readonly_sql` and `run_readonly_sql` for complex fallback queries.
9. `create_csv_export` only for an explicit CSV download of a prior query.

## Result envelopes

Data tools return `request_id`, `data_date`, `data`, `warnings`, and `quota`.
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

## Structured screens

`screen_stocks` accepts optional exchanges and date, zero to 30 AND-combined
filters, optional sort keys, an opaque cursor, and `page_size` up to 200. Use
only fields returned by `get_stock_schema`.

Use scalar values for `eq`, `ne`, `gt`, `gte`, `lt`, and `lte`. Use one to 100
values for `in`, and exactly two ordered values for `between`. Never pass an
object as a filter value.

## SQL fallback

Use SQL only when structured filters cannot represent the request. Generate one
bounded `SELECT` or `WITH ... SELECT`, call `validate_readonly_sql` with only
`sql`, and execute only when validation succeeds. `run_readonly_sql` may also
receive `max_rows`, `page_size`, and an opaque cursor.

## Company reports

`get_latest_company_report` reads cached analysis and never generates a report.
It requires uppercase `exchange` plus `ticker`; `source` defaults to `auto`, and
`pdf_range` defaults to `MAX`. It has no language parameter and always returns
English when a report exists.

- `active`: return the summary, relevant sections, citations, and optional PDF.
- `expired`: return the same content with the expiration warning.
- `not_found`: `report` and `pdf_download_url` are null; treat this as success.

The PDF URL selects the latest report from the requested source when downloaded;
it is not a frozen historical snapshot. Never expose raw markdown, model cost or
usage, search events, internal IDs, private addresses, or local paths.

## Exports

`create_csv_export` is the only non-read-only and non-idempotent tool. Pass only
a `query_id` returned by the current user's screen or SQL call. Its HTTPS URL is
a short-lived bearer capability: do not share it or call it a permanent archive.

## Access modes

The current private Developer Mode App uses `anonymous_dev`: no login is
required and all callers share global limits. The future `oauth` mode will use
the product-managed authorization flow and per-user entitlements. Never emulate
OAuth in chat or ask for credentials.

## Stable business errors

| Code | Handling |
|---|---|
| `invalid_scope` | Reconnect through OAuth UI. |
| `access_pending` | Show the returned access page. |
| `access_denied` | Direct the user to support. |
| `usage_limit_exceeded` | Show reset information; do not retry immediately. |
| `rate_limited` | Retry only after the returned delay. |
| `concurrency_limited` | Wait for an existing query to finish. |
| `query_rejected` | Narrow or safely rewrite the query. |
| `resource_not_found` | Stop; do not test whether another user's resource exists. |
| `result_too_large` | Narrow, paginate, or offer an allowed export. |
| `temporarily_unavailable` | Suggest retrying later. |
