---
name: anchises-analysis
description: Coordinate Anchises Analysis for product health, status, connection, access, plugin-version/current checks; install, update, or release-check permission requests; mixed deliverables; or ambiguous requests. For any Anchises status request, run unified diagnostics by calling anchises_analysis:get_connection_status once and independently reading the active host's bundled release metadata and running its Tag checker; never stop after service status. Return every fixed receipt field—service, access, coverage/data policy, platform/current version, update status, and check source—in the user's language, without business advice or follow-up. Otherwise classify exactly one primary task and route to plugin operations, Company Brief, Company Report, Company Comparison, or Market Analysis under the shared contract. Do not replace a clearly matching specialized Skill, trigger on unrelated health/status, treat incidental company mentions as research, retrieve filings, or answer news-only requests.
---

# Anchises Analysis

Act as the thin coordination entry for the Anchises Analysis plugin. Let users
ask in natural language; do not require tool names, SQL, schemas, tickers,
credentials, or local setup.

## Route operational intent first

When the user explicitly asks to inspect Anchises Analysis health, status,
connection, access, plugin version, update availability without installation,
or whether the product is available and current, set
`primary_task=diagnostics`. Require Anchises Analysis context or explicit
`$anchises-analysis` or `/anchises-analysis` invocation; unrelated uses of
“health”, “status”, “connection”, or “version” do not trigger it. This route
has priority over business classification and bypasses
`query-interpretation.md`.

For `primary_task=diagnostics`, execute this completion gate before answering:

1. Read [references/diagnostics.md](references/diagnostics.md) and the one
   active-host adapter and release file it names. Treat these reads as required
   diagnostic work, not optional background.
2. Call `anchises_analysis:get_connection_status` exactly once with `{}`.
3. Run the selected host's bundled release checker once as defined in the
   diagnostic reference. A normal request starts with the cache-only command;
   an explicit recheck skips that command and performs one fixed Git lookup.
4. Populate both `diagnostic_service_check` and `diagnostic_plugin_check`
   before composing the response. `unknown` is a valid terminal plugin-check
   result. A successful service call never permits skipping the plugin check,
   and a plugin-check failure never permits dropping the service result.
5. Return the fixed receipt below in the user's language. For Chinese, use
   these labels in this order and include every line:

   ```text
   Anchises Analysis 状态

   - 服务：<可用 / 不可用 / 无法确认>
   - 访问：<无需登录 / OAuth / 待批准 / 无法确认等>
   - 覆盖与数据策略：<简要摘要>
   - 插件：<Codex 或 Claude>，当前版本 <x>
   - 更新：<已是最新版 / 可更新到 y / 插件版本暂时无法确认>
   - 检查来源：<最近有效结果 / 刚刚重新检查>
   ```

If Skill-file reading, shell execution, permission, or network access is
unavailable, record the affected plugin result as `unknown`, obtain the
current version from the selected bundled release metadata when readable, and
still return all receipt lines. Never replace the fixed Tag check with MCP,
web search, or a guessed version. Do not expose raw errors. Execute the
diagnostic and stop; do not continue to the business check or business
classification below.

For every non-diagnostic Anchises Analysis request, read
[references/global-contract.md](references/global-contract.md),
[references/plugin-update.md](references/plugin-update.md), and
[references/service-access.md](references/service-access.md) before business
classification.

If the message is an explicitly authorized Anchises Analysis installation or
update, a persistent release-check permission request, a decline of the
offered update, or an acknowledgement after a completed update, use the
applicable operational route in `plugin-update.md`. Do not call MCP for these
routes; an authorized update receives fresh refs through the fixed Git
network segment. “Check and install the Anchises Analysis update” is
`plugin_update`, not `diagnostics`, and must not call MCP. Keep these routes
separate from business classification. A bare
“yes”, “是”, “install”, or “安装” is not explicit update authorization.
Execute the selected operational route and stop.

## Check a business request once

For a substantive Anchises business request, perform the cache-first release
check defined in `plugin-update.md` once and retain `plugin_update_check`, then
call `get_connection_status` exactly once with `{}` and retain the
service-access state. Plugin release discovery is independent of MCP service
versioning. Do not repeat either check for a business modifier.

## Classify once

Read [references/query-interpretation.md](references/query-interpretation.md)
before selecting any workflow. Assign exactly one `primary_task`, then extract
modifiers and user- or context-supplied entities. Select presentation policies
before execution, but apply result-dependent windows only after the owning
workflow has materialized discovered entities. Do not let a downstream Skill
reclassify the request.

Use this workflow map:

| `primary_task` | Owning workflow |
|---|---|
| `diagnostics` | This Skill; follow `references/diagnostics.md` only |
| `plugin_update` | This Skill; follow `references/plugin-update.md` only |
| `plugin_update_permission` | This Skill; follow the permission setup in `references/plugin-update.md` only |
| `company_brief` | [workflows/company-brief.md](workflows/company-brief.md) |
| `full_report` | [workflows/company-report.md](workflows/company-report.md) |
| `comparison` | [workflows/company-comparison.md](workflows/company-comparison.md) |
| `market_data` | [workflows/market-analysis.md](workflows/market-analysis.md) |
| supported structured `discovery` | [workflows/market-analysis.md](workflows/market-analysis.md) |
| `news` or official-record retrieval | Host web or a purpose-built source connector, not a generated report |
| `ambiguous` | Ask one focused question, then classify once from the answer |

This Skill coordinates; it does not duplicate the specialized delivery
workflows. Read exactly one linked workflow after classification. In Codex, a
clearly matching specialized Skill may start directly through its thin entry,
but it must load the same canonical workflow, read the same arbitration
reference, and verify that it owns the resulting task.

For mixed deep research plus market data, retain `primary_task=full_report`.
The `company-report` Skill completes the report first, then applies the
market-data modifier without merging the two evidence sets.

For a market screen, ranking, or evidence filter with attached standalone
company introductions, retain `primary_task=market_data` and set
`company_introductions=true`. The market workflow materializes the ranked
company set before applying the shared introduction component.

## Prepare shared state

Maintain the conceptual state defined in
[references/global-contract.md](references/global-contract.md), including
separate requested, contextual, and discovered entities.

Reuse the one service check and one release check already made for this
request. Never call `get_connection_status` or repeat the cache probe or
remote Tag lookup when a modifier adds another workflow.

Before a company brief, full report, comparison, or single-company market-data
workflow, read
[references/company-resolution.md](references/company-resolution.md).
Resolve each in-scope company separately. Ask only when exchange, issuer, or
share-class ambiguity remains after context, candidates, and light
primary-source verification.

Pass only the extracted company query fields to MCP. Never send the full
conversation, unrelated personal information, credentials, or copied web-page
text.

## Apply conditional components

When `company_introductions=true`, read
[references/company-introductions.md](references/company-introductions.md)
after the owning workflow has produced the applicable company set. Apply its
window only to standalone introduction blocks, never to the owning table,
ranking, comparison matrix, or report.

Read [references/common-errors.md](references/common-errors.md) for shared
failure handling. Assign `response_status`, then read
[references/response-finalization.md](references/response-finalization.md)
exactly once after the body and disclaimer are ready.

Always identify the product as **Anchises Analysis** in user-facing text. Keep
technical URLs unchanged when needed as links, but do not repeat stale product
labels surfaced by backend or historical metadata.
