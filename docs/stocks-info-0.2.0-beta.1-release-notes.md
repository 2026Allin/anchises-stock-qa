# Stocks Info 0.2.0-beta.1 Release Notes

Initial public beta release of Stocks Info.

Published by Anchises Capital.

Stocks Info provides credential-free public access to:

- stock-market discovery, screening, comparison, and ranking;
- historical schema inspection and bounded read-only SQL;
- cached English AI-generated company reports and report PDFs;
- source-linked host-side live company research when a cached report is missing
  or expired and the user confirms generation; and
- temporary CSV exports for completed screen or SQL queries.

The release bundles one complete `stock-data-desk` Skill with the production
Stocks Info MCP service. All service users share published rate, concurrency,
and usage limits.

Cached and live company reports are analytical information rather than official
company filings or financial advice. Live research is returned only in the
current conversation; it is not uploaded, cached, saved to a database, or
converted into a cached PDF.

CSV download URLs are short-lived bearer capabilities. The default lifetime is
60 minutes, and callers may request a lifetime from 60 through 3600 seconds.

Public Plugin Directory submission must scan:

```text
https://mcp.anchisesdata.com/mcp
```

The local Developer Mode App ID in `.app.json` is not the public submission
target.
