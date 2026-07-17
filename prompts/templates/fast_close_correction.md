# Fast-Close Correction

Fast-close is for low-risk corrections only. It is append-only: add a correction
block, never silently rewrite or delete prior text. Preserve the original text
unless it contains secrets or harmful content.

Correct operative text in a current-reference artifact in place. Preserve the
old value and rationale in this correction record; do not leave a known-wrong
identifier active merely to make the reference artifact append-only.

Use fast-close only when the replacement is objective, behavior does not change,
and a focused diff plus deterministic check can prove closure. Otherwise use
Level 2 or higher. An eligible fast-close does not need a new numbered coding and
review prompt pair.

The full rule lives in `05_governance/current/review_protocol.md`.

## Never Use Fast-Close For

- behavior or generated-output changes;
- public contract or API changes;
- schema changes;
- new dependencies;
- credentials or secrets;
- live-cost or cloud operations;
- security, privacy, or data-handling changes;
- substantive reinterpretation;
- any case where eligibility is uncertain.

Any of the above requires a normal Level 2+ slice and review.

## Correction

Actor:

Date:

Reason:

Linked evidence or finding:

Affected current-reference file and location:

Original issue:

Correction:

Behavior changed: no

Verification command and result:

Closure actor and decision:

Recommended next move:
