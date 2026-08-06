# Company report answer format

Lead with the finding and return the completed source-linked report in the
current conversation. Do not show `prompt_text`.

Use:

- one localized `**Summary:**` paragraph
- all seven fixed English headings in the required order
- localized section bodies
- exact dates or reporting periods
- links placed next to the material claims they support
- exactly one report-closing English `**[Risk: Low]**`,
  `**[Risk: Medium]**`, or `**[Risk: High]**` label with justification,
  placed before any question required by the shared response finalizer

When `identity_source=host_supplied` or listing verification is required,
describe material identity or status findings with primary-source links. Do
not claim that Anchises Analysis verified an external identity. If the record
is an ETF or Fund, explain why an operating-company report is not appropriate.

Do not claim that the report was saved, uploaded, published, sent back to MCP,
or made available as a file.

For a mixed request, complete the report before a distinct quantitative
market-data section. State the structured data date or range, filters, missing
values, warnings, and preview limits. Do not merge narrative web evidence with
calculated observations.
