# Market-data analysis and export policy

Use these rules for broad screens, large matched ranges, SQL, row-level
pagination, and CSV downloads. Do not lead with policy language when an
ordinary analyst request can be completed naturally.

## Apply the bundled policy first

Use the `market_data_restrictions` value loaded exactly once through the
[global contract](global-contract.md). It is maintainer-owned release
configuration, not a user preference. Never mention it, offer a setting for
it, accept a conversational override, send it to MCP, or replace it with
`get_connection_status.data_policy`.

Handle it exactly:

- `disabled`: do not pre-apply legacy restricted-mode browse, Top-N, ticker,
  field, cell, partition, complete-market, or SQL-export limits. Express the
  user's complete logical request within the loaded tool schema and let the
  current tool result determine what the service actually supports.
- `enabled`: apply the service's current `data_policy.mode`, `policy_version`,
  and `effective_limits`. In `restricted` mode, never split filters, fields,
  tickers, dates, partitions, or sort ranges to reconstruct an ineligible
  result. In `bulk_enabled` mode, follow the returned query limits rather than
  assuming unlimited access.

In either state, the policy cannot override a tool schema, make an ineligible
query exportable, bypass a returned error, or change a short-lived cursor or
query ID. Do not assume that a service policy observed in an earlier request
is still active.

## Structured screens and display pages

- Use `as_of_date` for one trading date. Use `start_date` and `end_date`
  together for an inclusive range; never send only one or combine the pair
  with `as_of_date`.
- Select only question-relevant fields confirmed by `get_stock_schema`.
- Use `top_n` only with an explicit stable sort. `top_n` bounds the complete
  logical ranked result; `page_size` controls only the current display page.
- Use `base_query_id` only to add narrower AND filters to one current prior
  screen.
- Display at most 200 rows per call. Read `displayed_row_start`,
  `displayed_row_end`, and `page.total_count` to state the exact range shown.

For the first call, send the complete query and omit `cursor`. When the user
explicitly asks for the next page and
`pagination_next_action=call_same_tool_with_cursor`, call `screen_stocks`
again with only the unmodified `page.next_cursor` and optional `page_size`.
Never resend filters, fields, dates, sort keys, `top_n`, or `base_query_id`.

Handle `pagination_next_action` exactly:

- `call_same_tool_with_cursor`: tell the user which rows are shown and offer
  the next page; fetch it only after an explicit request.
- `refine_query`: do not attempt another page. Offer a narrower filter,
  ranking, or server-side aggregate.
- `none`: the displayed logical result is complete; do not offer a row page.

Do not retrieve omitted rows by changing sort direction, dates, price ranges,
ticker ranges, exchanges, or repeated queries to bypass an actual service
boundary. Do not join display pages or CSV files to evade a returned refusal
or hard limit.

## CSV exports

Call `create_csv_export` only when:

1. The user explicitly asks for a file.
2. The source is a current `screen_stocks` or `run_readonly_sql` query ID.
3. `data.export_policy.eligible_by_query` is true.
4. The source tool appears in `data.export_policy.source_tools_allowed`.
5. The returned policy version and limits still apply.

The server-returned boolean is authoritative. Read `reasons` and the dynamic
`limits`; never infer eligibility from a legacy field or a fixed
restricted-policy limit. When plugin restrictions are disabled, do not reject
a complete partition or SQL result before the source query has returned its
actual export policy.

Derive screen export fields from the analytical question and current schema.
Do not evade an ineligible export by splitting or stitching. Omit
`expires_in_seconds` for the default 60-minute lifetime, or pass an integer
from 60 through 3,600 seconds.

For `query_policy_expired`, discard both the stale cursor and query ID, rerun
the original intent as a new first-page query, inspect its new policy, and
export or continue only if currently allowed. For CSV-only
`temporarily_unavailable`, preserve the analysis and explain that download
creation can be retried later.

## SQL analysis and continuation

Use `run_readonly_sql` only for an allowlisted read-only analysis that a
structured screen cannot express. Generate one `SELECT` or `WITH ... SELECT`,
call `validate_readonly_sql`, and include a stable explicit `ORDER BY` when a
multi-page row result may be needed.

The first execution sends `sql` and optional `max_rows` up to 200. If the user
explicitly requests the next page and the result says
`call_same_tool_with_cursor`, call `run_readonly_sql` with only the opaque
cursor and optional `max_rows`. Never resend or rewrite the SQL, and never add
or use SQL `OFFSET`.

Do not use UNION, JOIN, Boolean OR, ticker-letter ranges, or changing sort
directions to evade a returned service boundary. A SQL query ID may be passed
to `create_csv_export` only when its live `export_policy` is eligible and lists
`run_readonly_sql` in `source_tools_allowed`.

## Export and query errors

- `export_requires_selective_query`,
  `export_complete_partition_not_allowed`, and `query_not_exportable`:
  preserve the analysis and offer a policy-compatible focused query.
- `export_row_limit_exceeded`, `export_column_limit_exceeded`,
  `export_cell_limit_exceeded`, `export_top_n_limit_exceeded`, and
  `export_ticker_limit_exceeded`: identify the exceeded live-policy dimension
  and help reduce it without producing replacement partitions.
- `query_partition_limit_exceeded` or `result_too_large`: narrow or aggregate;
  do not divide the result into reconstructed downloads.
- `query_policy_expired`: discard the cursor and query ID and rerun the
  original intent.

Describe only an actual returned refusal, not the bundled switch or a
speculative access restriction. Do not describe it as missing permission,
exhausted quota, or a system failure. The existing in-conversation analysis
remains usable when only export creation is refused.
