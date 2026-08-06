# Anchises Analysis: Claude installation and updates

Anchises Analysis uses one shared plugin bundle for Claude Chat, Claude
Desktop, Cowork, and Claude Code. Claude discovers exactly one visible
`Anchises Analysis` Skill. That thin facade classifies once and loads one of
the unchanged canonical workflows used by Codex, while both platforms share
the same public Hosted MCP definition. Platform manifests, visible Skill
layout, release metadata, Tag namespaces, and update mechanics remain separate.

## Package identity

- Plugin: `anchises-analysis`
- Marketplace: `anchises-capital`
- Install ID: `anchises-analysis@anchises-capital`
- GitHub repository: `2026Allin/anchises-stock-qa`
- Release branch: `main`
- Claude Tags: `anchises-analysis/claude/v<semver>`
- MCP server: `anchises_analysis`
- MCP URL: `https://mcp.anchisesdata.com/mcp`
- Visible Claude Skill: `anchises-analysis`
- Canonical internal workflows: coordinator, Company Brief, Company Report,
  Company Comparison, and Market Analysis

## Install in Claude Code from GitHub

Add the repository as a Marketplace pinned to `main`, using sparse checkout for
only the Claude catalog and plugin package:

```bash
claude plugin marketplace add \
  2026Allin/anchises-stock-qa@main \
  --sparse .claude-plugin adapters/claude plugins/anchises-analysis

claude plugin install anchises-analysis@anchises-capital
```

This is a GitHub installation. The `owner/repository@ref` form is Claude Code's
GitHub shorthand; a separate download or copied Skill folder is not required.
Start a new Claude conversation after installation.

For local development without installing from the Marketplace:

```bash
claude --plugin-dir .
```

The local form is for testing only. The guarded in-Skill updater intentionally
rejects local sources.

## Test the QA branch before release

Claude Code can pin the Marketplace to the QA branch while validating this
adapter:

```bash
claude plugin marketplace add \
  2026Allin/anchises-stock-qa@qa-v2-auth \
  --sparse .claude-plugin adapters/claude plugins/anchises-analysis

claude plugin install anchises-analysis@anchises-capital
```

Remove the existing local `anchises-capital` Marketplace first if Claude Code
reports a name collision, then add the QA-pinned source and reinstall. The
guarded updater deliberately rejects a non-`main` Marketplace ref, so branch
testing covers installation, Skill routing, prompts, and MCP behavior—not the
production update command.

Claude Chat, Desktop, and Cowork repository installation follows the
repository's default branch and does not provide a branch selector. Validate
those web/UI surfaces only after the tested QA commit is merged to `main`.
Merging alone does not publish an update reminder; that still requires an
explicit Claude release Tag.

## Install in Claude Chat, Desktop, or Cowork

1. Open **Customize**. In Cowork, open the Cowork tab first.
2. Open **Plugins**.
3. Under **Personal plugins**, select **+**, then **Add marketplace**.
4. Choose **Add from a repository** and enter:

   ```text
   https://github.com/2026Allin/anchises-stock-qa
   ```

5. Open the `anchises-capital` Marketplace and install **Anchises Analysis**.
6. Start a new Claude conversation.

Claude Desktop and Cowork also support uploading a custom plugin file, but the
GitHub Marketplace is the release path for this repository. Team or Enterprise
administrators may restrict custom Marketplaces, plugins, or MCP servers; in
that case the administrator must allow the repository and the public MCP URL.

## Verify the installation

In Claude Code:

```bash
claude plugin list --json
claude plugin marketplace list --json
claude plugin details anchises-analysis@anchises-capital
```

Confirm that:

1. `anchises-analysis@anchises-capital` is installed and enabled at the
   expected `+claude.<timestamp>` release.
2. Exactly one visible Skill, `anchises-analysis`, is available under the
   plugin namespace.
3. The `anchises_analysis` MCP server connects to the public HTTP endpoint.
4. MCP discovery exposes exactly 12 tools.
5. Representative Company Brief, Company Report, Company Comparison, and
   Market Analysis requests route into their canonical internal workflows and
   preserve the existing response behavior.

In Chat, Desktop, or Cowork, type `/` or use the `+` menu to confirm that only
the one Anchises Analysis Skill appears, then run the same representative
requests.

## Release checks and reminders

Every substantive request handled by the single Claude facade performs the
same cache-first policy:

- A successful check is reused for 1 hour.
- An unknown, denied, malformed, or inconsistent check is reused for 10
  minutes when the host can retain that cache.
- A cache miss permits at most one direct, read-only `git ls-remote` against
  the fixed repository.
- Only `anchises-analysis/claude/v*` Tags are considered.
- A newer Tag is accepted only when it resolves to the current remote `main`
  head.
- Current, unknown, inconsistent, failed, and already-installed results remain
  silent.

When an update is validated, the business answer and its questions remain
unchanged. The response adds this separate final footer:

> 更新提示：Anchises Analysis 插件 `<target_version>` 已发布（当前为 `<installed_version>`）。如需现在更新，请回复：“请为我安装 Anchises Analysis 更新。”

Only an explicit sentence naming Anchises Analysis and an install/update intent
authorizes the next step. A bare “yes”, “install”, or “update” is insufficient.
Declining cancels only the current attempt, so the next substantive request
checks again.

## Update in Claude Code

After exact authorization, the plugin rechecks the Claude Tags from GitHub and
then runs one guarded sequence:

```bash
claude plugin list --json
claude plugin marketplace list --json
claude plugin marketplace update anchises-capital
claude plugin update anchises-analysis@anchises-capital
claude plugin list --json
```

The updater accepts only the fixed Marketplace, repository, `main` ref, and
plugin ID. Each command runs at most once. Any failure stops without retry,
source changes, uninstall-first, settings edits, or rollback. A successful
update requires a new Claude conversation.

## Update in Chat, Desktop, or Cowork

These surfaces do not run the Claude CLI updater. After exact authorization,
the Skill performs one fresh Tag recheck and hands control to the UI:

```text
Customize → Plugins → Anchises Analysis → Update
```

The handoff never claims the update completed. Complete it in the UI and start
a new Claude conversation. If the UI does not offer an Update action, refresh
or reopen the Marketplace through the host's own controls; the Skill does not
guess commands or modify local settings.

## Maintainer release boundary

Develop and validate away from `main`. For a Claude release:

1. Update `.claude-plugin/plugin.json` to one
   `<semver>+claude.<14-digit-UTC-timestamp>` value.
2. Synchronize and verify `plugin-release-claude.json`.
3. Validate the Marketplace and plugin with the Claude CLI.
4. Merge the tested commit to `main`.
5. Only after an explicit maintainer release decision, create
   `anchises-analysis/claude/v<semver>` at the same commit as remote `main`.

Codex Tags never trigger Claude updates, and Claude Tags never trigger Codex
updates. MCP-only deployments remain independent of both plugin release lines.
