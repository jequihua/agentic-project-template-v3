# Package Workspace

Status: ships the reusable OKF/profile framework contracts; also holds a
project's own package contracts when packaging is justified.

Keep package contracts close to the code:

- `architecture_contract.md`
- `public_api_contract.md`
- `testing_strategy.md`
- `package_status.md`

## Optional navigation view

`08_pkg/generated/okf_navigation.md` is an optional, generated, **disposable**
navigation read model over the OKF backbone (this package's contracts plus
`PROJECT_STATE.md`, `scripts/README.md`, the fixture manifest, and `MILESTONES.md`).
It is **not authoritative** and never copies live state; deleting it loses no
canonical information, and the direct links above plus the linked contracts remain
the manual navigation path. Regenerate or verify it with:

```text
python scripts/generate_okf_navigation.py
python scripts/generate_okf_navigation.py --check
```

It is not part of the mandatory `CLAUDE.md` read order.

## Architect operating card

`docs/template_framework/architect_operating_card.md` is the compact,
registry-validated architect quick start for the OKF/profile lane: the normal loop,
the four OKF rules, the artifact-type selection aid, the authority warning, and the
escalation triggers. It is a routine operator surface, not an authority; canonical
rules stay in `08_pkg/okf_profile_v0_1.md` and the source-of-truth hierarchy in
`CLAUDE.md`.
