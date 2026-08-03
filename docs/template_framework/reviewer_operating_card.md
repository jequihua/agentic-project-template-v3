# Reviewer Operating Card

Routine surface for running one review. `PROJECT_STATE.md` is the only
live-state source — this card copies none of it.

## Normal review

1. Read `PROJECT_STATE.md`, the coding prompt under review, the coder
   self-report, and the changed files — nothing else by default.
2. When the bundle cites repository paths or `test_*` identifiers, run
   `python scripts/artifact_integrity_preflight.py` on the exact artifacts
   before semantic review.
3. Check the round in the `Round` column of
   `05_governance/reviews/INDEX.md`. On round 2 or later, review only the
   previously blocking findings, the delta, and invalidated evidence.
4. Judge substance against the acceptance envelope: the prompt's Task,
   Non-Goals, Verification, and Definition Of Done, plus baseline safety
   rails. You may not widen the envelope — record a newly desired property
   as `envelope expansion` change control for the architect.
5. Classify every finding P0-P3 with a plane word (product / harness /
   evidence / authority / environment); a blocking finding names its
   violated invariant (table: `05_governance/current/review_protocol.md`).
6. Check recurrence: has this invariant failed before in this slice's
   lifecycle? Name the prior report and apply the escalation ladder
   (`docs/template_framework/closure_convergence.md`).
7. Write findings-first output: confirmed issues by severity; scope
   discipline; verification performed; documentation and governance
   honesty; closure decision; exactly one recommended next move.
8. End with the single verdict line:
   `Verdict: pass | needs_work | blocked | override — next: <one move>`.
9. Update `05_governance/reviews/INDEX.md` when the report and verdict
   exist.

## Hard rules

- Unresolved P0-P2 never coexists with `pass`; a P3 may accompany `pass` as
  a named follow-up. Uncertain severity stays P2.
- One verdict, one next move — never a menu.
- Candidate mode only: name the exact candidate identity reviewed, and
  recording the verdict must change no candidate bytes
  (`docs/template_framework/candidate_review_acceptance.md`).
- A universal term (`all`, `every`, `no path`, `exact`, `independent`) in
  blocking evidence needs a bounded domain and an independent falsifier;
  if the domain cannot be bounded, narrow the claim.

## Escalate instead of improvising

- the third same-invariant recurrence, or corrections that keep enlarging
  the assurance harness;
- a powerful harness (deletes, installs, signals, or mutates environment)
  inside the evidence;
- a candidate identity mismatch;
- anything on the architect card's escalation list (contracts, credentials,
  live cost, execution semantics).

## Deeper sources

- Convergence contract: `docs/template_framework/closure_convergence.md`.
- Disposition table and output shape:
  `05_governance/current/review_protocol.md`.
- Strictness levels: `docs/template_framework/review_strictness_levels.md`.
- Candidate lifecycle:
  `docs/template_framework/candidate_review_acceptance.md`.
- Live state: `PROJECT_STATE.md`.
