"""Reference checker for the template's slice prompt contract v1 (read-only).

Validates a sidecar (`<roadmap-stem>.slices.yaml`), the cross-projection
alignment of two sidecars, a rendered coding prompt against its sidecar entry,
and the closure record of a review report. The closed vocabularies are read
from the ONE canonical declaration, the `slice_prompt_contract` block of
`frutlups.layout.yaml`; nothing here restates them.

The rendered-prompt check is a keyed parse: every typed field is extracted from
its rendered position (metadata line, bullet, table cell, labeled bullet) and
compared with the entry by equality, so label text, duplicated text, or a
cross-section occurrence can never stand in for a field's value.

This is a reference implementation for the template's own fixtures and for
project-side preflight. It is never dispatch authority. Downstream tools keep
their own parsers and must pass the same fixtures.

Usage (from the repository root):

    python scripts/slice_contract_check.py --sidecar 03_experiments/x.slices.yaml
    python scripts/slice_contract_check.py --sidecar a.slices.yaml --sidecar b.slices.yaml
    python scripts/slice_contract_check.py --sidecar x.slices.yaml --slice M001-S02 \\
        --rendered prompts/for_coding_agent/012_x.md [--attempt 2]
    python scripts/slice_contract_check.py --review-report 05_governance/reviews/r.md

Properties: read-only, exact-path driven, deterministic, network-free, stable
diagnostic codes emitted in stable order, machine-readable `--json` output.
PyYAML (the declared dependency) is imported lazily so `--help` works without it.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SCHEMA = "template.slice_contract_check.v1"
MAX_INPUT_BYTES = 1_048_576
SLICE_ID_RE = re.compile(r"^M\d{3}-S\d{2}$")
MILESTONE_ID_RE = re.compile(r"^M\d{3}$")
ATTEMPT_RE = re.compile(r"^(?!000)\d{3}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STRICTNESS_RE = re.compile(r"^Level [1-4]$")
HEADING_RE = re.compile(r"^## (.+?)\s*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
VERDICT_FOOTER_RE = re.compile(r"^Verdict: (pass|needs_work|blocked|override) - next: \S.*$")
GATE_RE = re.compile(
    r"^(?P<kind>[a-z_]+): (?P<reference>.+?)"
    r"(?: \(sha256 (?P<sha256>[0-9a-f]{64})\))?"
    r"(?: \(repository (?P<repository>[^,]+), tag (?P<tag>[^,]+), commit (?P<commit>[^)]+)\))?$"
)
PROBE_RE = re.compile(r"^`(?P<command>.+)` \(expected (?P<expected_seconds>[0-9.]+) s\)$")
WALLS_RE = re.compile(r"^(?P<expected_wall_seconds>[0-9.]+) s; hard wall: (?P<hard_wall_seconds>[0-9.]+) s$")
SECONDS_RE = re.compile(r"^(?P<value>[0-9.]+) s$")
BINDING_RE = re.compile(r"^(?P<name>\S+) sha256 (?P<value_sha256>[0-9a-f]{64})$")
EVIDENCE_RE = re.compile(r"^`(?P<path>[^`]+)` sha256 (?P<sha256>[0-9a-f]{64})$")
RESIDUE_PHRASES = (
    "delete this section", "contract v1 section", "fills or deletes",
    "conditional: rendered only", "this preamble is scaffold documentation",
)
LOCAL_STATE_ROOT = "local_state/"
ENVELOPE_REQUIRED = (
    "timing_probe", "agent_budget_seconds", "subprocess_budget_seconds",
    "expected_wall_seconds", "hard_wall_seconds", "frozen_override",
    "environment_bindings", "identities", "retained_bytes_max",
    "local_output_root", "cleanup", "negative_result_handling",
    "stopped_result_handling",
)
SLICE_REQUIRED = (
    "slice", "title", "milestone", "authored_by", "status", "strictness", "mode",
    "live", "corrective", "task", "active_workspaces", "read_first", "writes",
    "non_goals", "verification", "opening_gates", "external_inputs",
    "candidate_identity", "correction", "execution_envelope", "objective",
    "definition_of_done",
)
CORRECTION_REQUIRED = (
    "findings", "prior_evidence", "controlling_ruling", "closure_proof",
    "claims_withdrawn", "evidence_invalidated", "minimum_rerun_set",
)
FINDING_REQUIRED = (
    "id", "violated_invariant", "prior_disposition", "authority_action",
    "coder_obligation", "closure_proof",
)
PATH_GATE_KINDS = ("accepted_review", "owner_note", "artifact_exists", "artifact_identity")

# Every content diagnostic the checker can emit. Each has at least one fixture in
# tests/fixtures/slice_contract/manifest.json expecting it (pinned by test), and the
# contract document lists exactly these plus ENVIRONMENT_CODES.
REASON_CODES = (
    # sidecar shape
    "sidecar_not_mapping", "version_missing", "unknown_contract_version",
    "roadmap_missing", "roadmap_link_unresolved", "slices_missing", "slice_not_mapping",
    "missing_field", "invalid_type", "duplicate_slice", "slice_id_format",
    "slice_milestone_mismatch",
    # identity, dispatch, class
    "authored_by_invalid", "status_invalid", "dispatch_authority_missing",
    "authority_path_invalid", "attempt_missing", "attempt_format", "strictness_invalid",
    "task_is_title_only", "empty_list", "read_first_path_invalid",
    # write manifest
    "write_path_empty", "write_path_directory", "write_path_glob", "write_path_absolute",
    "write_path_escape", "write_path_not_file", "artifact_type_invalid",
    "role_owner_invalid", "retry_policy_invalid", "role_type_incompatible",
    "reserved_artifact_mislabeled", "self_report_count", "attempt_token_missing",
    "attempt_token_unexpected", "attempt_token_multiple", "write_read_conflict",
    "sentinel_residue",
    # gates, inputs, identity
    "gate_kind_invalid", "gate_reference_missing", "gate_reference_invalid",
    "gate_identity_missing", "external_input_invalid", "candidate_identity_invalid",
    # correction
    "correction_missing", "correction_field_missing", "correction_findings_missing",
    "correction_prior_evidence_invalid", "correction_ruling_missing",
    "correction_closure_proof_missing", "correction_list_invalid", "correction_unexpected",
    # envelope
    "envelope_missing", "envelope_unexpected", "envelope_field_missing",
    "envelope_field_invalid", "envelope_probe_invalid", "envelope_binding_value_present",
    "envelope_binding_hash_format", "envelope_cleanup_invalid", "envelope_handling_invalid",
    "local_output_root_outside_local_state", "local_output_root_attempt_token",
    "objective_missing",
    # alignment
    "projection_version_mismatch", "projection_counterpart_missing",
    "projection_entry_mismatch",
    # rendered prompt
    "attempt_mismatch", "rendered_section_missing", "rendered_section_duplicate",
    "rendered_section_unexpected", "rendered_sentinel_residue", "rendered_section_residue",
    "rendered_token_unresolved", "rendered_metadata_missing",
    "rendered_manifest_row_missing", "rendered_attempt_path_reuse", "rendered_value_missing",
    # review report
    "closure_section_missing", "closure_section_duplicate", "closure_after_verdict",
    "closure_not_adjacent", "closure_line_count", "objective_status_line_missing",
    "objective_status_invalid", "objective_status_duplicate",
    "objective_evidence_line_missing", "objective_evidence_duplicate",
    "verdict_section_missing", "verdict_section_duplicate", "verdict_footer_invalid",
    "objective_status_in_verdict",
)
# I/O and usage diagnostics: unit-tested, not fixture-driven.
ENVIRONMENT_CODES = (
    "layout_unreadable", "layout_contract_block_missing", "layout_contract_block_incomplete",
    "sidecar_unreadable", "rendered_unreadable", "review_report_unreadable",
    "slice_not_found", "usage",
)


@dataclass
class Diagnostic:
    code: str
    path: str
    location: str
    message: str
    severity: str = "error"


@dataclass
class Extracted:
    """One rendered field value with the exact span of its value text."""
    path: tuple
    value: str
    line: int
    start: int
    end: int


class _StrictLoadError(Exception):
    pass


# --- bounded, duplicate-rejecting YAML loading (lazy PyYAML) ---------------


def _load_yaml_file(path: Path) -> object:
    try:
        import yaml  # lazy: the declared dependency, imported only when parsing
    except ImportError as exc:  # pragma: no cover - exercised only without PyYAML
        raise _StrictLoadError("PyYAML is required; install the project (see ENVIRONMENT.md)") from exc

    class _Strict(yaml.SafeLoader):
        pass

    def _construct_mapping(loader, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in seen:
                raise _StrictLoadError(f"duplicate mapping key: {key!r}")
            seen.add(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    _Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)
    raw = path.read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise _StrictLoadError(f"input exceeds {MAX_INPUT_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _StrictLoadError("input is not valid UTF-8") from exc
    try:
        return yaml.load(text, Loader=_Strict)  # noqa: S506 - SafeLoader subclass
    except yaml.YAMLError as exc:
        raise _StrictLoadError(f"YAML syntax error: {exc}") from exc


def load_layout_contract(layout_path: Path) -> tuple[dict | None, list[Diagnostic]]:
    rel = layout_path.as_posix()
    try:
        doc = _load_yaml_file(layout_path)
    except (OSError, _StrictLoadError) as exc:
        return None, [Diagnostic("layout_unreadable", rel, "", str(exc))]
    block = doc.get("slice_prompt_contract") if isinstance(doc, dict) else None
    if not isinstance(block, dict):
        return None, [Diagnostic("layout_contract_block_missing", rel, "", "no slice_prompt_contract block")]
    needed = (
        "version", "rendered_sections_required", "rendered_sections_conditional",
        "entry_status_values", "authored_by_values", "artifact_types", "role_owners",
        "role_type_matrix", "reserved_path_classification", "retry_policies",
        "attempt_token", "gate_kinds", "cleanup_values", "result_handling_values",
        "objective_status_values", "sentinels",
    )
    missing = [k for k in needed if k not in block]
    if missing:
        return None, [Diagnostic("layout_contract_block_incomplete", rel, "", "missing " + ", ".join(missing))]
    return block, []


# --- helpers ----------------------------------------------------------------


def _is_list_of_str(value, non_empty=True) -> bool:
    return isinstance(value, list) and (value or not non_empty) and all(
        isinstance(v, str) and v.strip() for v in value
    )


def _sentinel_hits(value, sentinels) -> list[str]:
    hits: list[str] = []
    if isinstance(value, str):
        for s in sentinels:
            if s in value:
                hits.append(s)
        if value.strip() == "...":
            hits.append("...")
    elif isinstance(value, dict):
        for v in value.values():
            hits.extend(_sentinel_hits(v, sentinels))
    elif isinstance(value, list):
        for v in value:
            hits.extend(_sentinel_hits(v, sentinels))
    return hits


def _normalized_relative(path_value: str) -> str | None:
    """Canonical repository-relative POSIX form, or None when the value is
    absolute, escapes the root, or is not a clean relative path."""
    if not isinstance(path_value, str) or not path_value.strip():
        return None
    p = path_value.strip().replace("\\", "/")
    if p.startswith("/") or re.match(r"^[A-Za-z]:/", p) or p.startswith("//"):
        return None
    trailing = p.endswith("/")
    norm = posixpath.normpath(p)
    if norm.startswith("../") or norm == ".." or norm == "." or norm.startswith("/"):
        return None
    return norm + ("/" if trailing and norm != "." else "")


def _path_problem(path_value: str) -> str | None:
    """Write-manifest path rule: an exact repository-relative FILE path."""
    if not isinstance(path_value, str) or not path_value.strip():
        return "write_path_empty"
    p = path_value.strip()
    if p.endswith("/") or p.endswith("\\"):
        return "write_path_directory"
    if any(ch in p for ch in "*?["):
        return "write_path_glob"
    if p.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", p) or p.startswith("\\\\"):
        return "write_path_absolute"
    parts = p.replace("\\", "/").split("/")
    if ".." in parts or "." in parts or _normalized_relative(p) is None:
        return "write_path_escape"
    if "." not in parts[-1]:
        return "write_path_not_file"
    return None


def _record_path_ok(value) -> bool:
    """Exact repository-relative record path (a file, no glob, no escape)."""
    return isinstance(value, str) and _path_problem(value) is None


def _is_junction(path: Path) -> bool:
    return bool(getattr(path, "is_junction", lambda: False)())


def _roadmap_link_problem(sidecar_path: Path, roadmap: str) -> str | None:
    """The roadmap must be an ordinary regular file beside the sidecar: no
    symlink or junction, and its strictly resolved parent equals the sidecar's."""
    candidate = sidecar_path.parent / roadmap
    if candidate.is_symlink() or _is_junction(candidate):
        return "the roadmap beside the sidecar is a link, not an ordinary file"
    try:
        resolved = candidate.resolve(strict=True)
        sidecar_parent = sidecar_path.resolve(strict=True).parent
    except (OSError, RuntimeError):
        return f"roadmap {roadmap!r} does not exist beside the sidecar"
    if not resolved.is_file():
        return f"roadmap {roadmap!r} is not a regular file"
    if resolved.parent != sidecar_parent:
        return f"roadmap {roadmap!r} resolves outside the sidecar's directory"
    return None


