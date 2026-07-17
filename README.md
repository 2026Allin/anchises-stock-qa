# Stocks Info Marketplace

<img src="plugins/stock-data-desk/assets/logo.png" alt="Stocks Info icon" width="96">

This repository contains the `Stock-Data-Desk` development marketplace and the
`Stocks Info` plugin package. The marketplace and plugin IDs remain stable for
upgrade compatibility; all user-visible product copy uses `Stocks Info`. The
verified publisher for the public listing is `Anchises Capital`.

The `qa-v2-auth` branch and the immutable `v0.2.0-beta.1` tag are the release
sources for the current beta; `main` intentionally remains unchanged. This
release connects the plugin to the Hosted MCP service and keeps plugin behavior
independent from the backend's runtime mode name. The current public release is
frozen to credential-free `public_noauth`: users do
not sign in, and quota represents shared service capacity rather than a
personal allowance. The product provides stock screening, comparison,
historical research, reports, and temporary CSV exports in Work, ChatGPT, and
Codex without a local database or credentials in chat.
CSV links default to a 60-minute lifetime and may be explicitly set from 60
through 3600 seconds.

## Repository layout

```text
.agents/plugins/marketplace.json
plugins/stock-data-desk/
  .codex-plugin/plugin.json
  .app.json                     # Hosted App connection
  contracts/
  skills/stock-data-desk/
  assets/
  README.md
tests/
  fixtures/
  mock_services.py
```

The development package is a single Hosted App plus one Skill. It does not ship
a local stdio MCP, API Token setup, or Python data runtime.

## Offline test suite

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
```

The default test suite starts loopback-only mock Auth0, Hosted MCP, and Stock
Data API endpoints for `closed`, `public_noauth`, and `oauth`. It never calls
production services. An explicit, credential-free live contract check is
available with `RUN_LIVE_MCP_TESTS=1`.

The OAuth profile is retained only as future compatibility coverage. Switching
production from `noauth` to OAuth requires a reviewed plugin update, fresh tool
scanning, and matching public documentation.

## Development marketplace

The repository marketplace remains available for local development and
regression testing:

```bash
codex plugin marketplace add https://github.com/2026Allin/anchises-stock-qa --ref v0.2.0-beta.1
codex plugin add stock-data-desk@Stock-Data-Desk
```

For branch-head testing before a tag is created, substitute
`--ref qa-v2-auth`. Installing without `--ref` reads the older `main` branch
and is not a valid beta-release verification.

The future public installation source is the universal Plugin Directory. The
submission must use the current credential-free profile; changing `noauth` to
OAuth after publication requires a reviewed plugin update.

## Design plan

See [`docs/hosted-mcp-oauth-migration-plan.md`](docs/hosted-mcp-oauth-migration-plan.md)
for historical architecture and rollout context. The checked-in contract and
the real MCP `tools/list` response are authoritative for plugin behavior.
