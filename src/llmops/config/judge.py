"""Judge LLM configuration, throttle control, response schema, and invocation.

Handles environment validation for OpenAI-compatible judge endpoints, throttled thread-safe
execution to prevent 429 rate limit errors, and JSON salvage parsing.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr, ValidationError, model_validator

# Default model per D9 if LLM_MODEL is omitted or empty
DEFAULT_JUDGE_MODEL = "Qwen/Qwen2.5-7B-Instruct-AWQ"


class JudgeError(Exception):
    """Typed error raised when judge invocation or salvage fails after retry.

    Message ALLOWS: prompt_id/key + short reason (e.g., 'invalid JSON after salvage').
    Message DENIES: LLM_BASE_URL, LLM_API_KEY, secrets, or raw response content (D11).
    """


def _get_env_var(var_name: str, required: bool = True) -> str | None:
    """Retrieve and strip environment variable safely.

    Raises RuntimeError if required and missing or empty after strip, without exposing
    the secret values in error messages.
    """
    raw_val = os.getenv(var_name)
    stripped_val = raw_val.strip() if raw_val is not None else ""

    if required and not stripped_val:
        raise RuntimeError(
            f"Required environment variable '{var_name}' is missing or empty. "
            f"Please set '{var_name}' in your environment or .env file."
        )

    return stripped_val if stripped_val else None


def judge_llm() -> ChatOpenAI:
    """Build judge ChatOpenAI client from environment.

    Reads:
      - LLM_BASE_URL (Required)
      - LLM_API_KEY  (Required)
      - LLM_MODEL    (Optional; falls back to DEFAULT_JUDGE_MODEL)

    Raises:
        RuntimeError: If LLM_BASE_URL or LLM_API_KEY is missing or empty.
    """
    base_url = _get_env_var("LLM_BASE_URL", required=True)
    api_key = _get_env_var("LLM_API_KEY", required=True)
    model = _get_env_var("LLM_MODEL", required=False) or DEFAULT_JUDGE_MODEL

    assert api_key is not None
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(api_key),
        base_url=base_url,
        temperature=0.0,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


class JudgeResponse(BaseModel):
    """Typed judge output.

    Attributes:
        winner: Must be strictly "A" or "B".
        score_a: Integer score between 0 and 10.
        score_b: Integer score between 0 and 10.
        reasoning: Non-empty step-by-step comparative explanation.
    """

    winner: Literal["A", "B"]
    score_a: int = Field(..., ge=0, le=10)
    score_b: int = Field(..., ge=0, le=10)
    reasoning: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _check_score_winner_consistency(self) -> JudgeResponse:
        """Validate logical consistency between score comparison and chosen winner.

        A tie (score_a == score_b) is permitted as long as a valid winner ("A" or "B")
        is selected.
        """
        if self.score_a > self.score_b and self.winner != "A":
            raise ValueError(
                f"score_a ({self.score_a}) > score_b ({self.score_b}) but winner='{self.winner}'"
            )
        if self.score_b > self.score_a and self.winner != "B":
            raise ValueError(
                f"score_b ({self.score_b}) > score_a ({self.score_a}) but winner='{self.winner}'"
            )
        return self


class _JudgeThrottle:
    """Thread-safe rate limiting spacing manager (~18 req/min).

    Maintains >=3.33s spacing between API dispatches to prevent 429 errors.
    """

    _MIN_SPACING_S: float = 60.0 / 18.0

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_send: float = 0.0

    def acquire(self) -> None:
        """Wait if necessary to ensure minimum spacing, then update _last_send on success."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_send
            wait_time = self._MIN_SPACING_S - elapsed

            if wait_time > 0:
                time.sleep(wait_time)

    def mark_success(self) -> None:
        """Record successful invocation timestamp.

        _last_send is updated ONLY on successful dispatch so endpoint failures
        do not compress the timing window.
        """
        with self._lock:
            self._last_send = time.monotonic()


_GLOBAL_THROTTLE = _JudgeThrottle()


def throttled_invoke(prompt: str, *, llm: ChatOpenAI) -> str:
    """Serialize judge calls through _GLOBAL_THROTTLE.

    Args:
        prompt: Raw string prompt to send to the judge.
        llm: Configured ChatOpenAI client.

    Returns:
        Raw text response string from LLM.
    """
    _GLOBAL_THROTTLE.acquire()
    try:
        response = llm.invoke(prompt)
        _GLOBAL_THROTTLE.mark_success()
        return str(response.content)
    except Exception as err:
        # Re-raise without exposing secrets or response details
        raise JudgeError(f"LLM API invocation failed: {type(err).__name__}") from err


def _strip_markdown_fences(text: str) -> str:
    """Remove surrounding markdown json code blocks if present."""
    cleaned = text.strip()
    # Match ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return cleaned


def parse_and_salvage_response(raw_response: str) -> JudgeResponse:
    """Parse raw LLM output into JudgeResponse, applying single-retry salvage if needed.

    Salvage strategy:
    1. Direct JSON parse and Pydantic validation.
    2. If failed: strip markdown fences (```json ... ```) and retry validation ONCE.
    3. If still invalid: raise JudgeError without leaking raw output or secrets.
    """
    # First attempt: direct json load
    try:
        data = json.loads(raw_response)
        if isinstance(data, dict):
            return JudgeResponse.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        pass

    # Salvage attempt: strip markdown code fences
    try:
        cleaned_text = _strip_markdown_fences(raw_response)
        data = json.loads(cleaned_text)
        if isinstance(data, dict):
            return JudgeResponse.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as err:
        raise JudgeError(
            f"Failed to parse judge output into valid JudgeResponse after salvage attempt: {type(err).__name__}"
        ) from err
    except Exception as err:
        raise JudgeError(f"Unexpected error during JSON salvage: {type(err).__name__}") from err

    raise JudgeError("Judge output format invalid (expected JSON object).")