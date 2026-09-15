"""tests/test_gates.py -- Mod 03 Regression Gates.

Promotion target for NB-003_regression_gates.ipynb: src/llmops/eval/
{metric_registry,run_suite,snapshot,compare}.py + __init__.py facade.

Test-id map (mirrors doc/design/03_lld_tests.md / the notebook's inline demos):
  T-03-1        registry invariants (validate_registry)
  T-03-2/2a/2b  run_suite determinism, empty-goldens error, golden_rules denominator
  T-03-3        gate_metric_ids() length/order
  T-03-3c       multi-source row flip regresses BOTH per-source gate metrics
  T-03-4        every gate row == 1.0 on committed goldens
  T-03-5/5a/5b  snapshot round-trip, write-time completeness, active pointer + battery
  T-03-6/6a/6b  compare PASS, inclusive boundary PASS, single-flip floor FAIL
  T-03-7        gate value below floor -> FAIL
  T-03-8*       compare() 11-step precedence (a..i) + direction-lower absolute boundary (8f)
  T-03-9/9a/9b  relative tolerance (non-zero baseline), CLI exit codes, usage errors -> 3
  T-03-10       get_metric raises KeyError on unknown id
  T-03-11*      offline seam: closure scan, env-spy, read-only/socket backstop

This file is the artifact of record; the notebook is scratch only (LLD closing
note). Tests that need the real committed goldens/corpus skip cleanly when run
outside the repo checkout so this file stays usable in isolation too.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import pytest

from llmops.eval.compare import compare, get_metric_or_none, main
from llmops.eval.metric_registry import (
    CORRECTNESS_N,
    MISROUTE_N,
    REGISTRY,
    RETRIEVER_N,
    gate_metric_ids,
    get_metric,
    metric_ids,
    validate_registry,
)
from llmops.eval.run_suite import (
    EvaluationInputError,
    MetricValue,
    compute_canonical_bytes,
    compute_corpus_sha256,
    evaluate_golden_records,
    run_suite,
)
from llmops.eval.snapshot import (
    ConfigurationError,
    Snapshot,
    load_snapshot,
    resolve_active_baseline,
    save_snapshot,
    write_active_pointer,
)

# ---------------------------------------------------------------------------
# Repo-root / real-golden fixtures (mirrors notebook cells 2-3). Tests that
# need the committed goldens/corpus skip if this file isn't run inside the
# repo checkout, so the suite stays importable/runnable standalone.
# ---------------------------------------------------------------------------

def _find_repo_root() -> Path | None:
    root = Path.cwd().resolve()
    while not (root / "pyproject.toml").is_file() and root != root.parent:
        root = root.parent
    return root if (root / "pyproject.toml").is_file() else None


ROOT = _find_repo_root()
GOLDENS_DIR = ROOT / "eval" / "goldens" if ROOT else None
DOCS_DIR = ROOT / "data" / "docs" if ROOT else None
BASELINES_DIR = ROOT / "eval" / "baselines" if ROOT else None

requires_repo = pytest.mark.skipif(
    ROOT is None or not GOLDENS_DIR.exists() or not DOCS_DIR.exists(),
    reason="requires the real eval/goldens + data/docs checkout",
)


@pytest.fixture(scope="module")
def real_report():
    """Candidate report computed against the committed goldens (module-scoped, expensive)."""
    return run_suite(GOLDENS_DIR, DOCS_DIR)


# ===========================================================================
# T-03-1 -- metric_registry invariants
# ===========================================================================

class TestRegistryInvariants:
    def test_validate_registry_passes_on_shipped_registry(self):
        validate_registry()  # must not raise

    def test_registry_row_count_and_kind_split(self):
        assert len(REGISTRY) == 25
        assert sum(1 for m in REGISTRY if m.kind == "gate") == 16
        assert sum(1 for m in REGISTRY if m.kind == "guardrail") == 3
        assert sum(1 for m in REGISTRY if m.kind == "info") == 6

    def test_no_duplicate_ids(self):
        ids = metric_ids()
        dupes = [i for i, n in Counter(ids).items() if n > 1]
        assert not dupes, f"duplicate metric ids: {dupes}"

    def test_ids_match_dotted_regex(self):
        import re

        id_re = re.compile(r"^eval\.(gate|guardrail|info)\.[a-z_]+(\.[a-z0-9_]+)*(\.S[1-5])?$")
        bad = [m.id for m in REGISTRY if not id_re.fullmatch(m.id)]
        assert not bad, f"ids failing the dotted-id regex: {bad}"

    def test_floor_families_use_single_flip_tolerance(self):
        """retriever.agreement + correctness.answer_cited: tol == 1/(n+1) exactly (D19/D39)."""
        for s, n in {**RETRIEVER_N}.items():
            m = get_metric(f"eval.gate.retriever.agreement.{s}")
            assert m.tolerance == pytest.approx(1.0 / (n + 1), abs=1e-12)
            assert m.expected_sample_size == n
        for s, n in {**CORRECTNESS_N}.items():
            m = get_metric(f"eval.gate.correctness.answer_cited.{s}")
            assert m.tolerance == pytest.approx(1.0 / (n + 1), abs=1e-12)
            assert m.expected_sample_size == n

    def test_misroute_family_keeps_judge_default_not_the_floor(self):
        """Misroute gates keep +/-0.03 by design (n=1/2 already trips on any flip)."""
        for s, n in MISROUTE_N.items():
            m = get_metric(f"eval.gate.routing.misroute_negation.{s}")
            assert m.tolerance == pytest.approx(0.03, abs=1e-12)
            assert m.expected_sample_size == n

    def test_per_source_gate_missing_sample_size_is_rejected(self, monkeypatch):
        """A floor-family or misroute row with expected_sample_size=None/<1 must fail validation."""
        import llmops.eval.metric_registry as reg_mod

        bad_metric = dataclasses.replace(
            get_metric("eval.gate.retriever.agreement.S1"), expected_sample_size=None
        )
        broken_registry = tuple(
            bad_metric if m.id == bad_metric.id else m for m in REGISTRY
        )
        monkeypatch.setattr(reg_mod, "REGISTRY", broken_registry)
        with pytest.raises(AssertionError, match="missing expected_sample_size"):
            reg_mod.validate_registry()

    def test_duplicate_id_is_rejected(self, monkeypatch):
        import llmops.eval.metric_registry as reg_mod

        broken_registry = REGISTRY + (REGISTRY[0],)
        monkeypatch.setattr(reg_mod, "REGISTRY", broken_registry)
        with pytest.raises(AssertionError, match="duplicate id"):
            reg_mod.validate_registry()

    def test_bad_tolerance_out_of_range_is_rejected(self, monkeypatch):
        import llmops.eval.metric_registry as reg_mod

        bad_metric = dataclasses.replace(REGISTRY[0], tolerance=-0.1)
        broken_registry = (bad_metric,) + REGISTRY[1:]
        monkeypatch.setattr(reg_mod, "REGISTRY", broken_registry)
        with pytest.raises(AssertionError, match="tolerance out of range"):
            reg_mod.validate_registry()


# ===========================================================================
# T-03-3 / T-03-10 -- accessors
# ===========================================================================

class TestAccessors:
    def test_gate_metric_ids_length_and_declaration_order(self):
        gids = gate_metric_ids()
        assert len(gids) == 16
        # declaration order preserved: gate ids appear in the same relative
        # order as REGISTRY, not re-sorted alphabetically.
        expected_order = tuple(m.id for m in REGISTRY if m.kind == "gate")
        assert gids == expected_order

    def test_get_metric_raises_keyerror_on_unknown_id(self):
        with pytest.raises(KeyError):
            get_metric("eval.gate.does_not_exist")

    def test_get_metric_or_none_wraps_keyerror(self):
        assert get_metric_or_none("eval.gate.does_not_exist") is None
        assert get_metric_or_none("eval.gate.golden_rules") is not None


# ===========================================================================
# T-03-2 / T-03-2a / T-03-2b / T-03-4 -- run_suite, on real committed goldens
# ===========================================================================

@requires_repo
class TestRunSuiteOnCommittedGoldens:
    def test_run_suite_produces_envelope_with_21_rows(self, real_report):
        assert real_report["schema_version"] == "1.0"
        assert "generated_utc" in real_report
        assert len(real_report["metrics"]) == 21  # 16 gate + 5 snapshot_rowcount

    def test_metrics_are_in_canonical_sorted_order(self, real_report):
        ids = [m["metric_id"] for m in real_report["metrics"]]
        assert ids == sorted(ids)

    def test_every_gate_row_is_1_0_on_committed_goldens(self, real_report):
        """T-03-4: nothing in the shipped goldens should currently trip a gate."""
        gate_rows = [m for m in real_report["metrics"] if m["metric_id"].startswith("eval.gate.")]
        assert len(gate_rows) == 16
        for row in gate_rows:
            assert row["value"] == pytest.approx(1.0), row

    def test_golden_rules_denominator_is_3_files_not_rows(self, real_report):
        """T-03-2b: golden_rules divides by 3 golden FILES, not the row count."""
        row = next(m for m in real_report["metrics"] if m["metric_id"] == "eval.gate.golden_rules")
        assert row["sample_size"] == 3

    def test_determinism_canonical_bytes_identical_across_runs(self):
        """T-03-2: two runs against the same committed goldens are byte-identical
        on the canonical subset (schema_version + sorted metrics; generated_utc excluded)."""
        b1 = compute_canonical_bytes(run_suite(GOLDENS_DIR, DOCS_DIR))
        b2 = compute_canonical_bytes(run_suite(GOLDENS_DIR, DOCS_DIR))
        assert b1 == b2

    def test_canonical_bytes_excludes_generated_utc(self, real_report):
        payload = json.loads(compute_canonical_bytes(real_report))
        assert "generated_utc" not in payload

    def test_corpus_sha256_is_stable_and_hex(self):
        h1 = compute_corpus_sha256(DOCS_DIR)
        h2 = compute_corpus_sha256(DOCS_DIR)
        assert h1 == h2
        assert len(h1) == 64
        int(h1, 16)  # raises if not hex


class TestRunSuiteInputErrors:
    """T-03-2a: malformed / missing inputs -> EvaluationInputError (exit 3)."""

    def test_missing_goldens_dir_raises(self, tmp_path):
        with pytest.raises(EvaluationInputError):
            evaluate_golden_records(tmp_path / "does_not_exist")

    def test_empty_goldens_dir_raises(self, tmp_path):
        empty = tmp_path / "goldens"
        empty.mkdir()
        with pytest.raises(EvaluationInputError):
            evaluate_golden_records(empty)

    def test_missing_docs_dir_raises(self, tmp_path):
        with pytest.raises(EvaluationInputError):
            compute_corpus_sha256(tmp_path / "no_docs")

    def test_empty_docs_dir_raises(self, tmp_path):
        empty = tmp_path / "docs"
        empty.mkdir()
        with pytest.raises(EvaluationInputError):
            compute_corpus_sha256(empty)

    def test_malformed_golden_json_raises(self, tmp_path):
        goldens = tmp_path / "goldens"
        goldens.mkdir()
        (goldens / "retriever_goldens.json").write_text("{ not json", encoding="utf-8")
        with pytest.raises(EvaluationInputError, match="Malformed golden JSON"):
            evaluate_golden_records(goldens)

    def test_empty_must_contain_raises_h8(self, tmp_path):
        goldens = tmp_path / "goldens"
        goldens.mkdir()
        rows = [{"id": "S1-Q1", "source": "S1", "must_contain": [],
                 "category": "cite", "query": "test", "ideal_answer": "test",
                 "ideal_context": "test", "path": "data/docs/s1_early_steps_bundle.md"}]
        (goldens / "retriever_goldens.json").write_text(json.dumps(rows), encoding="utf-8")
        with pytest.raises(EvaluationInputError, match="must_contain"):
            evaluate_golden_records(goldens)

    def test_zero_rows_for_a_source_never_yields_a_silent_0_0_gate(self, tmp_path):
        """A source with zero rows must error, not silently report value=0.0."""
        goldens = tmp_path / "goldens"
        goldens.mkdir()
        rows = [{"id": "S2-Q1", "source": "S2", "must_contain": ["x"],
                 "category": "cite", "query": "test", "ideal_answer": "test",
                 "ideal_context": "test", "path": "data/docs/s2_frameworks_bundle.md"}]
        (goldens / "retriever_goldens.json").write_text(json.dumps(rows), encoding="utf-8")
        with pytest.raises(EvaluationInputError, match="Zero retriever rows for S1"):
            evaluate_golden_records(goldens)


# ===========================================================================
# T-03-5 / T-03-5a / T-03-5b -- snapshot round-trip, completeness, pointer
# ===========================================================================

def _minimal_snapshot(metrics: dict[str, dict], *, snap_id: str = "snap-test") -> Snapshot:
    return Snapshot(
        id=snap_id,
        created_utc="2026-09-15T00:00:00+00:00",
        git_commit=None,
        schema_version="1.0",
        goldens_sha256="0" * 64,
        corpus_sha256="1" * 64,
        metrics=metrics,
        meta={"source": "test"},
    )


def _complete_gate_metrics(value: float = 1.0) -> dict[str, dict]:
    return {
        gid: {"value": value, "sample_size": get_metric(gid).expected_sample_size, "computation": "stub"}
        for gid in gate_metric_ids()
    }


class TestSnapshotRoundTrip:
    def test_save_then_load_preserves_every_field(self, tmp_path):
        snap = _minimal_snapshot(_complete_gate_metrics())
        path = tmp_path / f"{snap.id}.json"
        save_snapshot(snap, path=path)
        loaded = load_snapshot(path)
        assert dataclasses.asdict(loaded) == dataclasses.asdict(snap)

    def test_save_is_atomic_no_tmp_file_left_behind(self, tmp_path):
        snap = _minimal_snapshot(_complete_gate_metrics())
        path = tmp_path / f"{snap.id}.json"
        save_snapshot(snap, path=path)
        assert path.is_file()
        assert not (tmp_path / f"{snap.id}.json.tmp").exists()

    def test_load_missing_file_raises_configuration_error(self, tmp_path):
        with pytest.raises(ConfigurationError):
            load_snapshot(tmp_path / "missing.json")


class TestSnapshotWriteTimeCompleteness:
    """T-03-5a: all 16 gate rows must be present at write time; guardrail/info optional."""

    def test_complete_gate_set_saves_fine(self, tmp_path):
        snap = _minimal_snapshot(_complete_gate_metrics())
        save_snapshot(snap, path=tmp_path / "ok.json")  # must not raise

    def test_missing_one_gate_row_is_rejected(self, tmp_path):
        metrics = _complete_gate_metrics()
        del metrics["eval.gate.retriever.agreement.S1"]
        snap = _minimal_snapshot(metrics)
        with pytest.raises(EvaluationInputError, match="missing gate rows"):
            save_snapshot(snap, path=tmp_path / "incomplete.json")

    def test_guardrail_and_info_rows_are_optional(self, tmp_path):
        metrics = _complete_gate_metrics()
        metrics["eval.info.snapshot_rowcount.S1"] = {
            "value": 80.0, "sample_size": 80, "computation": "stub",
        }
        snap = _minimal_snapshot(metrics)
        save_snapshot(snap, path=tmp_path / "with_info.json")  # must not raise


class TestActivePointer:
    """T-03-5b: canonical pointer {schema_version, baseline_id, path}, path-safety rules."""

    @pytest.fixture()
    def baseline_dir(self, tmp_path):
        d = tmp_path / "baselines"
        d.mkdir()
        return d

    @pytest.fixture()
    def saved_baseline(self, baseline_dir):
        snap = _minimal_snapshot(_complete_gate_metrics(), snap_id="baseline-happy")
        save_snapshot(snap, path=baseline_dir / f"{snap.id}.json")
        return snap

    def test_happy_path_resolves(self, baseline_dir, saved_baseline):
        pointer = baseline_dir / "active.json"
        write_active_pointer(saved_baseline, pointer=pointer)
        resolved = resolve_active_baseline(pointer, base_dir=baseline_dir)
        assert resolved == (baseline_dir / f"{saved_baseline.id}.json").resolve()

    @pytest.mark.parametrize(
        "label,payload_or_none",
        [
            ("malformed-json", "{ not json"),
            (
                "traversal",
                json.dumps({"schema_version": "1.0", "baseline_id": "x", "path": "../other.json"}),
            ),
            (
                "absolute",
                json.dumps({"schema_version": "1.0", "baseline_id": "x", "path": "/tmp/escape.json"}),
            ),
            (
                "backslash",
                json.dumps({"schema_version": "1.0", "baseline_id": "x", "path": "..\\\\escape.json"}),
            ),
            (
                "wrong-extension",
                json.dumps({"schema_version": "1.0", "baseline_id": "x", "path": "baseline.txt"}),
            ),
            (
                "target-missing",
                json.dumps({"schema_version": "1.0", "baseline_id": "x", "path": "missing.json"}),
            ),
        ],
    )
    def test_malformed_pointer_battery_raises_configuration_error(
        self, baseline_dir, label, payload_or_none
    ):
        pointer = baseline_dir / "active_bad.json"
        pointer.write_text(payload_or_none, encoding="utf-8")
        with pytest.raises(ConfigurationError):
            resolve_active_baseline(pointer, base_dir=baseline_dir)

    def test_baseline_id_mismatch_raises_configuration_error(self, baseline_dir, saved_baseline):
        pointer = baseline_dir / "active_bad.json"
        pointer.write_text(
            json.dumps(
                {"schema_version": "1.0", "baseline_id": "wrong-id", "path": f"{saved_baseline.id}.json"}
            ),
            encoding="utf-8",
        )
        with pytest.raises(ConfigurationError, match="baseline_id mismatch"):
            resolve_active_baseline(pointer, base_dir=baseline_dir)

    def test_missing_pointer_file_raises_configuration_error(self, baseline_dir):
        with pytest.raises(ConfigurationError):
            resolve_active_baseline(baseline_dir / "does_not_exist.json", base_dir=baseline_dir)

    def test_pointer_missing_required_field_raises(self, baseline_dir):
        pointer = baseline_dir / "active_bad.json"
        pointer.write_text(json.dumps({"schema_version": "1.0", "baseline_id": "x"}), encoding="utf-8")
        with pytest.raises(ConfigurationError):
            resolve_active_baseline(pointer, base_dir=baseline_dir)


# ===========================================================================
# T-03-6 / 6a / 6b / 7 / 8* -- compare() 11-step precedence
# ===========================================================================

def _mv(metric_id: str, value: float, sample_size: int | None = None) -> MetricValue:
    m = get_metric_or_none(metric_id)
    n = sample_size if sample_size is not None else ((m.expected_sample_size if m else None) or 0)
    return MetricValue(metric_id=metric_id, value=value, sample_size=n, computation="stub")


@pytest.fixture()
def baseline_snapshot():
    return _minimal_snapshot(_complete_gate_metrics(), snap_id="baseline-fixture")


def _candidate_like_baseline(overrides: dict | None = None) -> list[MetricValue]:
    overrides = overrides or {}
    out = []
    for mid in gate_metric_ids():
        m = get_metric(mid)
        val, n = overrides.get(mid, (1.0, m.expected_sample_size))
        out.append(_mv(mid, val, n))
    return out


class TestComparePassFailBoundaries:
    def test_t03_6_candidate_equals_baseline_is_pass(self, baseline_snapshot):
        v = compare(baseline_snapshot, _candidate_like_baseline())
        assert v.code == 0
        assert v.regressed == ()

    def test_t03_6a_inclusive_boundary_still_passes(self, baseline_snapshot):
        """value sitting exactly at baseline - tolerance is still PASS (inclusive band)."""
        n = 34
        bound = float(Fraction(n, n + 1))  # == baseline(1.0) - tol(1/(n+1)) for S1 (n=34) -> 34/35
        v = compare(
            baseline_snapshot,
            _candidate_like_baseline({"eval.gate.retriever.agreement.S1": (bound, n)}),
        )
        assert v.code == 0, v.detail

    def test_t03_6b_single_flip_strictly_trips_the_gate(self, baseline_snapshot):
        n = get_metric("eval.gate.retriever.agreement.S1").expected_sample_size
        v = compare(
            baseline_snapshot,
            _candidate_like_baseline({"eval.gate.retriever.agreement.S1": ((n - 1) / n, n)}),
        )
        assert v.code == 1
        assert "eval.gate.retriever.agreement.S1" in v.regressed

    def test_t03_7_gate_below_floor_fails_with_detail(self, baseline_snapshot):
        v = compare(
            baseline_snapshot,
            _candidate_like_baseline({"eval.gate.retriever.agreement.S1": (0.90, 34)}),
        )
        assert v.code == 1
        assert "eval.gate.retriever.agreement.S1" in v.regressed
        assert "eval.gate.retriever.agreement.S1" in v.detail

    def test_compare_never_rounds_before_verdicting(self, baseline_snapshot):
        """INVARIANT: a value one float ULP inside the bound must still PASS."""
        n = 34
        tol = get_metric("eval.gate.retriever.agreement.S1").tolerance
        just_inside = 1.0 - tol + 1e-12
        v = compare(
            baseline_snapshot,
            _candidate_like_baseline({"eval.gate.retriever.agreement.S1": (just_inside, n)}),
        )
        assert v.code == 0


class TestComparePrecedence:
    def test_t03_8a_gate_fail_beats_guardrail_review(self, baseline_snapshot):
        cand = _candidate_like_baseline({"eval.gate.retriever.agreement.S1": (0.90, 34)})
        cand.append(_mv("eval.guardrail.position_bias.agreement", 0.80, 20))
        v = compare(baseline_snapshot, cand)
        assert v.code == 1
        assert "eval.gate.retriever.agreement.S1" in v.regressed

    def test_t03_8b_missing_candidate_gate_is_fail(self, baseline_snapshot):
        cand = [mv for mv in _candidate_like_baseline() if mv.metric_id != "eval.gate.correctness.answer_cited.S3"]
        v = compare(baseline_snapshot, cand)
        assert v.code == 1
        assert "eval.gate.correctness.answer_cited.S3" in v.regressed

    def test_t03_8c_guardrail_only_in_candidate_is_skipped_not_verdict(self, baseline_snapshot):
        """baseline has no guardrail row -> adding one in candidate is a no-op, PASS."""
        cand = _candidate_like_baseline()
        cand.append(_mv("eval.guardrail.position_bias.agreement", 0.80, 20))
        v = compare(baseline_snapshot, cand)
        assert v.code == 0

    def test_t03_8c_guardrail_in_baseline_only_is_skipped_with_provenance(self):
        metrics = _complete_gate_metrics()
        metrics["eval.guardrail.position_bias.agreement"] = {
            "value": 1.0, "sample_size": 20, "computation": "stub",
        }
        baseline = _minimal_snapshot(metrics, snap_id="baseline-guardrail")
        cand = _candidate_like_baseline()  # omits the guardrail
        v = compare(baseline, cand)
        assert v.code == 0
        notes = [d for d in v.detail.values() if "missing in candidate" in d]
        assert notes, v.detail

    def test_t03_8_guardrail_review_never_touches_gate_verdict(self):
        metrics = _complete_gate_metrics()
        metrics["eval.guardrail.position_bias.agreement"] = {
            "value": 1.0, "sample_size": 20, "computation": "stub",
        }
        baseline = _minimal_snapshot(metrics, snap_id="baseline-guardrail-review")
        cand = _candidate_like_baseline()
        cand.append(_mv("eval.guardrail.position_bias.agreement", 0.80, 20))
        v = compare(baseline, cand)
        assert v.code == 2
        assert "eval.guardrail.position_bias.agreement" in v.regressed

    def test_t03_8d_baseline_missing_gate_candidate_has_it_is_config_error(self):
        metrics = _complete_gate_metrics()
        del metrics["eval.gate.routing.misroute_negation.S1"]
        baseline = _minimal_snapshot(metrics, snap_id="baseline-8d")
        cand = _candidate_like_baseline()
        with pytest.raises(ConfigurationError, match="baseline missing gate row"):
            compare(baseline, cand)

    def test_t03_8e_zero_baseline_under_relative_tolerance_is_config_error(self):
        metrics = _complete_gate_metrics()
        metrics["eval.guardrail.latency.p95"] = {"value": 0.0, "sample_size": 100, "computation": "stub"}
        baseline = _minimal_snapshot(metrics, snap_id="baseline-8e")
        cand = _candidate_like_baseline()
        cand.append(_mv("eval.guardrail.latency.p95", 0.1, 100))
        with pytest.raises(ConfigurationError, match="relative tolerance undefined at zero baseline"):
            compare(baseline, cand)

    def test_t03_8g_unregistered_candidate_id_is_fail(self, baseline_snapshot):
        cand = _candidate_like_baseline() + [_mv("eval.gate.retriever.agreement.X1", 1.0, 10)]
        v = compare(baseline_snapshot, cand)
        assert v.code == 1
        assert "eval.gate.retriever.agreement.X1" in v.regressed

    def test_t03_8h_gate_missing_from_both_fires_candidate_missing_first(self):
        metrics = _complete_gate_metrics()
        del metrics["eval.gate.retriever.agreement.S2"]
        baseline = _minimal_snapshot(metrics, snap_id="baseline-8h")
        cand = [mv for mv in _candidate_like_baseline() if mv.metric_id != "eval.gate.retriever.agreement.S2"]
        v = compare(baseline, cand)
        assert v.code == 1
        assert "eval.gate.retriever.agreement.S2" in v.regressed
        assert "missing in candidate" in v.detail["eval.gate.retriever.agreement.S2"]

    def test_t03_8i_coverage_regression_is_fail_with_both_ns_in_detail(self, baseline_snapshot):
        cand = _candidate_like_baseline({"eval.gate.retriever.agreement.S1": (1.0, 33)})
        v = compare(baseline_snapshot, cand)
        assert v.code == 1
        assert "eval.gate.retriever.agreement.S1" in v.regressed
        detail = v.detail["eval.gate.retriever.agreement.S1"]
        assert "33" in detail and "34" in detail

    def test_t03_3c_multi_source_row_flip_regresses_both_sources(self):
        """T-03-3c: a flip in a multi-source row (e.g. S1+S3) degrades both per-source
        gate metrics simultaneously. At the compare() level, both S1 and S3 must
        regress when their values fall below tolerance."""
        n_s1 = get_metric("eval.gate.retriever.agreement.S1").expected_sample_size  # 34
        n_s3 = get_metric("eval.gate.retriever.agreement.S3").expected_sample_size  # 28
        baseline = _minimal_snapshot(_complete_gate_metrics(), snap_id="baseline-3c")
        # One shared multi-source row flipped: S1 becomes (n-1)/n, S3 becomes (n-1)/n
        cand = _candidate_like_baseline({
            "eval.gate.retriever.agreement.S1": ((n_s1 - 1) / n_s1, n_s1),
            "eval.gate.retriever.agreement.S3": ((n_s3 - 1) / n_s3, n_s3),
        })
        v = compare(baseline, cand)
        assert v.code == 1
        assert "eval.gate.retriever.agreement.S1" in v.regressed
        assert "eval.gate.retriever.agreement.S3" in v.regressed

    def test_t03_8f_direction_lower_absolute_inclusive_boundary(self, monkeypatch):
        """T-03-8f: direction=lower, tolerance_unit=absolute. Value exactly at
        baseline+tol → PASS (inclusive band); value strictly above → REVIEW."""
        from importlib import import_module
        cmp_mod = import_module("llmops.eval.compare")
        reg_mod = import_module("llmops.eval.metric_registry")

        original_cmp_reg = cmp_mod.REGISTRY
        abs_lat = dataclasses.replace(
            get_metric("eval.guardrail.latency.p95"), tolerance_unit="absolute"
        )
        abs_registry = tuple(abs_lat if m.id == "eval.guardrail.latency.p95" else m for m in original_cmp_reg)
        monkeypatch.setattr(cmp_mod, "REGISTRY", abs_registry)
        monkeypatch.setattr(reg_mod, "REGISTRY", abs_registry)  # keep get_metric/get_metric_or_none in sync
        metrics = _complete_gate_metrics()
        metrics["eval.guardrail.latency.p95"] = {
            "value": 100.0, "sample_size": 100, "computation": "stub",
        }
        baseline = _minimal_snapshot(metrics, snap_id="baseline-8f")
        # value == baseline + tol → PASS (inclusive)
        cand_ok = _candidate_like_baseline()
        cand_ok.append(_mv("eval.guardrail.latency.p95", 100.0 + 0.20, 100))
        v_ok = compare(baseline, cand_ok)
        assert v_ok.code == 0, f"exact boundary should PASS but got {v_ok.detail}"
        # value > baseline + tol → REVIEW (guardrail regression, not gate)
        cand_bad = _candidate_like_baseline()
        cand_bad.append(_mv("eval.guardrail.latency.p95", 100.0 + 0.21, 100))
        v_bad = compare(baseline, cand_bad)
        assert v_bad.code == 2, f"above boundary should REVIEW but got {v_bad.code}"
        assert "eval.guardrail.latency.p95" in v_bad.regressed

    def test_t03_9a_relative_tolerance_nonzero_baseline(self):
        """T-03-9a: relative tolerance on a non-zero baseline. direction=lower,
        tolerance=0.20 (relative). baseline=100.0 → 120.0 still PASS,
        121.0 → REVIEW."""
        metrics = _complete_gate_metrics()
        metrics["eval.guardrail.latency.p95"] = {
            "value": 100.0, "sample_size": 100, "computation": "stub",
        }
        baseline = _minimal_snapshot(metrics, snap_id="baseline-9a")
        # 120.0 <= 100.0 * 1.20 → PASS (relative inclusive)
        cand_pass = _candidate_like_baseline()
        cand_pass.append(_mv("eval.guardrail.latency.p95", 120.0, 100))
        v_pass = compare(baseline, cand_pass)
        assert v_pass.code == 0, f"120ms should PASS but got {v_pass.detail}"
        # 121.0 > 100.0 * 1.20 → REVIEW
        cand_review = _candidate_like_baseline()
        cand_review.append(_mv("eval.guardrail.latency.p95", 121.0, 100))
        v_review = compare(baseline, cand_review)
        assert v_review.code == 2, f"121ms should REVIEW but got {v_review.code}"
        assert "eval.guardrail.latency.p95" in v_review.regressed

    def test_duplicate_candidate_ids_raise_evaluation_input_error(self, baseline_snapshot):
        cand = _candidate_like_baseline()
        cand.append(cand[0])
        with pytest.raises(EvaluationInputError, match="duplicate candidate"):
            compare(baseline_snapshot, cand)


# ===========================================================================
# T-03-9 / T-03-9b -- CLI exit codes
# ===========================================================================

class TestCliExitCodes:
    def _write(self, tmp_path, name, metrics: list[MetricValue]):
        p = tmp_path / name
        payload = {
            "schema_version": "1.0",
            "generated_utc": "2026-09-15T00:00:00+00:00",
            "metrics": [dataclasses.asdict(mv) for mv in metrics],
        }
        p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return p

    def test_pass_is_exit_0(self, tmp_path):
        snap = _minimal_snapshot(_complete_gate_metrics(), snap_id="baseline-cli")
        baseline_path = tmp_path / "baseline-cli.json"
        save_snapshot(snap, path=baseline_path)
        cand_path = self._write(tmp_path, "cand.json", _candidate_like_baseline())
        rc = main(["--baseline", str(baseline_path), "--candidate", str(cand_path)])
        assert rc == 0

    def test_fail_is_exit_1(self, tmp_path):
        snap = _minimal_snapshot(_complete_gate_metrics(), snap_id="baseline-cli-fail")
        baseline_path = tmp_path / "baseline-cli-fail.json"
        save_snapshot(snap, path=baseline_path)
        cand = _candidate_like_baseline({"eval.gate.retriever.agreement.S1": (0.5, 34)})
        cand_path = self._write(tmp_path, "cand_fail.json", cand)
        rc = main(["--baseline", str(baseline_path), "--candidate", str(cand_path)])
        assert rc == 1

    def test_malformed_candidate_report_is_exit_3(self, tmp_path):
        snap = _minimal_snapshot(_complete_gate_metrics(), snap_id="baseline-cli-3")
        baseline_path = tmp_path / "baseline-cli-3.json"
        save_snapshot(snap, path=baseline_path)
        bad_candidate = tmp_path / "bad_candidate.json"
        bad_candidate.write_text("{ not json", encoding="utf-8")
        rc = main(["--baseline", str(baseline_path), "--candidate", str(bad_candidate)])
        assert rc == 3

    def test_missing_baseline_flag_or_active_is_usage_error_exit_3(self, tmp_path):
        """T-03-9b: argparse usage errors map to exit 3, never argparse's native 2 (2==REVIEW)."""
        cand_path = self._write(tmp_path, "cand.json", _candidate_like_baseline())
        rc = main(["--candidate", str(cand_path)])
        assert rc == 3

    def test_baseline_and_active_together_is_usage_error_exit_3(self, tmp_path):
        cand_path = self._write(tmp_path, "cand.json", _candidate_like_baseline())
        rc = main(["--baseline", "x.json", "--active", "--candidate", str(cand_path)])
        assert rc == 3

    def test_baseline_file_missing_is_exit_4(self, tmp_path):
        cand_path = self._write(tmp_path, "cand.json", _candidate_like_baseline())
        rc = main(["--baseline", str(tmp_path / "does_not_exist.json"), "--candidate", str(cand_path)])
        assert rc == 4

    def test_candidate_report_missing_metrics_key_is_exit_3(self, tmp_path):
        snap = _minimal_snapshot(_complete_gate_metrics(), snap_id="baseline-cli-nometrics")
        baseline_path = tmp_path / "baseline-cli-nometrics.json"
        save_snapshot(snap, path=baseline_path)
        bad_candidate = tmp_path / "no_metrics.json"
        bad_candidate.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
        rc = main(["--baseline", str(baseline_path), "--candidate", str(bad_candidate)])
        assert rc == 3

    @requires_repo
    def test_t03_14_end_to_end_active_baseline_from_any_cwd(self, tmp_path, real_report):
        """T-03-14: run_suite on the committed goldens, compare vs the committed
        active baseline -> exit 0 -- and the --active resolution must be cwd-INDEPENDENT
        (root derives from compare.py's location, not from Path.cwd())."""
        cand_path = tmp_path / "candidate.json"
        cand_path.write_text(json.dumps(real_report, indent=2) + "\n", encoding="utf-8")
        import os
        old_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)  # simulate running the CLI from an arbitrary subdir
            rc = main(["--active", "--candidate", str(cand_path)])
            assert rc == 0
        finally:
            os.chdir(old_cwd)


