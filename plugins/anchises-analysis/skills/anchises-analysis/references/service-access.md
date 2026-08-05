# Public service access

Apply this exactly once per substantive business request whenever an Anchises
Analysis Skill is selected explicitly or implicitly. Operational plugin-update
authorization and decline routes follow [plugin-update.md](plugin-update.md)
and do not call MCP.

1. Call `get_connection_status` exactly once with `{}`. Plugin version checking
   is a separate local Tag workflow and never changes this MCP call.
2. Continue the business workflow when `status=active`.
3. Treat returned quota as shared global service capacity, not the user's
   personal allowance. Public access has no account-linked cross-session
   cumulative budget.
4. If an authentication challenge or identity-specific access state appears,
   stop and explain that the credential-free public service cannot complete
   the request. Do not start an authorization flow or ask for credentials.
5. On HTTP 503 or service unavailability, report the outage and do not retry in
   a loop.

Never ask the user to paste passwords, API keys, authorization codes, access
tokens, refresh tokens, session cookies, or download capabilities into chat.
If one is exposed, recommend revoking or rotating it and explain that Anchises
Analysis does not use chat-supplied credentials.

Send MCP only the arguments required by the selected tool. Do not send the
full transcript, unrelated personal information, or copied web-page content.
