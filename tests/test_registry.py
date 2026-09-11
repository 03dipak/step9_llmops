"""Unit tests for prompt registry lifecycle and atomic disk operations."""

from pathlib import Path

import pytest

from llmops.prompts.registry import (
    JudgeError,
    approve,
    load_registry,
    record_eval,
    rollback,
    save_registry,
    select_approved,
)


@pytest.fixture
def sample_registry_data() -> dict:
    """Fixture providing a mock registry state."""
    return {
        "prompts": {
            "judge_system_generic_1.0.0": {
                "key": "judge_system_generic_1.0.0",
                "prompt_id": "judge_system",
                "source_type": "generic",
                "version": "1.0.0",
                "template": "Old prompt template",
                "input_variables": ["query", "ideal_answer", "candidate_a", "candidate_b"],
                "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
                "status": "approved",
                "eval_scores": {"accuracy": 0.80, "latency_ms": 400.0},
                "run_count": 5,
                "created_at": "2026-09-01T00:00:00Z",
                "updated_at": "2026-09-01T00:00:00Z",
            },
            "judge_system_generic_1.1.0": {
                "key": "judge_system_generic_1.1.0",
                "prompt_id": "judge_system",
                "source_type": "generic",
                "version": "1.1.0",
                "template": "New prompt template",
                "input_variables": ["query", "ideal_answer", "candidate_a", "candidate_b"],
                "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
                "status": "draft",
                "eval_scores": {"accuracy": 0.0, "latency_ms": 0.0},
                "run_count": 0,
                "created_at": "2026-09-10T00:00:00Z",
                "updated_at": "2026-09-10T00:00:00Z",
            },
        }
    }


def test_save_and_load_registry_atomic(tmp_path: Path, sample_registry_data: dict):
    """Verify load/save cycle works with explicit file paths and writes valid JSON."""
    registry_file = tmp_path / "registry.json"
    
    # Save to disk
    save_registry(sample_registry_data, path=registry_file)
    assert registry_file.exists()

    # Load from disk
    loaded = load_registry(path=registry_file)
    assert loaded == sample_registry_data


def test_select_approved_success(sample_registry_data: dict):
    """Verify select_approved retrieves the correct active version."""
    entry = select_approved(sample_registry_data, prompt_id="judge_system", source_type="generic")
    assert entry["key"] == "judge_system_generic_1.0.0"
    assert entry["status"] == "approved"


def test_select_approved_raises_when_none(sample_registry_data: dict):
    """Verify select_approved raises JudgeError when no matching approved prompt exists."""
    # Retire active prompt
    sample_registry_data["prompts"]["judge_system_generic_1.0.0"]["status"] = "retired"

    with pytest.raises(JudgeError) as exc_info:
        select_approved(sample_registry_data, prompt_id="judge_system", source_type="generic")
    
    assert "No approved prompt found" in str(exc_info.value)


def test_approve_transitions_old_version_to_retired(sample_registry_data: dict):
    """Verify approving a new prompt automatically retires the old approved version."""
    updated = approve(sample_registry_data, key="judge_system_generic_1.1.0")
    
    # Check new prompt is approved
    assert updated["prompts"]["judge_system_generic_1.1.0"]["status"] == "approved"
    # Check old prompt transitioned to retired
    assert updated["prompts"]["judge_system_generic_1.0.0"]["status"] == "retired"


def test_rollback_transitions_to_retired(sample_registry_data: dict):
    """Verify rollback sets target version status to 'retired'."""
    updated = rollback(sample_registry_data, key="judge_system_generic_1.0.0")
    assert updated["prompts"]["judge_system_generic_1.0.0"]["status"] == "retired"


def test_record_eval_updates_scores_and_count(sample_registry_data: dict):
    """Verify record_eval correctly updates telemetry and increments run_count."""
    updated = record_eval(
        sample_registry_data,
        key="judge_system_generic_1.1.0",
        accuracy=0.92,
        latency_ms=350.5,
    )

    entry = updated["prompts"]["judge_system_generic_1.1.0"]
    assert entry["eval_scores"]["accuracy"] == 0.92
    assert entry["eval_scores"]["latency_ms"] == 350.5
    assert entry["run_count"] == 1