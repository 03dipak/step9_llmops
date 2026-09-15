"""
LLM-Ops Eval Suite — Deterministic Suite Evaluator (Module 03)
Pure offline evaluator over committed golden datasets.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import operator
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_REPO_ROOT = str(Path(__file__).resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import tools.goldens.t01_verify as _t01
from llmops.eval.metric_registry import REGISTRY


class EvaluationInputError(Exception):
    """Raised when golden datasets, corpus paths, or input structures are missing/malformed."""

def _normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.strip()

def compute_corpus_sha256(docs_dir: Path) -> str:
    if not docs_dir.exists() or not docs_dir.is_dir():
        raise EvaluationInputError(f"Docs directory not found: {docs_dir}")
    rel_files = sorted(f.relative_to(docs_dir) for f in docs_dir.rglob("*") if f.is_file())
    if not rel_files:
        raise EvaluationInputError(f"No document files found in docs directory: {docs_dir}")
    hasher = hashlib.sha256()
    for rel in rel_files:
        hasher.update(str(rel).encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update((docs_dir / rel).read_bytes())
    return hasher.hexdigest()

def verify_golden_file_invariants(file_path: Path) -> bool:
    _rows, okflag = _t01.verify(str(file_path), 1, 10**9)
    return bool(okflag)

SOURCE_IDS = ("S1", "S2", "S3", "S4", "S5")

def _split_sources(row: dict) -> list[str]:
    return [s.strip() for s in str(row.get("source", "")).split("+") if s.strip()]

def _grounded(row: dict) -> bool:
    bundles = [_normalize_text(_t01.bund[s]) for s in _split_sources(row) if s in _t01.bund]
    joined = "\n".join(bundles)
    return all(_normalize_text(mc) in joined for mc in row.get("must_contain", []))

def _per_source_hits(rows: list[dict]) -> dict[str, list[int]]:
    out = {s: [0, 0] for s in SOURCE_IDS}
    for r in rows:
        mcs = r.get("must_contain")
        if not isinstance(mcs, list) or not mcs or not all(isinstance(mc, str) and mc for mc in mcs):
            raise EvaluationInputError(f"Empty/invalid must_contain at eval time: {r.get('id','?')}")
        grounded = _grounded(r)
        for s in _split_sources(r):
            if s in out:
                out[s][1] += 1
                if grounded:
                    out[s][0] += 1
    return out

def evaluate_golden_records(goldens_dir: Path) -> dict[str, tuple[float, int]]:
    if not goldens_dir.exists() or not goldens_dir.is_dir():
        raise EvaluationInputError(f"Goldens directory not found: {goldens_dir}")
    golden_files = sorted(goldens_dir.glob("*_goldens.json"))
    if not golden_files:
        raise EvaluationInputError(f"No golden files found in: {goldens_dir}")
    files: dict[str, list[dict]] = {}
    for fp in golden_files:
        try:
            files[fp.name] = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise EvaluationInputError(f"Malformed golden JSON in {fp.name}: {e}") from e

    values: dict[str, tuple[float, int]] = {}
    passing = sum(1 for fp in golden_files if verify_golden_file_invariants(fp))
    values["eval.gate.golden_rules"] = (passing / len(golden_files), len(golden_files))

    for s, (hits, n) in _per_source_hits(files.get("retriever_goldens.json", [])).items():
        if n == 0:
            raise EvaluationInputError(f"Zero retriever rows for {s}")
        values[f"eval.gate.retriever.agreement.{s}"] = (hits / n, n)

    for s, (hits, n) in _per_source_hits(files.get("correctness_goldens.json", [])).items():
        if n == 0:
            raise EvaluationInputError(f"Zero correctness rows for {s}")
        values[f"eval.gate.correctness.answer_cited.{s}"] = (hits / n, n)

    qp_rows = files.get("query_processing_goldens.json", [])
    mis_rows = [r for r in qp_rows if r.get("category") == "misroute"]
    for s in SOURCE_IDS:
        rows = [r for r in mis_rows if s in _split_sources(r)]
        n = len(rows)
        if n == 0:
            raise EvaluationInputError(f"Zero misroute rows for {s}")
        hits = sum(1 for r in rows if _normalize_text(r.get("ideal_answer", "")).lower().startswith(f"route to {s.lower()}"))
        values[f"eval.gate.routing.misroute_negation.{s}"] = (hits / n, n)

    for s in SOURCE_IDS:
        n = sum(1 for frows in files.values() for r in frows if s in _split_sources(r))
        values[f"eval.info.snapshot_rowcount.{s}"] = (float(n), n)

    return values

@dataclass(frozen=True)
class MetricValue:
    metric_id: str
    value: float
    sample_size: int
    computation: Literal["stub"]

def run_suite(goldens_dir: Path, docs_dir: Path) -> dict:
    values = evaluate_golden_records(goldens_dir)
    computed = []
    for m in REGISTRY:
        if m.id in values:
            val, n = values[m.id]
            computed.append({
                "metric_id": m.id,
                "value": val,
                "sample_size": n,
                "computation": "stub",
            })
    computed.sort(key=operator.itemgetter("metric_id"))
    return {
        "schema_version": "1.0",
        "generated_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "metrics": computed,
    }


def compute_canonical_bytes(report: dict) -> bytes:
    """Canonical bytes: schema_version + sorted metrics; generated_utc excluded (T-03-2)."""
    payload = {k: v for k, v in report.items() if k != "generated_utc"}
    payload["metrics"] = sorted(
        payload.get("metrics", []), key=operator.itemgetter("metric_id")
    )
    return json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    """CLI entry: python -m llmops.eval.run_suite --goldens-dir ... --docs-dir ..."""
    import argparse

    parser = argparse.ArgumentParser(prog="llmops.eval.run_suite",
                                     description="Deterministic offline eval suite (Module 03).")
    parser.add_argument("--goldens-dir", type=Path, required=True, help="dir containing golden JSON per source")
    parser.add_argument("--docs-dir", type=Path, required=True, help="dir containing corpus bundles")
    parser.add_argument("--output", type=Path, help="write report JSON to this path (else stdout)")
    args = parser.parse_args(argv)
    try:
        report = run_suite(args.goldens_dir, args.docs_dir)
    except EvaluationInputError as e:
        print(f"[eval] input error: {e}", file=sys.stderr)
        return 3
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        print(f"[eval] wrote {args.output}", file=sys.stderr)
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())