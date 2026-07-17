# Stocks Info

Stocks Info is a single-skill plugin for company research, stock screening,
historical comparison, read-only SQL, cached English AI company reports,
host-side live report generation, and temporary CSV exports across Work,
ChatGPT, and Codex.

## Release package

- Public beta version: `0.2.0-beta.1`
- Public product name: `Stocks Info`
- Verified publisher: `Anchises Capital`
- Internal plugin ID: `stock-data-desk`
- Repo Marketplace ID: `Stock-Data-Desk`
- Support: `tech@anchisesgroup.com`
- Website: `https://anchisesdata.com/stock-qa`
- Support page: `https://anchisesdata.com/support`
- Privacy policy: `https://anchisesdata.com/privacy`
- Terms: `https://anchisesdata.com/terms`

The public beta version is a clean semantic version without a local Codex
cachebuster. Future bug-fix and feature releases must use a new semantic
version instead of changing the contents of an already published version.

`Stocks Info` is the product name. `Anchises Capital` is the verified publisher
and developer identity used for the public listing.

## Repo Marketplace App wiring

The `qa-v2-auth` branch and `v0.2.0-beta.1` tag contain the Developer Mode App
wiring used by local and Repo Marketplace installations:

- Hosted MCP: `https://mcp.anchisesdata.com/mcp`
- Plugin display name: `Stocks Info`
- Developer Mode App: `Stock Data Desk Dev`
- Plugin App ID: `plugin_asdk_app_6a58a0d4059c8191a6a06438e698154a`
- App connector ID: `asdk_app_6a58a0d4059c8191a6a06438e698154a`
- App version ID: `asdk_app_v_6a58a0dd4d7081918a73fd2c41c097ad`
- Current contract snapshot mode: `public_noauth`
- Current tool security profile: 12 credential-free `noauth` tools
- Current limits: shared service capacity, not per-user allowance

The plugin package is now Hosted App-only: `.app.json` connects the App and the
single bundled Skill supplies workflow guidance. The package contains no local
stdio MCP, Python bootstrap, API Token setup, or local database runtime.

The current public release is frozen to credential-free access. The Skill does
not ask users to sign in and treats quota as shared global service capacity. An
unexpected authentication challenge is a contract transition or availability
problem for this release, not an instruction to start a login flow.

The contract harness retains `closed` and future OAuth profiles for regression
coverage only. Enabling OAuth in a later production version requires a reviewed
plugin update, new tool scanning, and matching public documentation.

The `.app.json` Developer Mode App reference is used only by local and Repo
Marketplace installations. A public Plugin Directory submission must not reuse
that App ID as the submission target. It must submit and scan the production
MCP URL directly, then upload the same final Skill bundle tested in this
package.

## Hosted contract

The checked-in target snapshot is based on the public Hosted MCP `tools/list`:

```text
contracts/hosted-mcp-v1.json
contracts/hosted_contract.py
contracts/sync_hosted_contract.py
```

The snapshot records its normalized descriptor SHA-256. Refresh or compare it
without changing the backend:

```bash
.venv/bin/python \
  plugins/stock-data-desk/contracts/sync_hosted_contract.py --check
```

The published 0.4.x contract now records `source.sync_state=live`. The sync
command captures the server initialization instructions as well as all tool
descriptors, so `--check` detects drift in either surface.

The current 0.4.x contract exposes 12 tools:

- `get_connection_status`
- `get_available_exchanges`
- `get_latest_dates`
- `get_stock_schema`
- `list_stock_tables`
- `get_table_schema`
- `screen_stocks`
- `validate_readonly_sql`
- `run_readonly_sql`
- `get_latest_company_report`
- `prepare_company_report_generation`
- `create_csv_export`

`get_latest_company_report` reads the latest cached English AI company report.
It never returns an official filing or performs live news search. `active`,
`expired`, and `not_found` are successful business states. Missing and expired
results return a generation offer; active reports do not.

After user confirmation, `prepare_company_report_generation` resolves the
company and sector and returns a bounded prompt for host-side live web research.
The host replies in the current conversation only. It does not cache, upload,
save, write a database row, or create a cached PDF.

`create_csv_export` creates a temporary bearer download. Its default lifetime is
3600 seconds (60 minutes), and callers may explicitly request any integer
lifetime from 60 through 3600 seconds.

## Testing

The offline suite mocks `closed`, the current `public_noauth` mode, and a future
OAuth authorization-code + PKCE profile for compatibility testing. It covers
all 12 descriptors, strict input schemas, paging, cached and host-generated
report preparation, CSV exports, security metadata, Skill routing, golden
prompts, and the Hosted App-only package boundary.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
```

Run the opt-in, credential-free production contract check separately:

```bash
RUN_LIVE_MCP_TESTS=1 \
  .venv/bin/python -m unittest tests.test_live_hosted_contract -v
```

Plugin and Skill validation use the bundled Codex helpers. Developer Mode
golden tests must run in a new task after a semantic version update and Repo
Marketplace reinstall.
