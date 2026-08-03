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
closure. The correction record lives beside the review evidence it relates to
(the milestone folder under `05_governance/reviews/`); any role may execute an
eligible fast-close when acting on an explicit reviewer finding or a recorded
human-owner instruction (an owner-reported defect is transcribed to a durable
note first and linked as the finding). Do not create a new full coding prompt,
self-report, and review prompt only to repair the tiny defect.
If eligibility is uncertain, use Level 2.

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

## Convergence And Disposition

Rounds, recurrence, the escalation ladder, the acceptance envelope, and
corrective-pass re-review scope are defined canonically in
`docs/template_framework/closure_convergence.md`. In short: reviews are
numbered rounds recorded in `05_governance/reviews/INDEX.md`; blocking
findings name their violated invariant; the third same-invariant recurrence
stops the correction loop and routes to architect reassessment with human
awareness; and a reviewer may not widen the acceptance envelope — a newly
desired property is an `envelope expansion` finding routed to the architect
as change control, never an in-place `needs_work` demand.

Every finding carries a disposition and a plane word (product / harness /
evidence / authority / environment):

| Disposition | Meaning | Default routing |
| --- | --- | --- |
| P0 | imminent safety, security, data-loss, credential, or destructive-authority risk | stop immediately; human awareness |
| P1 | incorrect behavior, broken contract, invalid candidate identity, or material architectural error | `needs_work` |
| P2 | material bounded defect in authority, evidence, compatibility, or maintainability | `needs_work` while unresolved |
| P3 | clarity, style, or follow-up that cannot misroute execution or falsify acceptance | may accompany `pass` as named follow-up |

An unresolved P0-P2 finding never coexists with `pass`. There is no
"non-blocking P2": if independent review cannot show a defect is unable to
affect behavior, authority, safety, evidence truth, or routing, it stays P2.
`needs_work` routes to the implementer of the reviewed slice; use `blocked`
when closure depends on an actor other than that implementer (another role,
external evidence, or authority) — the verdict line's next move then names
the owning actor.
A human owner may record an explicit external waiver naming the exact finding
and the reviewed identity; a waiver is a separate decision record and never
rewrites the review or its verdict.

## Review Output Shape

Use findings-first review:

1. Confirmed issues by severity.
2. Scope discipline.
3. Verification performed.
4. Documentation and governance honesty.
5. Closure decision.
6. Recommended next move: pick exactly one.

Each finding carries its P0-P3 disposition and plane word; blocking findings
name the violated invariant. On round 2 or later, review only the previously
blocking findings, the delta, and invalidated evidence.

End every review report with exactly one final verdict line:

`Verdict: pass | needs_work | blocked | override — next: <one move>`
