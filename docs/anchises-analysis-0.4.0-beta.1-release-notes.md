# Anchises Analysis 0.4.0-beta.1 Release Notes

Anchises Analysis 0.4 updates the plugin for Hosted MCP 0.6.0, Data API 0.3.0,
and export policy `stock-data-export-v1`.

## Highlights

- Preserved the `anchises-analysis` slug, Anchises Analysis brand, Anchises
  Capital publisher, Developer Mode App ID, public URLs, and credential-free
  `public_noauth` access.
- Synced all 12 Hosted MCP descriptors and their strict noauth schemas.
- Added exact-date and paired-date-range screens, selected fields, explicitly
  sorted Top-N up to 200, and safe `base_query_id` refinement.
- Full matched stock-data ranges can be filtered, counted, ranked, summarized,
  and aggregated on the server. The Host displays at most the first 200 rows
  and cannot fetch later row-level pages.
- CSV creation now requires a current `screen_stocks` result with
  `export_policy.eligible_by_query=true` and explicitly selected research
  fields.
- One CSV is limited to 1,000 rows, 25 total columns, 20,000 cells, Top-N 200,
  or 50 exact tickers. Identity columns are added automatically. Complete
  exchange-day partitions and SQL query IDs cannot be exported.
- Added safe handling for policy expiry, all export-limit errors, large
  results, and CSV-only temporary unavailability.
- Company identity resolution and live Host-side company report generation
  remain unchanged and continue to use Prompt pack 5.1.

## Public-access behavior

Public access requires no account or credentials. It has no account-linked
cross-session cumulative budget, while shared short-term rate and concurrency
limits still apply. Export eligibility is not based on a percentage of a
market.

Company reports and stock analysis are informational, not official filings or
investment advice. Temporary CSV URLs are bearer capabilities and should not be
shared.
