# 00b — Probe Notes (D9)

> Source of truth for **D9** (`doc/DECISIONS.md`) — which judge endpoint NB-000 actually
> proved live. Markdown only. No keys, no raw tokens — reference env var *names*, never values.

## D9 — Judge endpoint decision

- **Endpoint tried first:** default, `Qwen/Qwen2.5-7B-Instruct-AWQ` via `LLM_BASE_URL` /
  `LLM_API_KEY` / `LLM_MODEL`.
- **Result:** ✅ PASS on first attempt — no fallback to local Ollama `/v1` was needed.
- **Decision:** D9 = **default hosted endpoint** (`Qwen/Qwen2.5-7B-Instruct-AWQ`). Local
  Ollama `/v1` fallback path is documented but not currently exercised — revisit if the
  hosted endpoint starts rate-limiting or goes down.

## Run log

| Call | Model (via env) | Result | Notes |
|---|---|---|---|
| 1. Groq generation | `GROQ_MODEL` (default `openai/gpt-oss-120b`) | ✅ PASS | Non-empty text returned, asserted |
| 2. Gemini generation | `GEMINI_MODEL` (default `gemini-3.5-flash`) | ✅ PASS | Non-empty text returned, asserted |
| 3. Judge JSON | `LLM_MODEL` (`Qwen/Qwen2.5-7B-Instruct-AWQ`) | ✅ PASS | Valid JSON, matched expected schema (`winner`, `reasoning`, `score_a`, `score_b`) on first try — no fence-stripping needed |

## Sample judge output (for reference, not a golden)

```json
{
  "winner": "B",
  "reasoning": "More concise and directly addresses the question.",
  "score_a": 7,
  "score_b": 9
}
```

## Rate-limit / parse failures encountered

- None on this run. All three calls passed on the first attempt.
- *(Update this section the moment any call fails — record: which call, HTTP status /
  exception type if known, whether it was rate-limit vs malformed-JSON vs auth, and what
  fixed it. Do not paste keys or full raw error bodies if they might contain tokens.)*

## Scope note

- NB-000 carries **no package code** — this probe is purely a live-wire check.
- Marked `integration`; excluded from the default gate run.
- Nothing here is promoted into the config package — that lands in Mod 2 (`doc/task/02`).