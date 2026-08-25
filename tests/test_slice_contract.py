"""Slice prompt contract v1: fixtures, reference checker, scaffolds, and the
single canonical vocabulary declaration.

Stdlib-only structure tests always run. Tests that evaluate fixtures through
the reference checker need PyYAML (the declared dependency) and are skipped
when it is absent, exactly like the OKF profile-checker tests.
"""

from __future__ import annotations

import hashlib
import importlib
import io
import contextlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX_ROOT = ROOT / "tests" / "fixtures" / "slice_contract"
MANIFEST = FIX_ROOT / "manifest.json"
LAYOUT = ROOT / "frutlups.layout.yaml"
CONTRACT_DOC = ROOT / "docs" / "template_framework" / "slice_prompt_contract.md"
LEGACY_SCAFFOLD = ROOT / "prompts" / "templates" / "coding_prompt.md"
V1_SCAFFOLD = ROOT / "prompts" / "templates" / "coding_prompt_contract_v1.md"
CHECKER = ROOT / "scripts" / "slice_contract_check.py"

try:  # the declared dependency; only the checker-driven tests need it
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:  # pragma: no cover
    HAVE_YAML = False

MACHINE_FRAGMENTS = ("C:" + "\\Users\\dev", "repos" + "_dev", "/Users/", "/home/")
SLOT_RE = re.compile(r"TBD:[a-z_]+")
EXPECTED_V1_SECTION_ORDER = [
    "Current State", "Active Workspaces", "Read First", "Memory Posture", "Task",
    "Implementation Discipline", "OKF Authoring", "Write Manifest", "Opening Gates",
    "External Repositories", "Correction Scope Map", "Candidate Identity",
    "Execution Envelope", "Objective And Closure Proof", "Non-Goals", "Verification",
    "Seat Conduct", "Self-Report", "Definition Of Done",
]
LEGACY_REQUIRED = [
    "Current State", "Active Workspaces", "Read First", "Memory Posture", "Task",
    "Non-Goals", "Verification", "Self-Report", "Definition Of Done",
]


def _checker():
    scripts_dir = ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    return importlib.import_module("slice_contract_check")


def _headings(text: str) -> list[str]:
    out, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            out.append(line[3:].strip())
    return out


def _layout_block_text() -> str:
    text = LAYOUT.read_text(encoding="utf-8")
    start = text.index("\nslice_prompt_contract:\n")
    end = text.index("\ntemplate_owned_surfaces:\n")
    return text[start:end]


