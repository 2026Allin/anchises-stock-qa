# Codex plugin update adapter

Use this adapter only in Codex. The shared trigger, reminder, authorization,
decline, failure, and final-order rules are defined in
[plugin-update.md](plugin-update.md).

## Check the Codex release

Resolve both bundled scripts to absolute paths under this Skill directory.
Run the network-free cache probe exactly once:

```text
python3 scripts/check_plugin_update.py --cache-only
```

Only when it returns `check_required`, invoke the fixed Git segment directly
and pipe its captured stdout to the local parser:

```text
git ls-remote -- https://github.com/2026Allin/anchises-stock-qa.git | python3 <absolute-skill-directory>/scripts/check_plugin_update.py --remote-refs-stdin
```

Request that shell execution with exactly:

```json
{
  "cmd": "git ls-remote -- https://github.com/2026Allin/anchises-stock-qa.git | python3 <absolute-skill-directory>/scripts/check_plugin_update.py --remote-refs-stdin",
  "sandbox_permissions": "require_escalated",
  "justification": "允许只读检查 Anchises Analysis 的已发布版本吗？",
  "prefix_rule": [
    "git",
    "ls-remote",
    "--",
    "https://github.com/2026Allin/anchises-stock-qa.git"
  ]
}
```

The command has no wildcard, substitution, redirection, or additional
repository. A reusable approval covers only the direct read-only Git segment;
never request one for `python3`, either bundled script, a shell, or general
network access. Consider only `anchises-analysis/codex/v*`; ignore Claude Tags
and unrelated refs.

For an ordinary Codex diagnostic, use this cache probe and remote-on-miss
sequence exactly once. When `diagnostic_force_refresh=true`, skip
`--cache-only` and run the fixed Git-plus-`--remote-refs-stdin` command exactly
once. The parser writes that result to the normal cache. Do not use
`--no-cache`, add another query, or run the updater.

## Set up reusable Codex release-check permission

Treat “为 Anchises Analysis 启用永久版本检查” or an equally explicit request
as `plugin_update_permission`. Do not call MCP or install anything. Bypass the
cache and issue the same fixed Git-plus-parser request so Codex can propose only
its exact Git prefix.

Explain that **Approve for me** is Auto-review: it may approve the current
lookup but does not itself create a persistent allow rule. For reusable
permission, the user must temporarily use **Ask for approval** and choose
**Always allow** for the exact Git prefix. The Codex UI owns that decision and
may write `~/.codex/rules/default.rules`; this plugin must never create, edit,
or delete that file. The user may then return to Approve for me.

Do not claim persistence unless the user explicitly confirms **Always allow**.
If denied, say that reusable checking was not enabled and leave the plugin
functional; do not try another command or weaken the prefix.

## Update through the Codex CLI

After explicit authorization, pipe one fresh lookup to the updater exactly
once:

```text
git ls-remote -- https://github.com/2026Allin/anchises-stock-qa.git | python3 <absolute-skill-directory>/scripts/update_installed_plugin.py --remote-refs-stdin
```

Use the same `sandbox_permissions`, justification, and exact Git `prefix_rule`
above. The updater accepts no target version, Tag, repository, branch, or
command argument and never opens the network. It executes each command at most
once, in this order:

```text
codex plugin list --json
codex plugin marketplace list --json
codex plugin marketplace upgrade Anchises-Analysis --json
codex plugin add anchises-analysis@Anchises-Analysis --json
codex plugin list --json
```

The supported source is exactly Marketplace `Anchises-Analysis`, repository
`https://github.com/2026Allin/anchises-stock-qa.git`, and Git ref `main`. If
Codex omits or returns `null` for `marketplaceSource.refName`, accept it only
when the captured remote `HEAD`, `refs/heads/main`, and selected release Tag
resolve to the same commit. A local Marketplace, wrong repository, explicit
non-`main` ref, incomplete source metadata, or commit mismatch stops the
update. The compatibility check must not execute an additional command.

Never attempt `git pull`, `git clone`, Tag creation, commit, push, merge,
uninstall-first, Marketplace removal or re-addition, `config.toml` or
Marketplace JSON edits, force, rollback, or GUI fallback. Creating or
publishing a Codex Tag is a separate maintainer-only release action.

On `updated`, say:

> Anchises Analysis 已更新到 `<version>`。当前对话仍使用启动时加载的旧 Skill 和 MCP catalog，请新建一个 Codex 对话后再使用新版本。
