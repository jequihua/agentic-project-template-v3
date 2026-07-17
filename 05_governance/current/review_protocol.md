# Review Protocol

## Review Strictness Levels

Strictness levels are defined canonically in
`docs/template_framework/review_strictness_levels.md`. That file is the single
source for what each level requires. Do not restate the level definitions here.

In short: the strictness level (1-4) is the one ceremony axis. It decides prompt
size, review depth, artifact expectations, and closure burden. Workflow mode (see
`docs/template_framework/workflow_modes.md`) describes the kind of work, not its
weight. There is only one tiering axis.

## Fast-Close Guardrails

Fast-close (Level 1) is append-only. Never silently rewrite or delete historical
artifacts.

Fast-close is forbidden for:

- behavior or generated-output changes;
- public contract or API changes;
- schema changes;
- new dependencies;
- credentials or secrets;
- live-cost or cloud operations;
- security, privacy, or data-handling changes;
- substantive reinterpretation;
- any case where eligibility is uncertain.

Anything above requires a normal Level 2+ slice and review.

Fast-close is eligible only when all of these are true:

- the defect is confined to documentation or metadata wording;
- the intended replacement is objective and unambiguous;
- no behavior, generated output, public contract, schema, dependency,
  credential, cost, security, or data-handling behavior changes;
- a focused diff and deterministic check can prove closure;
- the current reference can be corrected without obscuring historical evidence.

When eligible, correct the current reference, append one compact correction
record linked to the finding, run the relevant deterministic check, and record
closure. Do not create a new full coding prompt, self-report, and review prompt
only to repair the tiny defect. If eligibility is uncertain, use Level 2.

A fast-close correction block must record:

- actor;
- date;
- reason;
- linked evidence or finding;
- whether behavior changed (must be "no" for fast-close).

Preserve the original text unless it contains secrets or harmful content. Use the
template at `prompts/templates/fast_close_correction.md`.

"Preserve the original text" applies to historical evidence. It does not require
an operative current-reference artifact to retain a known-wrong identifier; the
review/correction record preserves that history.

## Review Output Shape

Use findings-first review:

1. Confirmed issues by severity.
2. Scope discipline.
3. Verification performed.
4. Documentation and governance honesty.
5. Closure decision.
6. Recommended next move: pick exactly one.
