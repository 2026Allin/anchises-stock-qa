# Query interpretation

Operational `diagnostics`, `plugin_update`, and `plugin_update_permission`
requests are routed by the coordinator before this file is read. This file
arbitrates substantive business requests only.

## Classify exactly once

Classify an in-scope request into exactly one `primary_task`:

```text
company_brief
full_report
news
comparison
market_data
discovery
ambiguous
```

Use this file as the only source of task arbitration. After choosing
`primary_task`, do not reclassify the request in a downstream workflow.

Read [global-contract.md](global-contract.md) and process the request in one
direction:

```text
classify primary_task
-> extract modifiers
-> resolve requested or contextual entities
-> select presentation policies
-> execute the owning workflow
-> materialize discovered entities
-> apply presentation policies
-> format the answer
-> finalize the response
```

Do not represent primary tasks as independent Boolean flags. Freshness, news
coverage, standalone company introductions, a preliminary summary, output
language, a length constraint, an attached market-data calculation, a focused
CSV export, a short synthesis, and a request for no suggestions are modifiers;
they do not create another primary task.

## Choose the primary task

Choose by the user's requested final deliverable, not by company-name presence
or one isolated keyword:

| `primary_task` | Final deliverable |
|---|---|
| `company_brief` | Separate current three- or four-sentence introductions for one or more companies |
| `full_report` | A deep, structured company study, due-diligence response, investment-research report, or seven-section report |
| `news` | Current events, headlines, or a news timeline as the final answer |
| `comparison` | Cross-company differences, relative positioning, or a comparative judgment |
| `market_data` | Prices, returns, indicators, screens, rankings, SQL analysis, or CSV output |
| `discovery` | Finding or listing companies, exchanges, instruments, or public records without a generated report |
| `ambiguous` | No defensible final deliverable can be inferred, or explicit constraints conflict |

Apply these composition rules:

- “Introduce A and B, including recent news” is `company_brief`; news is a
  required brief component.
- “Show recent news for A and B” is `news`.
- “Research A deeply, but start with a summary” is `full_report`; the summary
  is a modifier.
- “Compare A and B and briefly say what they do” is `comparison`; the short
  identities support the comparison.
- “Give separate three- or four-sentence introductions, then briefly compare
  them” is `company_brief`; add one compact synthesis after the briefs.
- “Screen these markets, verify the catalysts, and introduce every validated
  company” is `market_data` with `company_introductions=true`. Complete the
  market workflow first, then apply the shared company-introduction component
  to its ranked result entities.
- “Compare A through F and briefly identify what each does” is `comparison`
  without standalone company introductions; short identities support the
  comparison.
- “Compare A through F and also give each company a separate three- or
  four-sentence introduction” is `comparison` with
  `company_introductions=true`. The comparison may cover the full set while
  the standalone introduction section uses its own presentation window.
- A mixed full-report and technical request remains `full_report` with an
  attached market-data modifier. Complete the live report first and keep its
  evidence separate from the quantitative result.
- When two requested deliverables are equally deep and cannot fit a coherent
  answer without materially compromising both, use `ambiguous` and ask which
  deliverable should take priority.
- If explicit length and depth requirements cannot both be satisfied, or a
  vague request such as “look at these companies” has no recoverable
  deliverable, use `ambiguous` and ask one focused clarification.

Treat a request as implicitly requiring `company_brief` only when answering it
requires separate quick context for each company, such as “What does each of
these companies do?” or “Give me the current situation for the companies
above.” Do not infer brief intent from an incidental mention, a discovery
list, or the assistant's own generated company names. An explicit request to
introduce companies produced by a screen sets the
`company_introductions=true` modifier without changing the screen's
`primary_task`.

Requests to retrieve an official “annual report,” “10-K,” “20-F,” or “filing”
must not enter `full_report`. Treat them as public-record retrieval outside the
generated report workflow.

## Resolve modifiers and entities

- Use `zh-CN` for a Chinese conversation unless the user requests another
  locale; use `en` for English.
- Accept a company name, ticker, exchange-ticker pair, or unambiguous reference
  to companies discussed earlier. Do not require a ticker.
- An expression such as “the companies above,” “the first three,” or “the
  second company” supplies entities only. It never determines `primary_task`.
- Current explicit identities override prior context. Preserve explicit user
  priority, then current-request order, then the order of the most recent
  relevant contextual company set.
- Keep `requested_entities`, `contextual_entities`, and
  `discovered_entities` distinct. Do not scan the whole conversation or add
  companies encountered incidentally during research.
