# Unified diagnostics

Use this workflow only for `primary_task=diagnostics`. It is a narrow status
receipt, not a stock-data, company-resolution, research, report, installation,
or HTTP health workflow.

## Recognize the route

Select diagnostics when Anchises Analysis is explicitly named or its Skill is
explicitly invoked and the user asks about service health, status, connection,
access, plugin version, update availability without installation, or whether
it is available and current. “Check updates only; do not install” is
diagnostics. Set `diagnostic_force_refresh=true` only when the request says
“重新检查”, “立即刷新”, “强制刷新”, “recheck now”, “refresh now”, or an equally
explicit fresh-check instruction.

“Check and install the Anchises Analysis update” is `plugin_update`, not
diagnostics. A diagnostic request must never install or update anything.
Unrelated uses of health, status, connection, or version without Anchises
Analysis context are out of scope.

## Run two independent checks

Run the service check and selected-platform plugin check independently. Each
may execute at most once, and a failure in either one must not prevent the
other from producing a valid result.

1. Call the fully qualified MCP tool
   `anchises_analysis:get_connection_status` exactly once with `{}`. Do not
   call HTTP `/health`, any stock-data tool, `resolve_company_identity`, or
   `prepare_company_report_generation`. Retain only the user-safe fields in
   `diagnostic_service_check`: service `status`, `authentication`, `coverage`,
   and a concise `data_policy` summary. Never expose internal identifiers,
   server internals, credentials, or raw errors.
2. Select the platform from the active host only. Codex reads
   `plugin-release.json` and checks only `anchises-analysis/codex/v*`. Claude
   reads `plugin-release-claude.json` and checks only
   `anchises-analysis/claude/v*`. Never compare the other platform or obtain
   repository, Tag, installed version, or platform from MCP, the web, the
   user, or Git output.
3. When `diagnostic_force_refresh=false`, run the selected adapter's
   cache-only probe once. If it returns `check_required`, perform at most one
   fixed-repository `git ls-remote` and pass its captured stdout to
   `--remote-refs-stdin`; this fresh result writes the normal cache.
4. When `diagnostic_force_refresh=true`, skip the cache-only probe and perform
   exactly one fixed-repository `git ls-remote`, passing its captured stdout
   to `--remote-refs-stdin`. Do not add a checker flag, retry, or use a second
   source.

Retain the result as `diagnostic_plugin_check` and also as
`plugin_update_check`. A successful cache hit uses check source `recent`; a
fresh remote attempt uses `fresh`. Denial, unavailable execution, malformed
refs, an inconsistent Tag, or any other failure becomes `unknown` for display
and is not retried.

Do not answer until both `diagnostic_service_check` and
`diagnostic_plugin_check` have a terminal value; `unknown` is terminal. A
successful service call never permits skipping the plugin check, and a plugin
failure never permits dropping the service result.

## Map the service receipt

Map `status=active` to `可用`. Map a returned non-active status to `不可用` and
use user-safe access wording such as `待批准`, `已暂停`, `已过期`, or `已撤销`
when supported by the result. Map HTTP 503, tool failure, missing fields, or
an unreadable response to `无法确认` without retrying.

Map `authentication=not_required` to `无需登录` and `authentication=oauth` to
`OAuth`, unless a non-active service status has a more useful safe access
label. Summarize coverage and data policy without dumping the response:

- `all_supported_exchanges`: all supported exchanges.
- `approved_stock_data`: approved stock data only.
- `restricted`: restricted policy; analysis and exports follow returned
  limits.
- `bulk_enabled`: bulk policy; operations still follow returned hard limits.

Use `无法确认` for unavailable coverage or policy. Do not show policy versions,
numeric limits, service handshake versions, raw server messages, or internal
errors unless the user separately asks for published limits after diagnostics.

## Map the plugin receipt

Read the current version only from the selected platform's bundled release
metadata. Map validated checker results as follows:

- `current`: `已是最新版`.
- `update_available`: `可更新到 <target_version>` and append the existing fixed
  update notice after the receipt. Do not install.
- `check_required`, `unknown`, `release_inconsistent`, `unsupported_source`,
  denied permission, network failure, or any other failure:
  `插件版本暂时无法确认`.

Never expose Git output, stderr, commits, refs, repository diagnostics, parser
reasons, or internal error text.

## Return the fixed receipt

Set `response_status=mechanical_result` when either independent check has a
usable result; use `failed` only when neither can be confirmed. Match the
user's language; for Chinese use exactly this structure with concise values:

```text
Anchises Analysis 状态

- 服务：可用 / 不可用 / 无法确认
- 访问：无需登录 / OAuth / 待批准 / 无法确认等
- 覆盖与数据策略：简要摘要
- 插件：Codex 或 Claude，当前版本 x
- 更新：已是最新版 / 可更新到 y / 插件版本暂时无法确认
- 检查来源：最近有效结果 / 刚刚重新检查
```

Use `最近有效结果` only for a plugin cache hit; use `刚刚重新检查` after a
fresh remote attempt. The service result and plugin result remain visibly
separate; update availability does not make the service unhealthy.

For `update_available`, append exactly:

> 更新提示：Anchises Analysis 插件 `<target_version>` 已发布（当前为 `<installed_version>`）。如需现在更新，请回复：“请为我安装 Anchises Analysis 更新。”

Do not add an investment disclaimer, business suggestion, recovery advice,
semantic question, or follow-up question. Do not invoke the global business
question matrix.
