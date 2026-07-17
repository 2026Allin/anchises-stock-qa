# Anchises Analysis Marketplace

<img src="plugins/anchises-analysis/assets/logo.png" alt="Anchises Analysis logo" width="96">

This repository contains the `Anchises-Analysis` development marketplace and
the `anchises-analysis` plugin package published by Anchises Capital. The plugin
connects to the public Hosted MCP at `https://mcp.anchisesdata.com/mcp` through
the existing Developer Mode App ID.

Current release target: `0.3.0-beta.1`.

## What changed in 0.3

- Public brand, plugin slug, Skill name, and directories are now Anchises
  Analysis / `anchises-analysis`.
- Company names, tickers, and chat references resolve to a canonical exchange,
  ticker, and company name before downstream calls.
- Every company-research request starts live Host web research directly.
- The Hosted MCP contract is `0.5.1`, uses Prompt pack `5.1`, and exposes 12
  tools including `resolve_company_identity`.
- Structured stock data covers ASX, CSE, NASDAQ, NYSE, TSX, and TSXV. Verified
  companies outside those markets may still receive live public-source research.

## Repository layout

```text
.agents/plugins/marketplace.json
plugins/anchises-analysis/
  .codex-plugin/plugin.json
  .app.json
  assets/
  contracts/
  skills/anchises-analysis/
tests/
docs/
```

The App ID value, MCP URL, website, privacy, terms, and support endpoints remain
unchanged. This repository does not contain or modify the Hosted MCP service,
AnchisesWeb, or the Data API.

## Validate

```bash
.venv/bin/python -m unittest discover -s tests -v

.venv/bin/python \
  ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  plugins/anchises-analysis/skills/anchises-analysis

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

See [release notes](docs/anchises-analysis-0.3.0-beta.1-release-notes.md),
[Directory listing](docs/anchises-analysis-plugin-directory-listing.md), and
[reviewer cases](docs/anchises-analysis-reviewer-test-cases.md).
