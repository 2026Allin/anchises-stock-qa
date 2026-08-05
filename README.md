# Anchises Analysis Marketplace

<img src="plugins/anchises-analysis/assets/logo.png" alt="Anchises Analysis logo" width="96">

This repository contains the `Anchises-Analysis` development marketplace and
the `anchises-analysis` plugin package published by Anchises Capital. The plugin
bundles five Skills and connects directly to the public Hosted MCP at
`https://mcp.anchisesdata.com/mcp`. It does not depend on a workspace-specific
Developer Mode App ID.

Current QA development target: `0.6.0-dev.5`. The submitted public-review
release remains `0.4.0-beta.2`.

## What changed in 0.6.0-dev.5

- Every selected Anchises Skill performs one schema-aware version check through
  `get_connection_status`; current, unknown, and failed checks stay silent.
- An available update adds one operational footer after the normal business
  answer. Installation requires an explicit Anchises Analysis update sentence;
  a bare “yes” or “install” never authorizes commands.
- The only updater performs one Git Marketplace preflight, upgrade, install,
  and verification sequence. It stops on local or mismatched sources and never
  tries an alternative command, uninstall, Git operation, config edit, retry,
  rollback, or force operation.
- This first supporting release still requires one manual install. Production
  MCP `0.7.1` does not yet publish client update metadata, so checks remain
  silently `unknown` until the MCP team deploys the documented `0.7.2`
  interface.

## What changed in 0.6.0-dev.4

- The Codex package now bundles one remote HTTP MCP definition in `.mcp.json`
  instead of referencing a Developer Mode App through `.app.json`.
- Local and cross-workspace Repo Marketplace installations load the same five
  Skills and MCP endpoint from one plugin package.
- A teammate can install from the public GitHub marketplace without creating
  an Anchises Analysis App ID or using workspace sharing.
- The former Developer Mode App may remain available as a short-term rollback
  resource, but it is not part of or required by this package.

## What changed for MCP 0.7.1

- `screen_stocks` and `run_readonly_sql` now use opaque cursor continuation;
  every call displays at most 200 rows and only an explicit user request
  advances to the next page.
- `top_n` bounds the complete logical ranked result independently of the
  current `page_size` display page.
- The service publishes a live restricted or bulk-enabled data policy.
  Export eligibility, allowed source tools, and limits are read dynamically,
  so an eligible screen or SQL query ID may be exported.
- Policy changes invalidate old cursors and query IDs; the Skill reruns the
  original intent instead of editing capabilities or using SQL `OFFSET`.
- Company reports keep the live Host-research workflow: resolve identity,
  prepare one sector prompt, research current sources, and answer only in the
  current conversation without MCP-side caching or upload.

## What changed in 0.6 development

- The plugin now exposes five peer Skills: a thin coordination entry plus
  dedicated Company Brief, Company Report, Company Comparison, and Market
  Analysis workflows.
- One canonical intent contract selects a single primary task before any
  specialist executes, so a downstream Skill cannot reinterpret the request.
- Only `company-report` may prepare the fixed seven-section live report;
  comparison and market analysis use their own bounded workflows.
- Every standalone multi-company introduction section is capped at five
  companies per response, regardless of the owning primary workflow. Market
  tables, rankings, and comparison matrices keep their own display limits.
- Successful substantive analysis uses one shared response-finalization
  contract for continuation and semantic questions.
- Each Skill uses the bundled Anchises Analysis MCP while preserving the same
  public-service access, privacy, and response contracts.

## What changed in 0.4

- The Hosted MCP contract is `0.6.0`, the Data API contract is `0.3.0`,
  and stock exports use policy `stock-data-export-v1`.
- Full matched ranges can participate in server-side filtering, statistics,
  ranking, and aggregation while the Host displays a bounded sorted preview.
- Stock-row previews have no next-page cursor and must not be reconstructed
  through split queries, changing sorts, or local stitching.
