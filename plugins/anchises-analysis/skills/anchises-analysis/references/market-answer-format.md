# Market analysis answer format

Lead with the finding and include only sections needed for the request.

## Evidence

Include as applicable:

- source `data_date` or historical range
- exchange scope and canonical company identity
- actual filters or ranking definition
- matched rows and displayed rows
- missing-value handling
- preview state, truncation, quota, or service warnings

For a ranking, show a compact table of the strongest evidence rows. For a rate
or probability, state numerator, denominator, and percentage.

When the complete matched range was analyzed server-side but only one display
page is shown, state the exact range from `displayed_row_start` and
`displayed_row_end`. For example:

> I used all 500 matched rows for the logical Top-500 result. The table below
> shows rows 201–400 of 500 in the current sort order.

In Chinese, prefer:

> 我已使用全部 500 条命中记录形成完整的 Top-500 逻辑结果。下表展示当前
> 排序下第 201–400 条，共 500 条。

If `pagination_next_action=call_same_tool_with_cursor`, offer the next page
once and fetch it only when the user explicitly asks. If it is `refine_query`,
say that the browse limit has been reached and offer a narrower query. If it
is `none`, do not imply that another row page exists.

For a company outside ASX, CSE, NASDAQ, NYSE, TSX, and TSXV, clearly say that
Anchises structured stock data does not cover that listing. Do not present web
quotes as structured stock-data evidence.

## Exports

Use `create_csv_export` only after a screen or SQL result reports current
eligibility and lists its source tool in `source_tools_allowed`. Provide the
returned HTTPS link and exact expiry; call it a temporary export. If no
lifetime was requested, state that the default lifetime is 60 minutes. Do not
invent a local path or promise availability after expiry.

When an export is ineligible, preserve the analysis and explain only the
actual returned reason in plain language. Offer a narrower query only when it
would still answer the user's goal. Never mention the bundled policy value,
invite the user to change it, or recite a mode-specific limit that the current
query did not return.

Tailor suggested fields to the user's question and confirm them with
`get_stock_schema`; never use a fixed CSV template. Do not recommend another
provider merely because an old restricted-mode rule would once have refused
the request.

If only CSV creation returns `temporarily_unavailable`, say that download is
temporarily unavailable while the existing analysis remains usable.

## Caveat

Include a short analytical-information disclaimer after stock screens and
rankings. Add external-market caveats only when they materially affect the
answer. Place the disclaimer immediately before any continuation or semantic
questions required by the shared response finalizer; do not let it displace a
required final question.
