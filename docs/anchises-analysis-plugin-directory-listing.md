# Anchises Analysis Plugin Directory Listing

Submission-ready public copy for `Anchises Analysis 0.4.0-beta.2`.

## Identity

- Plugin name: Anchises Analysis
- Publisher: Anchises Capital
- Publisher email: `tech@anchisesgroup.com`
- Category: Productivity
- Primary listing locale: English (en)
- Version: 0.4.0-beta.2
- Hosted MCP: `https://mcp.anchisesdata.com/mcp`
- MCP version: 0.6.0
- Data API version: 0.3.0
- Export policy: `stock-data-export-v1`
- Authentication: not required

## Short description

Live company research and server-side stock-market analysis.

## Long description

Anchises Analysis combines source-linked live public-company research with structured stock-market analysis. It resolves a company name or ticker to a canonical exchange, ticker, and company name, verifies ambiguous or external listings with primary public sources, and prepares company research for the host to execute with live web search directly in the current conversation. The MCP service does not persist the resulting report. Full matched stock-data ranges can be used server-side for filtering, statistics, rankings, and aggregation; the conversation presents a bounded sorted preview and provides no subsequent row-level pages. Temporary CSV downloads are available only when a structured screen's current export policy marks it eligible, with fields selected from the live schema to match the user's research question; complete exchange-day partitions and raw SQL results remain analysis-only. Export eligibility is query-specific and does not use a market-percentage limit. Anchises structured stock data covers ASX, CSE, NASDAQ, NYSE, TSX, and TSXV; company research may cover verified companies outside those markets. Reports and market analysis are informational, not official filings or investment advice. Public access requires no Anchises Analysis account or credentials and has no account-linked cross-session cumulative budget; shared short-term service limits still apply. CSV URLs are short-lived bearer links and should not be shared.

## Starter prompts

1. Research Apple, verify its primary listing, and generate a fresh source-linked company report.
2. Analyze NYSE advance/decline counts, averages, and distributions using the full market.
3. Rank the NASDAQ Top 100 by dollar volume and export only the key research fields as CSV.

## Links

- Website: `https://anchisesdata.com/stock-qa`
- Privacy: `https://anchisesdata.com/privacy`
- Terms: `https://anchisesdata.com/terms`
- Support: `https://anchisesdata.com/support`
- Publisher website: `https://anchisesdata.com`
- Source repository: `https://github.com/2026Allin/anchises-stock-qa`

## Assets

- Logo: `plugins/anchises-analysis/assets/logo.png`
- Composer icon: `plugins/anchises-analysis/assets/composer-icon.png`
- Alt text: `Anchises Analysis logo`

Custom UI: None. Screenshots: None. Do not submit placeholder screenshots.

## Capability and data disclosures

- Public access is credential-free and uses shared service limits.
- Structured stock data covers ASX, CSE, NASDAQ, NYSE, TSX, and TSXV.
- A company name, ticker, or clear chat reference may start identity resolution.
- Ambiguous listings and share classes are not selected silently.
- Verified external-market companies may receive live public-source research,
  but not Anchises structured stock data.
- MCP prepares a prompt; the Host performs web research and writes the report.
- The final report remains in the current conversation and is not written back
  to MCP.
- Full matched stock-data ranges may be analyzed, filtered, ranked, and
  aggregated on the server.
- The Host displays a bounded sorted preview and does not provide later
  row-level pages.
- CSV eligibility is query-specific; complete exchange-day partitions and SQL
  results cannot be exported.
- CSV fields are selected from the current schema to match the user's research
  question rather than from a fixed template.
- When a complete row-level file is required, the Host may suggest a verified
  bulk-data API or licensed exchange-data vendor suited to the requested data.
- Public noauth access has no account-linked cross-session cumulative budget;
  shared short-term service limits still apply.
- Temporary CSV links default to 60 minutes and are bearer capabilities.
- Reports and market analysis are analytical information, not investment advice
  or official company disclosure.

## Production verification record

| Surface | Expected result |
|---|---|
| `/health` | HTTP 200; version 0.6.0; ready; public access; authentication not required |
| MCP initialize | Anchises Analysis 0.6.0 |
| `tools/list` | Exactly 12 noauth tools |
| Identity resolver | resolved / ambiguous / not_found_in_supported_markets |
| Report preparation | Four required inputs; Prompt pack 5.1; Host action |
| Stock rows | Full-range server analysis; bounded preview; no next-page cursor |
| CSV | Eligible structured screen with question-led fields; policy `stock-data-export-v1`; default 60 minutes |

## Portal notes

Submit and scan the production MCP URL directly. Do not submit the local
Developer Mode App as the public Directory target. Refresh the Developer Mode
App after the MCP schema change and test in a new task before submission.

Before submission, complete exact CSP validation even though this release has
no custom component UI.

- [x] Confirm `Anchises Capital` is selectable as the verified publisher.
- [x] Confirm the submitter has `Apps Management: Write`.
- [x] Select broad public availability in the live Portal.
- [x] Deploy and verify the Terms and Product-page changes.
