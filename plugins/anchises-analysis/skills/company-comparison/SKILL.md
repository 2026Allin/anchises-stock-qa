---
name: company-comparison
description: Compare two or more named public companies across business mix, products, customers, competitive position, financial profile, recent developments, catalysts, risks, or requested market measures. Use when the primary deliverable is relative differences, a comparison table, positioning, trade-offs, or a comparative judgment; brief business context may support the comparison, and explicitly requested standalone introductions may be attached under the shared five-company presentation contract. Do not use when separate three- or four-sentence introductions are the primary deliverable, for separate full reports, news only, market data only, or incidental company mentions.
---

# Company Comparison

Build a source-linked, dimension-by-dimension comparison through Anchises
Analysis. Keep the comparative question—not a set of mini reports—as the
organizing principle.

## Check the selected plugin once

Read
[../anchises-analysis/references/global-contract.md](../anchises-analysis/references/global-contract.md),
[../anchises-analysis/references/plugin-update.md](../anchises-analysis/references/plugin-update.md),
and
[../anchises-analysis/references/service-access.md](../anchises-analysis/references/service-access.md).
Because this Skill has been selected, call `get_connection_status` exactly
once for this user request using its published schema and the shared
client-release metadata. Retain `client_update`; never probe with new
arguments and retry with `{}`.

## Confirm ownership once

Read
[../anchises-analysis/references/query-interpretation.md](../anchises-analysis/references/query-interpretation.md).
Proceed only when `primary_task=comparison`. Do not reclassify the request in
this Skill.

“Compare A and B and briefly say what they do” remains `comparison`; short
business descriptions support the relative answer. “Give A and B separate
three- or four-sentence Briefs, then compare them” remains `company_brief` and
belongs to the sibling Brief Skill.

## Establish access and identities

Reuse the single connection result already obtained for this request. Never
call `get_connection_status` again for an attached modifier.

Read
[../anchises-analysis/references/company-resolution.md](../anchises-analysis/references/company-resolution.md).
Resolve each selected company separately with `resolve_company_identity`.
Because the MCP enum has no comparison purpose, use
`purpose=company_report` for identity matching only.

That compatibility value does not authorize
`prepare_company_report_generation`. This Skill must never call that tool.

Preserve the user's explicit priority, then current-request order, then the
order of a clearly referenced recent company set. Do not add competitors,
customers, suppliers, or other companies discovered during research unless
the user asks to expand the comparison.

## Execute the comparison

Read
[references/comparison-workflow.md](references/comparison-workflow.md).
Use live Host web research for current business, positioning, official
developments, and independent context. Use structured Anchises market tools
only for market-data dimensions the user requested or that are necessary to
support the stated comparison.

The standalone company-introduction window does not limit the comparison
entity set, one-line business context, or comparison matrix. If the number of
companies and requested dimensions would make a meaningful comparison
unreadable, ask one focused scope question or use an explicit user-supplied
grouping. Never silently compare only the first five.

When the user additionally requests a separate three- or four-sentence profile
for every compared company, set `company_introductions=true`, retain
`primary_task=comparison`, and read
[../anchises-analysis/references/company-introductions.md](../anchises-analysis/references/company-introductions.md).
The comparison may cover the full resolved set, while the standalone
introduction section uses `current_intro_batch`. Reuse identities already
resolved during this request.

## Answer

Read
[references/comparison-format.md](references/comparison-format.md).
Match the user's language, state the comparison basis and dates, and lead with
the most decision-useful differences.

For common access and quota failures, read
[../anchises-analysis/references/common-errors.md](../anchises-analysis/references/common-errors.md).
Assign `response_status`, then apply
[../anchises-analysis/references/response-finalization.md](../anchises-analysis/references/response-finalization.md)
exactly once.

Call the product **Anchises Analysis**. Treat the comparison as analytical
information, not investment advice or official disclosure.
