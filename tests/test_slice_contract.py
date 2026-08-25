"""Slice prompt contract v1: fixtures, reference checker, scaffolds, the single
canonical vocabulary declaration, the dispatch preflight rules, the old-consumer
fence composition, and the pre-launch audit's drive-grammar reader.

Stdlib-only structure tests always run. Tests that evaluate fixtures through
the reference checker need PyYAML (the declared dependency) and are skipped
when it is absent, exactly like the OKF profile-checker tests.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
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
OPTIN = FIX_ROOT / "optin_project_for_old_consumer"

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
VOCABULARY_KEYS = (
    "entry_status_values", "authored_by_values", "artifact_types", "role_owners",
    "retry_policies", "gate_kinds", "cleanup_values", "result_handling_values",
    "objective_status_values", "sentinels",
)


def _scripts_module(name: str):
    scripts_dir = ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    return importlib.import_module(name)


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


def _doc_table(doc: str, first_header: str) -> dict[str, list[str]]:
    """Rows of the markdown table whose header starts with ``| first_header |``,
    as {key: [backticked values]}; keys are the first cell's backticked token."""
    rows: dict[str, list[str]] = {}
    lines = doc.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"| {first_header} |"):
            for row in lines[i + 2:]:
                if not row.startswith("|"):
                    break
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                key = re.findall(r"`([^`]+)`", cells[0])
                if key:
                    rows[key[0]] = re.findall(r"`([^`]+)`", cells[1])
            break
    return rows


def _section(doc: str, heading: str) -> str:
    start = doc.index(heading)
    nxt = doc.find("\n## ", start + 1)
    return doc[start:nxt if nxt != -1 else None]


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
        self.assertEqual(set(self.manifest["modes"]), {"sidecar", "align", "render", "review", "document", "external"})

    def test_ids_unique_sorted_and_shapes_valid(self) -> None:
        ids = [f["id"] for f in self.fixtures]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 100)
        for f in self.fixtures:
            with self.subTest(fixture=f["id"]):
                self.assertIn(f["mode"], self.manifest["modes"])
                self.assertIn(f["expected"]["result"], ("pass", "fail", "legacy", "old_consumer_refusal"))
                self.assertEqual(f["expected"]["codes"], sorted(set(f["expected"]["codes"])))
                self.assertEqual(bool(f["expected"]["codes"]), f["expected"]["result"] == "fail")

    def test_inventory_complete_both_directions_and_digests_match(self) -> None:
        listed = {(ROOT / f["path"]).resolve() for f in self.fixtures}
        on_disk = {p.resolve() for p in FIX_ROOT.rglob("*") if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts}
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

    def test_every_content_reason_code_has_a_fixture(self) -> None:
        """Exhaustive, not hand-picked: the checker's REASON_CODES tuple is the
        inventory; every code must be expected by at least one fixture."""
        source = CHECKER.read_text(encoding="utf-8")
        reason = re.search(r"REASON_CODES = \((.*?)\n\)", source, re.DOTALL).group(1)
        codes = set(re.findall(r'"([a-z_]+)"', reason))
        covered = {c for f in self.fixtures for c in f["expected"]["codes"]}
        self.assertEqual(codes - covered, set(), "content reason codes without a fixture")
        self.assertEqual(covered - codes, set(), "fixtures expecting a code the inventory does not declare")

    def test_every_emitted_code_is_inventoried(self) -> None:
        source = CHECKER.read_text(encoding="utf-8")
        reason = set(re.findall(r'"([a-z_]+)"', re.search(r"REASON_CODES = \((.*?)\n\)", source, re.DOTALL).group(1)))
        env = set(re.findall(r'"([a-z_]+)"', re.search(r"ENVIRONMENT_CODES = \((.*?)\n\)", source, re.DOTALL).group(1)))
        emitted = set(re.findall(r'(?:Diagnostic|err)\(\s*"([a-z_]+)"', source))
        self.assertEqual(emitted - (reason | env), set(), "emitted codes outside the inventory")
        self.assertEqual(reason & env, set())

    def test_contract_doc_lists_exactly_the_inventoried_codes(self) -> None:
        source = CHECKER.read_text(encoding="utf-8")
        reason = set(re.findall(r'"([a-z_]+)"', re.search(r"REASON_CODES = \((.*?)\n\)", source, re.DOTALL).group(1)))
        env = set(re.findall(r'"([a-z_]+)"', re.search(r"ENVIRONMENT_CODES = \((.*?)\n\)", source, re.DOTALL).group(1)))
        doc = _section(CONTRACT_DOC.read_text(encoding="utf-8"), "## 10. Validity Rules")
        listed = set(re.findall(r"`([a-z_]+)`", doc.split("Sentinels (layout")[0]))
        self.assertEqual(listed, reason | env)


