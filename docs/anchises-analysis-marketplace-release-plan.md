# Anchises Analysis Marketplace Release Plan

## Release target

- Plugin: `anchises-analysis`
- Skill: `anchises-analysis` / `$anchises-analysis`
- Display name: Anchises Analysis
- Publisher: Anchises Capital
- Version: `0.3.0-beta.1`
- Marketplace: `Anchises-Analysis`
- Hosted MCP: `0.5.1`
- Prompt pack: `5.1`
- Tools: 12

The Developer Mode App ID, MCP URL, website, privacy, terms, support URL, MCP
Python package name, and VPS service names remain unchanged.

## Automated release gates

1. Plugin and Skill directories, names, and manifests agree.
2. `agents/openai.yaml` explicitly invokes `$anchises-analysis`.
3. The checked-in live snapshot contains exactly 12 tools, including
   `resolve_company_identity`, and the preparation schema requires exchange,
   ticker, company name, and output locale.
4. Company-name, ticker-only, contextual, ambiguous, share-class, external,
   inactive/delisted, Fund, no-web, privacy, and hidden-prompt scenarios pass.
5. Structured data is never claimed outside ASX, CSE, NASDAQ, NYSE, TSX, and
   TSXV.
6. CSV copy states a 60-minute default and a 60-3600 second explicit range.
7. Full unit/mock/live tests, Skill validation, and plugin validation pass.
8. Cachebuster update and local reinstall succeed.

## Manual Portal and Developer Mode gates

1. Refresh the existing Developer Mode App so it discovers the 0.5.1 tool set.
2. Confirm the App ID value did not change; record the newly generated Version
   ID if the Portal creates one.
3. Test from a new task to avoid prior Skill or descriptor state.
4. Verify public name, publisher, logo alt text, starter prompts, website,
   Privacy, Terms, and support URLs.
5. Submit and scan the production MCP URL directly for the Directory listing.
6. Run all reviewer cases and capture current evidence.

## Rollback boundary

The 0.3 plugin requires the MCP 0.5 contract. If production discovery no longer
shows the expected 12 tools or four required preparation inputs, stop the
release rather than publishing against a mismatched schema.
