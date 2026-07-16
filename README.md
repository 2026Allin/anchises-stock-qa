# Stock Data Desk Marketplace

<img src="plugins/stock-data-desk/assets/logo.png" alt="Stock Data Desk icon" width="96">

This repository contains the `Stock-Data-Desk` development marketplace and the
`Stock Data Desk` plugin package.

The `qa-v2-auth` branch connects the plugin to the Hosted MCP service and keeps
the plugin behavior independent from the backend's runtime mode name. The
current live snapshot uses credential-free `anonymous_dev`; the backend also
supports fail-closed and future OAuth operation. The product provides stock
screening, comparison, historical research, reports, and temporary CSV exports
in Work, ChatGPT, and Codex without a local database or credentials in chat.

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
Data API endpoints for `closed`, `anonymous_dev`, and `oauth`. It never calls
production services. An explicit, credential-free live contract check is
available with `RUN_LIVE_MCP_TESTS=1`.

## Development marketplace

The repository marketplace remains available for local development and
regression testing:

```bash
codex plugin marketplace add https://github.com/2026Allin/anchises-stock-qa
codex plugin add stock-data-desk@Stock-Data-Desk
```

The future public installation source is the universal Plugin Directory. Freeze
the intended public access profile and re-scan the real MCP descriptors before
submission; changing `noauth` to OAuth after publication requires a reviewed
plugin update.

## Design plan

See [`docs/hosted-mcp-oauth-migration-plan.md`](docs/hosted-mcp-oauth-migration-plan.md)
for historical architecture and rollout context. The checked-in contract and
the real MCP `tools/list` response are authoritative for plugin behavior.
