"""llmops.eval.metric_registry -- Mod 03 Regression Gates: metric schema + registry.

Promoted from NB-003_regression_gates.ipynb, Section 1.

The registry is DATA ONLY -- no evaluator functions live here (LLD: "registry
is DATA"; task 03:84). `run_suite` (llmops.eval.run_suite) computes values;
this module only declares metric identity, tolerance policy, and provenance.

Tolerance policy (D10/D19):
  - judge-default            : +/-0.03 absolute
  - per-source single-flip   : 1/(n+1) absolute floor (retriever.agreement +
                                correctness.answer_cited families only)
  - latency                  : +/-0.20 relative

See T-03-1 in tests/test_gates.py for the full invariant suite.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "CORRECTNESS_N",
    "MISROUTE_N",
    "REGISTRY",
    "RETRIEVER_N",
    "Metric",
    "MetricDirection",
    "MetricKind",
    "gate_metric_ids",
    "get_metric",
    "metric_ids",
    "validate_registry",
]

type MetricKind = Literal["gate", "guardrail", "info"]
type MetricDirection = Literal["higher", "lower"]  # bigger = better


@dataclass(frozen=True)
class Metric:
    id: str                     # dotted id, step4-parity naming (T-03-1 regex)
    name: str                   # human-readable
    kind: MetricKind            # gate | guardrail | info
    direction: MetricDirection
    tolerance: float            # absolute delta (0.03 judge) or relative fraction (0.20 latency)
    tolerance_unit: Literal["absolute", "relative"]
    value_domain: Literal["fraction", "nonnegative"]  # fraction = finite & in [0,1]
    expected_sample_size: int | None  # committed closed-set n (D19); None for non-n rows
    description: str            # one-line semantics. NO evaluator function here.


# Per-source committed golden counts (D19 closed set, verified against
# eval/goldens/*.json) -- the single source of truth for tolerance floors.
RETRIEVER_N = {"S1": 34, "S2": 27, "S3": 28, "S4": 28, "S5": 26}
CORRECTNESS_N = {"S1": 25, "S2": 22, "S3": 20, "S4": 24, "S5": 21}
MISROUTE_N = {"S1": 1, "S2": 2, "S3": 2, "S4": 2, "S5": 1}


def _single_flip_tol(n: int) -> float:
    """Tolerance floor s.t. a single flipped golden row always trips the gate:
    (n-1)/n must fall strictly below n/(n+1). D19/D39."""
    return 1.0 / (n + 1)


REGISTRY: tuple[Metric, ...] = (
    Metric(
        id="eval.gate.golden_rules",
        name="Golden files pass L1 invariants",
        kind="gate", direction="higher",
        tolerance=0.0, tolerance_unit="absolute",
        value_domain="fraction",
        expected_sample_size=3,   # 3 golden FILES, not rows (T-03-2b)
        description="fraction of golden files passing L1 invariant checks "
                     "(reuses tools/goldens/t01_verify.py) -- global, all 3 files",
    ),
    *(
        Metric(
            id=f"eval.gate.retriever.agreement.{s}",
            name=f"Retriever agreement -- {s}",
            kind="gate", direction="higher",
            tolerance=_single_flip_tol(n), tolerance_unit="absolute",
            value_domain="fraction",
            expected_sample_size=n,
            description=f"per-source ideal_context <-> must_contain coverage ({s}, n={n})",
        )
        for s, n in RETRIEVER_N.items()
    ),
    *(
        Metric(
            id=f"eval.gate.routing.misroute_negation.{s}",
            name=f"Misroute negation -- {s}",
            kind="gate", direction="higher",
            tolerance=0.03, tolerance_unit="absolute",   # judge-default; n=1/2 already trips on any flip
            value_domain="fraction",
            expected_sample_size=n,
            description=f"misroute-category rows stay true negatives ({s}, n={n})",
        )
        for s, n in MISROUTE_N.items()
    ),
    *(
        Metric(
            id=f"eval.gate.correctness.answer_cited.{s}",
            name=f"Answer citation coverage -- {s}",
            kind="gate", direction="higher",
            tolerance=_single_flip_tol(n), tolerance_unit="absolute",
            value_domain="fraction",
            expected_sample_size=n,
            description=f"ideal_answer covers every citation-critical must_contain string ({s}, n={n})",
        )
        for s, n in CORRECTNESS_N.items()
    ),
    Metric(
        id="eval.guardrail.calibration.band8",
        name="Judge calibration -- band >=8 share",
        kind="guardrail", direction="higher",
        tolerance=0.03, tolerance_unit="absolute",
        value_domain="fraction",
        expected_sample_size=None,   # nightly live only (D29)
        description="share of flawless/grounded rows scoring >=8 under the judge -- nightly live only",
    ),
    Metric(
        id="eval.guardrail.position_bias.agreement",
        name="Judge position-bias agreement",
        kind="guardrail", direction="higher",
        tolerance=0.03, tolerance_unit="absolute",
        value_domain="fraction",
        expected_sample_size=None,   # nightly live only (D28)
        description="judge A/B vs B/A agreement on the same row -- nightly live only",
    ),
    *(
        Metric(
            id=f"eval.info.snapshot_rowcount.{s}",
            name=f"Golden rows evaluated -- {s}",
            kind="info", direction="higher",
            tolerance=0.0, tolerance_unit="absolute",
            value_domain="nonnegative",
            expected_sample_size=None,
            description=f"provenance only, never verdict ({s})",
        )
        for s in ("S1", "S2", "S3", "S4", "S5")
    ),
    Metric(
        id="eval.guardrail.latency.p95",
        name="P95 total latency",
        kind="guardrail", direction="lower",
        tolerance=0.20, tolerance_unit="relative",
        value_domain="nonnegative",
        expected_sample_size=None,   # Mod-4 computed (task 04 SLO report)
        description="P95 total latency vs baseline*1.2 -- registered now, value arrives with Mod 4",
    ),
    Metric(
        id="eval.info.latency.ttft_p95",
        name="TTFT P95",
        kind="info", direction="lower",
        tolerance=0.20, tolerance_unit="relative",
        value_domain="nonnegative",
        expected_sample_size=None,   # Mod-4 computed
        description="TTFT P95, recorded for provenance only -- Mod-4 computed",
    ),
)


# --- Accessors (registry-declaration order preserved) -----------------------

def get_metric(metric_id: str) -> Metric:
    """Raise KeyError on unknown id (T-03-10)."""
    for m in REGISTRY:
        if m.id == metric_id:
            return m
    raise KeyError(f"unknown metric id: {metric_id}")


def metric_ids() -> list[str]:
    """Registry-declaration order (asserted by T-03-1)."""
    return [m.id for m in REGISTRY]


def gate_metric_ids() -> tuple[str, ...]:
    """Gates only, declaration order; len == 16 (T-03-3)."""
    return tuple(m.id for m in REGISTRY if m.kind == "gate")


# --- validate_registry() -----------------------------------------------------
# Invariant checks (T-03-1). NOTE the scoping (LLD 03:89 vs 03:103/113): the
# 1/(n+1) single-flip floor applies to the retriever.agreement and
# correctness.answer_cited per-source families ONLY. misroute gates keep the
# judge +/-0.03 default by design (n=1/2 already trips on any flip); a
# literal "every per-source gate row" floor read WOULD reject them.

_ID_RE = re.compile(
    r"^eval\.(gate|guardrail|info)\.[a-z_]+(\.[a-z0-9_]+)*(\.S[1-5])?$"
)

_FLOOR_FAMILIES = ("eval.gate.retriever.agreement.", "eval.gate.correctness.answer_cited.")


def validate_registry() -> None:
    """Raise AssertionError listing every violation (T-03-1)."""
    errors: list[str] = []
    seen: set[str] = set()

    for m in REGISTRY:
        if m.id in seen:
            errors.append(f"duplicate id: {m.id}")
        seen.add(m.id)

        if not _ID_RE.fullmatch(m.id):
            errors.append(f"id does not match regex: {m.id}")

        if m.kind not in ("gate", "guardrail", "info"):
            errors.append(f"bad kind: {m.id}={m.kind!r}")
        if m.direction not in ("higher", "lower"):
            errors.append(f"bad direction: {m.id}={m.direction!r}")
        if m.value_domain not in ("fraction", "nonnegative"):
            errors.append(f"bad value_domain: {m.id}={m.value_domain!r}")
        if not (0.0 <= m.tolerance < float("inf")):
            errors.append(f"tolerance out of range: {m.id} tol={m.tolerance}")

        is_floor = m.kind == "gate" and m.id.startswith(_FLOOR_FAMILIES)
        is_misroute = m.kind == "gate" and m.id.startswith("eval.gate.routing.misroute_negation.")

        if is_floor or is_misroute:
            if m.expected_sample_size is None or m.expected_sample_size < 1:
                errors.append(f"per-source gate missing expected_sample_size: {m.id}")
            elif is_floor:
                expect = 1.0 / (m.expected_sample_size + 1)
                if abs(m.tolerance - expect) > 1e-12:
                    errors.append(
                        f"floor-family tolerance != 1/(n+1): {m.id} "
                        f"tol={m.tolerance} != {expect}"
                    )

    if not errors:
        return
    raise AssertionError("validate_registry failed:\n  - " + "\n  - ".join(errors))