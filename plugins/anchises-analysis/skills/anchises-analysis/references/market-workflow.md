# Structured market workflow

The request's `primary_task`, modifiers, and ordered entities must already be
set by
[the canonical arbitration reference](query-interpretation.md).
This file defines tool execution only. Do not reclassify the request here.

## Choose the smallest tool sequence

1. `get_connection_status` for service state and actual service capabilities.
2. `resolve_company_identity` for a single-company market-data request.
3. `get_available_exchanges` for authoritative structured-data markets.
4. `get_latest_dates` for market-data freshness.
5. `get_stock_schema` before selecting screen or export fields.
6. `list_stock_tables` and `get_table_schema` for historical coverage.
7. `screen_stocks` for ordinary filters, rankings, and latest snapshots.
8. `validate_readonly_sql` and then `run_readonly_sql` for complex aggregate
   or bounded read-only fallback queries.
9. `create_csv_export` only for an explicit CSV request backed by a currently
   eligible screen or SQL query ID.

Never call `prepare_company_report_generation` in this workflow.

## Result envelopes and pagination

Data tools return `data_date`, `data`, `warnings`, and `quota`.
`list_stock_tables`, `screen_stocks`, and `run_readonly_sql` also return a
`page` object. A stock-row page contains no more than 200 rows:

```json
{
  "page": {
    "row_count": 200,
    "total_count": 500,
    "truncated": true,
    "next_cursor": "opaque-server-value"
  }
}
```

Treat `data_date` as source freshness, not the current date. Preserve warnings.
For rowsets, read:

- `displayed_row_start` and `displayed_row_end` for the current visible range;
- `browsable_row_limit` and `pagination_limit_reached` for the query boundary;
- `pagination_next_action` for the only permitted next step.

On a first call, send the complete screen or SQL request. On a continuation,
send only the exact opaque cursor and the same tool's display-size field:

- `screen_stocks`: `cursor` and optional `page_size`;
- `run_readonly_sql`: `cursor` and optional `max_rows`.

Do not construct, decode, edit, cache for later use, or transfer a cursor
between tools. Do not continue until the user explicitly asks for the next
page. If the action is `refine_query`, offer a narrower query instead. If it
is `none`, the logical result is complete.

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

`screen_stocks` accepts optional exchanges, `as_of_date`, a paired
`start_date` plus `end_date`, selected fields, zero to 30 AND-combined filters,
sort keys, `top_n`, `base_query_id`, `cursor`, and `page_size` up to 200.

- Never combine an exact date with a range or send only one range boundary.
- Use only fields returned by `get_stock_schema`.
- Use scalar values for `eq`, `ne`, `gt`, `gte`, `lt`, and `lte`; one to 100
  values for `in`; and exactly two ordered values for `between`.
- Never pass an object as a filter value.
- Use `top_n` only with a non-empty stable sort. It bounds the complete
  logical result, while `page_size` bounds only the displayed page.
- Never combine a cursor continuation with any original query field.

The result includes `data.analysis` for matched/displayed counts, display
range, pagination decision, browse limit, and classification. It also includes
`data.export_policy` with the service mode, policy version, eligibility,
reasons, allowed source tools, and dynamic limits. The bundled plugin policy
does not alter these returned values.

## SQL fallback

Generate one allowlisted `SELECT` or `WITH ... SELECT`, call
`validate_readonly_sql` with only `sql`, and execute only after validation
succeeds. Include a stable `ORDER BY` when row continuation may be needed.

The first `run_readonly_sql` call uses `sql` and optional `max_rows` up to 200.
A continuation uses only `cursor` and optional `max_rows`. Never use SQL
`OFFSET`; the server cursor owns the offset and registered query state.

Do not construct UNION, JOIN, Boolean OR, ticker-letter range, date-slice, or
sort-direction schemes for enumerating market rows.

## Dynamic exports

`create_csv_export` is the only non-read-only and non-idempotent tool. Pass
only the current query ID when all of these are true:

- the user requested a file;
- `export_policy.eligible_by_query` is true;
- the originating tool is listed in `source_tools_allowed`;
- the query still belongs to the current policy version.

Do not assume SQL or complete exchange-day results are forbidden. Read the
query's `reasons` and `limits` every time. When bundled restrictions are
disabled, do not apply a legacy refusal before the query runs. In either
bundled state, never split one actually ineligible result into filters,
fields, tickers, date partitions, sort ranges, or multiple files.

For screens, select question-led fields verified with `get_stock_schema`.
Omit `expires_in_seconds` for the default 3,600-second lifetime; otherwise use
60 through 3,600 seconds. The HTTPS URL is a temporary bearer capability.

## Stable errors

| Code | Handling |
|---|---|
| `query_rejected` | Narrow or safely rewrite a new first-page query. |
| `query_requires_bounded_analysis` | Use a server-side aggregate or a bounded query. |
| `resource_not_found` | Rerun the original intent; do not edit an opaque capability. |
| `export_requires_selective_query` | Continue analysis and offer a policy-compatible subset. |
| `export_row_limit_exceeded` | Reduce rows without splitting files. |
| `export_column_limit_exceeded` | Select fewer relevant fields. |
| `export_cell_limit_exceeded` | Reduce rows or fields in one query. |
| `export_complete_partition_not_allowed` | Preserve analysis and refine only if useful. |
| `export_top_n_limit_exceeded` | Use the current policy's returned Top-N limit. |
| `export_ticker_limit_exceeded` | Use the current policy's returned ticker limit. |
| `query_not_exportable` | Preserve analysis and follow the returned policy reasons. |
| `query_policy_expired` | Discard cursor/query ID and rerun the original intent. |
| `query_partition_limit_exceeded` or `result_too_large` | Narrow or aggregate; do not reconstruct partitions. |
| `temporarily_unavailable` | Preserve analysis and report only the unavailable operation. |
