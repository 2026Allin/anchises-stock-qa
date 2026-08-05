# Market-data analysis and export policy

Use these rules for broad screens, large matched ranges, SQL, row-level
pagination requests, and CSV downloads. Do not lead with policy language for
an ordinary analyst request that can be completed naturally.

## Structured screens

- Use `as_of_date` for one trading date. Use `start_date` and `end_date`
  together for an inclusive range; never send only one or combine the pair
  with `as_of_date`.
- Select fields needed for the question and confirmed by `get_stock_schema`.
- Use `top_n` only with an explicit `sort`; both the Top-N and displayed
  preview are capped at 200.
- Use `base_query_id` only to add narrower AND filters to one prior screen.
- Treat `page_size` as a non-pageable preview. `screen_stocks` does not accept
  `cursor`, and `page.next_cursor` is always null.

Read `data.analysis` before answering. It distinguishes matched rows from
displayed rows and states the preview and query classification. The service may
still use the complete matched range for filtering, counting, statistics,
ranking, and aggregation.

Do not retrieve row 201 onward by changing sort direction, dates, price ranges,
ticker ranges, exchanges, or repeated queries. Do not join previews or CSV
files into a full market dataset.

## CSV exports

Call `create_csv_export` only when:

1. The user explicitly asks for a file.
2. The source is an immediately preceding `screen_stocks` result.
3. `data.export_policy.eligible_by_query` is true.
4. The screen selected fields relevant to the research question.

Never infer eligibility from a legacy `eligible` field or from limits alone.
The returned boolean is authoritative.

One export is limited to 1,000 rows, 25 total columns, and 20,000 data cells.
`EXCHANGE`, `Date`, and `TICKER` are automatically included and count toward
the column limit. A Top-N export is limited to 200, an exact-ticker export to
50 tickers, and a complete exchange-day partition is never exportable.

Treat these values as request-construction guardrails. Do not recite the list
in ordinary explanations. If the user asks for an exact applicable threshold,
quote only the relevant value returned by the current result.

Derive every export field from the analytical question and current schema. Do
not use a universal template. Do not evade an ineligible export by splitting
fields, tickers, dates, prices, letters, or sort direction; by creating
multiple files; by using SQL; or by stitching results locally.

Omit `expires_in_seconds` for the default 60-minute lifetime, or pass an
integer from 60 through 3,600 seconds.

For `query_policy_expired`, rerun the original screen without the stale query
ID, inspect the new policy, and export only if eligible. For CSV-only
`temporarily_unavailable`, preserve the analysis and explain that download
creation can be retried later.

## SQL analysis

Use `run_readonly_sql` only for a server-side statistic or aggregation that a
screen cannot express, or a bounded analysis of no more than 50 exact tickers.
Return no more than 200 rows. Do not use `cursor` or OFFSET.

Do not use UNION, JOIN, Boolean OR, ticker-letter ranges, or changing sort
directions to enumerate or reconstruct rows. A SQL `query_id` is
analysis-only and can never be passed to `create_csv_export`.

For `query_requires_bounded_analysis`, replace raw enumeration with one
server-side aggregate or no more than 50 exact tickers.

## Export errors

- `export_requires_selective_query`,
  `export_complete_partition_not_allowed`, and `query_not_exportable`:
  continue server-side analysis and offer a focused ticker, Top-N, price,
  volume, market-cap, or indicator subset.
- `export_row_limit_exceeded`, `export_column_limit_exceeded`,
  `export_cell_limit_exceeded`, `export_top_n_limit_exceeded`, and
  `export_ticker_limit_exceeded`: identify the exceeded dimension and help
  reduce it without producing replacement file partitions.
- `query_partition_limit_exceeded` or `result_too_large`: narrow or aggregate;
  do not divide the market into downloadable partitions.

Describe these as the scope of the current export workflow, not missing
permission, exhausted quota, or a system failure. For a bulk row-level request,
preserve in-conversation analysis and suggest a verified bulk-market-data API
or licensed exchange-data vendor when a complete file remains the goal.
