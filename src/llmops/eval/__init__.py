"""
LLM-Ops Eval Suite — Public Facade (D22)
Re-exports registry + run_suite + compare/snapshot entry helpers.
"""
from __future__ import annotations

from llmops.eval.compare import compare, save_report
from llmops.eval.compare import main as run_compare
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
from llmops.eval.run_suite import EvaluationInputError, MetricValue, run_suite
from llmops.eval.snapshot import (
    ConfigurationError,
    Snapshot,
    compute_goldens_sha256,
    load_snapshot,
    resolve_active_baseline,
    save_snapshot,
)

__all__ = [
    "CORRECTNESS_N",
    "MISROUTE_N",
    "REGISTRY",
    "RETRIEVER_N",
    "ConfigurationError",
    "EvaluationInputError",
    "MetricValue",
    "Snapshot",
    "compare",
    "compute_goldens_sha256",
    "gate_metric_ids",
    "get_metric",
    "load_snapshot",
    "metric_ids",
    "resolve_active_baseline",
    "run_compare",
    "run_suite",
    "save_report",
    "save_snapshot",
    "validate_registry",
]
