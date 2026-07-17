# Query interpretation

## Company identity and reports

- Interpret “调研,” “研究,” “背调,” “company research,” “company report,”
  “investment research,” and requests about a company's business, assets,
  products, customers, competition, finances, capital structure, management,
  catalysts, or risks as a direct live company-report request.
- Do not ask the user whether to generate after that intent is explicit.
- Accept a company name, ticker, exchange-ticker pair, or unambiguous reference
  to a company discussed earlier. Do not require a ticker.
- Resolve identity before calling a report or single-company stock-data tool.
  Ask only when exchange, issuer, or share class remains ambiguous after using
  context, MCP candidates, and primary public sources.
- Do not map a request to retrieve an “annual report,” “10-K,” “20-F,” or
  “filing,” or a news-only request, to the generated company-report workflow.
- Use `zh-CN` for a Chinese conversation unless the user requests another
  locale; use `en` for English.
- For mixed company research and technical analysis, finish the live research
  first and then execute the requested stock analysis with the same canonical
  supported-market identity.

## Exchanges

- Match broad market names and codes against `get_available_exchanges`.
- For a single company, use the canonical exchange from
  `resolve_company_identity` instead of silently substituting a listing.
- If a requested stock-data exchange is unavailable, state that structured
  coverage is limited to ASX, CSE, NASDAQ, NYSE, TSX, and TSXV.
- A verified company outside those markets may still receive live company
  research through `prepare_company_report_generation`.

## Dates

- “Latest” or no date: use each market's value from `get_latest_dates`.
- A specific day: use that source date and report when it is unavailable.
- “Since” a date: use a range ending at the latest available data date.
- “Last month”: use the previous calendar month.
- “Past month”: use a rolling one-month range ending at the latest data date.
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

## Ranking and evidence

- Use returned numeric fields for ranking and calculations.
- Preserve the denominator for rates and probabilities.
- Report missing values and whether rows were excluded.
- When a result is truncated, label it as partial or fetch subsequent pages
  before making a whole-market claim.
- Add external news context only when the user requests it and live browsing is
  available.
