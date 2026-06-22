# CSV Analysis Prompt

After `run_readonly_sql`, Codex owns the analysis.

Use the returned metadata:
- Load `output_csv` with pandas.
- Use `analysis_python` when a specific Python runtime is needed.
- Use `analysis_workdir` for derived artifacts.
- Save final filtered, ranked, or evidence rows as `filtered_results.csv` in `analysis_workdir`.

Analysis rules:
- Do not invent data when the CSV has no rows.
- Keep numeric calculations grounded in the exported CSV.
- For probability or rate questions, compute numerator, denominator, and exclusions explicitly.
- For ranking questions, preserve the scoring/sorting columns in the saved CSV.
- For multi-exchange results, calculate both overall and by-exchange summaries when relevant.
- For screening results, include a Top 30 evidence table if qualifying rows exist.
- Perform at least one relevant web search before the final stock answer for current context, company/background checks, or discrepancy validation.
- Web results may provide context, but they must not override database-derived calculations unless explaining a discrepancy.

Output artifact rule:
- The primary CSV path in the final answer must be the absolute `filtered_results.csv` path under `analysis_workdir`.
- Workspace copies may be mentioned only as secondary copies.