class SliceContractFixtureManifestTests(unittest.TestCase):
    """Stdlib-only: the fixture corpus is inventoried, digest-pinned, and clean."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.fixtures = cls.manifest["fixtures"]

    def test_manifest_schema(self) -> None:
        self.assertEqual(self.manifest["manifest_schema"], "slice_contract_fixture_manifest")
        self.assertEqual(self.manifest["contract_version"], 1)
        self.assertEqual(self.manifest["layout"], "frutlups.layout.yaml")
        self.assertEqual(self.manifest["checker"], "scripts/slice_contract_check.py")
        self.assertEqual(
            set(self.manifest["modes"]),
            {"sidecar", "align", "render", "review", "document", "external"},
        )

    def test_ids_unique_sorted_and_corpus_large_enough(self) -> None:
        ids = [f["id"] for f in self.fixtures]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 40)
        for f in self.fixtures:
            self.assertIn(f["mode"], self.manifest["modes"], f["id"])
            self.assertIn(f["expected"]["result"], ("pass", "fail", "legacy", "old_consumer_refusal"), f["id"])
            self.assertEqual(f["expected"]["codes"], sorted(set(f["expected"]["codes"])), f["id"])

    def test_inventory_complete_both_directions_and_digests_match(self) -> None:
        listed = {(ROOT / f["path"]).resolve() for f in self.fixtures}
        on_disk = {p.resolve() for p in FIX_ROOT.rglob("*") if p.is_file() and p.name != "manifest.json"}
        self.assertEqual(on_disk - listed, set(), "fixtures on disk absent from manifest")
        self.assertEqual(listed - on_disk, set(), "manifest paths absent on disk")
        for f in self.fixtures:
            with self.subTest(fixture=f["id"]):
                digest = hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest()
                self.assertEqual(digest, f["sha256"], "fixture bytes drifted from the pinned digest")

    def test_fixtures_are_utf8_lf_and_free_of_machine_paths(self) -> None:
        for f in self.fixtures:
            with self.subTest(fixture=f["id"]):
                raw = (ROOT / f["path"]).read_bytes()
                text = raw.decode("utf-8")
                self.assertNotIn(b"\r\n", raw)
                for fragment in MACHINE_FRAGMENTS:
                    self.assertNotIn(fragment, text)

    def test_adversarial_coverage_names_every_validity_rule(self) -> None:
        """Every validity rule the contract doc lists has a fixture asserting its code."""
        covered = {c for f in self.fixtures for c in f["expected"]["codes"]}
        for code in (
            "missing_field", "unknown_contract_version", "duplicate_slice",
            "write_path_directory", "write_path_glob", "write_path_absolute",
            "write_path_escape", "role_type_incompatible", "reserved_artifact_mislabeled",
            "sentinel_residue", "envelope_missing", "envelope_field_missing",
            "envelope_binding_value_present", "correction_findings_missing",
            "correction_ruling_missing", "local_output_root_outside_local_state",
            "authored_by_invalid", "dispatch_authority_missing", "attempt_token_missing",
            "attempt_token_multiple", "attempt_missing", "task_is_title_only",
            "projection_entry_mismatch", "rendered_manifest_row_missing",
            "rendered_section_unexpected", "rendered_section_residue",
            "rendered_sentinel_residue", "rendered_attempt_path_reuse",
            "objective_evidence_line_missing", "objective_status_in_verdict",
            "closure_section_missing",
        ):
            with self.subTest(code=code):
                self.assertIn(code, covered)


class SliceContractScaffoldTests(unittest.TestCase):
    """Stdlib-only: two scaffolds, legacy byte-identical, v1 fully slotted."""

    def test_legacy_scaffold_digest_is_pinned_in_the_contract_doc(self) -> None:
        doc = CONTRACT_DOC.read_text(encoding="utf-8")
        match = re.search(r"Legacy scaffold digest: `([0-9a-f]{64})`", doc)
        self.assertIsNotNone(match, "contract doc must pin the legacy scaffold digest")
        actual = hashlib.sha256(LEGACY_SCAFFOLD.read_bytes()).hexdigest()
        self.assertEqual(actual, match.group(1), "legacy scaffold bytes changed; update the pin deliberately")

    def test_layout_still_configures_the_legacy_scaffold(self) -> None:
        text = LAYOUT.read_text(encoding="utf-8")
        self.assertIn('coding_template: "prompts/templates/coding_prompt.md"', text)
        self.assertIn('scaffold: "prompts/templates/coding_prompt_contract_v1.md"', text)
        self.assertIn('legacy_scaffold: "prompts/templates/coding_prompt.md"', text)
        self.assertIn('sidecar_suffix: ".slices.yaml"', text)
        self.assertEqual(text.count("sidecar_suffix"), 1, "one suffix authority only")

    def test_v1_scaffold_section_order_and_slots(self) -> None:
        text = V1_SCAFFOLD.read_text(encoding="utf-8")
        self.assertEqual(_headings(text), EXPECTED_V1_SECTION_ORDER)
        legacy_positions = [EXPECTED_V1_SECTION_ORDER.index(h) for h in LEGACY_REQUIRED]
        self.assertEqual(legacy_positions, sorted(legacy_positions), "legacy sections keep their relative order")
        slots = set(SLOT_RE.findall(text))
        for slot in (
            "TBD:milestone", "TBD:slice", "TBD:title", "TBD:mode", "TBD:strictness",
            "TBD:live", "TBD:corrective", "TBD:attempt", "TBD:status", "TBD:task",
            "TBD:active_workspaces", "TBD:read_first", "TBD:write_manifest_rows",
            "TBD:opening_gates", "TBD:external_input_rows", "TBD:correction_rows",
            "TBD:controlling_ruling", "TBD:candidate_strategy", "TBD:hard_wall_seconds",
            "TBD:environment_bindings", "TBD:local_output_root",
            "TBD:objective_success_criteria", "TBD:objective_closure_proof",
            "TBD:non_goals", "TBD:verification", "TBD:self_report_path",
            "TBD:definition_of_done",
        ):
            self.assertIn(slot, slots)
        for phrase in ("fills or deletes", "delete this section"):
            self.assertNotIn(phrase, text.lower())
        self.assertIn("never coder outputs", text)

    def test_v1_rendered_fixtures_carry_no_slot_or_residue(self) -> None:
        for name in (
            "all_fields_rendered_m001_s01.md",
            "all_fields_rendered_m002_s02_attempt_001.md",
            "all_fields_rendered_m002_s02_attempt_002.md",
        ):
            with self.subTest(fixture=name):
                text = (FIX_ROOT / name).read_text(encoding="utf-8")
                self.assertNotIn("TBD", text)
                self.assertNotIn("{attempt}", text)
                self.assertNotIn("Conditional:", text)
                self.assertEqual(len(_headings(text)), len(set(_headings(text))), "duplicate heading")


@unittest.skipUnless(HAVE_YAML, "PyYAML is required to evaluate fixtures through the checker")
class SliceContractCheckerTests(unittest.TestCase):
    """The reference checker reproduces every fixture's expected outcome exactly."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.check = _checker()
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.layout, diags = cls.check.load_layout_contract(LAYOUT)
        assert cls.layout is not None, diags

    def _argv(self, fixture: dict) -> list[str] | None:
        mode, args = fixture["mode"], fixture["args"]
        base = ["--root", str(ROOT), "--json"]
        if mode == "sidecar":
            return base + ["--sidecar", str(ROOT / fixture["path"])]
        if mode == "align":
            argv = list(base)
            for s in args["sidecars"]:
                argv += ["--sidecar", str(FIX_ROOT / s)]
            return argv
        if mode == "render":
            argv = base + ["--sidecar", str(FIX_ROOT / args["sidecar"]), "--slice", args["slice"], "--rendered", str(ROOT / fixture["path"])]
            if "attempt" in args:
                argv += ["--attempt", str(args["attempt"])]
            return argv
        if mode == "review":
            return base + ["--review-report", str(ROOT / fixture["path"])]
        return None

    def test_every_fixture_reproduces_its_expected_result_and_codes(self) -> None:
        for fixture in self.manifest["fixtures"]:
            argv = self._argv(fixture)
            if argv is None:
                continue
            with self.subTest(fixture=fixture["id"]):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = self.check.main(argv)
                result = json.loads(out.getvalue())
                self.assertEqual(result["schema"], "template.slice_contract_check.v1")
                self.assertEqual(result["result"], fixture["expected"]["result"])
                self.assertEqual(code, 0 if fixture["expected"]["result"] == "pass" else 1)
                codes = sorted({d["code"] for d in result["diagnostics"]})
                self.assertEqual(codes, fixture["expected"]["codes"])

    def test_deleting_each_required_field_refuses(self) -> None:
        import yaml
        doc = yaml.safe_load((FIX_ROOT / "all_fields.slices.yaml").read_text(encoding="utf-8"))
        for field in self.check.SLICE_REQUIRED:
            with self.subTest(field=field):
                mutated = json.loads(json.dumps(doc))
                mutated["slices"][0].pop(field)
                codes = {d.code for d in self.check.validate_sidecar(mutated, "x", self.layout)}
                self.assertIn("missing_field", codes)

    def test_checker_output_is_deterministic_and_ordered(self) -> None:
        argv = ["--root", str(ROOT), "--json", "--sidecar", str(FIX_ROOT / "governance_record_label_on_reserved_path.slices.yaml")]
        outputs = []
        for _ in range(2):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.check.main(argv)
            outputs.append(out.getvalue())
        self.assertEqual(outputs[0], outputs[1])
        diags = json.loads(outputs[0])["diagnostics"]
        keys = [(d["path"], d["location"], d["code"], d["message"]) for d in diags]
        self.assertEqual(keys, sorted(keys))

    def test_contract_doc_tables_agree_with_the_layout_vocabularies(self) -> None:
        doc = CONTRACT_DOC.read_text(encoding="utf-8")
        for key in (
            "artifact_types", "role_owners", "retry_policies", "gate_kinds",
            "cleanup_values", "result_handling_values", "objective_status_values",
            "entry_status_values", "authored_by_values",
        ):
            for value in self.layout[key]:
                with self.subTest(key=key, value=value):
                    self.assertIn(f"`{value}`", doc, f"contract doc omits {key} value {value}")
        for role, types in self.layout["role_type_matrix"].items():
            with self.subTest(role=role):
                self.assertIn(f"`{role}`", doc)
                for t in types:
                    self.assertIn(t, self.layout["artifact_types"], f"matrix names unknown type {t} for {role}")
        self.assertNotIn("self_report", self.layout["role_type_matrix"]["reviewer"])
        for reserved in ("review_report", "verdict_record", "acceptance_record", "routing_state", "review_prompt"):
            self.assertNotIn(reserved, self.layout["role_type_matrix"]["coder"])

    def test_layout_block_lists_only_one_declaration_of_each_vocabulary(self) -> None:
        block = _layout_block_text()
        for key in ("artifact_types:", "role_owners:", "retry_policies:", "gate_kinds:", "objective_status_values:"):
            self.assertEqual(block.count(key), 1, key)


