# Anchises Stock QA Marketplace

<img src="plugins/anchises-stock-qa/assets/logo.png" alt="Anchises Stock QA icon" width="96">

This repository contains the `Anchises-Tech` development marketplace and the
`Anchises Stock QA` plugin package.

The `qa-v2-auth` branch is preparing the plugin for a Hosted MCP service with
Auth0 OAuth 2.1 authentication. The target product provides read-only stock
screening, comparison, historical research, and temporary CSV exports in Work,
ChatGPT, and Codex. Approved users connect through hosted sign-in; the normal
workflow does not require a local database or credentials in chat.

## Repository layout

```text
.agents/plugins/marketplace.json
plugins/anchises-stock-qa/
  .codex-plugin/plugin.json
  .mcp.json                     # Phase 1 compatibility and rollback only
  contracts/
  skills/anchises-stock-qa/
  assets/
  README.md
tests/
  fixtures/
  mock_services.py
```

Phase 1 does not include `.app.json`. A real app reference will be added after
`https://mcp.anchisesdata.com/mcp` and the Auth0 production tenant have passed
end-to-end validation.

## Offline test suite

Use the plugin-managed Python environment because the legacy regression suite
also exercises its existing data-analysis dependencies:

```bash
plugins/anchises-stock-qa/.venv/bin/python -m unittest discover -s tests -v
```

The test suite starts loopback-only mock Auth0, Hosted MCP, and Stock Data API
endpoints. It never calls production services.

## Development marketplace

The repository marketplace remains available for local development and
regression testing:

```bash
codex plugin marketplace add https://github.com/2026Allin/anchises-stock-qa
codex plugin add anchises-stock-qa@Anchises-Tech
```

The future public installation source is the universal Plugin Directory. Do not
publish the Phase 1 branch or remove the compatibility MCP until the activation
phase has passed production OAuth and Hosted MCP validation.

## Design plan

See [`docs/hosted-mcp-oauth-migration-plan.md`](docs/hosted-mcp-oauth-migration-plan.md)
for the Auth0, SQLite, allowlist, rollout, review-account, and rollback design.
