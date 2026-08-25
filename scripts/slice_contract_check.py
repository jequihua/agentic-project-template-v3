"""Reference checker for the template's slice prompt contract v1 (read-only).

Validates a sidecar (`<roadmap-stem>.slices.yaml`), the cross-projection
alignment of two sidecars, a rendered coding prompt against its sidecar entry,
and the closure record of a review report. The closed vocabularies are read
from the ONE canonical declaration, the `slice_prompt_contract` block of
`frutlups.layout.yaml`; nothing here restates them.

This is a reference implementation for the template's own fixtures and for
project-side preflight. It is never dispatch authority. Downstream tools keep
their own parsers and must pass the same fixtures.

Usage (from the repository root):

    python scripts/slice_contract_check.py --sidecar 03_experiments/x.slices.yaml
    python scripts/slice_contract_check.py --sidecar a.slices.yaml --sidecar b.slices.yaml
    python scripts/slice_contract_check.py --sidecar x.slices.yaml --slice M001-S02 \\
        --attempt 2 --rendered prompts/for_coding_agent/012_x.md
    python scripts/slice_contract_check.py --review-report 05_governance/reviews/r.md

Properties: read-only, exact-path driven, deterministic, network-free, stable
diagnostic codes emitted in stable order, machine-readable `--json` output.
PyYAML (the declared dependency) is imported lazily so `--help` works without it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SCHEMA = "template.slice_contract_check.v1"
MAX_INPUT_BYTES = 1_048_576
SLICE_ID_RE = re.compile(r"^M\d{3}-S\d{2}$")
MILESTONE_ID_RE = re.compile(r"^M\d{3}$")
ATTEMPT_RE = re.compile(r"^\d{3}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STRICTNESS_RE = re.compile(r"^Level [1-4]$")
HEADING_RE = re.compile(r"^## (.+?)\s*$")
VERDICT_FOOTER_RE = re.compile(r"^Verdict: (pass|needs_work|blocked|override) - next: \S.*$")
RESIDUE_PHRASES = (
    "delete this section", "contract v1 section", "fills or deletes",
    "conditional: rendered only", "this preamble is scaffold documentation",
)
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


@dataclass
class Diagnostic:
    code: str
    path: str
    location: str
    message: str
    severity: str = "error"


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

    _Strict.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
    )
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


def _path_problem(path_value: str) -> str | None:
    if not isinstance(path_value, str) or not path_value.strip():
        return "write_path_empty"
    p = path_value.strip()
    if p.endswith("/") or p.endswith("\\"):
        return "write_path_directory"
    if any(ch in p for ch in "*?[") :
        return "write_path_glob"
    if p.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", p) or p.startswith("\\\\"):
        return "write_path_absolute"
    parts = p.replace("\\", "/").split("/")
    if ".." in parts or "." in parts:
        return "write_path_escape"
    if "/" not in p and "." not in parts[-1]:
        return "write_path_not_file"
    if "." not in parts[-1]:
        return "write_path_not_file"
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


def resolve_attempt(path_value: str, token: str, attempt: str) -> str:
    return path_value.replace(token, attempt)


# --- sidecar validation -----------------------------------------------------


def validate_sidecar(doc: object, rel: str, layout: dict) -> list[Diagnostic]:
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
        for field in SLICE_REQUIRED:
            if field not in entry:
                d.append(Diagnostic("missing_field", rel, loc, f"required field missing: {field}"))
        if any(x.code == "missing_field" and x.location == loc for x in d):
            continue
        d.extend(_validate_entry(entry, rel, loc, layout))
    return d


def _validate_entry(e: dict, rel: str, loc: str, layout: dict) -> list[Diagnostic]:
    d: list[Diagnostic] = []
    err = lambda code, msg: d.append(Diagnostic(code, rel, loc, msg))  # noqa: E731
    sentinels = layout["sentinels"]
    hits = _sentinel_hits({k: v for k, v in e.items()}, sentinels)
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
    elif status == "ready":
        auth = e.get("dispatch_authority")
        if not isinstance(auth, str) or not auth.strip():
            err("dispatch_authority_missing", "status: ready requires dispatch_authority (exact record path)")
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
            if _path_problem(rf) in ("write_path_absolute", "write_path_escape", "write_path_glob"):
                err("read_first_path_invalid", f"read_first entry is not an exact repository-relative path: {rf}")

    # write manifest
    writes = e["writes"]
    self_reports = 0
    token = layout["attempt_token"]
    needs_attempt = bool(e["corrective"]) if isinstance(e["corrective"], bool) else False
    if not isinstance(writes, list) or not writes:
        err("empty_list", "writes must be a non-empty list")
        writes = []
    read_set = set(e["read_first"]) if _is_list_of_str(e["read_first"]) else set()
    for i, w in enumerate(writes):
        wloc = f"{loc}.writes[{i}]"
        if not isinstance(w, dict):
            d.append(Diagnostic("invalid_type", rel, wloc, "write entry must be a mapping")); continue
        for key in ("path", "artifact_type", "role_owner", "retry_policy"):
            if key not in w:
                d.append(Diagnostic("missing_field", rel, wloc, f"write entry missing {key}"))
        if any(x.location == wloc and x.code == "missing_field" for x in d):
            continue
        path_value = w["path"]
        problem = _path_problem(path_value)
        if problem:
            d.append(Diagnostic(problem, rel, wloc, f"invalid write path: {path_value!r}"))
        atype, owner, policy = w["artifact_type"], w["role_owner"], w["retry_policy"]
        if atype not in layout["artifact_types"]:
            d.append(Diagnostic("artifact_type_invalid", rel, wloc, f"unknown artifact_type {atype!r}"))
        if owner not in layout["role_owners"]:
            d.append(Diagnostic("role_owner_invalid", rel, wloc, f"unknown role_owner {owner!r}"))
        if policy not in layout["retry_policies"]:
            d.append(Diagnostic("retry_policy_invalid", rel, wloc, f"unknown retry_policy {policy!r}"))
        if atype in layout["artifact_types"] and owner in layout["role_owners"]:
            allowed = layout["role_type_matrix"].get(owner, [])
            if atype not in allowed:
                d.append(Diagnostic("role_type_incompatible", rel, wloc, f"{owner} may not own {atype}"))
        if isinstance(path_value, str):
            reserved = _classify_reserved(path_value, layout["reserved_path_classification"])
            if reserved and reserved != atype:
                d.append(Diagnostic("reserved_artifact_mislabeled", rel, wloc, f"path classifies as {reserved} but is labelled {atype!r}"))
            if reserved in ("review_report", "verdict_record") and owner == "coder":
                d.append(Diagnostic("role_type_incompatible", rel, wloc, f"coder may not own {reserved} (reserved path)"))
            count = path_value.count(token)
            if policy == "create_fresh_per_attempt":
                if count == 0:
                    d.append(Diagnostic("attempt_token_missing", rel, wloc, "create_fresh_per_attempt requires one {attempt} token"))
                needs_attempt = True
            elif count:
                d.append(Diagnostic("attempt_token_unexpected", rel, wloc, "{attempt} token allowed only with create_fresh_per_attempt"))
            if count > 1:
                d.append(Diagnostic("attempt_token_multiple", rel, wloc, "at most one {attempt} token per path"))
            if path_value in read_set and policy == "create_once":
                d.append(Diagnostic("write_read_conflict", rel, wloc, "create_once path also listed in read_first"))
        if owner == "coder" and atype == "self_report":
            self_reports += 1
    if self_reports != 1:
        err("self_report_count", f"exactly one coder-owned self_report write is required (found {self_reports})")
    attempt = e.get("attempt")
    if needs_attempt:
        if attempt is None:
            err("attempt_missing", "corrective or fresh-per-attempt slices require attempt")
        elif not (isinstance(attempt, str) and ATTEMPT_RE.match(attempt)):
            err("attempt_format", "attempt must be three zero-padded digits as a string, e.g. \"002\"")
    elif attempt is not None and not (isinstance(attempt, str) and ATTEMPT_RE.match(attempt)):
        err("attempt_format", "attempt must be three zero-padded digits as a string")

    # gates
    gates = e["opening_gates"]
    if gates != "none":
        if not isinstance(gates, list) or not gates:
            err("invalid_type", "opening_gates must be 'none' or a non-empty list")
        else:
            for i, g in enumerate(gates):
                gloc = f"{loc}.opening_gates[{i}]"
                if not isinstance(g, dict) or "kind" not in g:
                    d.append(Diagnostic("invalid_type", rel, gloc, "gate must be a mapping with kind")); continue
                kind = g["kind"]
                if kind not in layout["gate_kinds"]:
                    d.append(Diagnostic("gate_kind_invalid", rel, gloc, f"unknown gate kind {kind!r}")); continue
                if not isinstance(g.get("reference"), str) or not g["reference"].strip():
                    d.append(Diagnostic("gate_reference_missing", rel, gloc, "gate requires reference"))
                if kind == "artifact_identity" and not (isinstance(g.get("sha256"), str) and SHA256_RE.match(g["sha256"])):
                    d.append(Diagnostic("gate_identity_missing", rel, gloc, "artifact_identity gate requires sha256"))
                if kind == "pinned_external_release":
                    for key in ("repository", "tag", "commit"):
                        if not isinstance(g.get(key), str) or not g[key].strip():
                            d.append(Diagnostic("gate_identity_missing", rel, gloc, f"pinned_external_release gate requires {key}"))
    # external inputs
    ext = e["external_inputs"]
    if ext != "none":
        if not isinstance(ext, list) or not ext:
            err("external_input_invalid", "external_inputs must be 'none' or a non-empty list")
        else:
            for i, x in enumerate(ext):
                if not isinstance(x, dict) or not all(isinstance(x.get(k), str) and x[k].strip() for k in ("repository", "role", "identity")):
                    d.append(Diagnostic("external_input_invalid", rel, f"{loc}.external_inputs[{i}]", "external input requires repository, role, identity"))
    # candidate identity
    cand = e["candidate_identity"]
    if cand != "none":
        if not isinstance(cand, dict) or not all(k in cand for k in ("strategy", "paths", "identity_value")):
            err("candidate_identity_invalid", "candidate_identity must be 'none' or {strategy, paths, identity_value}")
        elif not _is_list_of_str(cand["paths"]) or not isinstance(cand["identity_value"], str) or not cand["identity_value"].strip():
            err("candidate_identity_invalid", "candidate_identity needs non-empty paths and identity_value")
    # correction
    corr = e["correction"]
    if e["corrective"] is True:
        if corr == "none" or not isinstance(corr, dict):
            err("correction_missing", "corrective: true requires a correction block")
        else:
            findings = corr.get("findings")
            if not isinstance(findings, list) or not findings or not all(
                isinstance(f, dict) and all(isinstance(f.get(k), str) and f[k].strip() for k in ("id", "violated_invariant", "prior_disposition")) for f in findings
            ):
                err("correction_findings_missing", "correction.findings requires id, violated_invariant, prior_disposition per finding")
            pe = corr.get("prior_evidence")
            if not isinstance(pe, list) or not pe or not all(
                isinstance(p, dict) and isinstance(p.get("path"), str) and isinstance(p.get("sha256"), str) and SHA256_RE.match(p["sha256"]) for p in pe
            ):
                err("correction_prior_evidence_invalid", "correction.prior_evidence requires path + sha256 entries")
            ruling = corr.get("controlling_ruling")
            ok_ruling = (isinstance(ruling, str) and ruling.strip() and ruling != "disputed") or (
                isinstance(ruling, dict) and isinstance(ruling.get("disputed"), str) and ruling["disputed"].strip()
            )
            if not ok_ruling:
                err("correction_ruling_missing", "correction.controlling_ruling must be an exact owner-note path or {disputed: <note path>}")
            if not _is_list_of_str(corr.get("closure_proof")):
                err("correction_closure_proof_missing", "correction.closure_proof must be a non-empty list")
    elif corr != "none":
        err("correction_unexpected", "correction block present but corrective is false")
    # execution envelope
    env = e["execution_envelope"]
    if e["live"] is True:
        if env == "none" or not isinstance(env, dict):
            err("envelope_missing", "live: true requires an execution_envelope")
        else:
            for key in ENVELOPE_REQUIRED:
                if key not in env:
                    err("envelope_field_missing", f"execution_envelope missing {key}")
            if all(k in env for k in ENVELOPE_REQUIRED):
                tp = env["timing_probe"]
                if not isinstance(tp, dict) or not isinstance(tp.get("command"), str) or not isinstance(tp.get("expected_seconds"), (int, float)):
                    err("envelope_probe_invalid", "timing_probe requires command and expected_seconds")
                for key in ("agent_budget_seconds", "subprocess_budget_seconds", "expected_wall_seconds", "hard_wall_seconds", "retained_bytes_max"):
                    if not isinstance(env[key], (int, float)) or isinstance(env[key], bool) or env[key] <= 0:
                        err("envelope_field_invalid", f"{key} must be a positive number")
                fo = env["frozen_override"]
                if fo != "none" and not (isinstance(fo, dict) and isinstance(fo.get("authority"), str) and fo["authority"].strip()):
                    err("envelope_field_invalid", "frozen_override must be 'none' or {authority: <owner-note path>}")
                bindings = env["environment_bindings"]
                if bindings != "none":
                    if not isinstance(bindings, list):
                        err("envelope_field_invalid", "environment_bindings must be 'none' or a list")
                    else:
                        for b in bindings:
                            if not isinstance(b, dict):
                                err("envelope_field_invalid", "binding must be a mapping"); continue
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
                if not isinstance(root, str) or not root.replace("\\", "/").startswith("local_state/"):
                    err("local_output_root_outside_local_state", "local_output_root must be under local_state/")
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
    for sid in sorted(set(sa) | set(sb)):
        if sid not in sa or sid not in sb:
            where = rel_b if sid not in sb else rel_a
            d.append(Diagnostic("projection_counterpart_missing", where, str(sid), "slice declared in only one projection"))
        elif sa[sid] != sb[sid]:
            d.append(Diagnostic("projection_entry_mismatch", rel_b, str(sid), "slice entry differs between projections"))
    return d


# --- rendered prompt check --------------------------------------------------


def _sections(text: str) -> tuple[list[str], dict[str, str]]:
    order: list[str] = []
    bodies: dict[str, list[str]] = {}
    current = ""
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        m = None if fenced else HEADING_RE.match(line)
        if m:
            current = m.group(1)
            order.append(current)
            bodies.setdefault(current, [])
            continue
        bodies.setdefault(current, []).append(line)
    return order, {k: "\n".join(v) for k, v in bodies.items()}


def check_rendered(doc: dict, slice_id: str, attempt: str | None, rendered: str, rel: str, layout: dict) -> list[Diagnostic]:
    d: list[Diagnostic] = []
    err = lambda code, msg, loc="": d.append(Diagnostic(code, rel, loc or slice_id, msg))  # noqa: E731
    entry = next((s for s in doc.get("slices", []) if isinstance(s, dict) and s.get("slice") == slice_id), None)
    if entry is None:
        return [Diagnostic("slice_not_found", rel, slice_id, "slice id not in sidecar")]
    token = layout["attempt_token"]
    order, bodies = _sections(rendered)
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
    # metadata
    for key in ("milestone", "slice", "title", "strictness", "mode", "status"):
        value = entry.get(key)
        if isinstance(value, str) and f"{key}: {value}" not in rendered and f'{key}: "{value}"' not in rendered:
            err("rendered_metadata_missing", f"workflow metadata missing {key}: {value}")
    for key in ("live", "corrective"):
        value = "true" if entry.get(key) is True else "false"
        if f"{key}: {value}" not in rendered:
            err("rendered_metadata_missing", f"workflow metadata missing {key}: {value}")
    if attempt and f"attempt: {attempt}" not in rendered and f'attempt: "{attempt}"' not in rendered:
        err("rendered_metadata_missing", f"workflow metadata missing attempt: {attempt}")
    # write manifest rows
    manifest = bodies.get("Write Manifest", "")
    for w in entry.get("writes", []):
        if not isinstance(w, dict):
            continue
        path_value = str(w.get("path", ""))
        resolved = resolve_attempt(path_value, token, attempt) if attempt else path_value
        row_ok = any(
            resolved in line and str(w.get("artifact_type")) in line and str(w.get("role_owner")) in line and str(w.get("retry_policy")) in line
            for line in manifest.splitlines()
        )
        if not row_ok:
            err("rendered_manifest_row_missing", f"write manifest row missing or incomplete for {resolved}")
        if token in path_value and attempt:
            for other in range(1, 1000):
                other_attempt = f"{other:03d}"
                if other_attempt == attempt:
                    continue
                if resolve_attempt(path_value, token, other_attempt) in manifest:
                    err("rendered_attempt_path_reuse", f"write target resolves to attempt {other_attempt}, not {attempt}")
                    break
        if w.get("artifact_type") == "self_report" and w.get("role_owner") == "coder":
            if resolved not in bodies.get("Self-Report", ""):
                err("rendered_value_missing", f"Self-Report section does not name {resolved}")
    # list values
    for field, section in (("read_first", "Read First"), ("non_goals", "Non-Goals"), ("verification", "Verification"), ("definition_of_done", "Definition Of Done"), ("active_workspaces", "Active Workspaces")):
        body = bodies.get(section, "")
        for item in entry.get(field, []) if isinstance(entry.get(field), list) else []:
            if str(item) not in body:
                err("rendered_value_missing", f"{section} does not carry: {item}")
    task_body = bodies.get("Task", "")
    for line in str(entry.get("task", "")).splitlines():
        if line.strip() and line.strip() not in task_body:
            err("rendered_value_missing", f"Task does not carry: {line.strip()[:60]}")
    obj = entry.get("objective") or {}
    obody = bodies.get("Objective And Closure Proof", "")
    for key in ("success_criteria", "closure_proof"):
        for item in obj.get(key, []) if isinstance(obj, dict) else []:
            if str(item) not in obody:
                err("rendered_value_missing", f"Objective And Closure Proof does not carry: {item}")
    if applicable["Opening Gates"]:
        gbody = bodies.get("Opening Gates", "")
        for g in entry.get("opening_gates", []):
            if isinstance(g, dict) and (str(g.get("kind")) not in gbody or str(g.get("reference")) not in gbody):
                err("rendered_value_missing", f"Opening Gates does not carry gate {g.get('kind')} {g.get('reference')}")
    if applicable["Execution Envelope"]:
        ebody = bodies.get("Execution Envelope", "")
        env = entry.get("execution_envelope") or {}
        for key in ("agent_budget_seconds", "subprocess_budget_seconds", "expected_wall_seconds", "hard_wall_seconds", "retained_bytes_max", "local_output_root", "cleanup", "negative_result_handling", "stopped_result_handling"):
            if isinstance(env, dict) and str(env.get(key)) not in ebody:
                err("rendered_value_missing", f"Execution Envelope does not carry {key}: {env.get(key)}")
        if isinstance(env, dict) and isinstance(env.get("environment_bindings"), list):
            for b in env["environment_bindings"]:
                if isinstance(b, dict) and (str(b.get("name")) not in ebody or str(b.get("value_sha256")) not in ebody):
                    err("rendered_value_missing", f"Execution Envelope does not carry binding {b.get('name')}")
    if applicable["Correction Scope Map"]:
        cbody = bodies.get("Correction Scope Map", "")
        corr = entry.get("correction") or {}
        if isinstance(corr, dict):
            for f in corr.get("findings", []) if isinstance(corr.get("findings"), list) else []:
                if isinstance(f, dict) and str(f.get("id")) not in cbody:
                    err("rendered_value_missing", f"Correction Scope Map does not carry finding {f.get('id')}")
            ruling = corr.get("controlling_ruling")
            ruling_text = ruling if isinstance(ruling, str) else (ruling.get("disputed") if isinstance(ruling, dict) else "")
            if ruling_text and str(ruling_text) not in cbody:
                err("rendered_value_missing", "Correction Scope Map does not carry the controlling ruling")
            for item in corr.get("closure_proof", []) if isinstance(corr.get("closure_proof"), list) else []:
                if str(item) not in cbody:
                    err("rendered_value_missing", f"Correction Scope Map does not carry closure proof: {item}")
    return d


# --- review report closure record -------------------------------------------


def check_review_report(text: str, rel: str, layout: dict) -> list[Diagnostic]:
    d: list[Diagnostic] = []
    err = lambda code, msg: d.append(Diagnostic(code, rel, "", msg))  # noqa: E731
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
    if closure_n and verdict_n and order.index("Closure Decision") > order.index("Verdict"):
        err("closure_after_verdict", "'## Closure Decision' must precede '## Verdict'")
    if closure_n == 1:
        lines = [l for l in bodies.get("Closure Decision", "").splitlines() if l.strip()]
        status_lines = [l for l in lines if l.startswith("Objective status:")]
        if len(status_lines) != 1:
            err("objective_status_line_missing", "exactly one 'Objective status:' line is required")
        else:
            value = status_lines[0].split(":", 1)[1].strip()
            if value not in layout["objective_status_values"]:
                err("objective_status_invalid", f"unknown objective status {value!r}")
            idx = lines.index(status_lines[0])
            nxt = lines[idx + 1] if idx + 1 < len(lines) else ""
            if not nxt.startswith("Objective evidence:") or not nxt.split(":", 1)[1].strip():
                err("objective_evidence_line_missing", "an 'Objective evidence:' line must immediately follow the status line")
    if verdict_n == 1:
        vlines = [l for l in bodies.get("Verdict", "").splitlines() if l.strip()]
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
    parser.add_argument("--attempt", type=int)
    parser.add_argument("--rendered", type=Path)
    parser.add_argument("--review-report", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    layout_path = (args.layout or root / "frutlups.layout.yaml")
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
            found = validate_sidecar(doc, rel, layout)
            diags.extend(found)
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