def _classify_reserved(path_value: str, classification: dict) -> str | None:
    p = path_value.replace("\\", "/")
    for artifact_type, marker in classification.items():
        if marker.endswith("/"):
            if p.startswith(marker):
                return artifact_type
        elif p.endswith(marker):
            return artifact_type
    return None


def resolve_attempt(value: str, token: str, attempt: str | None) -> str:
    return value.replace(token, attempt) if attempt else value


def iter_leaves(value, path=()):
    """Yield (key path, scalar) for every scalar leaf of a typed value."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield from iter_leaves(v, path + (str(k),))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from iter_leaves(v, path + (str(i),))
    else:
        yield path, value


def _leaf_text(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# --- sidecar validation -----------------------------------------------------


def validate_sidecar(doc: object, rel: str, layout: dict, sidecar_path: Path | None = None) -> list[Diagnostic]:
    d: list[Diagnostic] = []
    if not isinstance(doc, dict):
        return [Diagnostic("sidecar_not_mapping", rel, "", "top level must be a mapping")]
    version = doc.get("slice_prompt_contract_version")
    if version is None:
        d.append(Diagnostic("version_missing", rel, "", "slice_prompt_contract_version is required"))
    elif version != layout["version"]:
        d.append(Diagnostic("unknown_contract_version", rel, "", f"version {version!r} is not supported (supported: {layout['version']})"))
        return d
    roadmap = doc.get("roadmap")
    if not isinstance(roadmap, str) or not roadmap.strip() or "/" in roadmap or "\\" in roadmap:
        d.append(Diagnostic("roadmap_missing", rel, "", "roadmap must name the prose roadmap file beside this sidecar"))
    elif sidecar_path is not None:
        problem = _roadmap_link_problem(sidecar_path, roadmap)
        if problem:
            d.append(Diagnostic("roadmap_link_unresolved", rel, "", problem))
    slices = doc.get("slices")
    if not isinstance(slices, list) or not slices:
        d.append(Diagnostic("slices_missing", rel, "", "slices must be a non-empty list"))
        return d
    seen_ids: set[str] = set()
    for index, entry in enumerate(slices):
        loc = f"slices[{index}]"
        if not isinstance(entry, dict):
            d.append(Diagnostic("slice_not_mapping", rel, loc, "slice entry must be a mapping"))
            continue
        sid = entry.get("slice")
        if isinstance(sid, str):
            loc = sid
            if not SLICE_ID_RE.match(sid):
                d.append(Diagnostic("slice_id_format", rel, loc, "slice id must look like M001-S02"))
            if sid in seen_ids:
                d.append(Diagnostic("duplicate_slice", rel, loc, "slice id declared more than once"))
            seen_ids.add(sid)
        missing = [f for f in SLICE_REQUIRED if f not in entry]
        for field in missing:
            d.append(Diagnostic("missing_field", rel, loc, f"required field missing: {field}"))
        if missing:
            continue
        d.extend(_validate_entry(entry, rel, loc, layout))
    return d


def _validate_entry(e: dict, rel: str, loc: str, layout: dict) -> list[Diagnostic]:
    d: list[Diagnostic] = []

    def err(code: str, msg: str, where: str = loc) -> None:
        d.append(Diagnostic(code, rel, where, msg))

    sentinels = layout["sentinels"]
    hits = _sentinel_hits(dict(e), sentinels)
    if hits:
        err("sentinel_residue", "unresolved sentinel in entry: " + ", ".join(sorted(set(hits))))

    if not isinstance(e["title"], str) or not e["title"].strip():
        err("invalid_type", "title must be a non-empty string")
    if not (isinstance(e["milestone"], str) and MILESTONE_ID_RE.match(e["milestone"])):
        err("invalid_type", "milestone must look like M001")
    elif isinstance(e.get("slice"), str) and not e["slice"].startswith(e["milestone"] + "-"):
        err("slice_milestone_mismatch", "slice id does not belong to the declared milestone")
    if e["authored_by"] not in layout["authored_by_values"]:
        err("authored_by_invalid", f"authored_by must be one of {layout['authored_by_values']}")
    status = e["status"]
    if status not in layout["entry_status_values"]:
        err("status_invalid", f"status must be one of {layout['entry_status_values']}")
    auth = e.get("dispatch_authority")
    if status == "ready" and (not isinstance(auth, str) or not auth.strip()):
        err("dispatch_authority_missing", "status: ready requires dispatch_authority (exact record path)")
    elif auth is not None and not _record_path_ok(auth):
        err("authority_path_invalid", f"dispatch_authority must be an exact repository-relative record path: {auth!r}")
    if not (isinstance(e["strictness"], str) and STRICTNESS_RE.match(e["strictness"])):
        err("strictness_invalid", "strictness must be 'Level 1'..'Level 4'")
    if not isinstance(e["mode"], str) or not e["mode"].strip():
        err("invalid_type", "mode must be a non-empty string")
    for flag in ("live", "corrective"):
        if not isinstance(e[flag], bool):
            err("invalid_type", f"{flag} must be a boolean")
    task = e["task"]
    if not isinstance(task, str) or not task.strip():
        err("invalid_type", "task must be a non-empty string")
    elif isinstance(e.get("title"), str) and task.strip().lower() == e["title"].strip().lower():
        err("task_is_title_only", "task must specify more than the title")
    for field in ("active_workspaces", "read_first", "non_goals", "verification", "definition_of_done"):
        if not _is_list_of_str(e[field]):
            err("empty_list", f"{field} must be a non-empty list of strings")
    if _is_list_of_str(e["read_first"]):
        for rf in e["read_first"]:
            if _normalized_relative(rf) is None or any(ch in rf for ch in "*?["):
                err("read_first_path_invalid", f"read_first entry is not an exact repository-relative path: {rf}")

    # write manifest
    writes = e["writes"]
    self_reports = 0
    token = layout["attempt_token"]
    needs_attempt = e["corrective"] is True
    if not isinstance(writes, list) or not writes:
        err("empty_list", "writes must be a non-empty list")
        writes = []
    read_set = set(e["read_first"]) if _is_list_of_str(e["read_first"]) else set()
    for i, w in enumerate(writes):
        wloc = f"{loc}.writes[{i}]"
        if not isinstance(w, dict):
            err("invalid_type", "write entry must be a mapping", wloc)
            continue
        wmissing = [k for k in ("path", "artifact_type", "role_owner", "retry_policy") if k not in w]
        for key in wmissing:
            err("missing_field", f"write entry missing {key}", wloc)
        if wmissing:
            continue
        path_value = w["path"]
        problem = _path_problem(path_value)
        if problem:
            err(problem, f"invalid write path: {path_value!r}", wloc)
        atype, owner, policy = w["artifact_type"], w["role_owner"], w["retry_policy"]
        if atype not in layout["artifact_types"]:
            err("artifact_type_invalid", f"unknown artifact_type {atype!r}", wloc)
        if owner not in layout["role_owners"]:
            err("role_owner_invalid", f"unknown role_owner {owner!r}", wloc)
        if policy not in layout["retry_policies"]:
            err("retry_policy_invalid", f"unknown retry_policy {policy!r}", wloc)
        if atype in layout["artifact_types"] and owner in layout["role_owners"]:
            if atype not in layout["role_type_matrix"].get(owner, []):
                err("role_type_incompatible", f"{owner} may not own {atype}", wloc)
        if isinstance(path_value, str):
            reserved = _classify_reserved(path_value, layout["reserved_path_classification"])
            if reserved and reserved != atype:
                err("reserved_artifact_mislabeled", f"path classifies as {reserved} but is labelled {atype!r}", wloc)
            if reserved in ("review_report", "verdict_record") and owner == "coder":
                err("role_type_incompatible", f"coder may not own {reserved} (reserved path)", wloc)
            count = path_value.count(token)
            if policy == "create_fresh_per_attempt":
                if count == 0:
                    err("attempt_token_missing", "create_fresh_per_attempt requires one {attempt} token", wloc)
                needs_attempt = True
            elif count:
                err("attempt_token_unexpected", "{attempt} token allowed only with create_fresh_per_attempt", wloc)
            if count > 1:
                err("attempt_token_multiple", "at most one {attempt} token per path", wloc)
            if path_value in read_set and policy == "create_once":
                err("write_read_conflict", "create_once path also listed in read_first", wloc)
        if owner == "coder" and atype == "self_report":
            self_reports += 1
    if self_reports != 1:
        err("self_report_count", f"exactly one coder-owned self_report write is required (found {self_reports})")
    attempt = e.get("attempt")
    attempt_present = attempt is not None
    has_attempt = isinstance(attempt, str) and bool(ATTEMPT_RE.match(attempt))
    if needs_attempt and attempt is None:
        err("attempt_missing", "corrective or fresh-per-attempt slices require attempt")
    elif attempt is not None and not has_attempt:
        err("attempt_format", "attempt must be three zero-padded digits as a string, 001 through 999")

    # gates
    gates = e["opening_gates"]
    if gates != "none":
        if not isinstance(gates, list) or not gates:
            err("invalid_type", "opening_gates must be 'none' or a non-empty list")
        else:
            for i, g in enumerate(gates):
                gloc = f"{loc}.opening_gates[{i}]"
                if not isinstance(g, dict) or "kind" not in g:
                    err("invalid_type", "gate must be a mapping with kind", gloc)
                    continue
                kind = g["kind"]
                if kind not in layout["gate_kinds"]:
                    err("gate_kind_invalid", f"unknown gate kind {kind!r}", gloc)
                    continue
                ref = g.get("reference")
                if not isinstance(ref, str) or not ref.strip():
                    err("gate_reference_missing", "gate requires reference", gloc)
                elif kind in PATH_GATE_KINDS and not _record_path_ok(ref):
                    err("gate_reference_invalid", f"{kind} gate reference must be an exact repository-relative path: {ref!r}", gloc)
                if kind == "artifact_identity" and not (isinstance(g.get("sha256"), str) and SHA256_RE.match(g["sha256"])):
                    err("gate_identity_missing", "artifact_identity gate requires sha256", gloc)
                if kind == "pinned_external_release":
                    for key in ("repository", "tag", "commit"):
                        if not isinstance(g.get(key), str) or not g[key].strip():
                            err("gate_identity_missing", f"pinned_external_release gate requires {key}", gloc)
    # external inputs
    ext = e["external_inputs"]
    if ext != "none":
        if not isinstance(ext, list) or not ext:
            err("external_input_invalid", "external_inputs must be 'none' or a non-empty list")
        else:
            for i, x in enumerate(ext):
                xloc = f"{loc}.external_inputs[{i}]"
                if not isinstance(x, dict) or not all(isinstance(x.get(k), str) and x[k].strip() for k in ("repository", "path", "role", "identity")):
                    err("external_input_invalid", "external input requires repository, path, role, identity", xloc)
                elif not _record_path_ok(x["path"]):
                    err("external_input_invalid", f"external input path must be an exact relative file path: {x['path']!r}", xloc)
    # candidate identity
    cand = e["candidate_identity"]
    if cand != "none":
        if not isinstance(cand, dict) or not all(k in cand for k in ("strategy", "paths", "identity_value")):
            err("candidate_identity_invalid", "candidate_identity must be 'none' or {strategy, paths, identity_value}")
        elif not _is_list_of_str(cand["paths"]) or not isinstance(cand["identity_value"], str) or not cand["identity_value"].strip():
            err("candidate_identity_invalid", "candidate_identity needs non-empty paths and identity_value")
        elif any(not _record_path_ok(p) for p in cand["paths"]):
            err("candidate_identity_invalid", "candidate_identity paths must be exact repository-relative file paths")
    # correction
    corr = e["correction"]
    if e["corrective"] is True:
        if corr == "none" or not isinstance(corr, dict):
            err("correction_missing", "corrective: true requires a correction block")
        else:
            cmissing = [k for k in CORRECTION_REQUIRED if k not in corr]
            for key in cmissing:
                err("correction_field_missing", f"correction block missing {key}")
            findings = corr.get("findings")
            if "findings" not in cmissing and (
                not isinstance(findings, list) or not findings or not all(
                    isinstance(f, dict) and all(isinstance(f.get(k), str) and f[k].strip() for k in FINDING_REQUIRED)
                    for f in findings
                )
            ):
                err("correction_findings_missing", "each correction finding requires " + ", ".join(FINDING_REQUIRED))
            pe = corr.get("prior_evidence")
            if "prior_evidence" not in cmissing and (
                not isinstance(pe, list) or not pe or not all(
                    isinstance(p, dict) and _record_path_ok(p.get("path")) and isinstance(p.get("sha256"), str) and SHA256_RE.match(p["sha256"])
                    for p in pe
                )
            ):
                err("correction_prior_evidence_invalid", "correction.prior_evidence requires exact relative path + sha256 entries")
            ruling = corr.get("controlling_ruling")
            if "controlling_ruling" not in cmissing:
                if isinstance(ruling, dict) and set(ruling) == {"disputed"}:
                    if not _record_path_ok(ruling.get("disputed")):
                        err("correction_ruling_missing", "disputed ruling requires an exact owner-note path")
                elif not _record_path_ok(ruling) or ruling == "disputed":
                    err("correction_ruling_missing", "correction.controlling_ruling must be an exact owner-note path or {disputed: <note path>}")
            if "closure_proof" not in cmissing and not _is_list_of_str(corr.get("closure_proof")):
                err("correction_closure_proof_missing", "correction.closure_proof must be a non-empty list")
            for key in ("claims_withdrawn", "evidence_invalidated"):
                if key not in cmissing and corr[key] != "none" and not _is_list_of_str(corr[key]):
                    err("correction_list_invalid", f"correction.{key} must be 'none' or a non-empty list of strings")
            if "minimum_rerun_set" not in cmissing and not _is_list_of_str(corr.get("minimum_rerun_set")):
                err("correction_list_invalid", "correction.minimum_rerun_set must be a non-empty list of strings")
    elif corr != "none":
        err("correction_unexpected", "correction block present but corrective is false")
    # execution envelope
    env = e["execution_envelope"]
    if e["live"] is True:
        if env == "none" or not isinstance(env, dict):
            err("envelope_missing", "live: true requires an execution_envelope")
        else:
            emissing = [k for k in ENVELOPE_REQUIRED if k not in env]
            for key in emissing:
                err("envelope_field_missing", f"execution_envelope missing {key}")
            if not emissing:
                tp = env["timing_probe"]
                if not isinstance(tp, dict) or not isinstance(tp.get("command"), str) or not tp["command"].strip() or not isinstance(tp.get("expected_seconds"), (int, float)) or isinstance(tp.get("expected_seconds"), bool):
                    err("envelope_probe_invalid", "timing_probe requires command and expected_seconds")
                for key in ("agent_budget_seconds", "subprocess_budget_seconds", "expected_wall_seconds", "hard_wall_seconds", "retained_bytes_max"):
                    if not isinstance(env[key], (int, float)) or isinstance(env[key], bool) or env[key] <= 0:
                        err("envelope_field_invalid", f"{key} must be a positive number")
                fo = env["frozen_override"]
                if fo != "none":
                    if not (isinstance(fo, dict) and set(fo) == {"authority"}):
                        err("envelope_field_invalid", "frozen_override must be 'none' or {authority: <owner-note path>}")
                    elif not _record_path_ok(fo["authority"]):
                        err("authority_path_invalid", f"frozen_override.authority must be an exact repository-relative record path: {fo['authority']!r}")
                bindings = env["environment_bindings"]
                if bindings != "none":
                    if not isinstance(bindings, list) or not bindings:
                        err("envelope_field_invalid", "environment_bindings must be 'none' or a non-empty list")
                    else:
                        for b in bindings:
                            if not isinstance(b, dict):
                                err("envelope_field_invalid", "binding must be a mapping")
                                continue
                            if "value" in b:
                                err("envelope_binding_value_present", f"binding {b.get('name')!r} carries a value; only name and value_sha256 are allowed")
                            if not isinstance(b.get("name"), str) or not b["name"].strip():
                                err("envelope_field_invalid", "binding requires name")
                            if not (isinstance(b.get("value_sha256"), str) and SHA256_RE.match(b["value_sha256"])):
                                err("envelope_binding_hash_format", f"binding {b.get('name')!r} value_sha256 must be 64 lowercase hex digits")
                ids = env["identities"]
                if ids != "none" and not _is_list_of_str(ids):
                    err("envelope_field_invalid", "identities must be 'none' or a non-empty list of strings")
                root = env["local_output_root"]
                if not isinstance(root, str) or not root.strip():
                    err("local_output_root_outside_local_state", "local_output_root must be a path under local_state/")
                else:
                    tokens = root.count(token)
                    if attempt_present and tokens != 1:
                        err("local_output_root_attempt_token", "an attempt-bearing entry needs exactly one {attempt} token in local_output_root")
                    elif not attempt_present and tokens:
                        err("local_output_root_attempt_token", "an entry without an attempt must not carry an {attempt} token in local_output_root")
                    resolved = resolve_attempt(root, token, attempt if has_attempt else "001")
                    norm = _normalized_relative(resolved)
                    if norm is None or not norm.startswith(LOCAL_STATE_ROOT) or norm == LOCAL_STATE_ROOT:
                        err("local_output_root_outside_local_state", f"local_output_root must resolve under {LOCAL_STATE_ROOT}: {root!r}")
                if env["cleanup"] not in layout["cleanup_values"]:
                    err("envelope_cleanup_invalid", f"cleanup must be one of {layout['cleanup_values']}")
                for key in ("negative_result_handling", "stopped_result_handling"):
                    if env[key] not in layout["result_handling_values"]:
                        err("envelope_handling_invalid", f"{key} must be one of {layout['result_handling_values']}")
    elif env != "none":
        err("envelope_unexpected", "execution_envelope present but live is false")
    # objective
    obj = e["objective"]
    if not isinstance(obj, dict) or not _is_list_of_str(obj.get("success_criteria")) or not _is_list_of_str(obj.get("closure_proof")):
        err("objective_missing", "objective requires non-empty success_criteria and closure_proof lists")
    return d


def check_alignment(a: dict, b: dict, rel_a: str, rel_b: str) -> list[Diagnostic]:
    d: list[Diagnostic] = []
    if a.get("slice_prompt_contract_version") != b.get("slice_prompt_contract_version"):
        d.append(Diagnostic("projection_version_mismatch", rel_b, "", "sidecars declare different contract versions"))
    sa = {s.get("slice"): s for s in a.get("slices", []) if isinstance(s, dict)}
    sb = {s.get("slice"): s for s in b.get("slices", []) if isinstance(s, dict)}
    for sid in sorted(set(sa) | set(sb), key=str):
        if sid not in sa or sid not in sb:
            where = rel_b if sid not in sb else rel_a
            d.append(Diagnostic("projection_counterpart_missing", where, str(sid), "slice declared in only one projection"))
        elif sa[sid] != sb[sid]:
            d.append(Diagnostic("projection_entry_mismatch", rel_b, str(sid), "slice entry differs between projections"))
    return d


# --- fenced blocks and sections (CommonMark backtick and tilde fences) --------


def fenced_lines(text: str) -> list[tuple[str, bool]]:
    """(line, inside_fence) for every line. A fence opens with up to three spaces
    of indent and three or more backticks or tildes; it closes on a line of the
    same character at least as long, with only whitespace after it. Fence lines
    themselves count as fenced."""
    out: list[tuple[str, bool]] = []
    open_char, open_len = "", 0
    for line in text.splitlines():
        m = FENCE_RE.match(line)
        if open_char:
            if m and m.group(1)[0] == open_char and len(m.group(1)) >= open_len and not m.group(2).strip():
                out.append((line, True))
                open_char, open_len = "", 0
            else:
                out.append((line, True))
            continue
        if m and (open_char := m.group(1)[0]):
            open_len = len(m.group(1))
            out.append((line, True))
            continue
        out.append((line, False))
    return out


def _sections(text: str) -> tuple[list[str], dict[str, list[tuple[int, str]]]]:
    """Heading order and, per heading, the numbered lines of its body (fenced
    lines included, fenced headings ignored)."""
    order: list[str] = []
    bodies: dict[str, list[tuple[int, str]]] = {}
    current = ""
    for number, (line, fenced) in enumerate(fenced_lines(text)):
        m = None if fenced else HEADING_RE.match(line)
        if m:
            current = m.group(1)
            order.append(current)
            bodies.setdefault(current, [])
            continue
        bodies.setdefault(current, []).append((number, line))
    return order, bodies


# --- rendered prompt: keyed extraction ---------------------------------------


def _strip_ticks(value: str) -> str:
    v = value.strip()
    return v[1:-1] if len(v) >= 2 and v.startswith("`") and v.endswith("`") else v


def _span(line_no: int, line: str, value: str) -> tuple[int, int, int]:
    start = line.rfind(value) if value else len(line)
    return line_no, start, start + len(value)


def _bullets(lines: list[tuple[int, str]]):
    """Top-level bullets with their nested `  - ` children:
    (line_no, full_line, text, [(line_no, full_line, text)...])."""
    items = []
    for number, line in lines:
        if line.startswith("- "):
            items.append((number, line, line[2:], []))
        elif line.startswith("  - ") and items:
            items[-1][3].append((number, line, line[4:]))
    return items


def _table_rows(lines: list[tuple[int, str]]):
    rows = []
    for number, line in lines:
        if line.startswith("|") and not line.startswith("| ---") and not line.startswith("| Exact") and not line.startswith("| Repository") and not line.startswith("| Finding"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append((number, line, cells))
    return rows


def extract_rendered(text: str) -> tuple[list[str], dict[str, list[tuple[int, str]]], dict[tuple, Extracted]]:
    """Parse a rendered v1 prompt into (section order, section bodies, fields keyed
    by the entry's key path). Fields are found at their rendered positions only."""
    order, bodies = _sections(text)
    fields: dict[tuple, Extracted] = {}

    def put(path: tuple, value: str, line_no: int, line: str) -> None:
        n, s, e = _span(line_no, line, value)
        fields[path] = Extracted(path, value, n, s, e)

    # metadata: the first fenced block in the preamble
    in_block = False
    for number, line in bodies.get("", []):
        if FENCE_RE.match(line):
            if in_block:
                break
            in_block = True
            continue
        if in_block:
            m = re.match(r"^([a-z_]+): (.*)$", line)
            if m:
                value = m.group(2)
                if len(value) >= 2 and value[0] == value[-1] == '"':
                    value = value[1:-1]
                put((m.group(1),), value, number, line)

    def exact_list(section: str, key: tuple, leading_only: int | None = None) -> None:
        items = _bullets(bodies.get(section, []))
        if leading_only is not None:
            items = items[:leading_only]
        for i, (number, line, item, _children) in enumerate(items):
            put(key + (str(i),), _strip_ticks(item), number, line)

    exact_list("Active Workspaces", ("active_workspaces",))
    exact_list("Read First", ("read_first",))
    exact_list("Non-Goals", ("non_goals",))
    exact_list("Definition Of Done", ("definition_of_done",))
    # task: the section body joined
    task_lines = [line for _n, line in bodies.get("Task", [])]
    task_text = "\n".join(task_lines).strip()
    if task_text:
        first = next((n for n, l in bodies.get("Task", []) if l.strip()), 0)
        fields[("task",)] = Extracted(("task",), task_text, first, 0, 0)
    # tables
    for i, (number, line, cells) in enumerate(_table_rows(bodies.get("Write Manifest", []))):
        for key, cell in zip(("path", "artifact_type", "role_owner", "retry_policy"), cells):
            put(("writes", str(i), key), cell, number, line)
    for i, (number, line, cells) in enumerate(_table_rows(bodies.get("External Repositories", []))):
        for key, cell in zip(("repository", "role", "path", "identity"), cells):
            put(("external_inputs", str(i), key), cell, number, line)
    for i, (number, line, cells) in enumerate(_table_rows(bodies.get("Correction Scope Map", []))):
        for key, cell in zip(FINDING_REQUIRED, cells):
            put(("correction", "findings", str(i), key), cell, number, line)
    # gates
    for i, (number, line, item, _c) in enumerate(_bullets(bodies.get("Opening Gates", []))):
        m = GATE_RE.match(item)
        if not m:
            continue
        for key, value in m.groupdict().items():
            if value is not None:
                put(("opening_gates", str(i), key), value.strip(), number, line)

    def labeled(section: str) -> dict[str, tuple]:
        out = {}
        for number, line, item, children in _bullets(bodies.get(section, [])):
            if ": " in item:
                label, value = item.split(": ", 1)
                out[label] = (number, line, value, children)
            elif item.endswith(":"):
                out[item[:-1]] = (number, line, "", children)
        return out

    def list_field(section_fields: dict, label: str, key: tuple, transform=None) -> None:
        if label not in section_fields:
            return
        number, item, value, children = section_fields[label]
        if children:
            for i, (cn, cline, child) in enumerate(children):
                if transform:
                    for sub_key, sub_value in transform(child):
                        put(key + (str(i), sub_key), sub_value, cn, cline)
                else:
                    put(key + (str(i),), _strip_ticks(child), cn, cline)
        elif value.strip():
            put(key, value.strip(), number, item)

    corr = labeled("Correction Scope Map")
    if "Controlling ruling" in corr:
        number, item, value, _c = corr["Controlling ruling"]
        if value.startswith("disputed; see "):
            put(("correction", "controlling_ruling", "disputed"), _strip_ticks(value[len("disputed; see "):]), number, item)
        else:
            put(("correction", "controlling_ruling"), _strip_ticks(value), number, item)
    list_field(corr, "Prior evidence identities", ("correction", "prior_evidence"),
               lambda child: [(k, v) for k, v in (EVIDENCE_RE.match(child).groupdict().items() if EVIDENCE_RE.match(child) else [])])
    list_field(corr, "Required closure proof", ("correction", "closure_proof"))
    list_field(corr, "Claims withdrawn or narrowed", ("correction", "claims_withdrawn"))
    list_field(corr, "Evidence invalidated", ("correction", "evidence_invalidated"))
    list_field(corr, "Minimum rerun set", ("correction", "minimum_rerun_set"))

    cand = labeled("Candidate Identity")
    if "Identity strategy (file / manifest / git)" in cand:
        number, item, value, _c = cand["Identity strategy (file / manifest / git)"]
        put(("candidate_identity", "strategy"), value.strip(), number, item)
    list_field(cand, "Candidate paths", ("candidate_identity", "paths"))
    if "Identity value recorded at freeze" in cand:
        number, item, value, _c = cand["Identity value recorded at freeze"]
        put(("candidate_identity", "identity_value"), value.strip(), number, item)

    env = labeled("Execution Envelope")
    if "Timing probe" in env:
        number, item, value, _c = env["Timing probe"]
        m = PROBE_RE.match(value.strip())
        if m:
            put(("execution_envelope", "timing_probe", "command"), m.group("command"), number, item)
            put(("execution_envelope", "timing_probe", "expected_seconds"), m.group("expected_seconds"), number, item)
    for label, key in (("Agent/model budget", "agent_budget_seconds"), ("Scientific subprocess budget", "subprocess_budget_seconds")):
        if label in env:
            number, item, value, _c = env[label]
            m = SECONDS_RE.match(value.strip())
            if m:
                put(("execution_envelope", key), m.group("value"), number, item)
    if "Expected wall" in env:
        number, item, value, _c = env["Expected wall"]
        m = WALLS_RE.match(value.strip())
        if m:
            put(("execution_envelope", "expected_wall_seconds"), m.group("expected_wall_seconds"), number, item)
            put(("execution_envelope", "hard_wall_seconds"), m.group("hard_wall_seconds"), number, item)
    if "Frozen override" in env:
        number, item, value, _c = env["Frozen override"]
        v = value.strip()
        if v.startswith("authority "):
            put(("execution_envelope", "frozen_override", "authority"), _strip_ticks(v[len("authority "):]), number, item)
        else:
            put(("execution_envelope", "frozen_override"), v, number, item)
    list_field(env, "Environment bindings (name and value hash only; values live in the runner's policy)", ("execution_envelope", "environment_bindings"),
               lambda child: [(k, v) for k, v in (BINDING_RE.match(child).groupdict().items() if BINDING_RE.match(child) else [])])
    list_field(env, "Identities (arm / group / order / attempt)", ("execution_envelope", "identities"))
    for label, key in (("Retained bytes max", "retained_bytes_max"), ("Local output root", "local_output_root"), ("Cleanup", "cleanup"),
                       ("Negative result handling", "negative_result_handling"), ("Stopped result handling", "stopped_result_handling")):
        if label in env:
            number, item, value, _c = env[label]
            put(("execution_envelope", key), _strip_ticks(value), number, item)
    # objective: two lists split by their label lines
    obj_lines = bodies.get("Objective And Closure Proof", [])
    current_key = None
    counters = {"success_criteria": 0, "closure_proof": 0}
    for number, line in obj_lines:
        if line.startswith("Success criteria:"):
            current_key = "success_criteria"
        elif line.startswith("Closure proof the review will look for:"):
            current_key = "closure_proof"
        elif line.startswith("- ") and current_key:
            put(("objective", current_key, str(counters[current_key])), _strip_ticks(line[2:]), number, line)
            counters[current_key] += 1
    # verification: the leading bullets are the typed values (static bullets follow)
    for i, (number, line, item, _c) in enumerate(_bullets(bodies.get("Verification", []))):
        if item.startswith("When cases share") or item.startswith("If this prompt") or item.startswith("When changed artifacts"):
            break
        put(("verification", str(i)), _strip_ticks(item), number, line)
    # self-report path: first backticked token in the section
    for number, line in bodies.get("Self-Report", []):
        m = re.match(r"^`([^`]+)`$", line.strip())
        if m:
            fields[("self_report_path",)] = Extracted(("self_report_path",), m.group(1), number, line.find(m.group(1)), line.find(m.group(1)) + len(m.group(1)))
            break
    return order, bodies, fields


FIELD_SECTIONS = {
    "slice": "", "title": "", "milestone": "", "authored_by": "", "status": "",
    "dispatch_authority": "", "attempt": "", "strictness": "", "mode": "", "live": "",
    "corrective": "",
    "task": "Task", "active_workspaces": "Active Workspaces", "read_first": "Read First",
    "writes": "Write Manifest", "non_goals": "Non-Goals", "verification": "Verification",
    "opening_gates": "Opening Gates", "external_inputs": "External Repositories",
    "candidate_identity": "Candidate Identity", "correction": "Correction Scope Map",
    "execution_envelope": "Execution Envelope", "objective": "Objective And Closure Proof",
    "definition_of_done": "Definition Of Done",
}


def expected_fields(entry: dict, token: str) -> dict[tuple, str]:
    """The entry's scalar leaves as the rendered form must carry them."""
    attempt = entry.get("attempt") if isinstance(entry.get("attempt"), str) else None
    expected: dict[tuple, str] = {}
    for key, value in entry.items():
        if key not in FIELD_SECTIONS or (value == "none" and FIELD_SECTIONS[key]):
            continue
        if key == "task":
            expected[("task",)] = str(value).strip()
            continue
        for path, leaf in iter_leaves(value, (key,)):
            expected[path] = resolve_attempt(_leaf_text(leaf), token, attempt)
    for w in entry.get("writes", []) if isinstance(entry.get("writes"), list) else []:
        if isinstance(w, dict) and w.get("artifact_type") == "self_report" and w.get("role_owner") == "coder":
            expected[("self_report_path",)] = resolve_attempt(str(w.get("path")), token, attempt)
    return expected


def check_rendered(doc: dict, slice_id: str, attempt_arg: str | None, rendered: str, rel: str, layout: dict) -> list[Diagnostic]:
    d: list[Diagnostic] = []

    def err(code: str, msg: str) -> None:
        d.append(Diagnostic(code, rel, slice_id, msg))

    entry = next((s for s in doc.get("slices", []) if isinstance(s, dict) and s.get("slice") == slice_id), None)
    if entry is None:
        return [Diagnostic("slice_not_found", rel, slice_id, "slice id not in sidecar")]
    token = layout["attempt_token"]
    entry_attempt = entry.get("attempt") if isinstance(entry.get("attempt"), str) else None
    if attempt_arg is not None and attempt_arg != entry_attempt:
        err("attempt_mismatch", f"--attempt {attempt_arg} does not match the entry's attempt {entry_attempt!r}; an entry has one attempt identity")
    attempt = entry_attempt
    order, bodies, fields = extract_rendered(rendered)
    counts = {h: order.count(h) for h in order}
    for h in layout["rendered_sections_required"]:
        if counts.get(h, 0) == 0:
            err("rendered_section_missing", f"required section missing: {h}")
        elif counts[h] > 1:
            err("rendered_section_duplicate", f"section appears more than once: {h}")
    applicable = {
        "Opening Gates": entry.get("opening_gates") != "none",
        "External Repositories": entry.get("external_inputs") != "none",
        "Correction Scope Map": entry.get("corrective") is True,
        "Candidate Identity": entry.get("candidate_identity") != "none",
        "Execution Envelope": entry.get("live") is True,
    }
    for h in layout["rendered_sections_conditional"]:
        want = applicable.get(h, False)
        have = counts.get(h, 0)
        if want and have == 0:
            err("rendered_section_missing", f"applicable section missing: {h}")
        if not want and have:
            err("rendered_section_unexpected", f"section rendered although not applicable: {h}")
        if have > 1:
            err("rendered_section_duplicate", f"section appears more than once: {h}")
    for s in layout["sentinels"]:
        if s in rendered:
            err("rendered_sentinel_residue", f"unresolved sentinel in rendered prompt: {s}")
    low = rendered.lower()
    for phrase in RESIDUE_PHRASES:
        if phrase in low:
            err("rendered_section_residue", f"deleted-section residue: {phrase!r}")
    if token in rendered:
        err("rendered_token_unresolved", "{attempt} token survives in the rendered prompt")

    # keyed losslessness: every expected field must be extracted with exactly its value
    expected = expected_fields(entry, token)
    metadata_keys = {k for k, s in FIELD_SECTIONS.items() if s == ""}
    for path, value in expected.items():
        found = fields.get(path)
        where = ".".join(path)
        if path[0] in metadata_keys and len(path) == 1:
            if found is None:
                err("rendered_metadata_missing", f"workflow metadata missing {path[0]}: {value}")
            elif found.value != value:
                err("rendered_metadata_missing", f"workflow metadata {path[0]} renders {found.value!r}, expected {value!r}")
            continue
        if found is None:
            err("rendered_value_missing", f"{where} is not rendered at its field position (expected {value[:60]!r})")
        elif found.value != value:
            err("rendered_value_missing", f"{where} renders {found.value[:60]!r}, expected {value[:60]!r}")
    for path in fields:
        if path not in expected and path[0] in FIELD_SECTIONS:
            err("rendered_value_missing", f"{'.'.join(path)} is rendered but the entry declares no such value")
    if attempt is None and ("attempt",) in fields:
        err("rendered_metadata_missing", "attempt line rendered for an entry without an attempt")
    if entry.get("dispatch_authority") is None and ("dispatch_authority",) in fields:
        err("rendered_metadata_missing", "dispatch_authority line rendered for an entry without one")
    # write manifest rows: each row complete on one line; attempt reuse anywhere
    manifest_lines = [line for _n, line in bodies.get("Write Manifest", [])]
    for w in entry.get("writes", []) if isinstance(entry.get("writes"), list) else []:
        if not isinstance(w, dict):
            continue
        path_value = str(w.get("path", ""))
        resolved = resolve_attempt(path_value, token, attempt)
        row = f"| {resolved} | {w.get('artifact_type')} | {w.get('role_owner')} | {w.get('retry_policy')} |"
        if row not in manifest_lines:
            err("rendered_manifest_row_missing", f"write manifest row missing or incomplete for {resolved}")
        if token in path_value and attempt:
            for other in range(1, 1000):
                other_attempt = f"{other:03d}"
                if other_attempt != attempt and resolve_attempt(path_value, token, other_attempt) in rendered:
                    err("rendered_attempt_path_reuse", f"a write target resolves to attempt {other_attempt}, not {attempt}")
                    break
    env = entry.get("execution_envelope")
    if isinstance(env, dict) and isinstance(env.get("local_output_root"), str) and attempt:
        for other in range(1, 1000):
            other_attempt = f"{other:03d}"
            if other_attempt != attempt and resolve_attempt(env["local_output_root"], token, other_attempt) in rendered:
                err("rendered_attempt_path_reuse", f"local_output_root resolves to attempt {other_attempt}, not {attempt}")
                break
    return d


# --- review report closure record -------------------------------------------


def check_review_report(text: str, rel: str, layout: dict) -> list[Diagnostic]:
    d: list[Diagnostic] = []

    def err(code: str, msg: str) -> None:
        d.append(Diagnostic(code, rel, "", msg))

    order, bodies = _sections(text)
    closure_n = order.count("Closure Decision")
    verdict_n = order.count("Verdict")
    if closure_n == 0:
        err("closure_section_missing", "no '## Closure Decision' section")
    elif closure_n > 1:
        err("closure_section_duplicate", "more than one '## Closure Decision' section")
    if verdict_n == 0:
        err("verdict_section_missing", "no '## Verdict' section")
    elif verdict_n > 1:
        err("verdict_section_duplicate", "more than one '## Verdict' section")
    if closure_n == 1 and verdict_n == 1:
        ci, vi = order.index("Closure Decision"), order.index("Verdict")
        if ci > vi:
            err("closure_after_verdict", "'## Closure Decision' must precede '## Verdict'")
        elif vi != ci + 1:
            err("closure_not_adjacent", "'## Closure Decision' must be the section immediately before '## Verdict'")
    status_lines = sum(1 for line, fenced in fenced_lines(text) if not fenced and line.startswith("Objective status:"))
    evidence_lines = sum(1 for line, fenced in fenced_lines(text) if not fenced and line.startswith("Objective evidence:"))
    if status_lines > 1:
        err("objective_status_duplicate", f"exactly one 'Objective status:' line is allowed in the report (found {status_lines})")
    if evidence_lines > 1:
        err("objective_evidence_duplicate", f"exactly one 'Objective evidence:' line is allowed in the report (found {evidence_lines})")
    if closure_n == 1:
        lines = [l for _n, l in bodies.get("Closure Decision", []) if l.strip()]
        if len(lines) != 2:
            err("closure_line_count", f"the closure section must hold exactly two non-empty lines (found {len(lines)})")
        status_here = [l for l in lines if l.startswith("Objective status:")]
        if len(status_here) != 1:
            err("objective_status_line_missing", "exactly one 'Objective status:' line is required in the closure section")
        else:
            value = status_here[0].split(":", 1)[1].strip()
            if value not in layout["objective_status_values"]:
                err("objective_status_invalid", f"unknown objective status {value!r}")
            idx = lines.index(status_here[0])
            nxt = lines[idx + 1] if idx + 1 < len(lines) else ""
            if idx != 0 or not nxt.startswith("Objective evidence:") or not nxt.split(":", 1)[1].strip():
                err("objective_evidence_line_missing", "the status line must be first and an 'Objective evidence:' line must immediately follow it")
    if verdict_n == 1:
        vlines = [l for _n, l in bodies.get("Verdict", []) if l.strip()]
        if not vlines or not VERDICT_FOOTER_RE.match(vlines[0]):
            err("verdict_footer_invalid", "first non-empty line under '## Verdict' must be 'Verdict: <value> - next: <one move>'")
        if any(l.startswith("Objective status:") for l in vlines):
            err("objective_status_in_verdict", "objective status must not appear inside '## Verdict'")
    return d


# --- CLI ----------------------------------------------------------------------


def _stable(diags: list[Diagnostic]) -> list[Diagnostic]:
    return sorted(diags, key=lambda x: (x.path, x.location, x.code, x.message))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--layout", type=Path, default=None, help="layout file (default <root>/frutlups.layout.yaml)")
    parser.add_argument("--sidecar", action="append", default=[], type=Path)
    parser.add_argument("--slice", dest="slice_id")
    parser.add_argument("--attempt", type=int, help="optional confirmation of the entry's attempt identity")
    parser.add_argument("--rendered", type=Path)
    parser.add_argument("--review-report", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    layout_path = args.layout or root / "frutlups.layout.yaml"
    layout, diags = load_layout_contract(layout_path)
    docs: list[tuple[Path, dict]] = []
    if layout is not None:
        for sc in args.sidecar:
            rel = sc.as_posix()
            try:
                doc = _load_yaml_file(sc)
            except (OSError, _StrictLoadError) as exc:
                diags.append(Diagnostic("sidecar_unreadable", rel, "", str(exc)))
                continue
            diags.extend(validate_sidecar(doc, rel, layout, sidecar_path=sc))
            if isinstance(doc, dict):
                docs.append((sc, doc))
        if len(docs) == 2:
            diags.extend(check_alignment(docs[0][1], docs[1][1], docs[0][0].as_posix(), docs[1][0].as_posix()))
        if args.rendered is not None:
            if not docs or not args.slice_id:
                diags.append(Diagnostic("usage", args.rendered.as_posix(), "", "--rendered requires --sidecar and --slice"))
            else:
                attempt = f"{args.attempt:03d}" if args.attempt is not None else None
                try:
                    rendered = args.rendered.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    diags.append(Diagnostic("rendered_unreadable", args.rendered.as_posix(), "", str(exc)))
                else:
                    diags.extend(check_rendered(docs[0][1], args.slice_id, attempt, rendered, args.rendered.as_posix(), layout))
        if args.review_report is not None:
            try:
                text = args.review_report.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                diags.append(Diagnostic("review_report_unreadable", args.review_report.as_posix(), "", str(exc)))
            else:
                diags.extend(check_review_report(text, args.review_report.as_posix(), layout))
    diags = _stable(diags)
    result = "fail" if any(x.severity == "error" for x in diags) else "pass"
    if args.json:
        print(json.dumps({"schema": SCHEMA, "result": result, "diagnostics": [asdict(x) for x in diags]}, indent=2, sort_keys=True))
    else:
        print("Slice contract check (read-only)")
        for x in diags:
            loc = f":{x.location}" if x.location else ""
            print(f"{x.severity.upper()} {x.code} {x.path}{loc}: {x.message}")
        print(f"Result: {result} ({len(diags)} diagnostic(s))")
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
