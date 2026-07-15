# Answer format

Lead with the answer, then include only the sections needed for the request.

## Minimum evidence

- Source `data_date` or historical range
- Exchange scope
- Actual filters or ranking definition
- Number of rows examined and returned
- Missing-value handling
- Pagination, truncation, quota, or service warnings

For a ranking, show a compact table of the strongest evidence rows. For a rate
or probability, state numerator, denominator, and percentage. Do not imply that
the fixture, sample, or first page represents an entire market.

## Exports

When `create_csv_export` is used, provide the returned HTTPS download link and
expiry time. Call it a temporary export. Do not invent a local path or promise
that the link will remain available after expiry.

## Company reports

Identify the report as an English Anchises AI-generated analysis and include its
source, `generated_at`, expiration state, and any truncation warning. Summarize
the returned report rather than reproducing every section. Keep citations tied
to the claims they support. If a PDF URL is returned, describe its selected
chart range and do not imply that it is an official filing or immutable archive.

For `not_found`, state that no cached report exists without presenting it as an
error or claiming that a new report was requested.

## Caveat

End stock screens and rankings with a short analytical-information disclaimer.
Add external-market caveats only when they materially affect the conclusion.
