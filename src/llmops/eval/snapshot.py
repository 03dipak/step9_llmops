"""
LLM-Ops Eval Suite — Snapshot & Baseline Management (Module 03)
Provides baseline snapshot persistence, loading, and canonical active pointer resolution.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from llmops.eval.metric_registry import gate_metric_ids
from llmops.eval.run_suite import EvaluationInputError


class ConfigurationError(Exception):
    """Raised for baseline/pointer structural violations -> CLI exit 4 (D36)."""

def compute_goldens_sha256(goldens_dir: Path) -> str:
    if not goldens_dir.exists() or not goldens_dir.is_dir():
        raise EvaluationInputError(f"Goldens directory not found: {goldens_dir}")
    rel_files = sorted(f.relative_to(goldens_dir) for f in goldens_dir.rglob("*") if f.is_file())
    if not rel_files:
        raise EvaluationInputError(f"No golden files found in: {goldens_dir}")
    hasher = hashlib.sha256()
    for rel in rel_files:
        hasher.update(str(rel).encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update((goldens_dir / rel).read_bytes())
    return hasher.hexdigest()

def get_git_commit(root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root,
            capture_output=True, text=True, timeout=5, check=True,
        )
        return out.stdout.strip() or None
    except (subprocess.SubprocessError, OSError):
        return None

@dataclass
class Snapshot:
    id: str
    created_utc: str
    git_commit: str | None
    schema_version: str
    goldens_sha256: str
    corpus_sha256: str
    metrics: dict[str, dict]
    meta: dict

def save_snapshot(snapshot: Snapshot, path: Path) -> None:
    missing_gates = [gid for gid in gate_metric_ids() if gid not in snapshot.metrics]
    if missing_gates:
        raise EvaluationInputError(f"snapshot incomplete — missing gate rows: {missing_gates}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dataclasses.asdict(snapshot)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)

def load_snapshot(path: Path) -> Snapshot:
    if not path.exists() or not path.is_file():
        raise ConfigurationError(f"Baseline file missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Malformed baseline JSON: {e}") from e
    return Snapshot(**payload)

def write_active_pointer(snapshot: Snapshot, pointer: Path) -> None:
    payload = json.dumps({
        "schema_version": snapshot.schema_version,
        "baseline_id": snapshot.id,
        "path": f"{snapshot.id}.json",
    }, indent=2, sort_keys=True) + "\n"
    tmp = pointer.with_suffix(pointer.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(pointer)

def resolve_active_baseline(pointer: Path, base_dir: Path) -> Path:
    if not pointer.exists():
        raise ConfigurationError(f"active.json missing: {pointer}")
    try:
        pj = json.loads(pointer.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"malformed active.json: {e}") from e
    for field in ("schema_version", "baseline_id", "path"):
        if not isinstance(pj.get(field), str) or not pj[field]:
            raise ConfigurationError(f"active.json field missing/empty: {field!r}")
    name = Path(pj["path"])
    if name.name != str(name) or ".." in name.parts or name.is_absolute() or "\\\\" in str(pj["path"]):
        raise ConfigurationError(f"pointer path is not a safe basename: {pj['path']!r}")
    if name.suffix != ".json":
        raise ConfigurationError(f"pointer path must end .json: {pj['path']!r}")
    base_abs = base_dir.resolve()
    baseline_path = (base_abs / name).resolve()
    if not baseline_path.is_relative_to(base_abs):
        raise ConfigurationError(f"pointer path escapes baseline dir: {pj['path']!r}")
    if not baseline_path.is_file():
        raise ConfigurationError(f"pointer target missing: {baseline_path}")
    loaded = load_snapshot(baseline_path)
    if loaded.id != pj["baseline_id"]:
        raise ConfigurationError(f"baseline_id mismatch: pointer={pj['baseline_id']!r} snapshot={loaded.id!r}")
    return baseline_path