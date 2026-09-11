"""Unit tests for judge configuration, validation, environment security, and salvage parsing."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from llmops.config.judge import (
    JudgeError,
    JudgeResponse,
    judge_llm,
    parse_and_salvage_response,
    throttled_invoke,
)

# --- Environment & Security Tests (D6, D11) ---

def test_judge_llm_raises_on_missing_env(monkeypatch: pytest.MonkeyPatch):
    """Verify RuntimeError is raised when required env vars are missing."""
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        judge_llm()
    
    # Ensure error message does not leak raw credentials or endpoint URLs
    assert "LLM_BASE_URL" in str(exc_info.value)
    assert "http" not in str(exc_info.value)


def test_judge_llm_builds_client_from_env(monkeypatch: pytest.MonkeyPatch):
    """Verify ChatOpenAI client builds successfully with valid stripped env values."""
    monkeypatch.setenv("LLM_BASE_URL", "  https://api.vllm.ai/v1  ")
    monkeypatch.setenv("LLM_API_KEY", "  secret-key-123  ")
    monkeypatch.setenv("LLM_MODEL", "  Qwen/Qwen2.5-7B-Instruct-AWQ  ")

    client = judge_llm()
    assert client.openai_api_base == "https://api.vllm.ai/v1"
    assert client.openai_api_key.get_secret_value() == "secret-key-123"
    assert client.model_name == "Qwen/Qwen2.5-7B-Instruct-AWQ"


# --- Schema Validation & Consistency Tests (D25, D27) ---

def test_judge_response_valid_schema():
    """Verify valid JudgeResponse initialization."""
    response = JudgeResponse(
        winner="A",
        score_a=9,
        score_b=5,
        reasoning="Candidate A provided factually accurate claims."
    )
    assert response.winner == "A"
    assert response.score_a == 9


def test_judge_response_out_of_bounds_scores():
    """Verify scores outside 0-10 range fail Pydantic validation."""
    with pytest.raises(ValidationError):
        JudgeResponse(winner="A", score_a=11, score_b=5, reasoning="Out of bounds")

    with pytest.raises(ValidationError):
        JudgeResponse(winner="B", score_a=-1, score_b=5, reasoning="Negative score")


def test_judge_response_inconsistent_score_and_winner():
    """Verify model validator catches score/winner mismatches."""
    # score_a > score_b, but winner is 'B'
    with pytest.raises(ValidationError) as exc_info:
        JudgeResponse(winner="B", score_a=8, score_b=3, reasoning="Score A is higher")
    assert "score_a (8) > score_b (3) but winner='B'" in str(exc_info.value)

    # score_b > score_a, but winner is 'A'
    with pytest.raises(ValidationError) as exc_info:
        JudgeResponse(winner="A", score_a=2, score_b=7, reasoning="Score B is higher")
    assert "score_b (7) > score_a (2) but winner='A'" in str(exc_info.value)


# --- Response Salvage & Parsing Tests ---

def test_parse_and_salvage_raw_json():
    """Verify direct parsing of raw valid JSON string."""
    raw = '{"winner": "A", "score_a": 8, "score_b": 6, "reasoning": "A is better."}'
    parsed = parse_and_salvage_response(raw)
    assert parsed.winner == "A"
    assert parsed.score_a == 8


def test_parse_and_salvage_markdown_fenced_json():
    """Verify salvage path strips markdown code fences successfully."""
    raw = """```json
    {
      "winner": "B",
      "score_a": 4,
      "score_b": 9,
      "reasoning": "Candidate B had no missing constraints."
    }
    ```"""
    parsed = parse_and_salvage_response(raw)
    assert parsed.winner == "B"
    assert parsed.score_b == 9


def test_parse_and_salvage_fails_on_unrecoverable_json():
    """Verify JudgeError is raised when output cannot be salvaged into valid schema."""
    invalid_raw = "Sorry, as an AI model I cannot judge this query."
    with pytest.raises(JudgeError) as exc_info:
        parse_and_salvage_response(invalid_raw)
    assert "Failed to parse judge output" in str(exc_info.value) or "invalid" in str(exc_info.value)


# --- Throttling Behavior Test ---

def test_throttled_invoke_executes_successfully():
    """Verify throttled_invoke delegates to LLM client."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = '{"winner": "A", "score_a": 7, "score_b": 7, "reasoning": "Tie"}'

    result = throttled_invoke("Evaluate this", llm=mock_llm)
    assert "winner" in result
    mock_llm.invoke.assert_called_once_with("Evaluate this")