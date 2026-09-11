# Step 9 — LLMOps (the capstone map)

**One-line thesis:** *"Boring infra, smart gates."* Step 9 re-reads the entire journey
(step1–step8) through the LLMOps operating layer, so that LLMOps is the **spine** of the
story, not a chapter bolted on at the end.

> **House rule for this repo: agents write markdown only.** Every line of application code
> is written by you (the learner) — notebook first, then promoted into the package.
> Agents write task docs, interview Q&A, review checklists, and verdicts — never code.

> **Base project:** this folder is the reusable base project template — new projects are
> spawned from it (clone → rename → fresh secrets → re-grounded goldens). See
> `doc/BASE_PROJECT.md`.

## Why step 9 exists

Your earlier repos built components in build order: RAG → eval → frameworks → multi-source →
agents → deploy → fine-tuning. That was the right order to *build*, but it taught LLMOps as
an afterthought ("we later add the LLMOps"). Step 9 fixes the pedagogy: the 8-pillar LLMOps
spine from `step4/doc/QA_DEEP_DIVES.md §7` is the **curriculum frame**, and every step1–8
concept is filed under a pillar + lifecycle phase.

The map (see `doc/JOURNEY_MAP.md`) covers all of step1–8. The **code delta is tiny**:
config-as-package, judge wiring, the CI gate, the demo UI. Everything deep (mini-IVF,
dual-backend eval, regression harness) stays a cross-reference to step4 — you re-learn the
patterns, you do not duplicate the machinery.

## The role map (same as the step-series house rules)

| Say | Role | Behavior here |
|---|---|---|
| `review` | Reviewer | Read-only verification of your code and my docs — verdict tables, never edits |
| `writer md` | Tech writer | Updates the doc suite (README, JOURNEY_MAP, task docs, Interview-Q&A) |
| `mentor` | Mentor / architect | Evaluates suggestions against step9 + step4 constraints; scope discipline |
| `builder` | Implementer | **You** — notebook-first in `jupyter_notebook/`, promote into `src/llmops/` |
| `tester` | QA/Eval | L1/L2 eval contracts, asserts inside notebooks, gate exit codes |
| `planner` | Delivery lead | Module order from README/PLAN only — never invented |
| others | security / ops / data / ux | Slice advice per role section in the module docs |

## Learning workflow (each module)

1. **Read the module task doc** (`doc/task/0X_*.md`) — objective, LLMOps framing, exit criteria, **Interview-Q&A** for that module.
2. **Open the module notebook** (`jupyter_notebook/0X_*.ipynb`) — write *simple* LangChain code, run it, watch it fail and fix it.
3. **Promote** what survives: cells → typed modules in `src/llmops/` + tests in `tests/`.
4. **Ask for `review`** — reviewer verifies your claims against the actual files.
5. Fold decisions into the docs with `writer md`.

## Module order (dependency-first — this is the LLMOps-first difference)

| Mod | Topic | Pillar(s) | You build |
|---|---|---|---|
| 0 | LLMOps foundations (`doc/task/00`) | — | nothing — read + map |
| 00b | Scaffold (`uv init`/`add`/`sync`) | 7 | uv package, lockfile, tool config, `.env` hygiene |
| 1 | Data & testset (goldens) | 1 | corpus prep + golden questions |
| 2 | Prompts & the judge | 2, 3 | prompt registry slice + judge probe |
| 3 | Regression gates (the mid-course core) | 4 | `compare`-style verdict + CI gate |
| 4 | Observability & cost | 5, 6 | SLO metrics + cost ladder |
| 5 | Guardrails | 8 | abstention gate + PII-minimal |
| 6 | Lifecycle (deploy/rollback) | 7 | snapshot + gate as part of the flow |
| 7 | Demo & surfacing | 7 | Gradio UI with abstention/degraded/conflict states |

## The free stack (chosen, agreed)

Local-first engine (`uv` + `src/llmops/`) · Groq free tier primary → Gemini fallback ·
judge via OpenAI-compatible endpoint (default `Qwen/Qwen2.5-7B-Instruct-AWQ`, local Ollama
candidate — *verify in NB-000, not assumed*) · HF Spaces (Gradio) demo · GitHub Actions
offline-only gate. **Free-tier quotas are your pillar-6 budget** — the constraint is the lesson.

## Interview framing

`doc/INTERVIEW_Q&A.md` is the rehearsal deck: every module delivers at least one
interview-ready answer, and the doc's phase pipeline answers the question
*"how would you develop this from scratch?"* at every phase — LLD → probe → build →
test cases → gate/ops → cost → security → demo. You learn by writing; you interview by
explaining what you wrote and decided — including the deferrals.