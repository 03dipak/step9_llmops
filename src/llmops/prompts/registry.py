"""Prompt registry lifecycle management module.

Handles persistence, state transitions, metric logging, and selection of approved
prompt templates stored in registry.json.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from llmops.config.judge import JudgeError


def _get_default_path() -> Path:
    """Resolve default registry path relative to this file location."""
    return Path(__file__).parent / "registry.json"


def load_registry(path: Path | None = None) -> dict[str, Any]:
    """Load registry.json; default path = package-relative.
    
    Resolved from Path(__file__).parent / 'registry.json', never cwd-dependent.
    """
    target_path = path or _get_default_path()
    
    if not target_path.exists():
        return {"prompts": {}}
        
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as err:
        raise JudgeError(f"Failed to parse registry file at {target_path}: {err}") from err


def save_registry(registry: dict[str, Any], path: Path | None = None) -> None:
    """Dump registry to disk atomically via temporary file and os.replace.
    
    Atomically replaces the target file to prevent corrupted partial writes.
    Note: Assumes single-writer environment.
    """
    target_path = path or _get_default_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to a temporary file in the target directory
    temp_path = target_path.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
            
        os.replace(temp_path, target_path)
    except Exception as err:
        if temp_path.exists():
            temp_path.unlink()
        raise JudgeError(f"Failed to atomically save registry to {target_path}: {err}") from err


def approve(registry: dict[str, Any], key: str) -> dict[str, Any]:
    """Set status='approved' for key; existing approved version for same prompt_id + source_type -> 'retired'.

    Returns updated registry dictionary.
    Raises KeyError if key not found (T-02-9).
    """
    prompts = registry.get("prompts", {})
    if key not in prompts:
        raise KeyError(key)

    target_entry = prompts[key]
    prompt_id = target_entry.get("prompt_id")
    source_type = target_entry.get("source_type")
    now_iso = datetime.now(UTC).isoformat()

    # Retire currently approved prompt with matching (prompt_id, source_type)
    for k, entry in prompts.items():
        if (
            entry.get("prompt_id") == prompt_id
            and entry.get("source_type") == source_type
            and entry.get("status") == "approved"
            and k != key
        ):
            entry["status"] = "retired"
            entry["updated_at"] = now_iso

    # Approve target prompt
    target_entry["status"] = "approved"
    target_entry["updated_at"] = now_iso
    
    return registry


def rollback(registry: dict[str, Any], key: str) -> dict[str, Any]:
    """Set status='retired' for key and restore the prior version of same family to approved.

    T-02-8 binding spec: approve V2 (V1->retired), then rollback V2 -> V1 approved, V2 retired.
    Raises KeyError if key not found (T-02-9).
    """
    prompts = registry.get("prompts", {})
    if key not in prompts:
        raise KeyError(key)

    target = prompts[key]
    family = (target["prompt_id"], target["source_type"])
    now_iso = datetime.now(UTC).isoformat()

    # Retire the target
    target["status"] = "retired"
    target["updated_at"] = now_iso

    # Restore the previously-retired member of same family (T-02-8)
    for k, entry in prompts.items():
        if (
            k != key
            and entry.get("prompt_id") == family[0]
            and entry.get("source_type") == family[1]
            and entry.get("status") == "retired"
        ):
            entry["status"] = "approved"
            entry["updated_at"] = now_iso
            break

    return registry


def record_eval(registry: dict[str, Any], key: str, accuracy: float, latency_ms: float) -> dict[str, Any]:
    """Write eval_scores + increment run_count. Returns updated registry dictionary."""
    prompts = registry.get("prompts", {})
    if key not in prompts:
        raise KeyError(key)

    entry = prompts[key]
    
    if "eval_scores" not in entry:
        entry["eval_scores"] = {}
        
    entry["eval_scores"]["accuracy"] = accuracy
    entry["eval_scores"]["latency_ms"] = latency_ms
    entry["run_count"] = entry.get("run_count", 0) + 1
    entry["updated_at"] = datetime.now(UTC).isoformat()
    
    return registry


def select_approved(registry: dict[str, Any], prompt_id: str, source_type: str) -> dict[str, Any]:
    """Return the approved version entry for (prompt_id, source_type).
    
    Raises typed JudgeError if no matching approved entry is found.
    """
    prompts = registry.get("prompts", {})
    matching_approved = []

    for entry in prompts.values():
        if (
            entry.get("prompt_id") == prompt_id
            and entry.get("source_type") == source_type
            and entry.get("status") == "approved"
        ):
            matching_approved.append(entry)

    if not matching_approved:
        raise JudgeError(
            f"No approved prompt found for prompt_id='{prompt_id}' and source_type='{source_type}'."
        )

    # Return the single approved prompt entry
    return matching_approved[0]