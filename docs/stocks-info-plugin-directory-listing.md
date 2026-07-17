# Stocks Info Plugin Directory Listing

Submission-ready public copy for `Stocks Info 0.2.0-beta.1`.

Last verified: July 16, 2026.

## Info

```text
Plugin name: Stocks Info
Publisher / Developer Identity: Anchises Capital
Category: Productivity
Primary listing locale: English (en)
Website: https://anchisesdata.com/stock-qa
Support: https://anchisesdata.com/support
Privacy Policy: https://anchisesdata.com/privacy
Terms of Service: https://anchisesdata.com/terms
Support email: tech@anchisesgroup.com
```

### Short description

```text
Research public companies and analyze stock-market data.
```

### Long description

```text
Stocks Info provides public-company research and stock-market analysis across supported exchanges. Retrieve cached English AI-generated company reports and PDFs; cache status may be active, expired, or not found. When a report is missing or expired, users can confirm source-linked live web research that stays only in the current conversation and is not uploaded, cached, saved, or converted into a cached PDF. Discover exchanges and current data dates, screen and rank stocks, inspect schemas, run bounded read-only SQL, compare historical price, momentum, and volume, and export completed queries to temporary CSV files. Reports are analytical research, not official filings or investment advice. Stocks Info offers credential-free public access: no Stocks Info account or credentials are required, and all users use shared service limits. CSV URLs are short-lived bearer links and should not be shared.
```

## Availability

OpenAI's public ChatGPT support page listed 208 supported countries, regions,
and territories on July 16, 2026. The plugin portal does not document a
permanent static Marketplace list, so the live `Global` tab remains the source
of truth for selectable locations.

The complete dated planning snapshot and approved release decision are in
`docs/openai-plugin-availability-regions-2026-07-16.md`.

Approved for `0.2.0-beta.1`: broad public availability. Select every country
or region offered by the live portal, including the Americas, Europe,
Southeast Asia, East Asia, Africa, Oceania, and other supported locations.
Do not restrict the release to English-first countries, and do not add
locations that the portal does not offer.

## MCP

```text
Submission type: With MCP, app plus skills
MCP server type: Universal
Production MCP URL: https://mcp.anchisesdata.com/mcp
Authentication: None
Developer Mode App ID: Do not submit
Custom UI: None
Screenshots: None
```

The submission must scan the production MCP URL directly. Do not enter the
Developer Mode App ID from `.app.json`.

The app has no custom UI or linked UI resource. OpenAI's current submission
guidance says not to provide screenshots for an app without UI.

### CSP review

Use only exact origins that are required by the live service:

```text
https://mcp.anchisesdata.com
https://anchisesdata.com
```

The MCP origin serves the protocol endpoint and temporary CSV downloads.
`anchisesdata.com` serves report PDFs and the public product and policy pages.
Do not add wildcard domains or future OAuth origins. Confirm the final CSP
shape in the submission portal after `Scan Tools`; if the portal requires
server-advertised CSP metadata, update the MCP server and rescan.

## Logo

Upload:

```text
plugins/stock-data-desk/assets/logo.png
```

Verified properties:

```text
Format: PNG
Dimensions: 512 x 512
Color: RGB
Alpha channel: No
SHA-256: de6c611c6c88de224b0d52bc9b03d6a62b1de807bd5c2452fa82031260a815b7
```

The bundled composer icon is:

```text
plugins/stock-data-desk/assets/composer-icon.png
Dimensions: 128 x 128
SHA-256: a3070135807ac135ebb373669b646a126a10eb9e9028827a1bdec552a36c0564
```

## Starter prompts

```text
Research NASDAQ:AAPL. If its cached report is missing or expired, generate a fresh source-linked company report.
```

```text
Research ASX:BGL, then compare its latest 30-day price and volume trends using clearly dated market data.
```

```text
Screen the latest data for strong momentum and unusual volume, rank the results across exchanges, and export them as CSV.
```

