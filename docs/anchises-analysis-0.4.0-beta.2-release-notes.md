# Anchises Analysis 0.4.0-beta.2 Release Notes

Anchises Analysis 0.4.0-beta.2 refines the plugin's export guidance while
keeping Hosted MCP 0.6.0, Data API 0.3.0, and export policy
`stock-data-export-v1` unchanged.

## Highlights

- Preserved the `anchises-analysis` slug, Anchises Analysis brand, Anchises
  Capital publisher, Developer Mode App ID, public URLs, credential-free
  access, 12-tool surface, and Prompt pack 5.1.
- Continued to use `export_policy.eligible_by_query` as the authoritative CSV
  gate without attempting to bypass backend policy.
- Replaced numeric-limit recitals in ordinary user-facing replies with a
  courteous explanation of the focused-research export workflow.
- Selected proposed CSV fields dynamically from the user's research question
  and the current `get_stock_schema` response instead of using a fixed target
  schema.
- Preserved complete-range server-side analysis when a row-level download is
  unavailable and offered a more focused export as the first alternative.
- Added conditional guidance for verified bulk-market-data APIs or licensed
  exchange-data vendors when the user still needs a complete file. Provider
  suggestions must match the requested market and data shape and are not
  endorsements.
- Kept the default temporary CSV lifetime at 60 minutes, with the existing
  explicit 60-through-3600-second setting supported by the backend.
- Prevented fabricated call counts, monthly limits, or reset dates; such
  details are shown only when returned by the service.

## Contract behavior

The Hosted MCP contract and its operational export thresholds are unchanged.
They remain internal request-construction guardrails and contract-test inputs,
while ordinary replies avoid mechanically listing every threshold. Complete
exchange-day partitions and SQL query IDs remain non-exportable, and no row
reconstruction or split-file workaround is permitted.

Company reports and stock analysis are informational, not official filings or
investment advice. Temporary CSV URLs are bearer capabilities and should not
be shared.
