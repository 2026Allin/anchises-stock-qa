# Company Brief

Create compact, source-linked company snapshots through Anchises Analysis
without entering the seven-section company-report workflow.

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

## Classify once

Before doing any research, read the canonical arbitration rules in
[../references/query-interpretation.md](../references/query-interpretation.md).
Proceed only when the resulting `primary_task` is `company_brief`. Do not
reclassify the request inside this workflow.

The user's intent must request or semantically require a separate quick
understanding of each company. Company names may come from the current request
or an explicit reference to the most recent relevant company set. Company-name
presence alone is not sufficient. Set `company_introductions=true`.

## Apply public service access

Reuse the single connection result and release-check result already obtained
for this request. Apply the shared public-access, credential, privacy, outage,
retry, and update-footer rules. Never repeat either check for a modifier.

## Execute the shared introduction component

Read
[../references/company-introductions.md](../references/company-introductions.md)
and apply it to the ordered companies from the current request or explicit
recent-context reference. It owns ordering, the five-company window, identity
resolution, current web research, and the three- or four-sentence format.

Do not call `prepare_company_report_generation`. If the user explicitly asks
for a short comparison after the introductions, add one compact synthesis
paragraph after the completed introduction batch without expanding the entity
set.

## Finalize once

For common access or quota failures, read
[../references/common-errors.md](../references/common-errors.md).

After the component assigns `response_status`, read
[../references/response-finalization.md](../references/response-finalization.md)
exactly once. Call the product **Anchises Analysis** in user-facing text.
