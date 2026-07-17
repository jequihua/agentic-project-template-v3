# Coder Initialization - Optional llloom Memory

Use this prompt only when `PROJECT_STATE.md` says memory mode is `llloom`.

## Role

You use llloom as read-only source-grounded project memory during normal coding.
You do not mutate memory unless assigned a memory-update slice.

## Read First

1. `PROJECT_STATE.md`
2. `05_governance/current/memory_posture.md`
3. the active coding prompt
4. the llloom pages or claims named by the prompt

The llloom manual is here:

```text
<path-recorded-in-memory_posture.md>
```

## Startup

Use the memory root named in `PROJECT_STATE.md` or `memory_posture.md`.

Run proportional checks:

```powershell
.\.venv\Scripts\llloom.exe --root <memory_root> doctor
.\.venv\Scripts\llloom.exe --root <memory_root> verify
```

Run one relevant query only when memory matters to the slice:

```powershell
.\.venv\Scripts\llloom.exe --root <memory_root> query "<subsystem or question>"
```

If `doctor` reports serious errors, `verify` fails, or memory contradicts the
task prompt, stop and report the mismatch. Report stale or contradicted claims;
do not hand-patch them — that is a separate, assigned memory-update slice.

## Read-Only Commands

Allowed by default:

- `doctor`
- `status`
- `query`
- `claim-card`
- `list-claims`
- `list-sources`
- `list-pages`
- `list-render-targets`
- `verify`
- `lint`

Do not hand-edit:

- `claims/entities/*.yaml`
- rendered claim blocks in `pages/**`
- `state/source_registry.yaml`
- `state/journals/**`
- locks or tombstones
- raw sources unless assigned a memory-update slice

## Self-Report Additions

In your self-report, include:

- memory commands run;
- pages or claims used;
- stale or contradicted claims found;
- whether a memory update is requested.

Use claim, page, or source ids when available.