class SliceContractScaffoldTests(unittest.TestCase):
    """Stdlib-only: two scaffolds, legacy byte-identical, v1 fully slotted."""

    def test_legacy_scaffold_digest_is_pinned_in_the_contract_doc(self) -> None:
        doc = CONTRACT_DOC.read_text(encoding="utf-8")
        match = re.search(r"Legacy scaffold digest: `([0-9a-f]{64})`", doc)
        self.assertIsNotNone(match)
        actual = hashlib.sha256(LEGACY_SCAFFOLD.read_bytes()).hexdigest()
        self.assertEqual(actual, match.group(1), "legacy scaffold bytes changed; update the pin deliberately")

    def test_layout_still_configures_the_legacy_scaffold(self) -> None:
        text = LAYOUT.read_text(encoding="utf-8")
        self.assertIn('coding_template: "prompts/templates/coding_prompt.md"', text)
        self.assertIn('scaffold: "prompts/templates/coding_prompt_contract_v1.md"', text)
        self.assertIn('legacy_scaffold: "prompts/templates/coding_prompt.md"', text)
        self.assertEqual(text.count("sidecar_suffix"), 1, "one suffix authority only")
        self.assertNotIn("oracle_content_bound_bytes", text, "the oracle bound is a drive constant, not a declarable value")

    def test_v1_scaffold_section_order_and_slots(self) -> None:
        text = V1_SCAFFOLD.read_text(encoding="utf-8")
        self.assertEqual(_headings(text), EXPECTED_V1_SECTION_ORDER)
        legacy_positions = [EXPECTED_V1_SECTION_ORDER.index(h) for h in LEGACY_REQUIRED]
        self.assertEqual(legacy_positions, sorted(legacy_positions))
        slots = set(SLOT_RE.findall(text))
        for slot in (
            "TBD:milestone", "TBD:slice", "TBD:title", "TBD:authored_by", "TBD:mode",
            "TBD:strictness", "TBD:live", "TBD:corrective", "TBD:attempt", "TBD:status",
            "TBD:dispatch_authority", "TBD:task", "TBD:active_workspaces", "TBD:read_first",
            "TBD:write_manifest_rows", "TBD:opening_gates", "TBD:external_input_rows",
            "TBD:correction_rows", "TBD:controlling_ruling", "TBD:prior_evidence",
            "TBD:correction_closure_proof", "TBD:claims_withdrawn", "TBD:evidence_invalidated",
            "TBD:minimum_rerun_set", "TBD:candidate_strategy", "TBD:hard_wall_seconds",
            "TBD:environment_bindings", "TBD:local_output_root",
            "TBD:objective_success_criteria", "TBD:objective_closure_proof",
            "TBD:non_goals", "TBD:verification", "TBD:self_report_path", "TBD:definition_of_done",
        ):
            self.assertIn(slot, slots)
        for phrase in ("fills or deletes", "delete this section"):
            self.assertNotIn(phrase, text.lower())
        self.assertIn("never coder outputs", text)

    def test_v1_rendered_fixtures_carry_no_slot_or_residue(self) -> None:
        for name in (
            "all_fields_rendered_m001_s01.md", "frozen_entry_rendered_m001_s01.md",
            "all_fields_rendered_m002_s02_attempt_001.md", "all_fields_rendered_m002_s02_attempt_002.md",
        ):
            with self.subTest(fixture=name):
                text = (FIX_ROOT / name).read_text(encoding="utf-8")
                self.assertNotIn("TBD", text)
                self.assertNotIn("{attempt}", text)
                self.assertNotIn("Conditional:", text)
                self.assertEqual(len(_headings(text)), len(set(_headings(text))))
        self.assertNotIn("dispatch_authority", (FIX_ROOT / "frozen_entry_rendered_m001_s01.md").read_text(encoding="utf-8"))


