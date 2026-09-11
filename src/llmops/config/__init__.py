"""Public facade for llmops.config (D26).

Mod 2 exports ONLY judge_llm. generate_llm joins when Mod 4's generation.py lands.
"""

from llmops.config.judge import judge_llm

__all__ = ["judge_llm"]