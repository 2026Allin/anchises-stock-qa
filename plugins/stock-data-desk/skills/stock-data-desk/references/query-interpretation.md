# Query interpretation

## Exchanges

- Match exchange names and codes against `get_available_exchanges`.
- If the user gives no exchange, include every returned exchange unless the
  result size requires a clarifying scope.
- If a requested exchange is unavailable, state the supported list instead of
  silently substituting another market.

## Dates

- “Latest” or no date: use each market's value from `get_latest_dates`.
- A specific day: use that source date only; report when it is unavailable.
- “Since” a date: treat it as a range ending at the latest available date.
- “Last month”: use the previous calendar month.
- “Past month”: use a rolling one-month range ending at the latest data date.
- Do not confuse the current calendar date with `data_date`.

## Company reports

- Interpret “cached AI company report,” “AI company report,” or “your latest analysis” as
  a request for `get_latest_company_report` when exchange and ticker are known.
- Ask for or discover the exchange when the ticker could be listed on multiple
  markets. Do not silently guess an exchange.
- Interpret a named `ondemand` or `macmini` source literally; otherwise use
  `auto`.
- Interpret `1M`, `3M`, `6M`, `1Y`, `2Y`, or `MAX` only as the PDF chart range.
- Do not map “annual report,” “10-K,” “20-F,” “filing,” “today's news,” “search
  the web,” or “generate a new report” to the cached report tool.
- `not_found` means no cached report is available. It is not permission to start
  generation or search private data sources.

## Filters

Translate only explicit numeric thresholds into filters. Examples:

| Request | Filter |
|---|---|
| RSI below 30 | `field=rsi_10`, `operator=lt`, `value=30` |
| 30-day return above 10% | `field=price_change_pct_30day`, `operator=gt`, `value=10` |
| Market cap between 10M and 100M | `operator=between`, `value=[10000000,100000000]` |

For qualitative requests such as “strong momentum,” choose a transparent ranking
from available schema fields, state the ranking definition, and avoid inventing
an absolute threshold the user did not request.

## Ranking and evidence

- Use returned numeric fields for ranking and calculations.
- Preserve the denominator for rates and probabilities.
- Report missing values and whether rows were excluded.
- When a result is truncated, label it as a partial page or fetch subsequent
  pages before making a whole-market claim.
- Do not add live-news claims unless the user asks for external context and a
  suitable browsing capability is available.
