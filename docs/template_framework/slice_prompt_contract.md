# Slice Prompt Contract

Contract version: 1
Legacy scaffold digest: `be60e7c354df33fe13477eef56b6fb33e4e2a4d11eb07ed5b62eb4916143ae7e`

The typed, versioned, per-slice specification from which a safe coding prompt
is rendered without architectural invention at generation time. It exists
because a roadmap that reads as detailed to a human carries no field a tool is
obliged to honor: the first fully autonomous campaign lost its largest stop
class to prompts that named a task ("publish the closure decision") with no
exact write path. This contract makes the slice definition data.

Ownership: the template owns the schema, the canonical rendered form, the
validity rules, and the fixtures. Consumers (frutlups' renderer and prompt
health; any conforming runner) implement their own parsers and must reproduce
the fixtures in `tests/fixtures/slice_contract/manifest.json`. The closed
vocabularies below are declared ONCE, in the `slice_prompt_contract` block of
`frutlups.layout.yaml`; this document's tables are proven equal to it by
`tests/test_slice_contract.py`, and the reference checker
`scripts/slice_contract_check.py` reads them from there.

## 1. Declaration, Opt-In, Rollback, Fence

- The typed source is a **sidecar YAML beside each selected prose roadmap**,
  named `<roadmap-stem>` + the layout's `sidecar_suffix` (`.slices.yaml`).
  The prose roadmap stays the human narrative and is untouched.
- **Absent sidecar = legacy v3 semantics byte-for-byte.** Nothing about a
  project without a sidecar changes.
- **Opt-in is one reviewed migration step** with exactly two effects: add the
  sidecar(s), and set the layout's `prompts.coding_template` to the v1
  scaffold `prompts/templates/coding_prompt_contract_v1.md`. Rollback reverses
  both in one step. The legacy scaffold `prompts/templates/coding_prompt.md`
  is byte-identical to its pre-contract form (digest above).
- **Old-consumer fence.** The v1 scaffold's slots are unconsumable by a legacy
  renderer and carry the unresolved-sentinel class it already refuses; a
  legacy consumer pointed at an opted-in project must refuse before writing
  any prompt. It may not emit a legacy-shaped prompt. Downstream consumers
  prove this against their released legacy artifact using
  `tests/fixtures/slice_contract/optin_project_for_old_consumer/`.
- **Unknown contract version fails closed.** A request for autonomous prompt
  generation in a project with no sidecar refuses with a migration
  diagnostic; it never silently opts the project in.
- **Cross-projection alignment.** A project with an active and a detailed
  roadmap projection carries one sidecar per projection: both declare the
  same version, each `roadmap` link resolves to its prose file, an
  overlapping slice id is semantically identical in both, and a missing
  counterpart, version mismatch, or any field mismatch fails closed before
  rendering. No consumer silently prefers one conflicting sidecar.

Why a sidecar and not blocks inside the roadmap: the released legacy roadmap
parser treats any `Label:` line inside a milestone section as a field and
absorbs continuation lines until the next boundary, so typed YAML placed in
the roadmap would be folded into rendered prompt text without a diagnostic.

## 2. Sidecar Grammar

Top level:

```yaml
slice_prompt_contract_version: 1
roadmap: active_roadmap.md      # the prose roadmap beside this file
slices:
  - slice: M001-S01
    # ... one entry per slice, fields in section 3
```

The positive all-fields fixture (`tests/fixtures/slice_contract/all_fields.slices.yaml`)
is the normative example: one routine `ready` slice and one live, corrective,
attempt-`002` slice exercising every field.

## 3. Per-Slice Fields

All fields are required unless marked; `none` is a contract-defined explicit
value and is distinct from a missing key.

