# Anchises Analysis Marketplace Release Plan

## Release target

- Plugin: `anchises-analysis`
- Skills: coordinator, Company Brief, Company Report, Company Comparison, and
  Market Analysis
- Display name: Anchises Analysis
- Publisher: Anchises Capital
- Version: `0.6.0-dev.3`
- Marketplace: `Anchises-Analysis`
- Hosted MCP: `0.7.1`
- Data API: `0.3.0`
- Internal contract: `1.7.0-draft`
- Data policy: dynamic `restricted` or `bulk_enabled`
- Prompt pack: `5.1`
- Tools: 12

The Developer Mode App ID, MCP URL, website, privacy, terms, support URL, MCP
Python package name, and VPS service names remain unchanged.

## Automated release gates

1. Plugin and Skill directories, names, and manifests agree.
2. `agents/openai.yaml` explicitly invokes `$anchises-analysis`.
3. The checked-in live snapshot contains exactly 12 tools, including
   `resolve_company_identity`; both row tools accept opaque cursor
   continuation and publish `string | null` `next_cursor` values.
4. Company-name, ticker-only, contextual, ambiguous, share-class, external,
   inactive/delisted, Fund, no-web, privacy, and hidden-prompt scenarios pass.
5. Structured data is never claimed outside ASX, CSE, NASDAQ, NYSE, TSX, and
   TSXV.
6. Market Analysis distinguishes logical `top_n` from the current
   `page_size/max_rows`, displays no more than 200 rows per call, and follows
   `pagination_next_action` without speculative page traversal or SQL
   `OFFSET`.
7. CSV eligibility, allowed screen or SQL source tools, and limits come only
   from the current rowset's dynamic export policy. Restricted mode never
   splits fields, dates, filters, or partitions to reconstruct a dataset.
8. Policy changes invalidate old cursors and query IDs; tests rerun the
   original intent and inspect the new policy.
9. CSV copy states a 60-minute default and a 60-3600 second explicit range.
10. Full unit/mock/live tests, Skill validation, and plugin validation pass.
11. Cachebuster update and local reinstall succeed.

## Manual Portal and Developer Mode gates

1. Refresh the existing Developer Mode App so it discovers the 0.7.1 schemas.
2. Confirm the App ID value did not change; record the newly generated Version
   ID if the Portal creates one.
3. Test from a new task to avoid prior Skill or descriptor state.
4. Verify public name, publisher, logo alt text, starter prompts, website,
   Privacy, Terms, and support URLs.
5. Submit and scan the production MCP URL directly for the Directory listing.
6. Run all reviewer cases and capture current evidence.

## Rollback boundary

This release requires the MCP 0.7.1 / contract 1.7 surface. If production
discovery no longer shows exactly 12 tools, cursor pagination, dynamic data
and export policy fields, or four required report-preparation inputs, stop the
release rather than publishing against a mismatched schema.
