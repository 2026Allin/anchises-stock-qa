---
name: anchises-analysis
description: Use Anchises Analysis for public-company introductions, deep company reports, company comparisons, structured stock-market analysis or discovery, and Anchises Analysis installation, update, or persistent release-check requests. Serve as Claude's single visible Anchises Analysis entry, classify exactly one primary task, preserve shared request state, and load exactly one canonical internal workflow when needed. Do not use for unrelated news-only questions, official filing retrieval, or incidental company mentions.
---

# Anchises Analysis for Claude

Expose one Claude-facing Skill while reusing the canonical Anchises Analysis
workflows without copying their business prompts.

## Load the canonical coordinator

Read the complete canonical coordinator at
[plugins/anchises-analysis/skills/anchises-analysis/SKILL.md](../../../../plugins/anchises-analysis/skills/anchises-analysis/SKILL.md)
and follow it as the governing workflow. Resolve every relative link in a
canonical file from the directory containing that canonical file.

Classify the request exactly once and preserve the coordinator's shared state,
including `primary_task`, modifiers, entity sets, `plugin_update_check`, and
service-access state. Never repeat the cache probe, remote Tag lookup, or
`get_connection_status({})` call when loading an internal workflow or applying
a modifier.

## Load one internal workflow

Claude must not expose the specialist files as additional Skills. Treat them
as internal workflow documents and read exactly the one selected by the
canonical coordinator:

| `primary_task` | Internal workflow |
|---|---|
| `company_brief` | [Company Brief](../../../../plugins/anchises-analysis/skills/company-brief/SKILL.md) |
| `full_report` | [Company Report](../../../../plugins/anchises-analysis/skills/company-report/SKILL.md) |
| `comparison` | [Company Comparison](../../../../plugins/anchises-analysis/skills/company-comparison/SKILL.md) |
| `market_data` or supported structured `discovery` | [Market Analysis](../../../../plugins/anchises-analysis/skills/market-analysis/SKILL.md) |

For `plugin_update`, `plugin_update_permission`, a declined update, or an
acknowledgement after a completed update, remain in the canonical coordinator
and follow its platform-specific Claude update protocol. For `news`, official
record retrieval, or `ambiguous`, follow the coordinator's host or
clarification route without loading a specialist workflow.

The loaded canonical workflow controls tools, research, privacy, formatting,
failure behavior, final questions, and update-footer placement. A workflow's
instruction to check the plugin or service is already satisfied when the
shared state contains that result; reuse it instead of running either check
again. Always call the product **Anchises Analysis** in user-facing text.
