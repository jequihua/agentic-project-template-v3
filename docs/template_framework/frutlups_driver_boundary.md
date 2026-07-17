# Frutlups Driver Boundary

Status: specification boundary only. No runner is implemented in this template,
and this pass does not implement one.

A future thin local runner MAY:

- consume `frutlups status --json`;
- route generated prompt files to configured sinks;
- wait for expected artifacts to appear;
- record verdicts only from a valid review report;
- report `commit-ready` after an accepted verdict / milestone closure;
- report `pull-request-ready` at a suggested PR boundary (completed roadmap,
  release candidate, or human-defined work package);
- resume from durable repository state.

The runner MUST NOT commit or open pull requests by default. Auto-commit and PR
creation require explicit configuration and human authorization, and a stop
condition must never be bypassed to create a commit or open a PR (boundaries:
`docs/template_framework/method.md` Commit Discipline). The human owner may
request a PR link at any point.

In manual agent operation the architect/reviewer is the default committer at
milestone closure; this boundary governs only a runner. A runner authorized to
commit MUST perform the same Milestone Commit Closure checks (`.gitignore`
hygiene, `git status`/staged-diff review, staging only accepted milestone
changes) and stop if junk, secrets, local state, invalid reports, or unrelated
changes are detected.

The runner MUST stop cleanly on:

- `blocked` verdict;
- `override` required;
- invalid self-report;
- invalid review report;
- no frontier;
- memory gate failure;
- environment gate failure.

The runner stays thin on purpose: frutlups owns durable state, validation, gates,
deterministic prompts, and resumability. The runner only coordinates sinks and
waits. It must never hand-edit loop state, invent verdicts, or bypass a gate.
