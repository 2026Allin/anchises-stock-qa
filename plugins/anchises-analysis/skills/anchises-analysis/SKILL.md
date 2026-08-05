---
name: anchises-analysis
description: Coordinate Anchises Analysis requests when the user asks generally to use the product, requests an Anchises Analysis install or update, declines an offered update, combines a primary workflow with secondary deliverables, or leaves the desired deliverable ambiguous. Classify exactly one primary task, preserve shared request state, and route to plugin update, Company Brief, Company Report, Company Comparison, or Market Analysis under one global response contract. Do not replace a clearly matching specialized Skill, treat incidental company mentions as research requests, retrieve official filings, or answer news-only requests.
---

# Anchises Analysis

Act as the thin coordination entry for the Anchises Analysis plugin. Let users
ask in natural language; do not require tool names, SQL, schemas, tickers,
credentials, or local setup.

## Check the selected plugin once

Read [references/global-contract.md](references/global-contract.md),
[references/plugin-update.md](references/plugin-update.md), and
[references/service-access.md](references/service-access.md). Because this
Skill has been selected, call `get_connection_status` exactly once for this
user request using the schema-aware client-metadata rule. Retain both service
access state and `client_update` state. Do not make a second status call for a
business modifier.

If the message is an explicitly authorized Anchises Analysis installation or
update, a decline of the offered update, or an acknowledgement after a
completed update, use the `plugin_update` route and the only state machine in
`plugin-update.md`. Keep it separate from business classification. A bare
“yes”, “是”, “install”, or “安装” is not explicit update authorization.

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
| `plugin_update` | This Skill; follow `references/plugin-update.md` only |
| `company_brief` | Sibling `company-brief` Skill |
| `full_report` | Sibling `company-report` Skill |
| `comparison` | Sibling `company-comparison` Skill |
| `market_data` | Sibling `market-analysis` Skill |
| supported structured `discovery` | Sibling `market-analysis` Skill |
| `news` or official-record retrieval | Host web or a purpose-built source connector, not a generated report |
| `ambiguous` | Ask one focused question, then classify once from the answer |

This Skill coordinates; it does not duplicate the specialized delivery
workflows. A clearly matching specialized Skill may start directly, but it
must read the same canonical arbitration reference and verify that it owns the
resulting task.

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

Reuse the one service check already made for this request. Never call
`get_connection_status` again when a modifier adds another workflow.

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
