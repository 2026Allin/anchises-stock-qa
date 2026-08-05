# Anchises Analysis

Anchises Analysis is a five-Skill Codex plugin for concise company briefs,
deep live reports, cross-company comparison, and structured stock-market
analysis.

## Release identity

- Plugin slug: `anchises-analysis`
- Skill names: `anchises-analysis`, `company-brief`, `company-report`,
  `company-comparison`, `market-analysis`
- Explicit invocations: `$anchises-analysis`, `$company-brief`,
  `$company-report`, `$company-comparison`, `$market-analysis`
- Display name: `Anchises Analysis`
- Publisher: `Anchises Capital`
- Target semantic version: `0.6.0-dev.3`
- Repo marketplace: `Anchises-Analysis`
- Hosted MCP: `https://mcp.anchisesdata.com/mcp`
- Hosted MCP version: `0.7.1`
- Data API version: `0.3.0`
- Internal contract version: `1.7.0-draft`
- Data policy: live `restricted` or `bulk_enabled` policy from MCP
- Prompt pack: `5.1`

The local QA Developer Mode App is
`asdk_app_6a5a007aa5bc8191bbb5409005af37a6`; `.app.json` stores the matching
plugin resource ID under the `anchises_analysis` namespace. The App is used by
local and Repo Marketplace installations. A public Plugin Directory submission
must submit and scan the production MCP URL directly and use the same final
Skill bundle and public metadata.

## Skill architecture and entry

The plugin package is the installation entry, `.app.json` is the single Hosted
App entry, and the five Skill descriptions are peer request-routing entries:

- `anchises-analysis` is a thin coordinator for generic, mixed, and ambiguous
  requests. Its references provide the canonical classification, global
  request state, shared company-introduction component, access, identity,
  safety, error, and response-finalization rules.
- `company-brief` owns one-to-five current company introductions.
- `company-report` owns deep research and is the only Skill allowed to call
  `prepare_company_report_generation`.
- `company-comparison` owns relative positioning and cross-company judgments.
- `market-analysis` owns supported-market discovery, screens, rankings,
  historical data, bounded SQL, and focused CSV exports.

A clear specialist request may enter its matching Skill directly. Every
specialist first reads the same canonical `primary_task` rules and must stop if
it does not own the result; downstream Skills never reclassify.

## Company briefs

The `company-brief` Skill handles explicit or semantically equivalent requests
for quick context on named companies or a clearly referenced company set. It
classifies the request once, preserves user order, resolves each selected
identity, and uses Host web research without calling the seven-section report
preparation tool.

Each company receives three or four source-linked sentences covering its core
business, a dated official development, and a dated independent news item.
Any standalone company-introduction section covers at most five companies,
including an introduction section attached to Market Analysis or Company
Comparison. Market tables, rankings, and comparison matrices are not capped by
this rule. When introductions remain, the response asks how to continue and
offers one relevant follow-up concerning only the completed batch.

Successful substantive Brief, Report, Comparison, news, and Market Analysis
answers use one response-finalization matrix. The disclaimer appears before
required questions; a successful completed answer ends with one semantic
question, while a successful partial introduction batch ends with one
continuation question followed by one semantic question. Explicit requests for
no suggestions and failed or mechanical workflows use the documented
exceptions.

## Company identity and live research

For a company name, ticker, exchange-ticker pair, or clear chat reference, the
Skill calls `resolve_company_identity` with only the extracted query fields.
It uses current chat context and light primary-source web verification to
resolve exchange, ticker, and company name without sending the full transcript.

An explicit company-research request calls
`prepare_company_report_generation` directly with all four required fields:

```json
{
  "exchange": "NASDAQ",
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "output_locale": "zh-CN"
}
```

For a ready result, the Host executes the returned prompt with live web search
and writes the final report in the current conversation. The MCP does not
perform the search or persist the result. External, inactive, and delisted
companies may use the `Others` prompt after primary-source identity and listing
verification. ETF and Fund records are not eligible for an operating-company
report.

## Structured stock data

Structured coverage is limited to:

- ASX
- CSE
- NASDAQ
- NYSE
- TSX
- TSXV

The 12 Hosted MCP tools are:

- `get_connection_status`
- `get_available_exchanges`
- `get_latest_dates`
- `get_stock_schema`
- `list_stock_tables`
- `get_table_schema`
- `screen_stocks`
- `validate_readonly_sql`
- `run_readonly_sql`
- `resolve_company_identity`
- `prepare_company_report_generation`
- `create_csv_export`

CSV exports default to 3600 seconds (60 minutes) and may be explicitly set from
60 through 3600 seconds. Full matched ranges may be analyzed server-side, and
each stock-row call displays no more than 200 rows. When the service returns
`call_same_tool_with_cursor`, the Host can fetch the next display page only
after the user explicitly asks. A continuation sends only the opaque cursor
and `page_size` or `max_rows`; it never resends the query or uses SQL `OFFSET`.

`top_n` bounds the complete logical ranked result rather than the current
display page. `get_connection_status.data_policy` and each result's
`data.export_policy` define the live restricted or bulk-enabled mode, dynamic
limits, permitted source tools, and `eligible_by_query` gate. A currently
eligible `screen_stocks` or `run_readonly_sql` query ID may be exported. In
restricted mode the Skill never splits queries to reconstruct a refused
dataset; in bulk mode it still follows the returned hard limits.

## Contract sync

The checked-in descriptor snapshot is generated from the public service with a
credential-free, read-only JSON-RPC client:

```bash
.venv/bin/python plugins/anchises-analysis/contracts/sync_hosted_contract.py --check
```

The snapshot must contain exactly 12 strict descriptors, MCP `0.7.1`, the
company-identity resolver, a four-required-field prepare schema, noauth
security, Prompt pack `5.1`, opaque cursor pagination, dynamic data/export
policy metadata, and no legacy cached-report tools.

## Validation

From the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -v

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/anchises-analysis

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/company-brief

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/company-report

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/company-comparison

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/market-analysis

.venv/bin/python \
  ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/anchises-analysis
```
