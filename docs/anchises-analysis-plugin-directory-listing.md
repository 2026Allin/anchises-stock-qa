# Anchises Analysis Plugin Directory Listing

Current QA directory copy for `Anchises Analysis 0.6.0-dev.3`.

## Identity

- Plugin name: Anchises Analysis
- Publisher: Anchises Capital
- Publisher email: `tech@anchisesgroup.com`
- Category: Productivity
- Primary listing locale: English (en)
- Version: 0.6.0-dev.3
- Hosted MCP: `https://mcp.anchisesdata.com/mcp`
- MCP version: 0.7.1
- Data API version: 0.3.0
- Contract version: `1.7.0-draft`
- Data policy: dynamic `restricted` or `bulk_enabled`
- Authentication: not required

## Short description

Live company research and server-side stock-market analysis.

## Long description

Anchises Analysis combines source-linked live public-company research with structured stock-market analysis. It resolves a company name or ticker to a canonical exchange, ticker, and company name, verifies ambiguous or external listings with primary public sources, and prepares company research for the host to execute with live web search directly in the current conversation. The MCP service does not persist the resulting report. Full matched stock-data ranges can be used server-side for filtering, statistics, rankings, and aggregation; each call displays at most 200 rows and can continue through an opaque cursor only when the user asks for the next page. Top-N bounds the complete logical ranked result rather than the current display page. Temporary CSV downloads follow the live restricted or bulk-enabled data policy: eligibility, allowed screen or SQL source tools, and hard limits are returned for each query. Restricted mode never reconstructs refused datasets through split queries. Anchises structured stock data covers ASX, CSE, NASDAQ, NYSE, TSX, and TSXV; company research may cover verified companies outside those markets. Reports and market analysis are informational, not official filings or investment advice. Public access requires no Anchises Analysis account or credentials and has no account-linked cross-session cumulative budget; shared short-term service limits still apply. CSV URLs are short-lived bearer links and should not be shared.

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
- The Host displays at most 200 rows per call and fetches a returned opaque
  cursor only when the user explicitly asks for the next page.
- Top-N controls the complete logical result independently of the current
  display page.
- CSV eligibility, allowed screen or SQL source tools, and limits come from
  the current restricted or bulk-enabled policy.
- Policy changes invalidate old cursors and query IDs; the original intent is
  rerun without SQL `OFFSET` or capability editing.
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
| `/health` | HTTP 200; version 0.7.1; ready; public access; authentication not required |
| MCP initialize | Anchises Analysis 0.7.1 |
| `tools/list` | Exactly 12 noauth tools |
| Identity resolver | resolved / ambiguous / not_found_in_supported_markets |
| Report preparation | Four required inputs; Prompt pack 5.1; Host action |
| Stock rows | Full-range server analysis; at most 200 rows per page; opaque cursor continuation |
| CSV | Eligible screen or SQL query under the live dynamic policy; default 60 minutes |

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
