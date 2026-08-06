# Anchises Analysis Marketplace Release Plan

## Release target

- Plugin: `anchises-analysis`
- Canonical workflows: coordinator, Company Brief, Company Report, Company
  Comparison, and Market Analysis
- Codex visible Skills: all five canonical workflows
- Claude visible Skills: one self-contained `anchises-analysis` coordinator
- Display name: Anchises Analysis
- Publisher: Anchises Capital
- Codex version: `0.6.0-dev.9`
- Claude version: `0.6.0-dev.10`
- Codex Marketplace: `Anchises-Analysis`
- Claude Marketplace: `anchises-capital`
- Hosted MCP: version discovered dynamically from the MCP handshake
- Data API: `0.3.0`
- Internal capability contract: `1.9.0-draft`
- Bundled policy: shared maintainer-owned market-data switch
- Service policy: dynamic query and export capabilities
- Prompt pack: `5.1`
- Tools: 12

The MCP URL, website, privacy, terms, support URL, MCP Python package name, and
VPS service names remain unchanged. Codex and Claude reuse the same canonical
workflow core and remote MCP definition; Codex exposes five Skill entries
while Claude exposes one self-contained coordinator. Neither references a Developer Mode
App ID.

## Automated release gates

1. Plugin and Skill directories, names, and both platform manifests agree. The
   Codex manifest points to the canonical five-Skill directory. The root Claude
   manifest points directly to the self-contained coordinator root, the Claude Marketplace
   source is the repository root, and both manifests resolve to the same
   `.mcp.json`. The package contains no `.app.json` or `plugin_asdk_app`
   identifier.
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
   from the current rowset's dynamic export policy. The shared bundled switch
   never permits bypassing an actual service refusal through split queries.
8. Policy changes invalidate old cursors and query IDs; tests rerun the
   original intent and inspect the new policy.
9. CSV copy states a 60-minute default and a 60-3600 second explicit range.
10. Full unit/mock/live tests, Skill validation, and plugin validation pass.
11. Cachebuster update and local reinstall succeed; Codex shows all five Skills,
    Claude shows exactly one Skill, and each loads one `anchises_analysis`
    bundled MCP server.
12. Codex and Claude release metadata each match their manifest's base version
    and exactly one `+<platform>.<timestamp>` suffix.
13. A selected Codex Skill or the Claude coordinator checks exactly one platform
    namespace and does so once. Each fixed CLI updater refuses local or wrong
    sources, uses exactly five commands on the success path, and never retries
    or falls back.
14. The newest valid platform Tag, when one exists, points to the remote `main`
    head. Codex and Claude Tags never cross-trigger. Tag creation is a separate
    explicit maintainer action and never an automatic side effect of commit,
    push, merge, install, or update.
15. Structural guards prove the Claude root contains exactly one `SKILL.md`,
    all workflow/reference/script links remain inside that root, Codex keeps
    five entries, and `.mcp.json` plus the 12-tool Hosted MCP contract remain
    byte-for-byte unchanged.
16. Exactly one `references/plugin-policy.json` exists, both platforms load it
    through the shared global contract, ordinary users cannot override or see
    it, and invalid values fail release validation.
16. Diagnostic routing tests cover normal cache-first status, one-shot force
    refresh, check-only versus check-and-install, incidental health/status
    wording, independent service/plugin failures, and redaction of raw Git,
    server, commit, and credential details.

## Cross-workspace Codex gates

1. From a Codex account in a different OpenAI workspace with no Anchises
   Developer Mode App, add the Git marketplace at `main` and install
   `anchises-analysis@Anchises-Analysis`.
2. Confirm the plugin installs without an App ID, authentication credential,
   Portal Scan, or workspace share link.
3. Start a new task and confirm all five Skills are available.
4. Confirm `/mcp` shows the bundled `anchises_analysis` server and exactly 12
   production tools. Do not use HTTP `/health` as a plugin compatibility gate.
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

1. In Claude Code, first add `2026Allin/anchises-stock-qa@qa-v2-auth` using
   sparse paths `.claude-plugin` and `plugins/anchises-analysis`, then install
   `anchises-analysis@anchises-capital`.
2. Confirm Claude Code exposes exactly one `anchises-analysis` Skill, loads one
   `anchises_analysis` MCP server, and routes representative Brief, Report,
   Comparison, and Market requests into the unchanged canonical workflows.
   Confirm `/anchises-analysis 检查状态` loads every referenced file from the
   mounted Skill root and returns the Claude version rather than a file error.
3. After merging the tested commit to `main`, repeat installation from
   `2026Allin/anchises-stock-qa@main` and validate Claude Chat, Claude Desktop,
   and Cowork, whose repository UI uses the default branch rather than the QA
   ref.
4. Confirm a new Claude conversation performs at most one direct GitHub Tag
   lookup on its first substantive request when no persistent cache exists.
5. Validate the one-hour success TTL, ten-minute failure TTL, silent non-update
   states, final-footer placement, exact named authorization, and turn-local
   decline behavior.
6. In Claude Code on `main`, validate the fixed five-command CLI update and
   fail-closed source checks. In Chat, Desktop, and Cowork, confirm the plugin
   gives only the `Customize → Plugins → Anchises Analysis → Update` handoff
   and does not claim installation completed.
7. Start a new Claude conversation after every installation or update and
   verify the single visible Skill and exactly 12 MCP tools again.
8. In Codex and Claude, verify the same status entry reports service and
   plugin results independently, shows `current` explicitly, appends only the
   existing notice for an available update, and never installs from a
   check-only request.

## Future Plugin Directory gates

This Git Marketplace release does not use Portal Scan. If a later public
Plugin Directory release is requested, submit and scan the production MCP URL
directly rather than submitting the old Developer Mode App, then use the same
canonical workflow core, single Claude Skill, and public metadata.

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

- Implement and validate the self-contained Skill and diagnostics workflow on
  `qa-v2-auth`; do not publish a release Tag from the QA branch.
- Merge the tested release to `main` and push `main` only for a release.
- Publish Codex releases under `anchises-analysis/codex/v<semver>` and Claude
  releases under `anchises-analysis/claude/v<semver>`.
- Each platform Tag must identify the same commit as remote `main`; publishing
  one platform's Tag does not require publishing the other.
- Never create or push a tag unless the maintainer explicitly requests that
  release action.
