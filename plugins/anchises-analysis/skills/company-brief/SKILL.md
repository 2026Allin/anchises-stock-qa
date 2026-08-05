---
name: company-brief
description: Create concise, current 3-4-sentence introductions for one to five public companies when the user asks to understand, introduce, summarize, or get quick context on named companies or companies explicitly referenced from earlier conversation. Cover each company's core business, one dated recent official development, and one dated material independent news item. Use for quick company profiles and multi-company background, including requests such as “what does each company do?” Do not use merely because an assistant response mentions a company, for discovery lists, news-only questions, market-data requests, narrow comparisons, or full/deep company research.
---

# Company Brief

Create compact, source-linked company snapshots through Anchises Analysis
without entering the seven-section company-report workflow.

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

## Classify once

Before doing any research, read the canonical arbitration rules in
[../anchises-analysis/references/query-interpretation.md](../anchises-analysis/references/query-interpretation.md).
Proceed only when the resulting `primary_task` is `company_brief`. Do not
reclassify the request inside this workflow.

The user's intent must request or semantically require a separate quick
understanding of each company. Company names may come from the current request
or an explicit reference to the most recent relevant company set. Company-name
presence alone is not sufficient. Set `company_introductions=true`.

## Apply public service access

Reuse the single connection result already obtained for this request. Apply
the shared public-access, credential, privacy, outage, retry, and update-footer
rules. Never call `get_connection_status` again for a modifier.

## Execute the shared introduction component

Read
[../anchises-analysis/references/company-introductions.md](../anchises-analysis/references/company-introductions.md)
and apply it to the ordered companies from the current request or explicit
recent-context reference. It owns ordering, the five-company window, identity
resolution, current web research, and the three- or four-sentence format.

Do not call `prepare_company_report_generation`. If the user explicitly asks
for a short comparison after the introductions, add one compact synthesis
paragraph after the completed introduction batch without expanding the entity
set.

## Finalize once

For common access or quota failures, read
[../anchises-analysis/references/common-errors.md](../anchises-analysis/references/common-errors.md).

After the component assigns `response_status`, read
[../anchises-analysis/references/response-finalization.md](../anchises-analysis/references/response-finalization.md)
exactly once. Call the product **Anchises Analysis** in user-facing text.
