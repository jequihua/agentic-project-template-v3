# Artifact-First Method

The template is a repository-native operating method for agentic software work.

Core principle:

> Progress is an artifact becoming more explicit, reviewable, or correct.

The method prefers:

- visible files over hidden chat state;
- narrow slices over broad autonomy;
- explicit non-goals over impressive scope creep;
- the smallest correct useful change (YAGNI) over speculative architecture or a
  mechanically smallest diff, keeping structure earned by present evidence;
- findings-first review over generic approval;
- human stop/go over fully delegated ownership.

## Default Loop

1. Architect/reviewer prepares a narrow coding prompt.
2. Coder implements, verifies, and writes a self-report.
3. A review prompt or review checklist is prepared.
4. Reviewer checks code, artifacts, claims, and scope.
5. Verdict is recorded.
6. `PROJECT_STATE.md` and relevant indexes are updated.
7. Human owner decides whether to proceed, pause, or redirect.

### Closure Routing Ownership And Cadence

Step 6 updates only the surfaces whose cadence has been reached; do not mirror
one accepted change into every routing file.

| Surface | Default ownership and update cadence |
| --- | --- |
| `PROJECT_STATE.md` | update when accepted current truth changes |
| `prompts/INDEX.md` | update when a prompt is created or reaches terminal status |
| `05_governance/reviews/INDEX.md` | append/update when review evidence and a verdict exist |
| `MILESTONES.md` | update when a milestone is created or closes, not for every slice transition |
| `05_governance/review_log.md` | no routine duplicate row; pointer-only compatibility surface |

`05_governance/reviews/INDEX.md` is the canonical review routing surface.
`05_governance/review_log.md` remains only as a pointer-only compatibility
artifact and takes no routine review rows.

## Roadmap Uncertainty And Project Exclusions

Long-lived planning needs two words the loop above does not supply. Two optional
level-2 roadmap headings supply them: `## Not Yet Specified` for work inside the
destination that is not yet sharp, and `## Ruled Out` for work deliberately kept
outside it. Both registers are optional and manual-first — a project that uses
neither is fully valid — and neither adds a workspace, artifact type, dependency,
required `PROJECT_STATE.md` field, or tool.

Admit each concern exactly once:

- sharp and actionable: write a narrow slice;
- sharp but blocked on external evidence, ownership, or authority: record a
  question or block (`05_governance/current/question_policy.md`) — the work
  stays sharp, and a known blocker is never hidden as fog;
- in scope but not yet sharp enough to state a reviewable question or artifact
  transition: record a `Not Yet Specified` entry;
- outside the accepted destination: record a `Ruled Out` entry, subject to the
  authority rule below.

`Ruled Out` is a project-level terminal register. A prompt's `Non-Goals` are
slice-local fences that expire with their slice and may become valid work later;
they are never promoted into `Ruled Out` automatically.

Entries in both registers are ordinary top-level Markdown bullets. Neither
register is an executable slice, and neither enters the frontier.

Reconsider entries at an accepted slice or pass boundary, or during an explicit
architect planning pass — not on every loop action. At such a boundary a
`Not Yet Specified` entry may be left unchanged, sharpened into a proposed slice,
split, merged, or removed with a brief reviewed explanation.

The architect may record an exclusion that the accepted brief or an accepted
owner decision already establishes, and the reviewer checks that citation. A
proposed entry that would narrow or redraw the destination needs human approval
before it becomes an accepted exclusion. Removing or resurrecting an accepted
`Ruled Out` entry is always a Level 4, human-aware scope change.

An empty frontier is not completion evidence. Zero ready slices — with zero
`Not Yet Specified` entries beside them — never establish completion; only
explicit accepted closure evidence does.

Use either section only when it carries information:

```markdown
## Not Yet Specified

- Packaging hardening after the first consumer run — revisit when the run report
  shows which install and upgrade paths actually fail.

## Ruled Out

- Hosted multi-tenant control plane — excluded because the accepted brief
  requires a local-only tool; 2026-08-01; evidence:
  `00_brief/problem_statement.md`.
```

## Lightweight Context

`CONTEXT.md` files orient agents to folders. They are not the live project state.
The live state belongs in `PROJECT_STATE.md`.

## Commit Discipline

Git records coherent accepted states, not every conversational step. This is the
canonical commit rule; other surfaces reference it.

- Ordinary prompt passes do not imply a commit.
- After a positive review/verdict closes a milestone, the architect/reviewer agent
  normally performs Milestone Commit Closure (below) and creates the milestone
  commit. The architect/reviewer is the default committer at milestone closure.
- Coders do not commit during implementation unless explicitly assigned.
- Automation does not commit unless explicitly configured and authorized.
- Small post-milestone refinements may be batched, unless they change important
  rails (contracts, public API, state model) — those commit with their milestone.
- The human owner may pause, redirect, or override commit timing.
- Before risky experimentation, commit the last known-good state first.
- Pull request policy is separate and human-controlled (below).

### Milestone Commit Closure

When a milestone commit is being made (normally by the architect/reviewer at an
accepted closure, or by an explicitly authorized workflow), run this checklist
before staging:

1. Run validation, or record why it cannot be run.
2. Inspect `git status --short`.
3. Update `.gitignore` if generated junk or local state appears.
4. Optional local footprint glance: when tests, runs, data, memory, legacy
   review, or package builds may have produced local state, run
   `git status --short --ignored` or `python scripts/local_state_audit.py
   --root .`. Delete only clearly rebuildable caches/build output (for example
   `python scripts/local_cleanup.py --apply`), or record retained local roots in
   `LOCAL_STATE_NOT_COMMITTED.md`. This glance is optional and never a blocker.
5. Confirm no credentials, raw private data, caches, test output, local state, or
   unrelated files are being committed.
6. Stage only the accepted milestone files.
7. Inspect `git diff --cached --stat` (and `git diff --cached --name-only` when
   useful).
8. Commit with a clear milestone message.

### Pull Requests

`commit-ready` and `pull-request-ready` are different signals.

- Milestone commits may stack on a branch until a roadmap, release candidate, or
  human-defined work package closes.
- The suggested PR boundary is a completed roadmap, release candidate, or
  human-defined work package.
- The human owner may request a PR link at any point, regardless of that boundary.
- Agents and runners may report pull-request-ready, but must not open PRs by
  default.
- Opening a PR requires explicit human request or an explicitly authorized
  workflow.

## Adopting The Method

To adopt this method in a new or existing repository, follow
`docs/template_framework/migration_and_adoption.md`. Adoption is additive and
history-preserving by default.
