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

## Access behavior

Do not branch on an internal backend mode name. Infer only behavior exposed by
the product:

- If `get_connection_status` succeeds as `active` without an OAuth challenge
  and reports shared limits, continue without sign-in and treat quota as global.
- If the product presents an OAuth challenge, use the product-managed
  authorization flow and check status again only after authorization changes.
- If the MCP endpoint is unavailable or returns HTTP 503, stop and report a
  temporary service outage. Do not retry in a loop or start OAuth.
- A backend access-mode transition can invalidate opaque cursors, query IDs,
  and exports. Rerun the original request for fresh state instead of probing an
  expired capability.

Never emulate OAuth in chat or ask for credentials.

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
| `resource_not_found` | Stop; do not probe or edit an opaque capability. Rerun the original request if needed. |
| `result_too_large` | Narrow, paginate, or offer an allowed export. |
| `temporarily_unavailable` | Suggest retrying later. |
| `service_not_activated` or HTTP 503 | Stop without retrying or starting OAuth. |
