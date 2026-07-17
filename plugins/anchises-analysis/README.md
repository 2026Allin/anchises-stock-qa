# Anchises Analysis

Anchises Analysis is a single-Skill Codex plugin for live public-company
research and structured stock-market analysis.

## Release identity

- Plugin slug: `anchises-analysis`
- Skill name: `anchises-analysis`
- Explicit invocation: `$anchises-analysis`
- Display name: `Anchises Analysis`
- Publisher: `Anchises Capital`
- Target semantic version: `0.4.0-beta.1`
- Repo marketplace: `Anchises-Analysis`
- Hosted MCP: `https://mcp.anchisesdata.com/mcp`
- Hosted MCP version: `0.6.0`
- Data API version: `0.3.0`
- Export policy: `stock-data-export-v1`
- Prompt pack: `5.1`

The Developer Mode App ID value in `.app.json` is intentionally unchanged. Its
key is renamed to `anchises_analysis` to match the plugin namespace. The App is
used only by local and Repo Marketplace installations. A public Plugin
Directory submission must submit and scan the production MCP URL directly and
use the same final Skill bundle and public metadata.

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
60 through 3600 seconds. Full matched ranges may be analyzed server-side, but
only the first 200 stock rows are shown and no later row-level pages are
available.

CSV downloads are limited to selective `screen_stocks` research subsets.
`data.export_policy.eligible_by_query` is the only export gate. One file is
limited to 1,000 rows, 25 total columns, 20,000 cells, Top-N 200, or 50 exact
tickers; `EXCHANGE`, `Date`, and `TICKER` are added automatically and count
toward the column limit. Complete exchange-day partitions and SQL query IDs are
not exportable.

## Contract sync

The checked-in descriptor snapshot is generated from the public service with a
credential-free, read-only JSON-RPC client:

```bash
.venv/bin/python plugins/anchises-analysis/contracts/sync_hosted_contract.py --check
```

The snapshot must contain exactly 12 strict descriptors, MCP `0.6.0`, the
company-identity resolver, a four-required-field prepare schema, noauth
security, Prompt pack `5.1`, null stock-row cursors, and
`eligible_by_query` export policy metadata.

## Validation

From the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -v

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/anchises-analysis

.venv/bin/python \
  ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/anchises-analysis
```
