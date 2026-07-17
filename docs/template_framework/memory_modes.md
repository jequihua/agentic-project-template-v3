# Memory Modes

Memory is optional. The active mode is set by `Memory mode` in `PROJECT_STATE.md`.
The current posture (roots, commands, update rules) lives in
`05_governance/current/memory_posture.md`. This is an optional lane and follows
the shared shape in `docs/template_framework/optional_lanes.md`.

## Modes

### none (default)

Repository artifacts are the only memory. Agents run no memory commands, prompts
do not reference memory, and the `memory/` workspace stays inactive. A project
that has not chosen memory can ignore this lane completely.

### lightweight

A single plain-markdown facts/claims file is the shared memory. No llloom install
and no llloom dependency. Use it when a project wants a compact shared fact map
but not source-grounded provenance.

### llloom

Source-grounded memory via llloom: verified claims with source locators,
queryable pages, and journaled updates. Use it only when that provenance is worth
the operational cost, and only when the human owner chooses it. See the llloom
initialization prompts (`initialization/003_*`, `initialization/004_*`) and
record the manual path in `05_governance/current/memory_posture.md`.

## Switching Mode

Changing `Memory mode` in `PROJECT_STATE.md` is the switch. When it changes:

- to `none`: nothing else activates; ignore `memory/` and `memory_posture.md`.
- to `lightweight`: activate the `memory` toggle (per
  `docs/template_framework/project_profiles.md`) and record the facts-file
  location in `memory_posture.md`. No llloom.
- to `llloom`: activate the `memory` toggle, fill the llloom section of
  `memory_posture.md` (root, install source, read-first pages, last
  `doctor` / `verify`), and follow the llloom initialization prompts.

## Shared Rules (lightweight and llloom)

- the architect/reviewer initializes and populates memory;
- the coder defaults to read-only use;
- memory mutation requires an explicit memory-update slice;
- facts or claims used should be cited in self-reports;
- stale, contradictory, or failing memory should be reported, not hand-patched;
- memory failures block only when memory is authoritative for the slice.
