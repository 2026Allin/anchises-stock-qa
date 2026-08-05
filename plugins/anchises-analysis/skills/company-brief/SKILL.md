---
name: company-brief
description: Create concise, current 3-4-sentence introductions for one to five public companies when the user asks to understand, introduce, summarize, or get quick context on named companies or companies explicitly referenced from earlier conversation. Cover each company's core business, one dated recent official development, and one dated material independent news item. Use for quick company profiles and multi-company background, including requests such as “what does each company do?” Do not use merely because an assistant response mentions a company, for discovery lists, news-only questions, market-data requests, narrow comparisons, or full/deep company research.
---

# Company Brief

Create compact, source-linked company snapshots through Anchises Analysis
without entering the seven-section company-report workflow.

## Classify once

Before doing any research, read
[../anchises-analysis/references/global-contract.md](../anchises-analysis/references/global-contract.md)
and the canonical arbitration rules in
[../anchises-analysis/references/query-interpretation.md](../anchises-analysis/references/query-interpretation.md).
Proceed only when the resulting `primary_task` is `company_brief`. Do not
reclassify the request inside this workflow.

The user's intent must request or semantically require a separate quick
understanding of each company. Company names may come from the current request
or an explicit reference to the most recent relevant company set. Company-name
presence alone is not sufficient. Set `company_introductions=true`.

## Check public service access

Read
[../anchises-analysis/references/service-access.md](../anchises-analysis/references/service-access.md),
then call `get_connection_status` once for the whole brief request. Apply the
shared public-access, credential, privacy, outage, and retry rules.

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
