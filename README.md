# Anchises Analysis Marketplace

<img src="plugins/anchises-analysis/assets/logo.png" alt="Anchises Analysis logo" width="96">

This repository contains the `Anchises-Analysis` development marketplace and
the `anchises-analysis` plugin package published by Anchises Capital. The plugin
connects to the public Hosted MCP at `https://mcp.anchisesdata.com/mcp` through
the existing Developer Mode App ID.

Current QA development target: `0.6.0-dev.3`. The submitted public-review
release remains `0.4.0-beta.2`.

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
- Local QA now uses Developer Mode App
  `asdk_app_6a5a007aa5bc8191bbb5409005af37a6`.

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
  .app.json
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

See [release notes](docs/anchises-analysis-0.4.0-beta.2-release-notes.md),
[Directory listing](docs/anchises-analysis-plugin-directory-listing.md), and
[reviewer cases](docs/anchises-analysis-reviewer-test-cases.md).
