# Anchises Analysis Marketplace Release Plan

## Release target

- Plugin: `anchises-analysis`
- Skills: coordinator, Company Brief, Company Report, Company Comparison, and
  Market Analysis
- Display name: Anchises Analysis
- Publisher: Anchises Capital
- Version: `0.6.0-dev.8`
- Codex Marketplace: `Anchises-Analysis`
- Claude Marketplace: `anchises-capital`
- Hosted MCP: version discovered dynamically from the MCP handshake
- Data API: `0.3.0`
- Internal capability contract: `1.9.0-draft`
- Data policy: dynamic `restricted` or `bulk_enabled`
- Prompt pack: `5.1`
- Tools: 12

The MCP URL, website, privacy, terms, support URL, MCP Python package name, and
VPS service names remain unchanged. Codex and Claude install the same five-Skill
package and remote MCP definition; neither references a Developer Mode App ID.

## Automated release gates

1. Plugin and Skill directories, names, and both platform manifests agree. The
   package contains `.mcp.json`, both manifests declare `mcpServers`, the Claude
   Marketplace points to the same plugin directory, and the package contains
   no `.app.json` or `plugin_asdk_app` identifier.
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
12. Codex and Claude release metadata each match their manifest's base version
    and exactly one `+<platform>.<timestamp>` suffix.
13. Five-Skill update checks select exactly one platform namespace and are
    single-call. Each fixed CLI updater refuses local or wrong sources, uses
    exactly five commands on the success path, and never retries or falls back.
14. The newest valid platform Tag, when one exists, points to the remote `main`
    head. Codex and Claude Tags never cross-trigger. Tag creation is a separate
    explicit maintainer action and never an automatic side effect of commit,
    push, merge, install, or update.
15. Hash guards prove that the five business `SKILL.md` files, non-update
    business references, Codex UI metadata, `.mcp.json`, and the 12-tool Hosted
    MCP contract remain byte-for-byte unchanged by the Claude adapter.

## Cross-workspace Codex gates

1. From a Codex account in a different OpenAI workspace with no Anchises
   Developer Mode App, add the Git marketplace at `main` and install
   `anchises-analysis@Anchises-Analysis`.
2. Confirm the plugin installs without an App ID, authentication credential,
   Portal Scan, or workspace share link.
3. Start a new task and confirm all five Skills are available.
4. Confirm `/mcp` shows the bundled `anchises_analysis` server, exactly 12
   production tools, and a semantic server version matching `/health`.
5. Run representative Company Brief, Company Report, Company Comparison, and
   Market Analysis requests, including one cursor continuation and one dynamic
   export-policy case.
6. If the target workspace restricts custom marketplaces or plugin MCP
   servers, have its administrator allowlist the exact Git source, ref, plugin
   name, server name, and MCP URL before repeating the test.
7. Install `0.6.0-dev.6` manually as the bootstrap release. Validate one silent
   current tag check, one update reminder, one explicitly authorized update,
   and the required new-task message.

## Cross-surface Claude gates

1. Add `2026Allin/anchises-stock-qa@main` as a Claude Marketplace using sparse
   paths `.claude-plugin` and `plugins/anchises-analysis`, then install
   `anchises-analysis@anchises-capital`.
2. Confirm the same five Skills and one `anchises_analysis` MCP server load in
   Claude Code, Claude Chat, Claude Desktop, and Cowork where custom
   Marketplaces are allowed.
3. Confirm a new Claude conversation performs at most one direct GitHub Tag
   lookup on its first substantive request when no persistent cache exists.
4. Validate the one-hour success TTL, ten-minute failure TTL, silent non-update
   states, final-footer placement, exact named authorization, and turn-local
   decline behavior.
5. In Claude Code, validate the fixed five-command CLI update and fail-closed
   source checks. In Chat, Desktop, and Cowork, confirm the plugin gives only
   the `Customize → Plugins → Anchises Analysis → Update` handoff and does not
   claim installation completed.
6. Start a new Claude conversation after every installation or update and
   verify all five Skills and exactly 12 MCP tools again.

## Future Plugin Directory gates

This Git Marketplace release does not use Portal Scan. If a later public
Plugin Directory release is requested, submit and scan the production MCP URL
directly rather than submitting the old Developer Mode App, then use the same
five-Skill bundle and public metadata.

## Rollback boundary

This release requires capability profile `1.9.0-draft`, not a fixed MCP
semantic version. If production discovery no longer shows exactly 12 tools,
cursor pagination, dynamic data and export policy fields, service-only
connection status, or four required report-preparation inputs, stop the
release rather than publishing against a mismatched schema.

Plugin release discovery is deliberately separate from MCP. The Hosted MCP
snapshot records the observed handshake version for diagnostics, but contract
comparison ignores that value and Skills call status with `{}` only for
service access. A service-only update does not require a plugin release when
the capability contract remains compatible.

## Branch and tag release boundary

- Develop this adapter on `codex/claude-client-adapter`, based on
  `qa-v2-auth`, then merge its validated result back to `qa-v2-auth`.
- Merge the tested release to `main` and push `main` only for a release.
- Publish Codex releases under `anchises-analysis/codex/v<semver>` and Claude
  releases under `anchises-analysis/claude/v<semver>`.
- Each platform Tag must identify the same commit as remote `main`; publishing
  one platform's Tag does not require publishing the other.
- Never create or push a tag unless the maintainer explicitly requests that
  release action.