- CSV eligibility comes from the current `screen_stocks` export policy. Fields
  are selected dynamically from the research question and live schema; SQL
  query IDs and complete exchange-day partitions cannot be exported.
- When a complete row-level file is outside the export workflow, the Skill
  preserves in-session analysis and can suggest a verified bulk-data API or
  licensed exchange-data vendor suited to the requested market and fields.
- Company identity resolution and live Host-side company research remain
  unchanged from the 0.3 release.

## Repository layout

```text
.agents/plugins/marketplace.json
plugins/anchises-analysis/
  .codex-plugin/plugin.json
  .mcp.json
  assets/
  contracts/
  skills/
    anchises-analysis/
    company-brief/
    company-report/
    company-comparison/
    market-analysis/
tests/
docs/
```

The MCP URL, website, privacy, terms, and support endpoints remain unchanged.
This repository does not contain or modify the Hosted MCP service, AnchisesWeb,
or the Data API.

## Validate

```bash
.venv/bin/python -m unittest discover -s tests -v

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/anchises-analysis

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/company-brief

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/company-report

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/company-comparison

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/market-analysis

.venv/bin/python \
  ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/anchises-analysis
```

Run credential-free production checks explicitly:

```bash
RUN_LIVE_MCP_TESTS=1 \
  .venv/bin/python -m unittest tests.test_live_hosted_contract -v
```

## Local development install

The repo marketplace name is read from `.agents/plugins/marketplace.json`:

```bash
.venv/bin/python \
  ~/.codex/skills/.system/plugin-creator/scripts/read_marketplace_name.py \
  --marketplace-path .agents/plugins/marketplace.json

codex plugin add anchises-analysis@Anchises-Analysis
```

After changing plugin content, run the cachebuster helper before reinstalling
and start a new Codex task so the new Skill and MCP schema are loaded.

```bash
.venv/bin/python \
  ~/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py \
  plugins/anchises-analysis

.venv/bin/python \
  plugins/anchises-analysis/scripts/sync_client_release.py

.venv/bin/python \
  plugins/anchises-analysis/scripts/sync_client_release.py --check
```

The first command preserves the `0.6.0-dev.5` base and creates one new
`+codex.<timestamp>` suffix. The second copies that release ID into the client
metadata used by the Skill and MCP status call.

The automated in-Skill updater intentionally rejects this local development
Marketplace. Maintainers continue to use the manual cachebuster and reinstall
flow above.

## Cross-workspace Codex install

For QA from another OpenAI workspace, add the public Git marketplace with the
current QA ref and only the two required sparse paths:

```bash
codex plugin marketplace add \
  https://github.com/2026Allin/anchises-stock-qa.git \
  --ref qa-v2-auth \
  --sparse .agents/plugins \
  --sparse plugins/anchises-analysis

codex plugin add anchises-analysis@Anchises-Analysis
```

The equivalent desktop form uses the repository URL as **Source**,
`qa-v2-auth` as **Git ref**, and these two **Sparse paths**:

```text
.agents/plugins
plugins/anchises-analysis
```

This install does not use `Share with you`, Portal Scan, or a Developer Mode
App ID. A managed workspace may still require its administrator to allowlist
the Git marketplace source and the bundled MCP URL. Start a new Codex task
after installation.

After the MCP `0.7.2` client-update interface is deployed, a Git Marketplace
installation can detect newer QA releases during Anchises requests. It only
installs after the user explicitly authorizes the named Anchises Analysis
update. Local Marketplaces remain manual. See the
[MCP 0.7.2 handoff](docs/anchises-analysis-mcp-0.7.2-client-update-handoff.md).

See the complete
[cross-workspace installation guide](docs/anchises-analysis-codex-cross-workspace-install.md).

See [release notes](docs/anchises-analysis-0.4.0-beta.2-release-notes.md),
[Directory listing](docs/anchises-analysis-plugin-directory-listing.md), and
[reviewer cases](docs/anchises-analysis-reviewer-test-cases.md).