class ReadyPromptPreflightTests(unittest.TestCase):
    """The artifact preflight enforces the dispatch placeholder policy: a prompt
    whose workflow-metadata block says ``status: ready`` may carry no unresolved
    sentinel and no deleted-section residue; frozen and draft prompts may."""

    @staticmethod
    def _preflight():
        scripts_dir = ROOT / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        return importlib.import_module("artifact_integrity_preflight")

    def _run(self, body: str) -> tuple[int, str]:
        import tempfile
        preflight = self._preflight()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "prompt.md").write_text(body, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = preflight.main(["--root", str(root), "prompt.md"])
        return code, out.getvalue()

    @staticmethod
    def _prompt(status: str, body: str) -> str:
        return f"# P\n\n```yaml\nmilestone: M001\nslice: M001-S01\nstatus: {status}\n```\n\n## Task\n\n{body}\n"

    def test_ready_prompt_with_sentinel_is_an_error(self) -> None:
        for sentinel in ("TBD", "<value>", "<path>", "<one move>"):
            with self.subTest(sentinel=sentinel):
                code, out = self._run(self._prompt("ready", f"Do the thing {sentinel}."))
                self.assertEqual(code, 1)
                self.assertIn("ready_tbd", out)

    def test_ready_prompt_with_deleted_section_residue_is_an_error(self) -> None:
        code, out = self._run(self._prompt("ready", "Do the thing.\n\n## Opening Gates\n\n*Conditional: rendered only when the entry declares gates.*"))
        self.assertEqual(code, 1)
        self.assertIn("ready_optional_section_residue", out)

    def test_frozen_and_draft_prompts_may_carry_placeholders(self) -> None:
        for status in ("frozen", "draft"):
            with self.subTest(status=status):
                code, out = self._run(self._prompt(status, "TBD"))
                self.assertNotIn("ready_tbd", out)
                self.assertNotIn("ready_optional_section_residue", out)

    def test_clean_ready_prompt_passes(self) -> None:
        code, out = self._run(self._prompt("ready", "Implement the ledger writer."))
        self.assertEqual(code, 0, out)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
