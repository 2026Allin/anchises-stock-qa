---
name: anchises-stock-qa
description: Use when Codex needs to answer stock screening, ranking, probability, momentum, mining-stock, or exchange-scoped questions from a configured read-only Stocks_Tracker MySQL database by writing safe SQL, exporting CSV, and analyzing the CSV with pandas.
---

# Anchises Stock QA

Use this skill to answer stock-data questions from the user's configured
`Stocks_Tracker` database. The user should not need to name tools, provide SQL,
mention CSV, or describe the analysis process.

Automatic workflow:
1. Call `get_stock_qa_config` if configuration status is unclear.
2. Call `get_prompt_bundle` and follow the returned prompt markdown.
3. Discover current exchange codes with `get_available_exchanges`.
4. Inspect database context with `get_latest_dates` and `get_stock_schema`.
5. For historical date ranges, call `list_stock_tables`; call `get_table_schema` for selected tables if exact historical columns matter.
6. Translate the user's question into an internal query plan, then write safe read-only SQL.
7. Run `validate_readonly_sql`; revise unsafe SQL instead of asking the user to debug it.
8. Run `run_readonly_sql` with a short `output_name`. Omit `conversation_id` by default.
9. Read the returned `output_csv` with pandas for calculations, filtering, validation, and summaries.
10. Save final filtered or ranked evidence rows as `filtered_results.csv` in the returned `analysis_workdir`.
11. Perform at least one relevant web search before finalizing for current context, company/background checks, or external validation.
12. Write the final answer using the prompt bundle's final-answer rules.

Rules:
- Do not request or use `OPENAI_API_KEY`.
- Do not call OpenAI APIs or Code Interpreter from the plugin.
- Keep SQL to a single `SELECT` or `WITH ... SELECT`.
- Never run writes, DDL, session changes, stored procedures, file access, locks, sleeps/benchmarks, or system-schema queries.
- Database table names are the source of truth for exchange codes.
- If no exchange is specified, use all exchanges returned by `get_available_exchanges`.
- If the user mentions an exchange that is not discovered, refuse that exchange and state the discovered list.
- Keep numeric probabilities, rankings, and filters grounded in the exported CSV.
- Do not invent data if the database or CSV has no rows.
- The primary final CSV path must be the absolute `filtered_results.csv` path under the MCP `analysis_workdir`.

Reference routing:
- Prefer the live prompt files returned by `get_prompt_bundle`; they may be user-overridden.
- Use `references/workflow.md` only for additional tool, path, or failure details.
