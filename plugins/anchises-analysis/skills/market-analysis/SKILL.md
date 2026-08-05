---
name: market-analysis
description: Analyze structured stock-market data through Anchises Analysis, including supported-exchange discovery, latest dates, prices, returns, technical indicators, full-range server-side screens, rankings, historical comparisons, bounded read-only stock SQL, and selective research CSV exports. Use when the primary deliverable is quantitative market data or supported-market instrument discovery, including screens that additionally request standalone introductions for the resulting companies. Do not use when introductions are the primary deliverable, for a full company report, a narrative company comparison, news-only work, official filings, or incidental company mentions.
---

# Market Analysis

Use the Anchises Analysis MCP for supported-market quantitative work.
Let users ask in natural language; do not require schemas, SQL, tickers, local
files, Python, or credentials.

## Check the selected plugin once

Read
[../anchises-analysis/references/global-contract.md](../anchises-analysis/references/global-contract.md),
[../anchises-analysis/references/plugin-update.md](../anchises-analysis/references/plugin-update.md),
and
[../anchises-analysis/references/service-access.md](../anchises-analysis/references/service-access.md).
Because this Skill has been selected, call `get_connection_status` exactly
once for this user request using its published schema and the shared
client-release metadata. Retain `client_update`; never probe with new
arguments and retry with `{}`.

## Confirm ownership once

Read
[../anchises-analysis/references/query-interpretation.md](../anchises-analysis/references/query-interpretation.md).
Proceed only for `primary_task=market_data` or for `primary_task=discovery`
whose final deliverable is a supported exchange, instrument, table, or
structured-market list.

Do not reclassify in this Skill. A full report with an attached market-data
modifier remains owned by `company-report`, which may use this Skill's
workflow only after completing the report.

## Establish access and scope

Reuse the single connection result already obtained for this request. Never
call `get_connection_status` again for an attached modifier.

Anchises structured stock data covers ASX, CSE, NASDAQ, NYSE, TSX, and TSXV.
Use `get_available_exchanges` as authoritative and `get_latest_dates` for
freshness.

For a single named company, read
[../anchises-analysis/references/company-resolution.md](../anchises-analysis/references/company-resolution.md)
and call `resolve_company_identity` with `purpose=stock_data`. Use the
canonical exchange and ticker. For a broad market screen, do not perform
single-company resolution.

## Execute the quantitative workflow

Read [references/market-workflow.md](references/market-workflow.md) for tool
order and contracts. In summary:

1. Use `get_stock_schema` only for fields needed by the question.
2. Prefer `screen_stocks` for filters, rankings, latest snapshots, and eligible
   focused exports.
3. For historical coverage, inspect `list_stock_tables` and
   `get_table_schema`.
4. Use `validate_readonly_sql` followed by `run_readonly_sql` only when a
   requested server-side statistic cannot be represented by a screen.
5. Use the complete matched range for server-side filtering, counting,
   statistics, ranking, and aggregation; display no more than 200 rows per
   call and continue only when the user explicitly asks for the next page.
6. Call `create_csv_export` only when the user asks for a file and the
   current `screen_stocks` or `run_readonly_sql` result reports
   `data.export_policy.eligible_by_query=true` and names that source tool in
   `source_tools_allowed`.

Read
[references/market-data-policy.md](references/market-data-policy.md)
before broad results, row-level pagination, SQL, or CSV workflows.

## Apply an attached company-introduction modifier

When `company_introductions=false`, do not expand result companies into
profiles.

When `company_introductions=true`, complete the quantitative screen, ranking,
and requested evidence filter first. Materialize the eligible result companies
as `discovered_entities` in their original ranked order, then read
[../anchises-analysis/references/company-introductions.md](../anchises-analysis/references/company-introductions.md).

Keep the full quantitative result under the market display policy. Apply the
five-company window only to the standalone introduction section. Resolve and
research only `current_intro_batch`; do not call
`prepare_company_report_generation`.

On a continuation batch, reuse the prior result set, order, filters, and
`data_date`. Do not rerun the screen unless the user asks to refresh it.

## Safety

- Keep SQL to one `SELECT` or `WITH ... SELECT`. Never attempt writes, DDL,
  procedures, locks, file access, sleeps, benchmarks, system schemas, or
  unlisted tables.
- Use only an unmodified opaque `page.next_cursor` for the immediately
  requested next page of the same tool. Never invent a cursor, combine it with
  the original query, traverse pages speculatively, or use repeated sorts,
  split filters, date partitions, SQL, or local stitching to reconstruct rows.
- When `data_policy.mode=restricted`, never split or reshape one query to
  rebuild an ineligible dataset. In bulk mode, follow the returned policy and
  hard limits rather than assuming unrestricted access.
- Treat query IDs and export URLs as short-lived bearer capabilities. Never
  share, edit, or reuse them outside the related workflow.
- Ground numeric claims in returned data. Disclose the data date or range,
  filters, row counts, missing values, warnings, and truncation.
- Never imply structured coverage for a verified company outside the six
  supported markets.

## Answer and recover

Read
[references/market-answer-format.md](references/market-answer-format.md).
Match the user's language and lead with the result.

Use workflow-specific errors in
[references/market-data-policy.md](references/market-data-policy.md) and common
access or quota handling in
[../anchises-analysis/references/common-errors.md](../anchises-analysis/references/common-errors.md).
Assign `response_status`, then apply
[../anchises-analysis/references/response-finalization.md](../anchises-analysis/references/response-finalization.md)
exactly once.

Call the product **Anchises Analysis**. Treat the result as analytical
information, not investment advice or official disclosure.
