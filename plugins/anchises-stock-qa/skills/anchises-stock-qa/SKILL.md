---
name: anchises-stock-qa
description: Use when Codex needs to answer stock screening, ranking, probability, momentum, mining-stock, or exchange-scoped questions from a configured read-only Stocks_Tracker data source by writing safe SQL, exporting CSV, and analyzing the CSV with pandas.
---

# Anchises Stock QA

Use this skill to answer stock-data questions from the user's configured
`Stocks_Tracker` data source. The user should not need to name tools, provide SQL,
mention CSV, or describe the analysis process.

Setup workflow:
1. If the user says "Set up Anchises Stock QA", asks how to configure the plugin, asks to reset or replace the API token, or configuration is missing, call `get_setup_instructions`.
2. Show the returned `commands.setup_or_reset_token` command as the primary command to run in Terminal.
3. Explain that the same command works for first-time setup and later token reset, and that it keeps existing settings unless the user runs the force command.
4. Do not ask the user to find the README or browse the plugin cache directory.
5. Do not ask the user to paste the API token into chat.
6. After setup, suggest asking "Check the Anchises Stock QA connection".

Custom prompt workflow:
1. If the user asks to view, customize, edit, tune, reset, or restore Anchises Stock QA prompts, use the custom prompt tools instead of editing plugin files directly.
2. First call `get_prompt_catalog` and show the user the editable prompt names, purposes, active source, built-in path, user path, and a short preview.
3. Recommend the most relevant prompt based on the user's goal, but wait for the user to choose a prompt and describe the desired change.
4. After the user chooses, call `read_custom_prompt` for that prompt and use the active content as the edit base.
5. Propose a concise editing plan and, when ready, call `preview_custom_prompt_update` with the complete revised markdown to show a diff and current hash.
6. Do not call `write_custom_prompt` until the user confirms the preview. Pass `expected_current_hash` from the preview result when writing.
7. After writing, call `read_custom_prompt` or `get_prompt_catalog` again to verify the prompt now uses the user file.
8. Call `reset_custom_prompt` only when the user wants one prompt to return to the built-in version.
9. Explain that custom prompts are stored outside the plugin install and are not overwritten by plugin upgrades.

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
10. Save final filtered or ranked evidence rows as `filtered_results.csv` in the returned `analysis_workdir`; write it directly with pandas rather than copying through shell-only helpers.
11. Perform at least one relevant web search before finalizing for current context, company/background checks, or external validation.
12. Write the final answer using the prompt bundle's final-answer rules.

Rules:
- Do not request or use `OPENAI_API_KEY`.
- Do not call OpenAI APIs or Code Interpreter from the plugin.
- Do not edit files under the plugin `prompts/` directory for user customizations; use custom prompt tools.
- Keep SQL to a single `SELECT` or `WITH ... SELECT`.
- Never run writes, DDL, session changes, stored procedures, file access, locks, sleeps/benchmarks, or system-schema queries.
- Database table names are the source of truth for exchange codes.
- If no exchange is specified, use all exchanges returned by `get_available_exchanges`.
- If the user mentions an exchange that is not discovered, refuse that exchange and state the discovered list.
- Keep numeric probabilities, rankings, and filters grounded in the exported CSV.
- Do not invent data if the database or CSV has no rows.
- The primary final CSV path must be the absolute `filtered_results.csv` path under the MCP `analysis_workdir`.
- Do not use GNU-specific commands such as `install -D` for result files; macOS users may have BSD tools. Use pandas direct writes, or `mkdir -p` followed by `cp` when copying is unavoidable.

Reference routing:
- Prefer the live prompt files returned by `get_prompt_bundle`; they may be user-customized.
- Use `references/workflow.md` only for additional tool, path, or failure details.
