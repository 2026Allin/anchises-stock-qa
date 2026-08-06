# Global response finalization

Apply this policy exactly once after the answer body, data caveats, and
analytical-information disclaimer are ready. The substantive answer and the
operational plugin-update footer are separate. Finalize all business questions
first, then append an update footer only when
[plugin-update.md](plugin-update.md) requires it.

## Determine whether the answer is substantive

Treat a successful Brief, full report, company comparison, news analysis,
market screen, ranking, historical analysis, or quantitative interpretation as
substantive. A connection-status receipt, export link, or similarly narrow
operation may use `response_status=mechanical_result`.

## Apply the question matrix

Use `suggestions_allowed=false` when the user asks for no suggestions,
recommendations, next steps, or follow-up questions.

| `response_status` | Suggestions | Remaining introductions | Required ending |
|---|---|---|---|
| `success` | allowed | none | exactly one semantic question |
| `partial` | allowed | present | one continuation question, then one semantic question |
| `success` | disallowed | none | no question |
| `partial` | disallowed | present | exactly one continuation question |
| `needs_clarification` | either | either | exactly one focused clarification question |
| `failed` | either | either | no semantic question; give safe recovery guidance |
| `mechanical_result` | either | either | no question required |

A continuation question is necessary to finish the original request and is not
an optional product suggestion.

## Write continuation questions

When `remaining_intro_entities` is non-empty:

- Preserve their established order.
- For a concise explicit or contextual set, list every remaining company.
- For a long discovered set already shown in a ranked table, state the
  remaining count and ask whether to continue with the next five in that order
  or select companies from the table.
- Never ask to refresh or rerun the owning workflow unless the user requested
  fresh data.

## Choose one semantic question

Choose the most relevant unanswered direction for the completed work:

- `company_brief`: comparison, developments, catalysts and risks, market
  performance, or a full report for one completed company
- `full_report`: requested market measures, peer comparison, or a deeper
  examination of one unresolved catalyst or risk
- `comparison`: expand the comparison set, add market measures, or produce a
  full report for one compared company
- `market_data` or structured `discovery`: narrow the screen, introduce
  selected result companies, compare catalysts, or prepare a focused export
- `news`: assess impact, compare affected companies, or inspect market reaction

When introductions remain, the semantic question may concern only
`current_intro_batch`, even when the owning table displayed more companies.

Inspect the two most recent assistant messages. Classify their semantic
follow-ups by the families above, ignoring continuation questions. Exclude a
recent family when another relevant unanswered family exists. Reuse it only
when alternatives would be materially irrelevant, and avoid near-duplicate
wording.

Never use a generic question such as “Anything else?” Never offer work already
completed. Do not randomly rotate question families.

## Preserve final order

Use this order:

```text
answer body
-> data and risk caveats
-> analytical-information disclaimer
-> continuation question, when required
-> semantic question, when required
-> operational update footer, only when required
```

When a semantic question is required, it must be the final sentence of the
business answer. When only a continuation question is required, it must be the
final sentence of the business answer. An operational update footer may follow
as a separate final paragraph; it never replaces, merges with, or answers a
business question.

Do not show update text for `check_required`, `current`, `unknown`,
`release_inconsistent`, `unsupported_source`, a failed Tag check, or a release
already recorded in `installed_release_in_task`. Show the prescribed notice
only for `update_available`. Suppress it on a “暂不安装” acknowledgement, while
leaving the next substantive Anchises request eligible for a fresh check.
