# Shared company-introduction component

Use this component whenever `company_introductions=true`, whether the owning
workflow is Company Brief, Market Analysis, or Company Comparison. It governs
standalone three- or four-sentence company profiles; it does not limit market
tables, rankings, comparison matrices, report sections, news lists, one-line
identities, or incidental mentions.

## Build the ordered introduction set

Construct `ordered_intro_entities` from exactly one applicable source:

1. Explicit user priority.
2. Otherwise, company order in the current request.
3. Otherwise, the order of the most recent explicitly referenced company set.
4. For companies discovered by the owning workflow, its original server-side
   or evidence-backed ranking order.

Do not reorder by perceived importance. Do not scan the full conversation.
Do not add customers, suppliers, competitors, or companies encountered during
web research.

Apply the global presentation window after the entity set exists:

```text
current_intro_batch = ordered_intro_entities[0:5]
remaining_intro_entities = ordered_intro_entities[5:]
```

Research and write introductions only for `current_intro_batch`. Every later
batch is also limited to five.

## Compose with a discovery workflow

When Market Analysis or another owning workflow discovers the companies:

1. Complete the owning screen, ranking, and evidence filter first.
2. Preserve all eligible result rows and their original order.
3. Allow the quantitative table to show more than five companies under its own
   display policy.
4. Apply the five-company limit only to standalone introduction blocks.
5. On a continuation request, reuse the original result set, order, filters,
   and `data_date`. Do not rerun the screen unless the user asks to refresh it.

When remaining discovered companies are already visible in a table, the
continuation question may refer to that table and the remaining count instead
of repeating a materially long list. For a concise explicit or contextual
company set, list every remaining company.

## Resolve the current batch

Read [company-resolution.md](company-resolution.md). Resolve every company in
`current_intro_batch` separately with `resolve_company_identity`, reusing a
canonical identity already resolved during the same request.

The MCP contract has no `company_brief` purpose, so use
`purpose=company_report` for identity matching only. This compatibility value
does not authorize `prepare_company_report_generation`.

For `not_found_in_supported_markets`, establish the public identity with an
exchange, regulator, or investor-relations source and continue with Host web
research. Ask one concise identity question only when issuer, exchange, or
share class remains unresolved after candidates and primary-source checks.

## Research current context

For every company in `current_intro_batch`:

- Ground the core business and positioning in a current company page, filing,
  exchange record, or investor-relations source.
- Find one material, dated official development.
- Find one material, dated independent news item from a reputable publisher.
- Do not use the same company announcement as both the official development
  and independent news.
- Search the most recent 90 days first and expand to the most recent 12 months
  only when necessary.
- Put source links next to the claims they support.
- State plainly when no reliable recent independent item is available.

If live web research is unavailable, do not invent current developments or
news from model memory.

## Write each introduction

Use one heading with the canonical company name and listing identity. Write
exactly three or four prose sentences; the heading does not count:

1. State the company's principal products or services, business position, and
   core customers or market.
2. Describe one dated recent official development.
3. Describe one dated material independent news item, or state that none was
   verified in the search window.
4. Optionally explain why the development or news matters.

Do not turn an introduction into a seven-section report or pad it with
unrelated market metrics. If a separate comparison is part of the request,
keep its evidence and format under the owning workflow.

Set `response_status=partial` when `remaining_intro_entities` is non-empty;
otherwise preserve the owning workflow's successful status. The shared
response finalizer owns continuation and semantic questions.
