"""
LLM-Ops Eval Suite — Regression Gate Comparator & CLI (Module 03)
Executes verdict comparisons and provides the CLI entry point.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from llmops.eval.metric_registry import REGISTRY, Metric, gate_metric_ids, get_metric
from llmops.eval.run_suite import EvaluationInputError, MetricValue
from llmops.eval.snapshot import (
    ConfigurationError,
    Snapshot,
    load_snapshot,
    resolve_active_baseline,
)


class _UsageError(Exception):
    pass

class _GateParser(argparse.ArgumentParser):
    def error(self, message: str):
        raise _UsageError(f"usage error: {message}")

@dataclass(frozen=True)
class Verdict:
    code: int
    regressed: tuple[str, ...]
    detail: dict[str, str]

def _worse_than_baseline(m: Metric, base: float, cand: float) -> bool:
    if m.tolerance_unit == "absolute":
        bound = m.tolerance
        return (cand < base - bound) if m.direction == "higher" else (cand > base + bound)
    if m.direction == "higher":
        return cand < base * (1.0 - m.tolerance)
    return cand > base * (1.0 + m.tolerance)

def get_metric_or_none(metric_id: str) -> Metric | None:
    try:
        return get_metric(metric_id)
    except KeyError:
        return None

def compare(baseline: Snapshot, candidate: list[MetricValue]) -> Verdict:
    cand = {mv.metric_id: mv for mv in candidate}
    regressed: list[str] = []
    review: list[str] = []
    detail: dict[str, str] = {}

    dupes = [mid for mid, n in Counter(mv.metric_id for mv in candidate).items() if n > 1]
    if dupes:
        raise EvaluationInputError(f"duplicate candidate metric ids: {sorted(dupes)}")

    for mid in cand:
        m = get_metric_or_none(mid)
        if m is None:
            regressed.append(mid)
            detail[mid] = "unregistered candidate metric id -> FAIL"
            continue

    for mid in cand:
        m = get_metric_or_none(mid)
        if m is None or m.kind == "info":
            continue
        b_raw = baseline.metrics.get(mid)
        if b_raw is not None and m.tolerance_unit == "relative" and b_raw["value"] == 0.0:
            raise ConfigurationError(f"relative tolerance undefined at zero baseline: {mid}")

    for mid in gate_metric_ids():
        m = get_metric(mid)
        b_raw = baseline.metrics.get(mid)
        c_raw = cand.get(mid)
        if c_raw is None:
            regressed.append(mid)
            detail[mid] = "gate missing in candidate"
            continue
        if b_raw is None:
            raise ConfigurationError(f"baseline missing gate row that candidate has: {mid}")
        if m.expected_sample_size is not None and c_raw.sample_size != m.expected_sample_size:
            regressed.append(mid)
            detail[mid] = f"coverage regression n={c_raw.sample_size} != registered {m.expected_sample_size}"
            continue
        if _worse_than_baseline(m, b_raw["value"], c_raw.value):
            regressed.append(mid)
            detail[mid] = f"gate value {c_raw.value} vs baseline {b_raw['value']} tol {m.tolerance:.6g}"

    for m in REGISTRY:
        if m.kind != "guardrail":
            continue
        b_raw = baseline.metrics.get(m.id)
        c_raw = cand.get(m.id)
        if b_raw is None or c_raw is None:
            if b_raw is not None:
                detail[m.id] = "guardrail missing in candidate — skipped, not verdict"
            continue
        if _worse_than_baseline(m, b_raw["value"], c_raw.value):
            review.append(m.id)
            detail[m.id] = f"guardrail regressed: {c_raw.value} vs baseline {b_raw['value']} tol {m.tolerance:.6g}"

    if regressed:
        return Verdict(1, tuple(sorted(set(regressed))), detail)
    if review:
        return Verdict(2, tuple(sorted(set(review))), detail)
    return Verdict(0, (), detail)

def _parse_report(path: str) -> list[MetricValue]:
    p = Path(path)
    if not p.exists():
        raise EvaluationInputError(f"candidate report not found: {path}")
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise EvaluationInputError(f"malformed candidate report JSON: {e}") from e
    metrics = payload.get("metrics")
    if not isinstance(metrics, list):
        raise EvaluationInputError("candidate report has no 'metrics' list")
    out: list[MetricValue] = []
    for m in metrics:
        if not isinstance(m, dict) or not {"metric_id", "value", "sample_size", "computation"} <= set(m):
            raise EvaluationInputError(f"malformed metric row in candidate report: {m!r:.80}")
        out.append(MetricValue(metric_id=m["metric_id"], value=float(m["value"]),
                               sample_size=int(m["sample_size"]), computation=m["computation"]))
    return out

def _load_baseline(path: str | None, use_active: bool, base_dir: Path, pointer: Path) -> Snapshot:
    if use_active:
        resolved = resolve_active_baseline(pointer=pointer, base_dir=base_dir)
        return load_snapshot(resolved)
    if path is None:
        raise ConfigurationError("neither --baseline nor --active given")
    p = Path(path)
    if not p.is_file():
        raise ConfigurationError(f"baseline file missing: {p}")
    return load_snapshot(p)

def save_report(report: dict, path: Path | str) -> Path:
    """Write a run_suite report dict as a JSON envelope (LLD:51/189)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return out

def main(argv: list[str] | None = None) -> int:
    parser = _GateParser(prog="llmops.eval.compare",
                         description="Offline regression gate — exit 0=PASS 1=FAIL 2=REVIEW 3=input 4=config")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--baseline", metavar="PATH", help="committed baseline snapshot JSON")
    g.add_argument("--active", action="store_true", help="resolve eval/baselines/active.json instead")
    parser.add_argument("--candidate", metavar="PATH", required=True, help="candidate report JSON (run_suite output)")
    parser.add_argument("--baselines-dir", metavar="PATH", help=argparse.SUPPRESS)
    parser.add_argument("--active-pointer", metavar="PATH", help=argparse.SUPPRESS)
    try:
        args = parser.parse_args(argv)
        root = Path(__file__).resolve().parents[3]
        base_dir = Path(args.baselines_dir) if args.baselines_dir else root / "eval" / "baselines"
        pointer = Path(args.active_pointer) if args.active_pointer else base_dir / "active.json"
        baseline = _load_baseline(args.baseline, args.active, base_dir=base_dir, pointer=pointer)
        candidate = _parse_report(args.candidate)
        verdict = compare(baseline, candidate)
        print(f"[gates] verdict={verdict.code} regressed={list(verdict.regressed) or 'none'}")
        for k, v in verdict.detail.items():
            print(f"        detail {k}: {v}")
        return verdict.code
    except _UsageError as e:
        print(f"[gates] usage error -> exit 3: {e}")
        return 3
    except EvaluationInputError as e:
        print(f"[gates] input error -> exit 3: {e}")
        return 3
    except ConfigurationError as e:
        print(f"[gates] config error -> exit 4: {e}")
        return 4

if __name__ == "__main__":
    sys.exit(main())