| Group | Field | Rule |
| --- | --- | --- |
| identity | `slice` | `Mnnn-Snn`, unique per sidecar, belongs to `milestone` |
| identity | `title`, `milestone` | non-empty; `milestone` is `Mnnn` |
| identity | `authored_by` | `architect_reviewer` or `human_owner` — never a coder seat or a runner |
| dispatch | `status` | `frozen` (default; valid planning material, not current work) or `ready` |
| dispatch | `dispatch_authority` | required when `ready`: exact path of the record granting dispatch (owner note or controller record); `ready` also presumes every opening gate is satisfied |
| dispatch | `attempt` | three zero-padded digits as a string (`"001"`…); required for corrective entries and whenever a write uses `create_fresh_per_attempt` |
| class | `strictness` | `Level 1` … `Level 4` |
| class | `mode` | a workflow mode (`docs/template_framework/workflow_modes.md`) |
| class | `live`, `corrective` | booleans; they switch the envelope and correction requirements |
| task | `task` | multi-line specification; a task equal to the title is invalid |
| task | `active_workspaces`, `read_first` | non-empty lists; `read_first` entries are exact repository-relative paths |
| writes | `writes` | non-empty list of write-manifest entries (section 4) |
| scope | `non_goals`, `verification`, `definition_of_done` | non-empty lists; verification entries are exact commands or checks |
| gates | `opening_gates` | `none` or a non-empty list of `{kind, reference[, sha256 \| repository, tag, commit]}` |
| inputs | `external_inputs` | `none` or a non-empty list of `{repository, path, role, identity}`; `role` per `docs/template_framework/external_repository_roles.md` |
| inputs | `candidate_identity` | `none` or `{strategy, paths, identity_value}` |
| correction | `correction` | required iff `corrective: true`, else `none` (section 6) |
| live | `execution_envelope` | required iff `live: true`, else `none` (section 7) |
| objective | `objective.success_criteria`, `objective.closure_proof` | non-empty lists; closure proof names the evidence the review looks for, distinct from the implementation's definition of done |

## 4. Write Manifest

Each `writes` entry: `path`, `artifact_type`, `role_owner`, `retry_policy`.

- `path` is an exact repository-relative **file** path. Directory paths,
  globs, absolute paths, parent traversal, and implicit neighbouring-file
  authority are invalid. A task noun with no declared path grants nothing.
- `artifact_type` (global vocabulary): `implementation`, `test`, `evidence`,
  `analysis`, `documentation`, `fixture`, `generated_output`, `config`,
  `self_report`, `coding_prompt`, `review_prompt`, `review_report`,
  `verdict_record`, `acceptance_record`, `routing_state`, `framework_doc`,
  `governance_record`.
- `role_owner`: `coder`, `reviewer`, `architect_reviewer`, `human_owner`,
  `runner`.
- `retry_policy`: `create_once` (never overwrites an existing artifact),
  `create_fresh_per_attempt` (requires exactly one attempt token in the
  path), `modify` (only the exact authorized working artifact; never across an
  accepted-history fence), `append_only` (never alters prior bytes).

Role/type compatibility matrix (a row outside it is invalid):

| Role | May own |
| --- | --- |
| `coder` | `implementation`, `test`, `evidence`, `analysis`, `documentation`, `fixture`, `generated_output`, `config`, and exactly one `self_report` |
| `reviewer` | `review_report`, `evidence`, `analysis`, `documentation` |
| `architect_reviewer` | everything except `self_report` and `routing_state` |
| `human_owner` | `documentation`, `coding_prompt`, `review_prompt`, `verdict_record`, `acceptance_record`, `governance_record`, `framework_doc`, `config` |
| `runner` | `coding_prompt`, `review_prompt`, `verdict_record`, `routing_state`, `generated_output`, `evidence` |

Reserved paths classify the artifact regardless of label: a path ending in
`_self_report.md`, `_review_report.md`, or `_verdict_record.md`, or under the
review-prompt or coding-prompt folders, IS that artifact type; labelling it
`governance_record` does not bypass the matrix. Under contract v1 the
`review_prompt` is not coder-owned (a deliberate tightening; the legacy
`coder_may_create_review_prompt` convention is unchanged for legacy projects).
A coder-owned `review_report`, `verdict_record`, `acceptance_record`, or
`routing_state` is always invalid. Exactly one coder-owned `self_report` is
required; it is a claim artifact, never review or acceptance authority.

### Attempt grammar

