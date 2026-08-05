# Anchises Analysis: Cross-workspace Codex installation

This guide installs the complete Anchises Analysis Codex plugin from GitHub for
a user in another OpenAI workspace that permits custom Git marketplaces and
plugin-bundled MCP servers. The package includes five Skills and one bundled
remote MCP server; it does not use `Share with you`, a Developer Mode App ID,
Portal Scan, or a separate `codex mcp add` command.

## Package contents

- Plugin: `anchises-analysis`
- Marketplace: `Anchises-Analysis`
- Skills: `anchises-analysis`, `company-brief`, `company-report`,
  `company-comparison`, and `market-analysis`
- MCP server key: `anchises_analysis`
- MCP URL: `https://mcp.anchisesdata.com/mcp`
- MCP version: `0.7.1`
- Tools: 12
- Authentication: none

The GitHub repository is public. Anyone who can reach GitHub and the MCP URL
can read the plugin package and connect to the credential-free service. Making
the repository private would restrict package downloads, but it would not by
itself restrict the public MCP endpoint.

## Install from the Codex CLI

During QA, pin the marketplace to `qa-v2-auth` and fetch only the marketplace
metadata and plugin directory:

```bash
codex plugin marketplace add \
  https://github.com/2026Allin/anchises-stock-qa.git \
  --ref qa-v2-auth \
  --sparse .agents/plugins \
  --sparse plugins/anchises-analysis

codex plugin add anchises-analysis@Anchises-Analysis
```

After the release is merged, use the stable release ref selected by the
maintainer instead of `qa-v2-auth`.

## Install from the Codex desktop app

In **Add plugin marketplace**, enter:

```text
Source
https://github.com/2026Allin/anchises-stock-qa.git

Git ref
qa-v2-auth

Sparse paths
.agents/plugins
plugins/anchises-analysis
```

Add the marketplace, select **Anchises Analysis**, and install it. Start a new
Codex task after installation so the new Skill catalog and MCP runtime are
loaded.

## Verify the installation

1. Run `codex plugin list` and confirm
   `anchises-analysis@Anchises-Analysis` is installed and enabled at the
   expected version.
2. In a new task, verify that all five Skills are available.
3. Open `/mcp` and confirm the bundled `anchises_analysis` server is connected.
4. Confirm MCP discovery returns exactly 12 tools and reports version `0.7.1`.
5. Run one Company Brief, Company Report, Company Comparison, and Market
   Analysis request.
6. Verify a market result displays no more than 200 rows, cursor continuation
   occurs only after an explicit next-page request, and exports follow the
   current dynamic policy.

No Anchises Analysis Developer Mode App should be required or enabled for this
verification. If the old App remains available as a rollback resource, leave
it disabled while testing the bundled MCP to avoid duplicate tool surfaces.

## Managed workspace allowlists

No administrator action is needed when the target workspace allows custom Git
marketplaces and plugin-bundled MCP servers. If it restricts either surface,
its administrator can add the exact QA source and MCP identity to the managed
`requirements.toml` file:

```toml
[marketplaces]
restrict_to_allowed_sources = true

[marketplaces.allowed_sources.anchises_analysis]
source = "git"
url = "https://github.com/2026Allin/anchises-stock-qa.git"
ref = "qa-v2-auth"

[plugins."anchises-analysis".mcp_servers.anchises_analysis.identity]
url = "https://mcp.anchisesdata.com/mcp"
```

When the stable ref changes, update or remove the exact `ref` constraint under
the target workspace's change-control process.

## Update and rollback

Refresh the configured Git marketplace, then reinstall the plugin and start a
new task:

```bash
codex plugin marketplace upgrade Anchises-Analysis
codex plugin add anchises-analysis@Anchises-Analysis
```

For rollback, pin the marketplace to a previously validated Git tag or commit,
refresh it, and reinstall the same plugin slug. The old Developer Mode App is
not required for package rollback.
