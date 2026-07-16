# Stock Data Desk

Stock Data Desk is a single-skill plugin for stock screening, historical
comparison, read-only SQL, cached English AI company reports, and
temporary CSV exports across Work, ChatGPT, and Codex.

## Hosted App status

The `qa-v2-auth` branch contains the private Phase 7A Developer Mode activation:

- Hosted MCP: `https://mcp.anchisesdata.com/mcp`
- Developer Mode App: `Stock QA Dev`
- App manifest ID: `plugin_asdk_app_6a5754cdf4ac8191a27ec8854675482a`
- Current contract snapshot mode: `anonymous_dev`
- Supported backend modes: `closed`, `anonymous_dev`, and `oauth`
- Future OAuth issuer: `https://auth.anchisesdata.com/`

The plugin package is now Hosted App-only: `.app.json` connects the App and the
single bundled Skill supplies workflow guidance. The package contains no local
stdio MCP, Python bootstrap, API Token setup, or local database runtime.

The private Developer Mode App currently uses `anonymous_dev`. The plugin Skill
does not branch on that internal name: it reacts to observable noauth, OAuth,
and service-unavailable behavior. Freeze and re-scan the intended public access
profile before submitting this version to the Plugin Directory.

## Hosted contract

The checked-in snapshot is generated from the public Hosted MCP `tools/list`:

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

The current draft exposes 11 tools:

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
- `create_csv_export`

`get_latest_company_report` reads the latest cached English AI company report.
It never returns an official filing, performs live news search, or starts report
generation. `active`, `expired`, and `not_found` are successful business states.

## Testing

The offline suite mocks `closed`, the current `anonymous_dev` mode, and the
future OAuth authorization-code + PKCE mode. It covers all 11 descriptors,
strict input schemas, paging, reports, CSV exports, security metadata, Skill
routing, golden prompts, and the Hosted App-only package boundary.

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
golden tests must run in a new task after cachebuster update and local reinstall.