Every corrective or fresh-per-attempt operation carries an attempt identity.
A path may contain at most one attempt token (layout `attempt_token`,
`{attempt}`); the token is source syntax only. The rendered prompt carries the
resolved exact path (`..._attempt_002_...`), never the token or any sentinel.
A rendered prompt for attempt N whose write target resolves to another
attempt's path reuses history and is invalid. Deterministic allocation and
historical collision checks are the operating tool's job; this contract fixes
the grammar and the fixtures (`attempts_001_002_distinct`,
`rendered_attempt_path_reuse`).

## 5. Dispatch Status Is Not Validity

A valid entry is not automatically dispatchable. Pre-created entries for
later roadmap slices stay `status: frozen`: they validate, they are never
current work, and no consumer promotes them silently. `ready` requires every
opening gate satisfied and a recorded `dispatch_authority`. The renderer
copies the entry's status into the prompt's workflow metadata; a prompt is
dispatchable only at workflow `status: ready`, and a ready prompt contains no
unresolved sentinel and no deleted-section residue
(`scripts/artifact_integrity_preflight.py` errors on both).

Gate kinds: `accepted_review`, `owner_note`, `artifact_exists`,
`artifact_identity` (reference + `sha256`), `pinned_external_release`
(`repository`, `tag`, `commit`), `human_launch_word`, `external_answer`.
`artifact_exists` alone never gates a consumption of bytes that matter; use
`artifact_identity` or `pinned_external_release`.

## 6. Corrective Entries And The Governed Transaction

A corrective entry (`corrective: true`) carries `correction.findings`
(`id`, `violated_invariant`, `prior_disposition` each), `correction.prior_evidence`
(`path` + `sha256` each), `correction.controlling_ruling` (the exact owner-note
path, or `{disputed: <owner-note path>}` when authority is disputed), and
`correction.closure_proof`.

Authority and atomicity:

- sidecar entries are authored by `architect_reviewer` or `human_owner` —
  never by a coder seat and never by a runner's writer;
- a corrective proposal is not dispatchable until a released governed
  operation of the operating tool validates and records its sidecar entry;
  that transaction may create the entry and render the prompt atomically and
  publishes neither unless the whole transaction is valid;
- a runner's guarded writer applies exactly one artifact — the rendered
  prompt at its declared path — and never writes the sidecar;
- retries never overwrite an accepted sidecar entry or a historical prompt.

## 7. Execution Envelope (live entries)

Required fields: `timing_probe` (`command`, `expected_seconds`),
`agent_budget_seconds`, `subprocess_budget_seconds` (model/agent wall and
scientific subprocess wall are separate), `expected_wall_seconds`,
`hard_wall_seconds`, `frozen_override` (`none` or `{authority: <owner-note
path>}`), `environment_bindings` (`none` or a list of `{name, value_sha256}` —
names and hashes only; a `value` key is invalid), `identities` (`none` or a
list; arm / group / order / attempt), `retained_bytes_max`,
`local_output_root` (must be under the declared local-state root),
`cleanup` (`retain_until_closure`, `delete_after_evidence`, `quarantine`),
`negative_result_handling` and `stopped_result_handling` (`preserve_and_stop`,
`preserve_and_continue`). `delete_after_evidence` is a declared lifecycle
policy, never deletion authority by itself.

