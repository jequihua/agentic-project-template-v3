---
type: framework_doc
framework_profile: "0.1-rc.1"
---

# Architect Operating Card

Operate the template; do not memorize its architecture. This card is the routine
architect surface. `PROJECT_STATE.md` is the only live-state source — this card copies
none of it.

## Normal loop

1. Read `PROJECT_STATE.md`.
2. Name one artifact transition.
3. Write one narrow prompt: exact paths, task, non-goals, verification, definition of done.
4. Leave artifacts legacy unless exact new paths are explicitly profiled.
5. For a profiled artifact: choose a type, use the two-field minimum, justify any extra field, run the profile checker.
6. Review body correctness separately from profile conformance.
7. Record one verdict and one next move.
8. After a positive milestone verdict, run milestone commit closure and commit accepted files.

## Four OKF rules

1. Legacy Markdown stays valid — do nothing with OKF unless a profiled artifact helps.
2. Opt in exact new artifact paths — never infer adoption from a directory, neighbour, tool, or dependency.
3. Use the minimum block (`type` and `framework_profile: "0.1-rc.1"`) and justify any optional field.
4. Conformance is not authority — a checker pass grants no truth, approval, freshness, safety, or execution.

## Legacy or profile?

```text
Ordinary legacy work?
  yes -> author normal Markdown; no OKF action.
  no  -> is an exact new artifact path explicitly opted in?
          no  -> stay legacy, or ask for an explicit decision.
          yes -> choose a type, use the minimum block, justify extras, run the checker.
```

## Choose a template-owned type

- Project knowledge: `brief`, `constraint`, `decision`, `analysis`.
- Implementation loop: `coding_prompt`, `review_prompt`, `self_report`, `review_report`, `verdict_record`.
- Delivery / framework: `delivery_plan`, `framework_doc`.

Package-owned types — `source`, `claim`, `entity`, `page` (llloom) and `milestone`,
`slice` (frutlups) — are not ordinary template choices; use them only when the owning
package is active. This aid is checked against the accepted registry, not a second
authority: a newly accepted template-owned type must be added here or a test fails.

## Escalate instead of improvising when the work changes

- existing history or migration;
- profile version, type, or contract;
- parser, dependency, writer, or generated authority;
- credentials, live cost, security, or data handling;
- llloom / frutlups execution semantics.

## Deeper sources

- Method and loop: `docs/template_framework/method.md`.
- Strictness levels: `docs/template_framework/review_strictness_levels.md`.
- Review protocol: `05_governance/current/review_protocol.md`.
- Authoring and migration: `docs/template_framework/okf_authoring_and_migration.md`.
- Profile contract: `08_pkg/okf_profile_v0_1.md`.
- Live state: `PROJECT_STATE.md`.
