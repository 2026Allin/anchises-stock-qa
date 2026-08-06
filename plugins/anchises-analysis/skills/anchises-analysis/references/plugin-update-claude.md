# Claude plugin update adapter

Use this adapter only in Claude Chat, Claude Desktop, Cowork, or Claude Code.
The shared trigger, reminder, authorization, decline, failure, and final-order
rules are defined in [plugin-update.md](plugin-update.md).

## Check the Claude release

Resolve the bundled checker to an absolute path under this Skill directory.
Run the network-free cache probe exactly once:

```text
python3 scripts/check_plugin_update.py --platform claude --cache-only
```

Claude Code and any Cowork runtime that exposes `${CLAUDE_PLUGIN_DATA}` use its
persistent plugin data directory for the cache. Other Claude surfaces fall
back to a conversation-scoped or temporary cache. Success remains fresh for 1
hour and failure for 10 minutes in either case; each new conversation without
persistent cache starts with a cache miss.

Only when the probe returns `check_required`, run at most one direct lookup and
pipe its captured stdout to the network-free parser:

```text
git ls-remote -- https://github.com/2026Allin/anchises-stock-qa.git | python3 <absolute-skill-directory>/scripts/check_plugin_update.py --platform claude --remote-refs-stdin
```

If the host asks for execution or network permission, request it only for the
exact read-only Git segment. Never request a reusable permission for Python,
the bundled scripts, a shell, or general network access. Do not use a GitHub
API, a web-search result, a release page, or an MCP response as a fallback.
If direct execution is unavailable or denied, retain `unknown` for the request
and remain silent about updates.

The parser considers only `anchises-analysis/claude/v*`, ignores Codex Tags
and unrelated refs, and requires the selected Claude Tag to resolve to remote
`main`.

For an ordinary Claude diagnostic, use this cache probe and remote-on-miss
sequence exactly once. When `diagnostic_force_refresh=true`, skip
`--cache-only` and run the fixed Git-plus-`--remote-refs-stdin` command exactly
once. The parser writes that result to the normal cache. Do not use
`--no-cache`, add another query, use a web or MCP fallback, or run the updater.

## Handle reusable-check requests on Claude

Treat an explicit request to enable reusable release checking as
`plugin_update_permission`. Do not call MCP, install anything, or edit
`.claude/settings.json`, managed settings, or any permission file. Use only a
host-provided permission control for the exact Git segment when such a control
is visible. If the host offers no persistent choice, state that the current
read-only check may be approved but this plugin cannot make it permanent.

## Update in Claude Code

Use this automated path only when the active surface is unambiguously Claude
Code. After explicit authorization, pipe one fresh lookup to the updater:

```text
git ls-remote -- https://github.com/2026Allin/anchises-stock-qa.git | python3 <absolute-skill-directory>/scripts/update_installed_plugin.py --platform claude --remote-refs-stdin
```

The updater accepts no target version, Tag, repository, branch, Marketplace,
plugin ID, scope, or command argument. It executes each step at most once:

```text
claude plugin list --json
claude plugin marketplace list --json
claude plugin marketplace update anchises-capital
claude plugin update anchises-analysis@anchises-capital
claude plugin list --json
```

The supported source is Marketplace `anchises-capital` from GitHub repository
`2026Allin/anchises-stock-qa` or the exact Git URL
`https://github.com/2026Allin/anchises-stock-qa.git`. An explicit ref must be
`main`. An omitted ref is accepted only when the captured remote `HEAD`,
`refs/heads/main`, and selected release Tag resolve to the same commit. Local,
URL-file, seed-managed, wrong-repository, explicit non-`main`, disabled,
duplicate, or incomplete installations fail closed.

Never attempt `git pull`, `git clone`, Tag creation, commit, push, merge,
uninstall-first, Marketplace removal or re-addition, settings edits, force,
rollback, or an interactive fallback. Creating or publishing a Claude Tag is a
separate maintainer-only release action.

On `updated`, say:

> Anchises Analysis 已更新到 `<version>`。当前对话仍使用启动时加载的旧 Skill 和 MCP catalog，请新建一个 Claude 对话后再使用新版本。

## Hand off in Claude Chat, Desktop, and Cowork

These surfaces must not run the Claude CLI updater. After exact authorization,
perform one fresh Claude Tag recheck. If the validated update is still
available, reply with only the fixed handoff after any necessary one-sentence
context:

> 请在 `Customize → Plugins → Anchises Analysis → Update` 完成更新；完成后新建一个 Claude 对话。此处尚未执行或确认安装。

Do not claim `updated`, do not write `installed_release_in_task`, and do not
guess another UI path. If the fresh result is current, say no update is needed;
if it is unknown or inconsistent, use the shared failure rule without exposing
raw errors.