@unittest.skipUnless(HAVE_YAML, "PyYAML is required to evaluate fixtures through the checker")
class SliceContractCheckerTests(unittest.TestCase):
    """The reference checker reproduces every fixture and refuses every mutation."""

    @classmethod
    def setUpClass(cls) -> None:
        import yaml
        cls.check = _scripts_module("slice_contract_check")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.layout, diags = cls.check.load_layout_contract(LAYOUT)
        assert cls.layout is not None, diags
        cls.positive = yaml.safe_load((FIX_ROOT / "all_fields.slices.yaml").read_text(encoding="utf-8"))
        cls.attempt_001 = yaml.safe_load((FIX_ROOT / "all_fields_attempt_001.slices.yaml").read_text(encoding="utf-8"))

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

    def _run(self, argv: list[str]) -> tuple[int, dict]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.check.main(argv)
        return code, json.loads(out.getvalue())

    def test_every_fixture_reproduces_its_expected_result_and_codes(self) -> None:
        for fixture in self.manifest["fixtures"]:
            argv = self._argv(fixture)
            if argv is None:
                continue
            with self.subTest(fixture=fixture["id"]):
                code, result = self._run(argv)
                self.assertEqual(result["schema"], "template.slice_contract_check.v1")
                self.assertEqual(result["result"], fixture["expected"]["result"])
                self.assertEqual(code, 0 if fixture["expected"]["result"] == "pass" else 1)
                codes = sorted({d["code"] for d in result["diagnostics"]})
                self.assertEqual(codes, fixture["expected"]["codes"])

    # --- exhaustive deletion: every key path of both canonical entries is load-bearing

    @staticmethod
    def _key_paths(value, path=()):
        if isinstance(value, dict):
            for k, v in value.items():
                yield path + (k,)
                yield from SliceContractCheckerTests._key_paths(v, path + (k,))
        elif isinstance(value, list):
            for i, v in enumerate(value):
                yield from SliceContractCheckerTests._key_paths(v, path + (i,))

    @staticmethod
    def _delete(doc, path):
        target = doc
        for step in path[:-1]:
            target = target[step]
        last = path[-1]
        if isinstance(target, list):
            target.pop(last)
        else:
            del target[last]

    def test_deleting_every_key_path_refuses(self) -> None:
        for index in (0, 1):
            entry = self.positive["slices"][index]
            for path in list(self._key_paths(entry)):
                with self.subTest(slice=entry["slice"], path=".".join(map(str, path))):
                    mutated = json.loads(json.dumps(self.positive))
                    self._delete(mutated["slices"][index], path)
                    diags = self.check.validate_sidecar(mutated, "x", self.layout, sidecar_path=FIX_ROOT / "all_fields.slices.yaml")
                    self.assertTrue(diags, f"deleting {path} was accepted")

    # --- structural losslessness: removing any leaf from a canonical rendering is detected

    def test_removing_any_leaf_from_a_canonical_rendering_is_detected(self) -> None:
        cases = (
            (self.positive, "M001-S01", "all_fields_rendered_m001_s01.md"),
            (self.positive, "M002-S02", "all_fields_rendered_m002_s02_attempt_002.md"),
            (self.attempt_001, "M002-S02", "all_fields_rendered_m002_s02_attempt_001.md"),
        )
        token = self.layout["attempt_token"]
        for doc, slice_id, name in cases:
            entry = next(s for s in doc["slices"] if s["slice"] == slice_id)
            rendered = (FIX_ROOT / name).read_text(encoding="utf-8")
            attempt = entry.get("attempt")
            self.assertEqual(self.check.check_rendered(doc, slice_id, None, rendered, name, self.layout), [])
            for path, leaf in self.check.iter_leaves(entry):
                if entry.get(path[0]) == "none" and len(path) == 1:
                    continue
                text = self.check.resolve_attempt(self.check._leaf_text(leaf), token, attempt)
                if not text.strip() or len(text) < 3:
                    continue
                if path[0] == "task":
                    text = text.strip().splitlines()[0].strip()
                with self.subTest(fixture=name, leaf=".".join(map(str, path))):
                    self.assertIn(text, rendered, "canonical rendering lacks the leaf itself")
                    mutated = rendered.replace(text, "REMOVED")
                    diags = self.check.check_rendered(doc, slice_id, None, mutated, name, self.layout)
                    self.assertTrue(diags, f"removing {path} from the rendering went undetected")

    def test_confirming_a_different_attempt_is_refused(self) -> None:
        rendered = (FIX_ROOT / "all_fields_rendered_m002_s02_attempt_002.md").read_text(encoding="utf-8")
        codes = {d.code for d in self.check.check_rendered(self.positive, "M002-S02", "001", rendered, "x", self.layout)}
        self.assertIn("attempt_mismatch", codes)
        self.assertEqual(self.check.check_rendered(self.positive, "M002-S02", "002", rendered, "x", self.layout), [])

    def test_reviewer_probes_refuse(self) -> None:
        """The exact false-accepts of review 037 F2, as in-memory mutations."""
        base = FIX_ROOT / "all_fields.slices.yaml"
        for label, mutate, code in (
            ("roadmap unresolved", lambda d: d.update(roadmap="absent_roadmap.md"), "roadmap_link_unresolved"),
            ("attempt 000", lambda d: d["slices"][1].update(attempt="000"), "attempt_format"),
            ("external input without path", lambda d: d["slices"][1]["external_inputs"][0].pop("path"), "external_input_invalid"),
            ("output root escapes", lambda d: d["slices"][1]["execution_envelope"].update(local_output_root="local_state/../06_infra/attempt_{attempt}/"), "local_output_root_outside_local_state"),
            ("absolute dispatch authority", lambda d: d["slices"][0].update(dispatch_authority="C:/outside/authority.md"), "authority_path_invalid"),
        ):
            with self.subTest(probe=label):
                mutated = json.loads(json.dumps(self.positive))
                mutate(mutated)
                codes = {d.code for d in self.check.validate_sidecar(mutated, "x", self.layout, sidecar_path=base)}
                self.assertIn(code, codes)

    def test_checker_output_is_deterministic_and_ordered(self) -> None:
        argv = ["--root", str(ROOT), "--json", "--sidecar", str(FIX_ROOT / "governance_record_label_on_reserved_path.slices.yaml")]
        outputs = [self._run(argv)[1] for _ in range(2)]
        self.assertEqual(outputs[0], outputs[1])
        keys = [(d["path"], d["location"], d["code"], d["message"]) for d in outputs[0]["diagnostics"]]
        self.assertEqual(keys, sorted(keys))

    def test_contract_doc_tables_equal_the_layout_in_both_directions(self) -> None:
        doc = CONTRACT_DOC.read_text(encoding="utf-8")
        vocab = _doc_table(doc, "Vocabulary")
        self.assertEqual(set(vocab), set(VOCABULARY_KEYS))
        for key in VOCABULARY_KEYS:
            with self.subTest(vocabulary=key):
                self.assertEqual(vocab[key], list(self.layout[key]))
        matrix = _doc_table(doc, "Role")
        self.assertEqual(set(matrix), set(self.layout["role_type_matrix"]))
        for role, types in self.layout["role_type_matrix"].items():
            with self.subTest(role=role):
                self.assertEqual(matrix[role], list(types))
                self.assertTrue(set(types) <= set(self.layout["artifact_types"]))
        self.assertEqual(set(self.layout["role_type_matrix"]), set(self.layout["role_owners"]))
        for reserved in ("review_report", "verdict_record", "acceptance_record", "routing_state", "review_prompt"):
            self.assertNotIn(reserved, self.layout["role_type_matrix"]["coder"])
        self.assertIn("review_prompt", self.layout["role_type_matrix"]["reviewer"])

    def test_layout_block_lists_only_one_declaration_of_each_vocabulary(self) -> None:
        block = _layout_block_text()
        for key in VOCABULARY_KEYS:
            self.assertEqual(block.count(f"{key}:"), 1, key)

    def test_environment_codes_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_layout = Path(tmp) / "frutlups.layout.yaml"
            bad_layout.write_text("x: 1\n", encoding="utf-8")
            layout, diags = self.check.load_layout_contract(bad_layout)
            self.assertIsNone(layout)
            self.assertEqual([d.code for d in diags], ["layout_contract_block_missing"])
            code, result = self._run(["--root", str(ROOT), "--json", "--sidecar", str(Path(tmp) / "missing.slices.yaml")])
            self.assertEqual(code, 1)
            self.assertEqual({d["code"] for d in result["diagnostics"]}, {"sidecar_unreadable"})
        codes = {d.code for d in self.check.check_rendered(self.positive, "M009-S09", None, "", "x", self.layout)}
        self.assertEqual(codes, {"slice_not_found"})


