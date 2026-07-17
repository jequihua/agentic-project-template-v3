# Local State Not Committed

Use this file to record local-only paths and secret boundaries.

Do not commit:

- `.venv/` or other virtual environments
- caches and temporary test output
- credentials, tokens, service account files, API keys
- raw private data
- bulky generated run outputs
- local llloom memory roots unless the human owner explicitly approves

If llloom is enabled, record:

- memory root:
- whether it is local-only:
- allowed commands:
- last verified status:

`.gitignore` enforces these exclusions. Before a milestone commit, follow the
Milestone Commit Closure checklist in `docs/template_framework/method.md`.

## Known Local Roots

Record substantial local-only roots a new agent or human should know about
(virtual environments, memory roots, run-output folders, copied reference trees,
large data caches). Keep it short; it is a pointer, not live state.

| Path | Purpose | Rebuildable | Retain Until | Cleanup Note |
| --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD |

## Seeing And Cleaning Local Footprint

Rebuildable residue (caches, coverage, build output) can be surfaced and removed
without touching meaningful artifacts:

```powershell
python scripts/local_state_audit.py --root .   # read-only footprint report
python scripts/local_cleanup.py --check --root .   # dry-run: list rebuildable residue
python scripts/local_cleanup.py --apply --root .   # delete only rebuildable residue
```

Cleanup never deletes `.git`, virtual environments, `local_state/`, memory roots,
the evidence/governance workspaces, archives, or nested repositories. See
`docs/template_framework/security_and_local_state.md`.

If cloud or credentialed work is enabled, use `06_infra/live_validation_gate.md`.

