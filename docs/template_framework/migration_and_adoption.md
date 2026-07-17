# Migration And Adoption

How to adopt this v3 template in a new repo or an existing v1-style project.

Principle: **adoption is additive and reversible.** Do not destroy, move, or
reinterpret history without explicit human approval and a recorded decision.

## New Project

1. Copy the scaffold (or use it as a GitHub template).
2. Fill `PROJECT_STATE.md` honestly: status, profile, active workspaces, modes
   (default `Memory mode: none`, `Frutlups mode: manual`), objective, next action,
   validation command.
3. Choose the base profile and activate only the optional workspaces you need
   (see `project_profiles.md`). Leave the rest inactive as scope markers.
4. Run the scaffold tests to confirm the rails are intact.
5. Start the loop: the architect/reviewer writes the first coding prompt.

## Existing (v1-style) Project — Additive First

Do the additive steps before any cleanup:

1. Add the v3 control surfaces without deleting anything:
   - `PROJECT_STATE.md` (the single current-state surface);
   - `CLAUDE.md` source-of-truth order and workspace map;
   - `05_governance/current/` protocols (review, fast-close, and memory/frutlups
     posture only if those lanes are used).
2. Point existing docs at `PROJECT_STATE.md` instead of restating live state.
3. Keep existing prompts, reviews, verdicts, and notes exactly where they are —
   they remain historical evidence.
4. If the repo already has memory or loop tooling, set the matching controlled
   mode value; do not enable a lane you are not using.
5. For an existing codebase, fill `90_legacy_review/` before major changes, and
   record any interpretation of old history in `migration_decision_log.md`
   (append-only).
6. Only after the v3 surfaces are in place and trusted, consider optional
   cleanup — and only with explicit human approval (see below).

## History Preservation (defaults)

- Do not move or delete historical v1 prompt/review artifacts by default.
- Do not run destructive prune scripts as a default migration step.
- Do not rewrite old artifacts just to fit v3 naming.
- Interpret old history with append-only notes or the migration decision log,
  never by editing the original record.
- Physically pruning optional workspaces is an explicit human/project decision,
  recorded in `migration_decision_log.md` — never the default.

## Front Matter (OKF Profile)

Front matter is optional and applies to **new artifacts only**; legacy
no-frontmatter documents remain the default and are never retrofitted by default.
Opt-in is per exact artifact path, and the minimum block is just `type` and
`framework_profile: "0.1-rc.1"`. For the copy-ready per-type examples, the adoption
and rollback sequence, and profile-version change control, see the canonical guide
`docs/template_framework/okf_authoring_and_migration.md`.

## Commit Cadence / Checkpoints

- Commit after each accepted slice or adoption step so `git log` reflects the
  loop.
- `PROJECT_STATE.md` should say whether there are accepted-but-uncommitted
  artifacts.

## Human Stop/Go Points

Get explicit human approval, and record the decision, before: deleting or moving
history, running any prune/cleanup, enabling an optional lane (memory or
frutlups), or any other irreversible step.