- Preserve the owning workflow's server-side or evidence-backed ranking for
  discovered entities. Materialize that set after the owning workflow and
  before applying any result-dependent presentation window.
- Resolve identity before calling a full-report, comparison, company-brief, or
  single-company stock-data workflow. Ask only when exchange, issuer, or share
  class remains ambiguous after context, MCP candidates, and primary public
  sources.

## Hand off without reclassification

- Hand `company_brief` to
  [the Company Brief workflow](../workflows/company-brief.md). It must not call
  `prepare_company_report_generation`.
- Hand `full_report` to
  [the Company Report workflow](../workflows/company-report.md). The explicit
  report request authorizes immediate live research; do not ask whether to
  generate it.
- Hand `comparison` to
  [the Company Comparison workflow](../workflows/company-comparison.md).
- Hand `market_data` and supported structured-market `discovery` to
  [the Market Analysis workflow](../workflows/market-analysis.md).
- Whenever `company_introductions=true`, keep the selected owning workflow and
  additionally apply
  [the shared company-introduction component](company-introductions.md). Do
  not create a second `primary_task`.
- For `ambiguous`, ask one focused question and stop. Classify the user's
  answer as a new one-way pass; do not guess a specialist workflow.
- Do not use the generated company-report workflow for `news`, `comparison`,
  `market_data`, `discovery`, or `ambiguous`.
- For an official filing or public-record request, do not substitute a
  generated company report.

## Exchanges

- Match broad market names and codes against `get_available_exchanges`.
- For a single company, use the canonical exchange from
  `resolve_company_identity` instead of silently substituting a listing.
- If a requested stock-data exchange is unavailable, state that structured
  coverage is limited to ASX, CSE, NASDAQ, NYSE, TSX, and TSXV.
- A verified company outside those markets may still receive live company
  research through the `company-report` workflow.

## Dates

- “Latest” or no date: use each market's value from `get_latest_dates`.
- A specific day: use `as_of_date` and report when it is unavailable.
- “Since” a date: use both `start_date` and `end_date`, ending at the latest
  available data date.
- “Last month”: use paired boundaries for the previous calendar month.
- “Past month”: use paired boundaries for a rolling one-month range ending at
  the latest data date.
- Never send one range boundary alone or combine a range with `as_of_date`.
- Do not confuse the current calendar date with `data_date`.

## Filters

Translate explicit numeric thresholds directly. Examples:

| Request | Filter |
|---|---|
| RSI below 30 | `field=rsi_10`, `operator=lt`, `value=30` |
| 30-day return above 10% | `field=price_change_pct_30day`, `operator=gt`, `value=10` |
| Market cap between 10M and 100M | `operator=between`, `value=[10000000,100000000]` |

For “strong momentum” or another qualitative request, choose a transparent
ranking from available schema fields, state the definition, and avoid inventing
an absolute threshold the user did not request.

## Field selection

- Infer the smallest useful field set from the user's analytical question,
  then confirm every field with `get_stock_schema`.
- Do not reuse a fixed CSV template. A liquidity question may need price,
  volume, dollar volume, and price change; historical bars may need OHLC,
  adjusted close, and volume; momentum research may need price change,
  selected technical indicators, and volume.
- Include only measures that help answer the question. Let automatically added
  identity fields remain automatic instead of using them as a reason to add
  unrelated columns.
- If the goal is unclear but a field choice would materially change the
  result, offer a concise question-led field set or ask one focused follow-up.

## Analyst requests

Complete ordinary analyst requests without first explaining export policy:

- Translate “volume above one million and gain above five percent” into two
  AND-combined filters.
- Translate “NASDAQ dollar-volume Top 100” into an explicit descending sort,
  `top_n=100`, and only the fields needed to explain the ranking.
- Treat a 30-50 ticker watchlist as one exact `in` filter, not many requests.
- Use one paired date range for a single stock's one-year history.
- Use SQL aggregation for whole-NYSE advance/decline counts, averages, and
  distributions when a structured screen cannot return the statistic.
- For a broad match, analyze the complete matched range server-side and show
  only the first 200 rows in the current sort order.
- Create a CSV only after selecting a focused set of necessary fields and reading
  `eligible_by_query=true`.

Explain product boundaries only when the user asks for a complete row-level
table, row 201 onward, a next page, or a large/full-partition download.

## Ranking and evidence

- Use returned numeric fields for ranking and calculations.
- Preserve the denominator for rates and probabilities.
- Report missing values and whether rows were excluded.
- When rows are truncated, distinguish complete-range server-side analysis from
  the displayed preview. Do not fetch or reconstruct subsequent stock rows.
- Add external news context only when the user requests it and live browsing is
  available.
