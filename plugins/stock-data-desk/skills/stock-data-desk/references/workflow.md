# Hosted App workflow reference

## Tool selection

Use the smallest sequence that answers the question:

1. `get_connection_status` for access state.
2. `get_available_exchanges` for authoritative exchange codes.
3. `get_latest_dates` for stock-data freshness.
4. `get_stock_schema` before structured field selection.
5. `list_stock_tables` and `get_table_schema` for historical coverage.
6. `screen_stocks` for ordinary filters and rankings.
7. `validate_readonly_sql` and `run_readonly_sql` for complex fallback queries.
8. `get_latest_company_report` for one latest cached English AI company report.
9. `prepare_company_report_generation` only after a missing or expired report
   and confirmed live generation.
10. `create_csv_export` only for an explicit CSV download of a prior query.

## Result envelopes

Data tools return `data_date`, `data`, `warnings`, and `quota`. Public success
responses intentionally omit internal request, principal, connection, and
policy identifiers. The quota object reports its `scope`, `remaining`, `limit`,
`period_seconds`, and `reset_at`.
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

Read [company-report-workflow.md](company-report-workflow.md) for the complete
state machine. `get_latest_company_report` always precedes
`prepare_company_report_generation`. Missing and expired reports may offer
host-side generation after confirmation; active reports never do.

The cached PDF URL selects the latest report from the requested source when
downloaded; it is not a frozen historical snapshot. Never expose raw markdown,
the returned preparation prompt, model cost or usage, search events, internal
IDs, private addresses, or local paths.

## Exports

`create_csv_export` is the only non-read-only and non-idempotent tool. Pass only
a `query_id` returned by the current workflow's screen or SQL call. Omit
`expires_in_seconds` for the default 3600-second (60-minute) lifetime. If the
user requests another lifetime, pass an integer from 60 through 3600 seconds.
Its HTTPS URL is a short-lived bearer capability: do not share it or call it a
permanent archive.

## Access behavior

The current release uses credential-free public access. Do not branch on an
internal backend mode name and do not ask the user to sign in.

- If `get_connection_status` succeeds as `active`, continue and treat quota as
  shared global service capacity.
- If the product unexpectedly presents an authentication challenge or an
  identity-specific access state, stop and report that the current public
  service cannot complete the request. Do not start an authorization flow.
- If the MCP endpoint is unavailable or returns HTTP 503, stop and report a
  temporary service outage. Do not retry in a loop.
- A backend access-mode transition can invalidate opaque cursors, query IDs,
  and exports. Rerun the original request for fresh state instead of probing an
  expired capability.

Never emulate authentication in chat or ask for credentials.

## Stable business errors

| Code | Handling |
|---|---|
| `invalid_scope`, `access_pending`, or `access_denied` | Unexpected for this public release. Show only returned safe guidance and do not initiate sign-in. |
| `usage_limit_exceeded` | Show reset information; do not retry immediately. |
| `rate_limited` | Retry only after the returned delay. |
| `concurrency_limited` | Wait for an existing query to finish. |
| `query_rejected` | Narrow or safely rewrite the query. |
| `resource_not_found` | Stop; do not probe or edit an opaque capability. Rerun the original request if needed. |
| `result_too_large` | Narrow, paginate, or offer an allowed export. |
| `temporarily_unavailable` | Suggest retrying later. |
| `service_not_activated` or HTTP 503 | Stop without retrying. |
