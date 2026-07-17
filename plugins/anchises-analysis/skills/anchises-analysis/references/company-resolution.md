# Company identity resolution

Use this reference before a single-company report or stock-data request when
the user provides a company name, ticker, exchange-ticker pair, or a clear
reference to a company discussed earlier.

## Extract the target

Build the smallest possible working identity from:

1. Explicit values in the current request.
2. The most recent single, unambiguous company identity in chat history.
3. A reference such as “it,” “this company,” “that stock,” or “the second
   company above.”

Current explicit values override earlier context. Do not inherit an exchange or
share class after the user switches companies. If several companies are in
scope, resolve the user's ordinal or descriptive reference before calling MCP.

Send only the extracted company query fields. Never send the full chat history,
web-page text, unrelated names, credentials, or personal information.

## Verify lightly with public sources

Use a small number of focused searches when a field is missing or identity is
ambiguous. Prefer, in order:

1. Exchange issuer or instrument pages.
2. Securities-regulator records.
3. Company investor-relations pages.
4. Official announcements and formal filings.

Confirm the issuer, exchange, ticker, and security/share class. Preserve ticker
dots, hyphens, slashes, and suffixes. Do not use a search-result snippet alone
for a decisive identity claim.

## Call the resolver

Call:

```json
{
  "query": "company name or ticker",
  "exchange_hint": "optional exchange",
  "purpose": "stock_data or company_report"
}
```

`query` is required. Omit `exchange_hint` unless it comes from the user,
unambiguous chat context, or primary-source verification. Set `purpose` to the
actual downstream workflow.

## Handle resolver states

### `resolved`

Use the returned canonical `company.exchange`, `company.ticker`, and
`company.company_name`. If a principal public source materially conflicts with
the master, do not guess: verify another primary source, account for historical
listing changes, or ask the user.

Check `instrument_type`, `is_active`, and `match_type`. Do not silently turn a
fund or non-operating instrument into an operating-company report.

### `ambiguous`

Use the returned candidates plus primary-source evidence to eliminate false
matches. Prefer an explicit exchange from the user and the security discussed
in the current context. Never silently choose among:

- the same ticker on different exchanges
- ordinary shares, depositary receipts, preferred shares, or another share
  class
- distinct companies with the same or a normalized similar name
- current and historical listings that cannot be reconciled

Ask one concise question only if exchange, issuer, or share class remains
uncertain after verification. Do not call downstream tools before resolution.

### `not_found_in_supported_markets`

For stock data, explain that Anchises structured coverage is limited to ASX,
CSE, NASDAQ, NYSE, TSX, and TSXV. Do not imply coverage outside those markets.

For a company report, this state is not a failure. Use primary public sources to
establish the external or historical `exchange`, `ticker`, and `company_name`,
then call `prepare_company_report_generation` with that verified triplet. The
preparation response should use `identity_source=host_supplied`,
`listing_status_verification_required=true`, and `selected_sector=Others`.

If the Host has no web-search capability and a complete identity cannot be
verified, do not rely on model memory. Ask the user for a verifiable exchange,
ticker, company name, or official link, or explain that verification cannot be
completed.

## Reuse within one conversation

After confirming a triplet, reuse it for later references to that same company
unless the user changes the issuer, listing, or share class. Broad screens and
multi-company rankings do not need single-company identity resolution.
