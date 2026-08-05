# MCP 0.7.2 handoff: Anchises Analysis client updates

## Ownership and deployment boundary

This document is the complete interface handoff from the Codex plugin team to
the MCP team. The plugin repository implements the client behavior, schemas,
Mock, and tests, but does **not** modify or deploy the real MCP service.

The MCP team owns these production changes:

- release the service as `0.7.2`;
- add the optional `client` input and required `client_update` output below;
- keep the other 11 tool descriptors and all current data-policy behavior
  unchanged;
- keep discovery at exactly 12 tools.

Until that deployment, production remains MCP `0.7.1` with internal contract
`1.7.0-draft`. The plugin sees the old input schema, calls
`get_connection_status` with `{}`, treats update status as `unknown`, and
shows no update text.

## `get_connection_status` input

Add one optional closed-object property named `client`. Omitting it must remain
a valid call. Its complete shape is:

```json
{
  "client": {
    "name": "anchises-analysis",
    "platform": "codex",
    "version": "0.6.0-dev.5",
    "release_id": "codex.20260805135302",
    "channel": "qa-v2-auth"
  }
}
```

The five nested fields are required whenever `client` is present, and no
additional fields are accepted. Each is a non-empty string of at most 128
characters. The recognized `name` is `anchises-analysis`, the recognized
`platform` is `codex`, `version` is a SemVer base version without build
metadata, and `release_id` uses `codex.` followed by a 14-digit UTC release
timestamp. The current supported channel is `qa-v2-auth`. Do not encode those
recognized values as JSON Schema `const` or `pattern` restrictions: the
runtime must be able to turn unrecognized string values into `unknown`.

Missing client metadata, an invalid version or release ID, an unknown channel,
or an unrecognized client must not turn the status call into a tool error.
Return `client_update.status=unknown` instead.

## `get_connection_status` output

Add a required closed object named `client_update` to every successful status
response:

```json
{
  "client_update": {
    "status": "current",
    "installed_version": "0.6.0-dev.5",
    "installed_release_id": "codex.20260805135302",
    "latest_version": "0.6.0-dev.5",
    "latest_release_id": "codex.20260805135302",
    "minimum_supported_version": "0.6.0-dev.5",
    "channel": "qa-v2-auth",
    "summary": null
  }
}
```

All eight fields are required. `status` allows exactly:

- `current`: the installed base version and release ID are current or newer;
- `update_available`: a newer allowed release exists;
- `unsupported`: the installed base version is below the minimum supported
  version;
- `unknown`: client metadata cannot be evaluated safely.

The other seven fields allow `string | null`. For a recognized client, echo
the validated installed version and release ID, and return the channel's
latest and minimum releases. For `unknown` caused by absent or invalid client
metadata, use `null` for fields that cannot be trusted. `summary` is a short,
non-executable release summary or `null`.

## Comparison and security rules

The server owns base-version and release-ID comparison. Compare SemVer first;
when base versions are equal, compare the 14-digit `codex` release timestamp.
Never recommend a downgrade.

The response must never contain:

- shell commands or executable fragments;
- a repository URL, Marketplace source, Git ref, plugin slug, or script path;
- authorization claims or instructions to bypass workspace policy.

The client uses its own allowlisted distribution source and fixed updater.
Version discovery and installation therefore remain separate trust domains.

## Contract and release acceptance

After MCP `0.7.2` is deployed, the plugin maintainer will run the read-only
production synchronizer. It detects `client` plus `client_update` together and
sets the checked-in internal contract to `1.8.0-draft`. A partial publication
of only one side is rejected.

MCP acceptance criteria:

1. `initialize` reports server version `0.7.2`.
2. `tools/list` contains exactly the existing 12 tools.
3. The other 11 descriptors are unchanged.
4. `get_connection_status({})` succeeds with `client_update.status=unknown`.
5. A valid current client returns `current` and echoes installed metadata.
6. Older allowed and below-minimum clients return `update_available` and
   `unsupported`, respectively.
7. Missing, malformed, or unknown-channel metadata returns `unknown`, not a
   tool error.
8. No response contains executable update or distribution data.
9. Existing connection state, quota, `data_policy`, cursor, SQL, export, and
   company-report behavior is unchanged.

Only after those checks pass should the plugin maintainer synchronize the
production snapshot, run live smoke tests, and refresh the plugin cachebuster.
