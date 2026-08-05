# Public service access

Apply this exactly once per user request whenever an Anchises Analysis Skill is
selected explicitly or implicitly. Do not apply it to unrelated requests.

1. Read [client-release.json](client-release.json), then inspect the currently
   published `get_connection_status` input schema before calling the tool.
2. If `inputSchema.properties.client` exists, call
   `get_connection_status` once with exactly:

   ```json
   {
     "client": {
       "name": "anchises-analysis",
       "platform": "codex",
       "version": "<client-release version>",
       "release_id": "<client-release release_id>",
       "channel": "<client-release channel>"
     }
   }
   ```

3. If the schema does not publish `client`, call it once with `{}` and set the
   conceptual update status to `unknown`. Never first send `client`, observe a
   failure, and retry with `{}`.
4. Retain any returned `client_update` object for the response finalizer and
   the update state machine. A missing, invalid, failed, or legacy update
   response is `unknown`, not a reason to retry.
5. Continue the business workflow when `status=active`.
6. Treat returned quota as shared global service capacity, not the user's
   personal allowance. Public access has no account-linked cross-session
   cumulative budget.
7. If an authentication challenge or identity-specific access state appears,
   stop and explain that the credential-free public service cannot complete
   the request. Do not start an authorization flow or ask for credentials.
8. On HTTP 503 or service unavailability, report the outage and do not retry in
   a loop.

Never ask the user to paste passwords, API keys, authorization codes, access
tokens, refresh tokens, session cookies, or download capabilities into chat.
If one is exposed, recommend revoking or rotating it and explain that
Anchises Analysis does not use chat-supplied credentials.

Send MCP only the arguments required by the selected tool. Do not send the
full transcript, unrelated personal information, or copied web-page content.
