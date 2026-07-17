# Market-data analysis and export policy

Use these rules for broad screens, large matched ranges, SQL, row-level
pagination requests, and CSV downloads. Do not lead with policy language for an
ordinary analyst request that can be completed naturally.

## Structured screens

- Use `as_of_date` for one trading date. Use `start_date` and `end_date`
  together for an inclusive range; never send only one or combine the pair with
  `as_of_date`.
- Select fields that are needed for the question. Use only names returned by
  `get_stock_schema`.
- Use `top_n` only with an explicit `sort`; both the Top-N and displayed
  preview are capped at 200.
- Use `base_query_id` only to add narrower AND filters to one prior
  `screen_stocks` result. Never use several refinements to reconstruct omitted
  rows.
- Treat `page_size` as the size of a non-pageable preview. `screen_stocks`
  does not accept `cursor`, and `page.next_cursor` is always null.

Read `data.analysis` before answering. It distinguishes matched rows from
displayed rows, states whether the result is a preview, and gives the query
classification. Full matched data may still be used by the service for
filtering, counting, statistics, ranking, and aggregation.

Do not retrieve row 201 onward by changing sort direction, dates, price ranges,
ticker ranges, exchange partitions, or repeated queries. Do not join previews
or CSV files into a full market dataset.

## CSV exports

Call `create_csv_export` only when all of these are true:

1. The user explicitly asks for a file.
2. The source is an immediately preceding `screen_stocks` result.
3. `data.export_policy.eligible_by_query` is true.
4. The screen explicitly selects fields relevant to the research question.

Never read or infer eligibility from a legacy `eligible` field. Never infer
eligibility from limits alone; the returned boolean is authoritative.

One export is limited to 1,000 rows, 25 total columns, and 20,000 data cells.
`EXCHANGE`, `Date`, and `TICKER` are automatically included and count
toward the 25-column limit, so select at most 22 additional fields. All limits
apply together. A Top-N export is limited to 200, an exact-ticker export to 50
tickers, and a complete exchange-day partition is never exportable.

Treat these numbers as internal request-construction guardrails. Do not recite
the threshold list in ordinary user-facing explanations. The current result's
`eligible_by_query`, `reasons`, and `limits` are authoritative; if the user
explicitly asks for an exact applicable threshold, quote only the relevant
value returned by that result rather than a memorized list.

Derive every export field list from the user's analytical question and confirm
the names with `get_stock_schema`. Do not use a fixed universal target schema.
Keep only fields needed to answer the question; automatic identity fields do
not justify adding unrelated measures.

Do not evade a refusal by splitting fields, tickers, dates, prices, letters, or
sort direction; by creating multiple files; by using SQL; or by stitching
results locally. Omit `expires_in_seconds` for the default 60-minute
(3,600-second) lifetime, or pass an integer from 60 through 3,600 seconds.

For `query_policy_expired`, rerun the original structured screen from the
user's intent without the stale query ID, inspect the new policy, and export
only if it is eligible. For CSV-only `temporarily_unavailable`, preserve the
analysis and explain that download creation can be retried later.

## SQL analysis

Use `run_readonly_sql` only for server-side statistics or aggregation that
`screen_stocks` cannot express, or for a bounded analysis of no more than 50
exact tickers. Return at most 200 rows. Do not use `cursor` or `OFFSET`.

Do not use UNION, JOIN, Boolean OR clauses, ticker-letter ranges, or changing
sort directions to enumerate or reconstruct market rows. Legitimate bounded
aggregation must remain tied to the user's analytical question.

A SQL `query_id` is analysis-only and can never be passed to
`create_csv_export`. If the user needs a download, restate the eligible part
as one selective `screen_stocks` request with explicit fields.

For `query_requires_bounded_analysis`, replace raw row enumeration with one
server-side aggregate or a query for no more than 50 exact tickers.

## Export errors

- `export_requires_selective_query`,
  `export_complete_partition_not_allowed`, and `query_not_exportable`:
  continue server-side analysis and offer a ticker, Top-N, price, volume,
  market-cap, or indicator subset.
- `export_row_limit_exceeded`, `export_column_limit_exceeded`,
  `export_cell_limit_exceeded`, `export_top_n_limit_exceeded`, and
  `export_ticker_limit_exceeded`: identify the exceeded dimension and help
  reduce it without producing multiple replacement files.
- `query_partition_limit_exceeded` or `result_too_large`: narrow or
  aggregate; do not divide the market into downloadable partitions.

Describe these as the scope of the current export workflow, not missing
permission, exhausted quota, or a system failure. Do not enumerate every
numeric threshold. For a bulk row-level request, say that the complete matched
range remains available for in-conversation analysis and gently suggest a
verified bulk-market-data API or licensed exchange-data vendor when a complete
file remains the goal. Tailor any proposed fields and provider type to the
original research question. Do not invent usage counts, call counts, or reset
dates. Use the full response pattern in
[answer-format.md](answer-format.md#exports).
