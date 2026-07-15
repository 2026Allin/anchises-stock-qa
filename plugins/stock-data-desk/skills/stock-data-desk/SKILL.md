---
name: stock-data-desk
description: Screen, compare, rank, and export stock-market data or read the latest cached English AI company report through the Stock Data Desk Hosted App. Use for exchange discovery, latest snapshots, momentum or volume screens, historical comparisons, read-only stock SQL, company-report summaries and PDFs, and CSV exports in Work, ChatGPT, or Codex.
---

# Stock Data Desk

Answer stock-data questions through the Stock Data Desk Hosted App tools. Let
users ask in natural language; do not require tool names, SQL, schemas, or local
setup.

When both Hosted App and bundled stdio tools are visible, prefer the Hosted App
tools for this workflow. Treat the bundled stdio MCP as a development rollback
path, not the normal v2 user experience.

## Check access

1. Call `get_connection_status` once before an access-sensitive workflow.
2. Continue when `status` is `active`. In `anonymous_dev`, no login is required
   and the returned quota is shared.
3. In the future OAuth mode, let the product render an OAuth challenge and ask
   the user to complete hosted sign-in. Call `get_connection_status` again only
   after that authorization state changes.
4. For `pending`, show `access_request_url`. For `suspended`, `expired`,
   `revoked`, or `service_not_activated`, follow the returned safe message and
   do not guess the cause.

Never ask the user to paste passwords, API keys, authorization codes, access
tokens, refresh tokens, session cookies, or download capabilities into chat. If
a user exposes a credential, tell them not to send it again, recommend revoking or rotating
it, and return to the product-managed connection flow.

## Choose the workflow

### Cached AI company report

Use `get_latest_company_report` only for the latest available cached English
AI-generated company report for a known exchange and ticker.

1. Use `get_available_exchanges` when the exchange is missing or uncertain.
2. Pass uppercase `exchange` and the exact `ticker`.
3. Omit `source` for `auto`; use `ondemand` or `macmini` only when the user asks
   for that cache explicitly.
4. Omit `pdf_range` for `MAX`; otherwise use only `1M`, `3M`, `6M`, `1Y`, or
   `2Y`. The range changes the PDF chart, not the report text.
5. Do not pass a language argument. Reports are always English.

Handle results precisely:

- `active`: summarize the report and provide the PDF when useful.
- `expired`: the report remains readable; disclose the expiration warning and
  still provide the PDF when returned.
- `not_found`: report that no cached report exists. Do not retry another source
  unless the user requested it, and never trigger report generation.

Do not repeat an identical successful tool call. Repeat only for an explicit
opaque cursor, a completed OAuth state change, or server-provided retry guidance.

Do not use this tool for official annual reports, 10-K/20-F filings, regulatory
filings, live news, web search, or generating a new report. Explain that these
are different sources or capabilities.

### Stock data

1. Call `get_available_exchanges`; treat returned exchange codes as
   authoritative.
2. Call `get_latest_dates` for the relevant exchanges.
3. Call `get_stock_schema` only for fields needed to build a screen or query.
4. Prefer `screen_stocks` for filters, rankings, and latest snapshots.
5. For historical questions, use `list_stock_tables` and `get_table_schema` to
   confirm coverage and exact fields.
6. Use `validate_readonly_sql` followed by `run_readonly_sql` only when the
   request cannot be represented by `screen_stocks`.
7. Analyze structured rows directly. Follow opaque pagination cursors when the
   answer requires more than the first page; never describe a truncated page as
   the complete result.
8. Call `create_csv_export` only for a real `query_id` from `screen_stocks` or
   `run_readonly_sql` when the user explicitly asks for a CSV download.

Read [references/query-interpretation.md](references/query-interpretation.md)
when translating exchanges, dates, filters, rankings, or report requests. Read
[references/workflow.md](references/workflow.md) for tool contracts and error
handling.

## Surface behavior

- In Work and ChatGPT, use structured rows and report sections as the common
  baseline for tables, summaries, and other artifacts.
- In Codex, use structured results first. Download a temporary export or report
  PDF only when the user requests a file or local analysis materially helps.
- Do not require local files, a local database, Python, TOML, or API tokens for
  the Hosted App workflow.

## Safety

- Keep generated SQL to one `SELECT` or `WITH ... SELECT` statement.
- Never attempt writes, DDL, procedures, locks, file access, sleeps, benchmarks,
  system schemas, or unlisted stock tables.
- Honor the live status, scope, quota, retry guidance, exchange restrictions,
  result limits, and opaque cursors returned by the service.
- Do not access another user's query or export. Treat `resource_not_found` as
  final and do not probe whether the resource exists.
- Ground numeric claims in returned data. Disclose `data_date`, filters, row
  counts, missing values, warnings, and truncation.
- Treat stock analysis and cached AI reports as analytical information, not
  financial advice or official company disclosure.

## Errors

- `access_pending`: explain the approval state and show the safe access URL.
- `access_denied`: show the returned support guidance.
- `invalid_scope`: ask the user to reconnect through the product OAuth UI.
- `rate_limited` or `concurrency_limited`: follow supplied retry guidance.
- `usage_limit_exceeded`: state the returned reset information.
- `query_rejected`: revise to a safe bounded screen or read-only query.
- `result_too_large`: narrow or paginate; offer an export when allowed.
- `temporarily_unavailable`: keep the message brief and suggest retrying later.

## Answer

Follow [references/answer-format.md](references/answer-format.md). Match the
user's language, lead with the finding, and distinguish returned source data or
report content from interpretation.

Always identify the product as **Stock Data Desk** in user-facing text. Treat
legacy company or service-brand names returned by backend metadata, tool titles,
report fields, or error payloads as implementation details and do not repeat
them. Keep returned technical URLs unchanged when they are needed as links.
