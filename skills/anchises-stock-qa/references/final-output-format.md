# Anchises Stock QA Final Output Format

This file applies only to the `anchises-stock-qa` skill/plugin. It controls the visible final answer after Codex has exported the SQL result CSV, analyzed it with pandas, and completed required web checks.

Do not expose private chain-of-thought. The `Interpretation` section should show the final screening/query rules Codex derived from the user question, not hidden reasoning.

## Required Section Order

For probability, rate, persistence, screening, ranking, momentum, or mining-stock answers, use these sections in this order:

1. `**Interpretation**`
2. `**Result**`
3. `**Summary**`
4. `**By exchange**` when more than one exchange is in scope
5. `**Top 30 qualifying stocks**` when qualifying rows exist
6. `**Shell Risk Verification Notes**`
7. `**Files**`
8. `**Caveats**`
9. `**Quick takeaways**`

## Interpretation

`**Interpretation**` is mandatory. It must state the concrete screening/query rules Codex chose before doing the calculation.

Write it as a short rule list, for example:

- `Universe`: exchanges, instruments, discovered-exchange handling, and what default was used if the user did not specify an exchange.
- `Date window`: requested window, actual database window, latest table/date per exchange, and any unavailable dates.
- `Event rule`: spike, breakout, momentum, volume, mining-stock, shell-risk, or other event/filter definition.
- `Financial filter`: market cap, price, liquidity, sector/metal, company type, or other thresholds, including whether each threshold is applied on the event date, latest date, or across the window.
- `Deduplication rule`: first event per stock, latest row per stock, one row per ticker/exchange, or all event rows.
- `Comparison rule`: current/latest close, rounded-vs-raw comparison, benchmark date, return formula, numerator/denominator definition, and missing-price handling.
- `Output rule`: score column chosen, Top 30 ordering rule, and CSV saving rule.

Do not write only vague text such as "I analyzed the CSV." The user should be able to read `Interpretation` and know exactly what SQL/pandas screening logic was applied.

## Result

`**Result**` must give the direct answer first:

- For probability/rate questions: numerator, denominator, percentage, and the plain-English interpretation.
- For rankings/screens: number of qualifying rows and the main ranked conclusion.
- For rounding-sensitive price comparisons: show the rounded result and mention the raw unrounded result if it differs.

## Summary

`**Summary**` must be a markdown table with the key metrics for the whole analysis. Use actual database dates, row counts, numerator/denominator, probability/rate, median/mean returns, and missing-row counts when relevant.

## By Exchange

Use `**By exchange**` whenever more than one exchange is included. Show counts, numerator/denominator or score summaries, and probability/rate by exchange when relevant.

## Top 30 Qualifying Stocks

This section is mandatory whenever the qualifying dataframe has at least one row, even if the user only asked for a probability.

Rules:

- Save all qualifying/evidence rows to `filtered_results.csv`.
- Display only Top 30 rows in the markdown when there are more than 30.
- Add the exact line `**Showing Top 30 of [TOTAL] results.**` when total rows exceed 30.
- Sort by an analysis-specific score. For post-spike persistence, use `POST_SPIKE_SCORE` based on return from first spike close to latest comparison close.
- The table must include at least: `TICKER`, `name`, score column, `Shell_Risk`, `Shell_Risk_Flags`, `EXCHANGE`, event date, event close, latest/comparison close, return percentage, and Yes/No result column.

## Shell Risk Verification Notes

This section is mandatory.

- If Medium/High/Critical shell-risk rows appear in the displayed Top 30, include concise web-verification notes.
- If none appear, write `None required: no Medium/High/Critical rows appeared in the Top 30.`
- Keep table `Shell_Risk_Flags` short. Put details here, not inside the table cell.

## Files

This section must include:

```markdown
**Full results saved to filtered_results.csv**
Primary CSV path: /absolute/path/to/plugin/outputs/.../filtered_results.csv
MCP export CSV: /absolute/path/to/plugin/outputs/.../<output_name>.csv
```

The primary CSV path must be under the MCP `output_dir`. A Codex workspace copy may be listed only as a secondary copy.

## Caveats

Include calculation caveats, database coverage caveats, missing-data assumptions, web-search limitations, and the note that the answer is analytical information only, not financial advice.

## Quick Takeaways

End with `**Quick takeaways**` and 2-4 bullets. Keep them concrete and tied to the database result.
