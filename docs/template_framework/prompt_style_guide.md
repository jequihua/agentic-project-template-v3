# Prompt Style Guide

Prompts should make the next action safer without becoming a mini manual.

## Rules

- Point to stable artifacts instead of repeating long history.
- Use a short read-first list. Normal prompts should aim for five or fewer files.
- State active workspaces.
- State non-goals.
- State verification.
- State output paths.
- State definition of done.
- Use `rg` / `rg --files` for search instructions.
- Keep llloom and frutlups optional unless `PROJECT_STATE.md` enables them.
- Do not copy volatile live state into durable prompts or reports. Active prompt
  numbers, index row counts, worktree contents, workspace lists, and next actions
  should be linked or derived from `PROJECT_STATE.md` and indexes. If an observed
  value is evidence, label it as a dated snapshot.
- When the slice cites repository paths or test identifiers, require the
  read-only `scripts/artifact_integrity_preflight.py` check before semantic
  review.

## Size Budgets

Budgets are guidance, not gates, but respect them:

- a coding prompt aims for one page; if it cannot fit, the slice is too big;
- a review report leads with at most ten findings — more is a finding against
  the prompt's scope, not a reason for more review text;
- a self-report aims for one page plus verification evidence.

Active review input is bounded by the evidence window in
`docs/template_framework/closure_convergence.md`; link history instead of
re-reading it.

## Recommended Coding Prompt Shape

1. Role and workflow mode.
2. Current state link.
3. Active workspaces.
4. Read first.
5. Task.
6. Non-goals.
7. Verification.
8. Self-report requirements.
9. Definition of done.

