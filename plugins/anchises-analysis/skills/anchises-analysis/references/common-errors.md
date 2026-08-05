# Common error handling

Follow safe returned guidance without probing hidden state:

- `rate_limited`: retry only after the supplied delay when a retry remains
  useful.
- `concurrency_limited`: wait for the existing query to finish; do not start a
  retry loop.
- `usage_limit_exceeded`: state the returned reset information. Do not invent
  usage counts or reset dates.
- `resource_not_found`: rerun the original workflow only when needed; never
  edit or probe an opaque capability.
- `service_not_activated`, an authentication challenge, or HTTP 503: stop,
  state the public-service condition, and suggest retrying later without an
  automatic loop.

Do not reveal internal request, connection, policy, or principal identifiers.
Preserve user-safe warnings and recovery guidance returned by the service.
Workflow-specific report and market-data errors remain with their owning
Skills.
