# Anchises Analysis Marketplace Release Plan

## Release target

- Plugin: `anchises-analysis`
- Skills: coordinator, Company Brief, Company Report, Company Comparison, and
  Market Analysis
- Display name: Anchises Analysis
- Publisher: Anchises Capital
- Version: `0.6.0-dev.6`
- Marketplace: `Anchises-Analysis`
- Hosted MCP: `0.7.2`
- Data API: `0.3.0`
- Internal contract: `1.8.0-draft`
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
12. Plugin release metadata matches the manifest's base version and single
    `+codex.<timestamp>` suffix.
13. Five-Skill update checks use the Codex Git tag namespace and are
    single-call. The fixed
    updater refuses local or wrong sources, uses exactly five CLI calls on the
    success path, and never retries or falls back.
14. The newest valid Codex tag, when one exists, points to the remote `main`
    head. Tag creation is a separate explicit maintainer action and never an
    automatic side effect of commit, push, merge, install, or update.

## Cross-workspace Codex gates

1. From a Codex account in a different OpenAI workspace with no Anchises
   Developer Mode App, add the Git marketplace at `main` and install
   `anchises-analysis@Anchises-Analysis`.
2. Confirm the plugin installs without an App ID, authentication credential,
   Portal Scan, or workspace share link.
3. Start a new task and confirm all five Skills are available.
4. Confirm `/mcp` shows the bundled `anchises_analysis` server and exactly 12
   production tools from MCP `0.7.2`.
5. Run representative Company Brief, Company Report, Company Comparison, and
   Market Analysis requests, including one cursor continuation and one dynamic
   export-policy case.
6. If the target workspace restricts custom marketplaces or plugin MCP
   servers, have its administrator allowlist the exact Git source, ref, plugin
   name, server name, and MCP URL before repeating the test.
7. Install `0.6.0-dev.6` manually as the bootstrap release. Validate one silent
   current tag check, one update reminder, one explicitly authorized update,
   and the required new-task message.

## Future Plugin Directory gates

This Git Marketplace release does not use Portal Scan. If a later public
Plugin Directory release is requested, submit and scan the production MCP URL
directly rather than submitting the old Developer Mode App, then use the same
five-Skill bundle and public metadata.

## Rollback boundary

This release requires the MCP 0.7.2 / contract 1.8 surface. If production
discovery no longer shows exactly 12 tools, cursor pagination, dynamic data
and export policy fields, or four required report-preparation inputs, stop the
release rather than publishing against a mismatched schema.

Plugin release discovery is deliberately separate from MCP. The Hosted MCP
snapshot records its optional compatibility metadata, but Skills call status
with `{}` and ignore `client_update` for plugin releases. A service-only update
does not require a plugin release when the tool contract remains compatible.

## Branch and tag release boundary

- Develop and validate on `qa-v2-auth`.
- Merge the tested release to `main` and push `main` only for a release.
- Publish Codex releases under `anchises-analysis/codex/v<semver>`; reserve a
  separate `anchises-analysis/claude/v<semver>` namespace for Claude.
- A Codex tag must identify the same commit as remote `main`.
- Never create or push a tag unless the maintainer explicitly requests that
  release action.
