# Anchises Analysis Plugin Directory Listing

Submission-ready public copy for `Anchises Analysis 0.3.0-beta.1`.

## Identity

- Plugin name: Anchises Analysis
- Publisher: Anchises Capital
- Publisher email: `tech@anchisesgroup.com`
- Category: Productivity
- Primary listing locale: English (en)
- Version: 0.3.0-beta.1
- Hosted MCP: `https://mcp.anchisesdata.com/mcp`
- MCP version: 0.5.1
- Authentication: not required

## Short description

Live company research and structured stock-market analysis.

## Long description

Anchises Analysis combines source-linked live public-company research with structured stock-market analysis. It resolves a company name or ticker to a canonical exchange, ticker, and company name, verifies ambiguous or external listings with primary public sources, and prepares company research for the host to execute with live web search directly in the current conversation. The MCP service does not persist the resulting report. Discover supported exchanges and current data dates, screen and rank stocks, inspect schemas, run bounded read-only SQL, compare historical price, momentum, and volume, and create temporary CSV exports. Anchises structured stock data covers ASX, CSE, NASDAQ, NYSE, TSX, and TSXV; company research may cover verified companies outside those markets. Reports are analytical research, not official filings or investment advice. Public access requires no Anchises Analysis account or credentials, and all callers use shared service limits. CSV URLs are short-lived bearer links and should not be shared.

## Starter prompts

1. Research Apple, verify its primary listing, and generate a fresh source-linked company report.
2. Research the company discussed above, then analyze its latest 30-day price and volume trends.
3. Screen supported exchanges for strong momentum and unusual volume, then export the ranked results as CSV.

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
- Temporary CSV links default to 60 minutes and are bearer capabilities.
- Reports and market analysis are analytical information, not investment advice
  or official company disclosure.

## Production verification record

| Surface | Expected result |
|---|---|
| `/health` | HTTP 200; version 0.5.1; ready; public access; authentication not required |
| MCP initialize | Anchises Analysis 0.5.1 |
| `tools/list` | Exactly 12 noauth tools |
| Identity resolver | resolved / ambiguous / not_found_in_supported_markets |
| Report preparation | Four required inputs; Prompt pack 5.1; Host action |
| CSV | Default 60 minutes; explicit 60-3600 seconds |

## Portal notes

Submit and scan the production MCP URL directly. Do not submit the local
Developer Mode App as the public Directory target. Refresh the Developer Mode
App after the MCP tool-set change and test in a new task before submission.

Before submission, complete exact CSP validation even though this release has
no custom component UI.

- [x] Confirm `Anchises Capital` is selectable as the verified publisher.
- [x] Confirm the submitter has `Apps Management: Write`.
- [x] Select broad public availability in the live Portal.
- [x] Deploy and verify the Terms and Product-page changes.
