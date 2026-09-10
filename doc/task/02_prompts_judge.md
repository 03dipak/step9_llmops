# Task 02 — Prompts & the Judge (Mod 2)

## LLMOps framing

- **Pillar(s):** 2 (prompt & template mgmt) + 3 (LLM-as-judge).
- **Why it matters:** the judge is the *measurement instrument* of the whole system. It must
  be pinned (drift = noise), shared across backends, throttled, and **out of the CI gate**.
  Prompts are code: versioned, reviewable, rollback-able — never literals in `app.py`.
- **Cross-ref:** `doc/JOURNEY_MAP.md` (pillars 2/3), `doc/DECISIONS.md` D6/D9, step4
  `eval/judge.py`, step4 `src/multi_source_rag/prompts/prompt_registry.json`.

## Deliverables (your code; this repo's agents write only docs + review)

1. **NB-002 `judge_wiring.ipynb`** — your notebook: build the judge from env
   (`LLM_BASE_URL` + `LLM_API_KEY` + `LLM_MODEL`, OpenAI-compatible), send one JSON-only
   prompt, parse the JSON reply, assert a schema. The endpoint itself was already proven in
   **NB-000 (Mod 00b close)** — D9 is decided there and recorded in
   `doc/notes/00b_probe_notes.md`; NB-002 wires and hardens exactly that choice.
2. **`src/llmops/config/judge.py`** (promote from NB-002) — `judge_llm()` factory + a
   `throttled_invoke` (lock + spacing; step4 observed 429 at ~20 req/min — `eval/judge.py:26`)
   + JSON-mode with pydantic-schema validation and a salvage path on malformed JSON.
3. **Prompt registry slice** — `src/llmops/prompts/registry.json` mirroring step4's
   composite key `prompt_id + source_type + version` with **approve / rollback lifecycle**
   (two versions of one system prompt, one rolled back, recorded).
4. `tests/test_judge.py` + `tests/test_registry.py` — offline: registry approve/rollback;
   judge factory builds from env without secrets; malformed-JSON salvage.

## Depends on

- Task 00b + its NB-000 stack probe (D9 endpoint chosen, `doc/notes/00b_probe_notes.md`) · Task 01 (goldens exist — judge exercises need queries).

## Contracts (reference, don't redefine)

- Judge reads **only** `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL` — generation is a separate
  ladder (Groq→Gemini) and the two are never mixed (step4 `config.py:131-215`).
- Registry `record["model"]` = logical model id for provenance only; provider→model
  resolution lives in config, never in the registry (step4 task-01 contract).

## Exit criteria

- [ ] NB-002 runs end-to-end; judge JSON reply parsed and schema-validated (asserts in notebook)
- [ ] Judge endpoint in NB-002 matches the D9 choice recorded by NB-000 (`doc/notes/00b_probe_notes.md`)
- [ ] Registry has ≥2 versions of one prompt; rollback exercised and recorded
- [ ] `uv run pytest tests/test_judge.py tests/test_registry.py` green
- [ ] `uv run ruff check .` + `uv run mypy src/` clean
- [ ] No key/literal in any file; logs carry no content

## Verify

```
uv run jupyter nbconvert --to notebook --execute jupyter_notebook/02_judge_wiring.ipynb
uv run pytest tests/test_judge.py tests/test_registry.py -q
```

## Interview-Q&A (Mod 2)

**Q1. "Why is your judge pinned to one endpoint?"** — It is the instrument: if it drifts,
metric changes look like answer regressions. Pinned + throttled + shared across backends
(DeepEval *and* Ragas wrap the same `judge_llm()`) means scores are comparable and drift in
the *system* is what shows up, not drift in the yardstick.
**Check:** "measurement instrument" framing, not "I picked a model".

**Q2. "Why is the judge out of your CI gate?"** — Noise. Judge output has ±0.03 variation; a
gate that can flake trains people to ignore it. The gate runs deterministic L1 rules and
offline L2; the judge serves live/nightly eval where its opinion is the point.
**Check:** determinism-before-LLM reasoning (D5).

**Q3. "How do you version prompts?"** — Composite key `prompt_id + source_type + version`,
approve/rollback lifecycle, generation reads from the registry never from literals. Rollback
is not theoretical: I exercised it in this module.
**Check:** concrete registry + rollback evidence, not hand-waving.

## Next module

Task 03 (Regression gates) — needs goldens (01) + judge harness (02).