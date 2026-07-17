# Anchises Analysis 0.3.0-beta.1 Release Notes

Anchises Analysis is the renamed and expanded public-company research and
stock-data plugin from Anchises Capital.

## Highlights

- Renamed the plugin slug, Skill, package directories, marketplace entry, and
  user-facing brand to `anchises-analysis` / Anchises Analysis.
- Preserved the existing Developer Mode App ID and all public service and policy
  URLs.
- Synced the Hosted MCP `0.5.1` public descriptor snapshot with 12 tools.
- Added `resolve_company_identity` for company names, tickers, exchange hints,
  and contextual company references.
- Company-research intent now starts live Host web research directly after
  identity resolution; no extra generation confirmation is required.
- `prepare_company_report_generation` now requires exchange, ticker, company
  name, and output locale and returns Prompt pack `5.1` instructions for the
  Host to execute.
- Added external-market, inactive/delisted, multi-listing, multi-share-class,
  ETF/Fund, no-web, privacy, and hidden-prompt safeguards.
- Expanded mining-company quality checks for cash, debt, runway, fully diluted
  capital, warrants, convertibles, financing capacity, and funding gaps.
- CSV exports continue to default to 60 minutes and support explicit lifetimes
  from 60 through 3600 seconds.

## Compatibility

This is a plugin-slug migration. Local users must install
`anchises-analysis@Anchises-Analysis` and start a new task. Portal and Developer
Mode installations must be refreshed after the MCP tool-set change so they do
not retain an older schema or Skill package.

Company reports are analytical research, not official filings or investment
advice. Anchises structured stock data covers ASX, CSE, NASDAQ, NYSE, TSX, and
TSXV.