class ReadyPromptPreflightTests(unittest.TestCase):
    """The artifact preflight enforces the dispatch placeholder policy."""

    def _run(self, body: str) -> tuple[int, str]:
        preflight = _scripts_module("artifact_integrity_preflight")
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
                _, out = self._run(self._prompt(status, "TBD"))
                self.assertNotIn("ready_tbd", out)
                self.assertNotIn("ready_optional_section_residue", out)

    def test_clean_ready_prompt_passes(self) -> None:
        code, out = self._run(self._prompt("ready", "Implement the ledger writer."))
        self.assertEqual(code, 0, out)


class OldConsumerFenceFixtureTests(unittest.TestCase):
    """The fence fixture composes an opted-in project; with a released 0.1.8
    interpreter available it also proves the refusal."""

    def _compose(self, out: Path) -> None:
        proc = subprocess.run([sys.executable, str(OPTIN / "compose.py"), "--template", str(ROOT), "--out", str(out)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_composition_applies_exactly_the_opt_in_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "project"
            self._compose(out)
            layout = (out / "frutlups.layout.yaml").read_text(encoding="utf-8")
            self.assertIn('coding_template: "prompts/templates/coding_prompt_contract_v1.md"', layout)
            self.assertNotIn('coding_template: "prompts/templates/coding_prompt.md"', layout)
            for name in ("active_roadmap.md", "development_roadmap.md", "active_roadmap.slices.yaml", "development_roadmap.slices.yaml"):
                self.assertTrue((out / "03_experiments" / name).is_file(), name)
            self.assertIn("Status: active", (out / "03_experiments" / "active_roadmap.md").read_text(encoding="utf-8"))
            self.assertFalse((out / ".git").exists())
            self.assertFalse((out / "local_state").exists())
            self.assertTrue((out / "prompts" / "templates" / "coding_prompt_contract_v1.md").is_file())

    def test_released_0_1_8_refuses_before_writing(self) -> None:
        interpreter = os.environ.get("FRUTLUPS_0_1_8_PYTHON")
        if not interpreter or not Path(interpreter).is_file():
            self.skipTest("external evidence: set FRUTLUPS_0_1_8_PYTHON to an interpreter with released frutlups 0.1.8 installed")
        expected = [l.strip() for l in (OPTIN / "expected_refusal.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "project"
            self._compose(out)
            before = sorted(p.name for p in (out / "prompts" / "for_coding_agent").iterdir())
            proc = subprocess.run([interpreter, "-m", "frutlups", "make-coding-prompt", str(out), "--dry-run", "--json"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout[proc.stdout.index("{"):])
            self.assertFalse(payload.get("would_write"))
            self.assertEqual(sorted(payload.get("errors", [])), sorted(expected))
            after = sorted(p.name for p in (out / "prompts" / "for_coding_agent").iterdir())
            self.assertEqual(before, after, "the legacy consumer wrote a prompt")


class PrelaunchAuditManifestTests(unittest.TestCase):
    """The pre-launch size check reads the drive's released manifest grammar and
    refuses what the drive refuses; an absent manifest means none declared."""

    def _run(self, root: Path, exclusions: str | None) -> tuple[int, str]:
        audit = _scripts_module("local_state_audit")
        argv = ["--root", str(root), "--limit-bytes", "2048"]
        if exclusions is not None:
            argv += ["--exclusions", exclusions]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = audit.main(argv)
        return code, out.getvalue()

    def _root(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "big").mkdir()
        (root / "big" / "huge.bin").write_bytes(b"x" * 3000)
        (root / "06_infra").mkdir()
        (root / "05_governance" / "reviews").mkdir(parents=True)
        (root / "05_governance" / "reviews" / "INDEX.md").write_text("# Review Index\n", encoding="utf-8")
        return root

    def _manifest(self, root: Path, payload) -> str:
        (root / "06_infra" / "oracle_exclusion_manifest.json").write_text(json.dumps(payload), encoding="utf-8")
        return "06_infra/oracle_exclusion_manifest.json"

    def test_valid_manifest_excludes_by_exact_path_and_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            code, out = self._run(root, None)
            self.assertEqual(code, 1)
            self.assertIn("none declared", out)
            code, _ = self._run(root, self._manifest(root, {"contract_version": 1, "exact_paths": ["big/huge.bin"], "top_level_prefixes": []}))
            self.assertEqual(code, 0)
            code, _ = self._run(root, self._manifest(root, {"contract_version": 1, "exact_paths": [], "top_level_prefixes": ["big/"]}))
            self.assertEqual(code, 0)

    def test_drive_invalid_manifests_fail_closed(self) -> None:
        cases = {
            "missing version": {"exact_paths": ["big/huge.bin"], "top_level_prefixes": []},
            "non-canonical prefix": {"contract_version": 1, "exact_paths": [], "top_level_prefixes": ["big"]},
            "extra key": {"contract_version": 1, "exact_paths": [], "top_level_prefixes": [], "note": "x"},
            "wrong version": {"contract_version": 2, "exact_paths": [], "top_level_prefixes": []},
            "duplicate exact": {"contract_version": 1, "exact_paths": ["big/huge.bin", "big/huge.bin"], "top_level_prefixes": []},
            "exact under prefix": {"contract_version": 1, "exact_paths": ["big/huge.bin"], "top_level_prefixes": ["big/"]},
            "excludes the reviews index": {"contract_version": 1, "exact_paths": ["05_governance/reviews/INDEX.md"], "top_level_prefixes": []},
            "excludes itself": {"contract_version": 1, "exact_paths": ["06_infra/oracle_exclusion_manifest.json"], "top_level_prefixes": []},
            "governed surface": {"contract_version": 1, "exact_paths": [], "top_level_prefixes": ["local_state/"]},
            "traversal": {"contract_version": 1, "exact_paths": ["../huge.bin"], "top_level_prefixes": []},
        }
        for label, payload in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                root = self._root(tmp)
                code, out = self._run(root, self._manifest(root, payload))
                self.assertEqual(code, 1, out)
                self.assertIn("exclusion manifest invalid", out)
                self.assertIn("nothing was excluded", out)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