Enforcement (stated honestly; the drive's version-5 answer is the source):

| Field | Enforced by |
| --- | --- |
| budgets, walls, `frozen_override` | the runner validates them against its own policy and gate at admission; an envelope exceeding the policy/gate ceilings is refused, never silently overridden; an override still needs the policy to admit it |
| `environment_bindings` | the runner injects the value declared in its policy/gate and refuses at admission when the policy value's hash differs from the slice's `value_sha256`; a project declaring a binding here must declare its value runner-side |
| `timing_probe`, `retained_bytes_max`, `local_output_root`, `cleanup`, result handling | template/operator-enforced (the pre-launch audit command and the human gate); useful contract data a later runner version may consume |

Every runner-consumed field reaches the runner only through the operating
tool's versioned machine payload; no runner parses the sidecar. The human
gate `06_infra/live_validation_gate.md` records approval and the launch word
against the envelope; a live entry without a complete envelope is not
dispatchable.

## 8. Canonical Rendered Form

One scaffold per regime. The legacy scaffold is unchanged. The v1 scaffold
`prompts/templates/coding_prompt_contract_v1.md` carries typed slots; every
retained typed value appears verbatim in exactly one section; not-applicable
sections are removed entirely, marker line included; no slot token, sentinel,
or residue survives rendering. Rendering map:

| Typed field | Rendered location |
| --- | --- |
| `milestone`, `slice`, `title`, `mode`, `strictness`, `live`, `corrective`, `attempt`, `status` | workflow metadata block (the `attempt` line is removed when the entry has none) |
| `task`, `active_workspaces`, `read_first` | Task, Active Workspaces, Read First |
| `writes` | Write Manifest table (resolved paths) and the Self-Report path |
| `opening_gates` | Opening Gates (conditional) |
| `external_inputs` | External Repositories (conditional) |
| `correction` | Correction Scope Map (conditional) |
| `candidate_identity` | Candidate Identity (conditional) |
| `execution_envelope` | Execution Envelope (conditional) |
| `objective` | Objective And Closure Proof |
| `non_goals`, `verification`, `definition_of_done` | Non-Goals, Verification, Definition Of Done |
| seat conduct | Seat Conduct (static pointer to `CLAUDE.md`) |

Section order and the required/conditional split are declared in the layout
(`rendered_sections_required`, `rendered_sections_conditional`). The
canonical renderings are `all_fields_rendered_m001_s01.md` (routine: no
conditional section, no attempt line) and
`all_fields_rendered_m002_s02_attempt_001.md` / `_002.md` (live corrective:
every conditional section, resolved attempt paths). Downstream conformance
means reproducing them field-for-field from the positive sidecar.

## 9. Review Side: The Closure Record

Every review report carries, before `## Verdict`, exactly one section:

```markdown
## Closure Decision

Objective status: <achieved|not_achieved|not_applicable|indeterminate>
Objective evidence: <one line citing the slice closure-proof artifacts, or the exact not-applicable justification>

## Verdict

Verdict: <pass|needs_work|blocked|override> - next: <one move>
```

Exactly one non-fenced `Objective status:` line, one immediately following
`Objective evidence:` line, no objective line inside `## Verdict`, and the
verdict footer unchanged as the first non-empty line under `## Verdict`.
Values: `achieved` (cited closure evidence establishes every applicable
criterion), `not_achieved` (evidence establishes at least one criterion was
not met), `not_applicable` (no applicable objective dimension, with an
explicit reason), `indeterminate` (relevant evidence is absent, incomplete,
conflicting, or otherwise insufficient to decide).

Rule: implementation `pass` and objective achievement are independent.
`pass` + `not_achieved` and `pass` + `indeterminate` are legal receipts that
never imply milestone completion; `pass` + `not_applicable` completes only
with an explicit compatible routing status from the operating tool; last-slice
position is never sufficient. This contract defines no route for any status:
routing is the operating tool's dimension. Full doctrine:
`05_governance/current/review_protocol.md` and
`docs/template_framework/closure_convergence.md`.

## 10. Validity Rules (reason codes)

Sidecar: `version_missing`, `unknown_contract_version`, `roadmap_missing`,
`slices_missing`, `missing_field`, `invalid_type`, `duplicate_slice`,
`slice_id_format`, `slice_milestone_mismatch`, `authored_by_invalid`,
`status_invalid`, `dispatch_authority_missing`, `attempt_missing`,
`attempt_format`, `strictness_invalid`, `task_is_title_only`, `empty_list`,
`read_first_path_invalid`, `write_path_directory`, `write_path_glob`,
`write_path_absolute`, `write_path_escape`, `write_path_not_file`,
`artifact_type_invalid`, `role_owner_invalid`, `retry_policy_invalid`,
`role_type_incompatible`, `reserved_artifact_mislabeled`, `self_report_count`,
`attempt_token_missing`, `attempt_token_unexpected`, `attempt_token_multiple`,
`write_read_conflict`, `sentinel_residue`, `gate_kind_invalid`,
`gate_reference_missing`, `gate_identity_missing`, `external_input_invalid`,
`candidate_identity_invalid`, `correction_missing`,
`correction_findings_missing`, `correction_prior_evidence_invalid`,
`correction_ruling_missing`, `correction_closure_proof_missing`,
`correction_unexpected`, `envelope_missing`, `envelope_unexpected`,
`envelope_field_missing`, `envelope_field_invalid`, `envelope_probe_invalid`,
`envelope_binding_value_present`, `envelope_binding_hash_format`,
`envelope_cleanup_invalid`, `envelope_handling_invalid`,
`local_output_root_outside_local_state`, `objective_missing`.
Alignment: `projection_version_mismatch`, `projection_counterpart_missing`,
`projection_entry_mismatch`. Rendered prompt: `rendered_section_missing`,
`rendered_section_duplicate`, `rendered_section_unexpected`,
`rendered_sentinel_residue`, `rendered_section_residue`,
`rendered_token_unresolved`, `rendered_metadata_missing`,
`rendered_manifest_row_missing`, `rendered_attempt_path_reuse`,
`rendered_value_missing`, `slice_not_found`. Review report:
`closure_section_missing`, `closure_section_duplicate`,
`closure_after_verdict`, `objective_status_line_missing`,
`objective_status_invalid`, `objective_evidence_line_missing`,
`verdict_section_missing`, `verdict_section_duplicate`,
`verdict_footer_invalid`, `objective_status_in_verdict`.

Sentinels (layout `sentinels`): `TBD`, `<value>`, `<path>`, `<one move>`; a
scalar that is only `...` counts as unresolved.

## 11. Reference Checker And Fixtures

`scripts/slice_contract_check.py` is the reference implementation: read-only,
exact-path driven, deterministic, network-free, stable reason codes in stable
order, `--json` output (`template.slice_contract_check.v1`). It is never
dispatch authority. Modes: validate one sidecar; validate two and prove
alignment; prove a rendered prompt against its entry (`--slice`, optional
`--attempt`); check a review report's closure record. It needs the declared
PyYAML dependency (`ENVIRONMENT.md`).

The fixture corpus `tests/fixtures/slice_contract/` is inventoried and
digest-pinned by `manifest.json` (every fixture carries its SHA-256; the
suite fails when bytes drift). Groups: positive (`all_fields`, the three
canonical renderings, `frozen_entry_valid`, `projections_aligned`,
`review_report_closure_valid`), adversarial sidecars (one per validity rule
above), adversarial renderings, adversarial review reports, the legacy
document, and the external old-consumer fence fixture. Downstream parsers are
tested against these fixtures, not against private reimplementations; the
release receipt carries their digests.

## 12. Companion Rails

- Seat conduct: `CLAUDE.md` Autonomous-Loop Seat Posture (bounded probes; no
  recursive enumeration; no external snapshots; no secret values; the runner
  fence is the evidence) — rendered as the Seat Conduct section.
- Template-source purity and local-output topology: the layout's
  `template_owned_surfaces` and `local_state` blocks; the drive's JSON
  exclusion manifest at the layout's recommended path
  (`local_state.oracle_exclusion_manifest`) is the single machine-read
  exclusion source; the pre-launch check is the layout's
  `local_state.prelaunch_size_check` command
  (`docs/template_framework/security_and_local_state.md`):

  ```text
  python scripts/local_state_audit.py --limit-bytes 16777216 --exclusions 06_infra/oracle_exclusion_manifest.json
  ```
- Placeholders and dispatch: `docs/template_framework/prompt_style_guide.md`.

## 13. Migration And Release Identity

- Migration rule: absent sidecar = legacy. Opt in per section 1. A project
  refreshes the template-owned surfaces per
  `docs/template_framework/migration_and_adoption.md` and records the
  template pin in `PROJECT_STATE.md`.
- Release identity: contract v1 ships with a template release tag; the release
  receipt names the contract version, the tag, the full commit, the fixture
  manifest path and per-fixture digests, the legacy scaffold digest above, and
  this migration rule. Consumers declare compatibility against the tag,
  never against a branch. A later revision of the schema is contract version
  2 with its own fixtures; version 1 artifacts stay readable under version 1.
