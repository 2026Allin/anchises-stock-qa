# Query Planning Prompt

Use this prompt before writing SQL for a natural-language stock question.

Goal:
- Convert the user's request into a concrete internal query plan.
- Do not show the plan unless the user asks for it.
- Prefer returning enough row-level evidence for pandas analysis over over-filtering in SQL.

Exchange handling:
- Call `get_available_exchanges` before deciding exchange scope.
- If no exchange is specified, use all exchanges discovered from the configured database.
- If the user requests an exchange that is not discovered from the database, reject that exchange and state the discovered exchange codes.
- Built-in or user-configured aliases may map natural-language names to discovered exchange codes, but database table names are the source of truth.

Date handling:
- Treat "latest", "today", and missing dates as the latest available database date returned by `get_latest_dates`.
- For date ranges, call `list_stock_tables` with the requested exchanges and date window, then use only the actual available table dates returned by the tool.
- If the date range spans tables whose columns may differ, call `get_table_schema` for the selected daily tables before writing SQL.
- If the requested start date predates available data, use the available start date and state the adjustment in the final answer.

Schema-change handling:
- If a query fails because a column is missing, or if the user asks whether table structure changed, call `get_schema_snapshot`.
- For exact columns on any historical or changed table, call `get_table_schema` instead of assuming the latest daily schema applies to every date.

Plan fields to decide:
- Exchange scope.
- Actual database date window.
- Event definition and numeric filters.
- Financial filters.
- Deduplication rule.
- Numerator/denominator logic for probability or rate questions.
- Missing-data handling.
- Output fields needed for pandas analysis.
- Sorting/scoring rule for ranked output.

Field mapping:
- Market_Cap -> capitalization
- Volume_traded -> Volume_Traded
- Price_close -> Price_Close
- Price_open -> Price_Open
- Price_high -> Price_High
- Price_low -> Price_Low
- Price_change_pct_* -> price_change_pct_*
- Volume_change_pct_over_avg* -> volume_change_pct_over_avg*
- Avg_volume_* -> avg_volume_*
- Rsi_* -> rsi_*
- Macd_* -> macd_*
- Mfi_10 -> mfi_10
- Stoch_* -> stoch_*
- Williams_r -> williams_r
- Cci_20 -> cci_20
- Bb_* -> bb_*
- Sma_* -> sma_*
- Ema_* -> ema_*
- Atr_10 -> atr_10
- Roc_10 -> roc_10
- Corr_* -> corr_*
