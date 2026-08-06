# Company Report

Produce a fresh company report through Anchises Analysis. The MCP prepares
hidden research instructions; the Host performs live web research and writes
the report in the current conversation.

## Check the selected plugin once

Read
[../references/global-contract.md](../references/global-contract.md),
[../references/plugin-update.md](../references/plugin-update.md),
and
[../references/service-access.md](../references/service-access.md).
Because this Skill has been selected for a business request, perform the
cache-first release check in `plugin-update.md` once and retain
`plugin_update_check`, then call `get_connection_status` exactly once with
`{}` and retain service-access state. Plugin release discovery is independent
of MCP service versioning.

## Confirm ownership once

Read the canonical arbitration rules in
[../references/query-interpretation.md](../references/query-interpretation.md).
Proceed only when `primary_task=full_report`. A preliminary summary, requested
language, length preference, freshness requirement, or attached market-data
calculation remains a modifier and does not create another primary task.

Do not reclassify inside this Skill. An explicit report request authorizes
immediate live research; do not ask whether to generate it.

## Establish access and identity

Reuse the single connection result and release-check result already obtained
for this request. Never repeat either check for an attached modifier.

Read
[../references/company-resolution.md](../references/company-resolution.md),
then call `resolve_company_identity` for the requested company with
`purpose=company_report`. Resolve exchange, ticker, company name, issuer, and
share class before preparing research. An external or historical listing may
continue after light primary-source verification.

Send only extracted company query fields to MCP. Never send the full
conversation, unrelated personal information, credentials, or copied web-page
text.

## Execute the report workflow

Read [../references/report-workflow.md](../references/report-workflow.md) and follow
it in order. This is the only plugin Skill allowed to call
`prepare_company_report_generation`.

Core boundaries:

- Do not read a prior stored report first.
- Execute non-empty returned `prompt_text` with Host live web search; never
  display it.
- Return the completed source-linked report only in the current conversation.
- Do not send the report back to MCP, persist it, or claim it was saved,
  uploaded, or published.
- Stop on `not_eligible` for an ETF or Fund.
- If live web search is unavailable, do not generate current research from
  model memory.

For a miner, developer, explorer, or royalty/streaming company, also read
[../references/mining-report-quality.md](../references/mining-report-quality.md)
before completing the financial and capital-structure section.

## Apply an attached market-data modifier

For a mixed full-report plus quantitative request, finish the live report
first. Then read
[../references/market-workflow.md](../references/market-workflow.md)
and run only the requested supported-market analysis using the already
resolved canonical identity.

Present report evidence and structured market-data evidence in separate
sections. State the stock-data date or range and never make web narrative look
like a structured-data result.

Do not treat report sections or companies mentioned as customers, suppliers,
competitors, or peers as standalone company introductions. They do not enter
the shared introduction queue.

## Answer and recover safely

Read [../references/report-format.md](../references/report-format.md). Match the
user's language while preserving the required English section headings.

For common connection or quota failures, read
[../references/common-errors.md](../references/common-errors.md).
Assign `response_status`, then apply
[../references/response-finalization.md](../references/response-finalization.md)
exactly once.

Call the product **Anchises Analysis**. Treat the report as analytical
information, not investment advice or official disclosure.