# ===========================================================================
# T-03-11 / 11b / 11c / 11d -- offline seam enforcement
# ===========================================================================

_LIVE_DENY_MODULES = (
    "config.judge",
    "openai",
    "langchain",
    "langchain_openai",
    "httpx",
    "requests",
    "urllib",
    "http.client",
    "socket",
)

_LIVE_DENY_SYMBOLS = ("judge_llm", "ChatOpenAI")


class TestOfflineSeam:
    def test_t03_11_static_import_closure_excludes_live_judge_modules(self):
        """AST-scan the four eval modules' import statements for the live/judge deny-set.

        Matches deny-set as module prefixes (import X or from X import ...), as
        sub/super-module containment, as langchain_* wildcard family, and at the
        imported-symbol level (judge_llm / ChatOpenAI) so that
        ``from llmops.config.judge import judge_llm`` is caught too.
        """
        import ast
        from importlib import import_module

        mod_names = ("metric_registry", "run_suite", "snapshot", "compare")

        def _denied(module_path: str) -> bool:
            parts = module_path.split(".")
            if parts and parts[0].startswith("langchain"):
                return True
            for deny in _LIVE_DENY_MODULES:
                if module_path == deny or module_path.startswith(deny + "."):
                    return True
                if module_path.endswith("." + deny):
                    return True
            return False

        hits: list[str] = []
        for name in mod_names:
            mod = import_module(f"llmops.eval.{name}")
            src_path = Path(mod.__file__)
            tree = ast.parse(src_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        if _denied(a.name):
                            hits.append(f"{src_path.name}:{a.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if _denied(node.module):
                        hits.append(f"{src_path.name}:{node.module}")
                    for a in node.names:
                        if a.name in _LIVE_DENY_SYMBOLS:
                            hits.append(f"{src_path.name}:{node.module}.{a.name}")
        assert not hits, f"eval modules import live/judge deny-set modules: {hits}"

    def test_t03_11b_eval_code_never_reads_env(self, monkeypatch):
        """Env-spy: os.environ / os.getenv reads from inside eval code must never occur.

        We don't strip the process env (that's normal, see notebook cell 8's
        rationale) -- we assert the read-SIDE never touches it while running
        the offline suite, by making any read blow up loudly.
        """
        import os

        class _EnvSpyDict(dict):
            def __getitem__(self, key):  # pragma: no cover - defensive
                raise AssertionError(f"eval code read os.environ[{key!r}] -- offline seam violation")

            def get(self, key, default=None):  # pragma: no cover - defensive
                raise AssertionError(f"eval code called os.environ.get({key!r}) -- offline seam violation")

        def _spy_getenv(key, default=None):  # pragma: no cover - defensive
            raise AssertionError(f"eval code called os.getenv({key!r}) -- offline seam violation")

        if ROOT is None:
            pytest.skip("requires repo checkout for a realistic run_suite() call")

        monkeypatch.setattr(os, "getenv", _spy_getenv)
        # Manual save/restore for os.environ to avoid monkeypatch leaking into
        # pytest's own reporting code after the test returns.
        saved_environ = os.environ
        os.environ = _EnvSpyDict(saved_environ)  # noqa: B003  # intentional swap; save/restore below
        try:
            # Must complete without tripping the spy.
            run_suite(GOLDENS_DIR, DOCS_DIR)
        finally:
            os.environ = saved_environ  # noqa: B003  # restores the real environ for pytest reporting

    @requires_repo
    def test_t03_11c_env_stripped_subprocess_produces_identical_bytes(self):
        """Run the real eval code in a child process with a minimal, stripped
        env (no LLM_*/GROQ_*/.env-derived vars, no network) and require
        byte-identical canonical output vs. the in-process run."""
        script = (
            "import hashlib, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from llmops.eval.run_suite import run_suite, compute_canonical_bytes\n"
            "from pathlib import Path\n"
            "report = run_suite(Path(sys.argv[2]), Path(sys.argv[3]))\n"
            "print(hashlib.sha256(compute_canonical_bytes(report)).hexdigest())\n"
        )
        child = subprocess.run(
            [sys.executable, "-c", script, str(ROOT), str(GOLDENS_DIR), str(DOCS_DIR)],
            capture_output=True,
            text=True,
            timeout=180,
            env={"PATH": "/usr/bin:/bin", "HOME": "/tmp", "PYTHONPATH": str(ROOT)},
            check=False,
        )
        assert child.returncode == 0, child.stderr[:2000]
        child_hash = child.stdout.strip().splitlines()[-1]

        in_proc_hash = __import__("hashlib").sha256(
            compute_canonical_bytes(run_suite(GOLDENS_DIR, DOCS_DIR))
        ).hexdigest()
        assert child_hash == in_proc_hash

    def test_t03_11d_run_suite_never_opens_a_socket(self, monkeypatch):
        """Read-only/socket backstop: any socket construction during run_suite() fails the test."""
        import socket

        def _deny_socket(*_args, **_kwargs):  # pragma: no cover - defensive
            raise AssertionError("eval code attempted to open a network socket -- offline seam violation")

        monkeypatch.setattr(socket, "socket", _deny_socket)
        if ROOT is None:
            pytest.skip("requires repo checkout for a realistic run_suite() call")
        run_suite(GOLDENS_DIR, DOCS_DIR)  # must not raise


# ===========================================================================
# Misc / cross-cutting
# ===========================================================================

class TestNormalization:
    def test_normalize_text_nfc_and_line_endings(self):
        from llmops.eval.run_suite import _normalize_text

        assert _normalize_text("a\r\nb\rc") == "a\nb\nc"
        assert _normalize_text("  padded  ") == "padded"
        assert _normalize_text(123) == ""  # non-str input -> "" (defensive)