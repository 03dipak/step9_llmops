# Task 00b — Scaffold: uv init → uv add → uv add --dev (mirror of step4)

## Objective

Stand up step9 as an installable **src-layout package** with the same `uv` toolchain step4
uses (verified against `step4/pyproject.toml`): `uv init`, runtime deps via `uv add`, dev
tools via `uv add --dev` (→ `[dependency-groups] dev`), pytest/mypy/ruff config, `.env`
never committed.

> **House rule:** you (the learner) run every command below. Agents write docs and review
> verdicts only — no code, no scaffolding commands executed by agents.

## LLMOps framing

- **Pillar 7 (lifecycle):** the lockfile + `uv sync` is the reproducibility unit — the Mod-3
  CI gate runs the *same* commands you run here. A repo that can't rebuild identically can't
  gate regressions honestly.
- **Why it matters:** `uv.lock` pins the whole eval stack; a drifting lockfile is drift in
  the measurement, and §7 says judge drift is noise you must eliminate.
- **Cross-ref:** `step4/pyproject.toml` (template), `step4/doc/task/01_scaffold_and_judge.md`.

## Step 1 — init (src layout, python >=3.12 like step4:9)

```bash
cd /home/dipak/agentic/step9_llmops
uv init --package --name llmops --python 3.12
```

Produces: `pyproject.toml`, `src/llmops/__init__.py`, `README.md` (overwrite with ours),
`uv.lock` (commit it). Note: `.gitignore` **already exists** in this repo (created with the
secrets protection below) — `uv init` may append its defaults; keep the `.env` lines.

## Step 2 — runtime deps (step9 slice of step4:10-36)

```bash
uv add langchain-core langchain-groq langchain-google-genai \
       langchain-openai openai python-dotenv pydantic
```

**Deliberately deferred (add in later modules, mirroring step4):**
- Mod 2/3: `ragas` (+`deepeval==2.9.3`) — *only* when you add the L2 eval contracts.
- Mod 4: `numpy` (cost/latency math) · Mod 7: `streamlit` or `gradio` (demo).
- Mod 3, not now: `rank-bm25`, `sentence-transformers` — the retrieval engine is cross-ref
  to step4, not re-implemented, so step9 does *not* need them unless an exercise does.

## Step 3 — dev tools (mirror step4:45-57)

```bash
uv add --dev pytest pytest-cov pytest-mock ruff mypy pyright \
         ipykernel ipywidgets nbclient nbformat pytest-asyncio
```

`uv add --dev` writes to `[dependency-groups] dev` — then check:

```bash
uv sync                        # reproducible env from uv.lock
uv run pytest -q               # needs ≥1 learner-written smoke test
uv run ruff check .
uv run mypy src/
```

## Step 4 — tool config (mirror step4:59-79, with two deltas noted)

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]           # step4 uses ["src", "eval"] once eval/ lands (Mod 2)
asyncio_mode = "auto"
addopts = "-m 'not integration'"
markers = ["integration: real network/model roundtrip (run with -m integration)"]

[tool.mypy]
# add overrides below the day you `uv add ragas` / `uv add rank-bm25` (step4:70-79 —
# both lack py.typed)
```

## Step 5 — hygiene (no secrets, ever)

- `.gitignore` must cover: `.env`, `.venv/`, `chroma_db/`, `*.npz`, `__pycache__/`,
  `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.ipynb_checkpoints/`.
- `.env.example` (committed, empty values) with the 5 keys from step4: `GROQ_API_KEY`,
  `GEMINI_API_KEY`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`.
- Copy to `.env` (gitignored) with **your own** values — never paste real keys into any file
  an agent or reviewer can read.

## Step 6 — NB-000 stack probe (closes this module)

Prove the free stack before any build: your notebook `jupyter_notebook/NB-000_config_probe.ipynb`
makes exactly three live calls and asserts each (uses only the deps from Step 2):

1. **Groq generation** — one short prompt through `GROQ_API_KEY` (primary model).
2. **Gemini generation** — one short prompt through `GEMINI_API_KEY` (fallback model).
3. **Judge JSON** — one JSON-only prompt through `LLM_BASE_URL` + `LLM_API_KEY` +
   `LLM_MODEL` (OpenAI-compatible), parse the JSON reply, assert your expected schema.

This is where **D9 is decided** (`doc/DECISIONS.md`): if the default
`Qwen/Qwen2.5-7B-Instruct-AWQ` endpoint fails, try local Ollama `/v1` and record which one
passes. Write the decision and any rate-limit/parse failures into
`doc/notes/00b_probe_notes.md` (markdown, no keys). NB-000 carries **no package code** —
nothing is promoted from it (the config package lands in Mod 2 per `doc/task/02`); the probe
is `integration`-marked and never part of the gate's default run.

## Files expected after this task

```
pyproject.toml · uv.lock · .gitignore · .env.example
src/llmops/__init__.py
tests/test_smoke.py            # you write it: `import llmops` + one assert
jupyter_notebook/NB-000_config_probe.ipynb   # stack probe: Groq + Gemini + judge JSON (D9)
doc/notes/00b_probe_notes.md                 # D9 decision + probe evidence (markdown only)
```

## Exit criteria

- [ ] `uv run python -c "import llmops; print(llmops.__name__)"` prints `llmops`
- [ ] `uv run pytest -q` green (≥1 learner-written smoke test)
- [ ] `uv run ruff check .` clean
- [ ] `uv run mypy src/` clean
- [ ] `.env.example` committed with the 5 keys, values empty; `.gitignore` covers `.env`
- [ ] `uv.lock` committed
- [ ] NB-000 probe green: Groq + Gemini + judge JSON each succeed with asserts; D9 endpoint
      decision recorded in `doc/notes/00b_probe_notes.md`

## Depends on

- **None — base build task.** Runs before Task 01 (corpus loading + anchor checks need the
  package to exist).

## Contracts (reference, don't redefine)

- Tool-config conventions mirror step4 `pyproject.toml` so the Mod-3 gate behaves identically.
- `[project.scripts]` CLI entry: **deferred** — step9 ships no CLI unless Mod 7 needs one
  (recorded decision, not an omission).

## Interview-Q&A (Mod 00b)

**Q1. "Walk me through setting up a Python project from scratch, production-grade."**
**A:** `uv init --package` (src layout, `requires-python >=3.12`) — then *two* dep lanes:
`uv add` for runtime, `uv add --dev` for tooling (that's `[dependency-groups] dev`), both
locked in `uv.lock` so `uv sync` reproduces the env byte-for-byte — which is the prerequisite
for a reproducible CI gate. Then pytest/mypy/ruff config, `addopts = "-m 'not integration'"`
so the gate stays fast and offline, and `.env` gitignored with `.env.example` as the schema.
**Check:** they hear *reproducibility-before-gating*, not just "I typed uv init".

**Q2. "Why uv instead of pip/poetry?"**
**A:** One tool for init/add/sync/run; native lockfile; dependency groups; fast resolution —
and my step4 was built on it, so gates and notebooks share one environment story. Tool choice
is a decision with a lockfile as evidence.
**Check:** they hear a decision with reasons, not a trend.

**Q3. "What belongs in .gitignore and why?"**
**A:** Secrets (`.env`), machine state (`chroma_db/`, `*.npz`), tool caches, `.venv`. If it is
a secret, a build artifact, or a cache — never commit. `.env.example` is the committed
schema; real values live only in the local `.env`.
**Check:** security instinct — secrets never reach files agents/reviewers can read.

## Next module

Task 01 (Data & testset) — as soon as the scaffold's exit criteria are green.