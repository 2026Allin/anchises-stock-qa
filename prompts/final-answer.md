# Final Answer Prompt

Write the visible answer in markdown.

Required order:
1. Interpretation
2. Result
3. Summary
4. By exchange, when more than one exchange is in scope
5. Top 30 qualifying stocks, when qualifying rows exist
6. Shell Risk Verification Notes
7. Files
8. Caveats
9. Quick takeaways

Interpretation must state:
- Exchange scope.
- Actual database date window.
- Event/filter definition.
- Financial filters and timing.
- Deduplication rule.
- Comparison and numerator/denominator logic.
- Missing-data handling.
- Output scoring/sorting rule.

Files section:
- Include the exact line `**Full results saved to filtered_results.csv**`.
- Include the absolute path to the primary `filtered_results.csv`.
- Include the MCP export CSV path when useful.

Style:
- Do not answer with only a bare probability, bare stock list, or short result-only summary.
- Keep tables concise but include enough evidence to audit the conclusion.
- State that the answer is analytical information, not financial advice.
