# Company comparison workflow

Use only when the canonical `primary_task` is `comparison`. The entity set and
modifiers must already be fixed; do not reclassify or recursively add companies.

## 1. Define the comparison frame

Extract the requested dimensions. When the user does not specify them, choose a
small transparent frame that normally covers:

- core business and revenue drivers
- products, customers, and geographic or regulatory exposure
- competitive position and differentiation
- recent official developments
- financial profile or capital intensity when material
- catalysts, execution dependencies, and principal risks

State any inferred frame before presenting a judgment. Do not force seven
full-report sections or produce a separate Company Brief for every entity.

## 2. Resolve each company

Resolve every selected company independently under the shared identity rules.
Confirm exchange, ticker, issuer, and share class. Ask one concise question
only when a remaining ambiguity would materially change the comparison.

For an external-market or historical company, verify the identity through
exchange, regulator, investor-relations, or official sources. Continue with
Host web research; do not call `prepare_company_report_generation`.

## 3. Research comparable evidence

Use the same definition and period for every company on each dimension:

- Prefer primary sources for business structure, filings, results, guidance,
  strategy, and official developments.
- Use reputable independent sources for material outside context.
- Use exact dates or reporting periods and place links near supported claims.
- Distinguish reported facts, company guidance, and analytical inference.
- State when a measure is unavailable or not economically comparable rather
  than silently substituting a different metric.

Do not let one company receive materially deeper evidence solely because its
sources are easier to find.

## 4. Add structured market evidence only when relevant

For requested prices, returns, indicators, liquidity, or historical measures,
read
[the Market Analysis workflow](../../market-analysis/references/market-workflow.md).
Use the canonical supported-market listing for each company and align the date
or range.

Structured Anchises stock data is limited to ASX, CSE, NASDAQ, NYSE, TSX, and
TSXV. Keep external-market web evidence distinct and never imply structured
coverage where none exists.

## 5. Synthesize

Identify:

- the clearest similarities and differences
- which company leads on each requested dimension and why
- trade-offs or caveats that prevent a simple ranking
- the evidence date and any missing or non-comparable inputs

Do not create an overall winner unless the user's criteria support one. If the
user provides weights, apply them transparently and preserve the denominator.
