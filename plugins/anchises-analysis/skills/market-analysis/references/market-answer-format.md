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

When the complete matched range was analyzed server-side, say:

> I used the full matched range for server-side analysis. Below are only the
> first 200 rows in the current sort order. Row-level next pages are not
> available, but I can continue to calculate statistics, filters, rankings,
> and aggregates over the full result.

In Chinese, prefer:

> 我已使用完整命中范围进行服务端分析。下面仅展示当前排序下的前 200
> 条；不提供后续行级分页，但仍可以继续对完整结果进行统计、筛选、排名和聚合。

For a company outside ASX, CSE, NASDAQ, NYSE, TSX, and TSXV, clearly say that
Anchises structured stock data does not cover that listing. Do not present web
quotes as structured stock-data evidence.

## Exports

Use `create_csv_export` only after an eligible selective screen. Provide the
returned HTTPS link and exact expiry; call it a temporary export. If no
lifetime was requested, state that the default lifetime is 60 minutes. Do not
invent a local path or promise availability after expiry.

When an export is ineligible, preserve the analysis and explain that the
current export workflow is for focused research extracts. Offer to select
question-relevant fields and prepare a narrower CSV.

For a complete market or trading-day download:

1. State that the complete matched range can still be analyzed in the current
   conversation.
2. Explain that the current export workflow does not provide a complete
   row-level partition download.
3. Offer a focused research CSV or a suitable verified bulk-market-data API or
   licensed exchange-data vendor.

Tailor suggested fields to the user's question and confirm their names with
`get_stock_schema`; never use a fixed CSV template. If naming external
providers would help, verify their current official documentation and present
two or three matched options rather than an endorsement.

If only CSV creation returns `temporarily_unavailable`, say that download is
temporarily unavailable while the existing analysis remains usable.

## Caveat

Include a short analytical-information disclaimer after stock screens and
rankings. Add external-market caveats only when they materially affect the
answer. Place the disclaimer immediately before any continuation or semantic
questions required by the shared response finalizer; do not let it displace a
required final question.