All three prompts are English and remain below the 128-character manifest
limit.

## Release notes

```text
Initial public beta release of Stocks Info.

Stocks Info provides credential-free public-company research, stock screening,
historical comparison, bounded read-only SQL, cached English AI-generated
company reports and PDFs, source-linked live research when a cached report is
missing or expired, and temporary CSV exports.

This release bundles one complete workflow Skill with the production Stocks
Info MCP service. Public access requires no Stocks Info account or credentials
and uses shared service limits. Live research remains only in the current
conversation and is not uploaded, cached, saved to a database, or converted
into a cached PDF.
```

The longer repository release record remains in
`docs/stocks-info-0.2.0-beta.1-release-notes.md`.

## Public URL audit

The following pages returned HTTPS 200 on July 16, 2026:

| Field | URL | Reachability | Content review |
|---|---|---:|---|
| Website | `https://anchisesdata.com/stock-qa` | 200 | Ready; live-research workflow verified |
| Support | `https://anchisesdata.com/support` | 200 | Ready |
| Privacy | `https://anchisesdata.com/privacy` | 200 | Ready; optional clarification remains below |
| Terms | `https://anchisesdata.com/terms` | 200 | Ready; host-side workflow verified |
| MCP | `https://mcp.anchisesdata.com/mcp` | 200 on initialize | Ready; server `Stocks Info` 0.4.4 |

### Verified Terms disclosure

The deployed Terms remove the old on-demand-generation contradiction and
provide an equivalent disclosure to this review target:

```text
Company reports available through Stocks Info are AI-generated analysis.
Cached reports may be active, expired, or unavailable. When a cached report is
missing or expired and the user confirms, the host may perform source-linked
live web research in the current conversation. Live research is not uploaded
to Stocks Info, cached, saved to a database, or converted into a cached PDF.
Reports are not official company filings, audited statements, or issuer
communications. Verify important information against authoritative sources.
```

### Verified Product-page disclosure

The deployed Product page now provides an equivalent disclosure to this review
target:

```text
Retrieve cached AI-generated company analysis and report PDFs. When a cached
report is missing or expired, Stocks Info can prepare source-linked live web
research after user confirmation. Live research stays only in the current
conversation and is not saved by Stocks Info.
```

### Optional Privacy enhancement

Add under task-specific tool arguments:

```text
Fresh company-report preparation processes the requested exchange, ticker, and
output locale and returns a research instruction to the client. Stocks Info
does not receive or store the host's web-search results or the final live
report produced in the conversation.
```

## Submission confirmations

Required before submission:

- [x] Select broad public availability: every country or region offered by the
      live submission portal.
- [x] Confirm `Anchises Capital` is selectable as the verified Developer
      Identity in the submitting OpenAI Platform organization.
- [x] Confirm the submitter has `Apps Management: Write`.
- [x] Confirm the Product, Privacy, and Terms URLs exist and are publicly
      reachable.
- [x] Deploy and verify the Terms and Product-page changes above.
- [ ] Run `Scan Tools` and resolve the portal's exact CSP validation for this
      no-UI app.

Optional improvement:

- [ ] Add the explicit Privacy clarification above. The deployed policy already
      discloses the preparation fields and separate host processing.

## Portal handoff

After the external confirmations are complete:

1. Create a `With MCP` plugin draft.
2. Enter `https://mcp.anchisesdata.com/mcp` and choose no authentication.
3. Complete domain verification if prompted.
4. Scan and review all 12 tools, server instructions, schemas, security
   schemes, and annotations.
5. Upload the final single-Skill bundle.
6. Paste the listing copy and three starter prompts from this file.
7. Add the stage-six five positive and three negative reviewer cases.
8. In `Global`, select every country or region offered by the portal and
   review the resulting list.
9. Paste the release notes and complete policy attestations.
10. Submit for review; after approval, publish manually.
