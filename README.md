# Stock Data Desk Marketplace

<img src="plugins/stock-data-desk/assets/logo.png" alt="Stock Data Desk icon" width="96">

This repository contains the `Stock-Data-Desk` development marketplace and the
`Stock Data Desk` plugin package.

The `qa-v2-auth` branch is preparing the plugin for a Hosted MCP service with
Auth0 OAuth 2.1 authentication. The target product provides read-only stock
screening, comparison, historical research, and temporary CSV exports in Work,
ChatGPT, and Codex. Approved users connect through hosted sign-in; the normal
workflow does not require a local database or credentials in chat.

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

The test suite starts loopback-only mock Auth0, Hosted MCP, and Stock Data API
endpoints. It never calls production services.

## Development marketplace

The repository marketplace remains available for local development and
regression testing:

```bash
codex plugin marketplace add https://github.com/2026Allin/anchises-stock-qa
codex plugin add stock-data-desk@Stock-Data-Desk
```

The future public installation source is the universal Plugin Directory. Do not
publish the current `anonymous_dev` build until production OAuth, allowlist
enforcement, and user-isolation validation are complete.

## Design plan

See [`docs/hosted-mcp-oauth-migration-plan.md`](docs/hosted-mcp-oauth-migration-plan.md)
for the Auth0, SQLite, allowlist, rollout, review-account, and rollback design.
