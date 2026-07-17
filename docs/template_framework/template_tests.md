# Template Tests

Scaffold tests guard the template's rails. They are intentionally small,
structural, and fast. They are not a validation framework and must not pretend
the template is finished.

Run them with the command in `PROJECT_STATE.md`:

    python -m unittest discover -s tests

## What Belongs In A Scaffold Test

Test structural invariants and contracts, not prose:

- required files / docs exist;
- a contract and the file it governs do not drift (for example the
  `PROJECT_STATE` field contract vs `PROJECT_STATE.md`, or the self-report schema
  vs its onboarding copy);
- a single source of truth is actually referenced, not re-stated;
- controlled field values stay within their allowed set;
- workspace activation is explicit (active or inactive, never ambiguous);
- optional tools (llloom, frutlups) are never imported by the test suite.

## What Stays Documentation-Only

- philosophy, rationale, and guidance prose;
- anything that requires human judgment to evaluate;
- long narrative that would turn a test into a paragraph snapshot.

## Avoiding Brittle Tests

- check structure or classification, not exact wording, so harmless rewording
  does not break the suite;
- when a phrase is checked, it must protect a load-bearing guarantee (for example
  `append-only`, or `no runner is implemented`);
- match real import statements (line-anchored), not arbitrary mentions, so a
  guard does not flag its own assertion text;
- never assert a value a legitimate project would change (for example do not
  hard-assert `Memory mode: none`); assert membership in the allowed set instead,
  so the test stays downstream-safe.

## Optional Tools Must Not Be Imported

The suite must run without llloom or frutlups installed. A shared helper checks
that no `test_*.py` imports either tool. This keeps the template usable by
projects that never enable an optional lane.

## Adversarial Checks Belong In Reviews

Existence tests prove a guard is present; reviews prove it has teeth. A review
should temporarily break an invariant (drop a required field, add a forbidden
import) and confirm the matching test fails, then restore. This "verify, do not
trust" step lives in the review prompt, not in the committed suite.

## Reporting Test Changes

In a self-report, state the old and new test count (for example "16 -> 18") and
what each new or changed test protects. If a test was made stricter or a helper
was extracted, say so and why.
