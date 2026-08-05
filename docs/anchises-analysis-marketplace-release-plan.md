# Anchises Analysis Marketplace Release Plan

## Release target

- Plugin: `anchises-analysis`
- Skills: coordinator, Company Brief, Company Report, Company Comparison, and
  Market Analysis
- Display name: Anchises Analysis
- Publisher: Anchises Capital
- Version: `0.6.0-dev.4`
- Marketplace: `Anchises-Analysis`
- Hosted MCP: `0.7.1`
- Data API: `0.3.0`
- Internal contract: `1.7.0-draft`
- Data policy: dynamic `restricted` or `bulk_enabled`
- Prompt pack: `5.1`
- Tools: 12

The MCP URL, website, privacy, terms, support URL, MCP Python package name, and
VPS service names remain unchanged. The Codex package now bundles the remote
MCP definition directly and no longer references a Developer Mode App ID.

## Automated release gates

1. Plugin and Skill directories, names, and manifests agree. The package
   contains `.mcp.json`, declares `mcpServers`, contains no `.app.json`, and
   contains no `plugin_asdk_app` identifier.
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
11. Cachebuster update and local reinstall succeed; the installed plugin shows
    all five Skills and one `anchises_analysis` bundled MCP server.

## Cross-workspace Codex gates

1. From a Codex account in a different OpenAI workspace with no Anchises
   Developer Mode App, add the Git marketplace at `qa-v2-auth` and install
   `anchises-analysis@Anchises-Analysis`.
2. Confirm the plugin installs without an App ID, authentication credential,
   Portal Scan, or workspace share link.
3. Start a new task and confirm all five Skills are available.
4. Confirm `/mcp` shows the bundled `anchises_analysis` server and exactly 12
   production tools from MCP `0.7.1`.
5. Run representative Company Brief, Company Report, Company Comparison, and
   Market Analysis requests, including one cursor continuation and one dynamic
   export-policy case.
6. If the target workspace restricts custom marketplaces or plugin MCP
   servers, have its administrator allowlist the exact Git source, ref, plugin
   name, server name, and MCP URL before repeating the test.

## Future Plugin Directory gates

This Git Marketplace release does not use Portal Scan. If a later public
Plugin Directory release is requested, submit and scan the production MCP URL
directly rather than submitting the old Developer Mode App, then use the same
five-Skill bundle and public metadata.

## Rollback boundary

This release requires the MCP 0.7.1 / contract 1.7 surface. If production
discovery no longer shows exactly 12 tools, cursor pagination, dynamic data
and export policy fields, or four required report-preparation inputs, stop the
release rather than publishing against a mismatched schema.
