<!-- Bundle S5 (D14): sources = step4 README + AGENTS, step9 README + AGENTS -->

# Step 4 — Multi-Source RAG with Routing

An end-to-end **Retrieval-Augmented Generation (RAG)** system that answers questions across
**multiple data sources** by deciding *which source(s)* to query, retrieving the best context,
citing where each answer came from, and proving it works with a **three-level evaluation suite
backed by *two* metric engines (DeepEval + Ragas)** and a regression harness.

> **In plain words:** Step 3 answered questions from one source. Step 4 answers questions from
> several sources, routes each question to the right source(s), hybrid-retrieves, returns
> **cited** answers, and *measures* that it works — with two independent eval frameworks so we
> don't trust a single vendor's score.

> **Status at a glance (which parts are real today):** the **data plane** (ingestion, chunking,
> embeddings, vector store) and the **eval plane** (dual DeepEval+Ragas seam, component evals)
> are implemented and tested (102 unit + integration tests, real-mode smoke). The **inference
> plane** (routing → hybrid retrieval → rerank → cited generation → pipeline → CLI/UI) is the
> current build phase, scaffolded per `doc/task/`. Detail in §1's status column.

---

## 1. What this is (for a Business Analyst / Product person)

**The problem:** Real projects don't have one source of truth. You have documents, web pages,
databases, and APIs — each needs a different loader, chunk strategy, prompt, and retrieval method.

**What this project delivers, and the honest status of each piece:**

| Capability | What it does | Status |
|------------|-----------------|--------|
| Multi-source ingestion | Loads `text`, `web`, `pdf`, `db` via LangChain loaders into one uniform `{text, metadata}` shape | ✅ implemented + tested |
| Text chunking | 5 strategies (`character`, `recursive`, `markdown`, `semantic`, `code`) behind one `Chunker` facade | ✅ implemented + tested |
| Embeddings | Local ONNX `Qwen3-Embedding-0.6B` + deterministic offline embedder behind one `Embedder` interface | ✅ implemented + tested |
| Vector store | Chroma (HNSW cosine) + hand-built mini-IVF + `IndexConfig` | ✅ implemented + tested |
| **Dual-backend evaluation seam** | **Same** test cases through **both DeepEval and Ragas** behind neutral schemas (`run_backends`) | ✅ seam works (live smoke test) |
| Component evals (L1) | ingestion/chunking/embeddings/vector-store scored against goldens | ✅ for implemented components |
| Query routing | Rules / embedding / LLM — decides which source(s) a question hits | 🚧 scaffold (empty `router.py`) |
| Hybrid retrieval | Dense + sparse (BM25) → fuse → rerank | 🚧 scaffold (empty `retrievers/*`) |
| Source-cited generation | Cited answers from a source-aware PromptRegistry | 🚧 scaffold (empty `generation/`, `prompts/*`) |
| Pipeline assembler `build_pipeline()` | Router → retrievers → rerank → generate, one factory injected everywhere | 🚧 scaffold (empty `pipeline.py`) |
| CLI (Typer) | `ingest` / `search` / `ask` / `eval` / `prompt` / `rollback` | 🚧 scaffold (empty `cli.py`) |
| Pipeline triad (L2) + system/ops (L3) evals | Correctness, latency, cost, reliability, minimal PII | 🚧 scaffold (empty `eval_*pipeline*`/`eval_ops_*`) |
| Regression harness | Snapshots metrics, decides **PASS / REVIEW / FAIL** | 🚧 scaffold (empty `regression/*`) |
| Notebook-first dev | Loaders → chunking → embedding → (search) explored in `jupyter_notebook/` before promoting to `src/` | ✅ exercise + reference notebook |
| Web UI (Streamlit) | Chat app | 🚧 scaffold (empty `app.py`) |

> **Status note (Train-of-Truth):** `✅` = real code + passing tests (`pytest`, 102 passed). `🚧` =
> file skeleton only — its task (`doc/task/`) is not yet implemented. This README shows the
> **target architecture** with a per-capability status column so nobody mistakes a scaffold for a
> finished feature.

**Non-goals (tracked, deferred):** safety suite (scope/leakage/toxicity) + injection defense,
prompt optimization, LLM fine-tuning/DPO, CI/CD automation, observability tooling (LangSmith),
semantic caching, data-freshness/re-indexing, human-feedback loop, access control/multi-tenancy
— plus **router misroute detection, embedding-model version drift, streaming-citation integrity,
and eval-library version pinning** (added from the second architecture-review pass). See
`doc/GAP_REGISTER.md` for the committed register.

---

## 2. How it works (for a Solution Architect)

```
User Question
      │
      ▼
┌───────────────────── ROUTER ─────────────────────────┐
│  Rules/embedding/LLM: which source(s) to query?       │
│  source tags: text / web / pdf / db                   │
└──────┬───────────────────────────┬────────────────────┘
       ▼                           ▼
┌─ text source ─────────────┐  ┌─ web source ─────────────┐
│ loader→chunker            │  │ loader→chunker           │
│ index per chunk           │  │ index per chunk          │
└──────┬────────────────────┘  └──────┬───────────────────┘
       ▼                         ▼
┌──────────────── HYBRID RETRIEVAL ────────────────────┐
│  dense (cosine) + sparse (BM25) → fuse → rerank      │
│  top-k with source metadata                          │
└──────────────────────┬───────────────────────────────┘
                       ▼
┌────────────────── GENERATOR ─────────────────────────┐
│  source-aware prompt (PromptRegistry, composite key) │
│  → cited answer (source + page/url)                  │
│  → refusal_string if confidence below gate (Task 10) │
└──────────────────┬────────────────────────────────────┘
                   ▼
┌────────────── EVALUATION ────────────────────────────┐
│  One neutral sample set → DeepEval AND Ragas         │
│  (eval/contracts/ seam, run_backends)               │
│  → Report → regression PASS/REVIEW/FAIL             │
└──────────────────────────────────────────────────────┘
```

### Dual-backend evaluation seam (the post-design change)

Step 4 does **not** hard-code a single metric framework. `eval/contracts/` defines:

- **Framework-neutral schemas** — `EvalCase` (question / response / retrieved_contexts / reference),
  `MetricResult`, `Report`. Our vocabulary, not a vendor's.
- **A `MetricBackend` protocol** — the only thing a backend must expose is
  `measure(samples, metric_specs) -> Report` and `validate(metric_specs)`.
- **`run_backends(samples, metric_specs, backends=[...])`** — runs the same cases through one or
  more engines and returns `{backend_name: Report}`.
- **`get_backend("deepeval" | "ragas")`** registry in `eval/contracts/registry.py`
  (`DEFAULT_BACKEND = "deepeval"`).
- **Version pinning matters**: DeepEval is pinned (`==2.9.3`) and Ragas is floored (`>=0.3.1`,
  lockfile-resolved to 0.3.1) precisely because an upstream metric-math change would otherwise
  look identical to a real regression in the harness (Task 18) — see `GAP_REGISTER.md` §D row #27.

The four neutral metric names share the same math across engines (Ragas spells two of them
`ContextPrecision`/`ContextRecall`, DeepEval `ContextualPrecision`/`ContextualRecall`):

| Neutral spec | Meaning | DeepEval metric | Ragas (0.3.x) metric |
|---|---|---|---|
| `faithfulness` | answer grounded in retrieved context | FaithfulnessMetric | Faithfulness |
| `answer_relevancy` | answer actually responds to the question | AnswerRelevancyMetric | AnswerRelevancy (needs embeddings) |
| `context_precision` | relevant chunks ranked first | ContextualPrecisionMetric | ContextPrecision |
| `context_recall` | retrieval surfaced everything needed | ContextualRecallMetric | ContextRecall |

Both engines are driven by the **same** config-driven judge LLM (`LLM_BASE_URL` + `LLM_API_KEY`),
so swapping engines never changes where the model or endpoint comes from.

### LLMOps spine (the operating view)

Read as a system, Step 4 is an **LLMOps harness**, not just a RAG app. Each pillar maps to real
code or a committed plan:

| # | LLMOps pillar | In this repo | Status |
|---|---|---|---|
| 1 | Data & testset management | goldens (`eval/goldens/*.json`) + Ragas synthetic testset (`eval/ragas_suite/testset.py`) | ✅ |
| 2 | Prompt & template management | PromptRegistry, composite keys `prompt_id+source_type+version`, approve/rollback | 🚧 Task 10 |
| 3 | LLM-as-judge evaluation | `eval/contracts` seam, `run_backends` (DeepEval **and** Ragas), one config-driven judge | ✅ |
| 4 | Regression & quality gates | `run_suite` snapshot → `compare` PASS(0)/FAIL(1)/REVIEW(2), `metric_registry` rules, version-pin check | 🚧 Task 18 |
| 5 | Observability & SLOs | e2e + TTFT latency, cost projection, reliability, minimal PII | 🚧 Task 14 |
| 6 | Cost ladder & efficiency | cheap-routing-first; rerank/LLM-routing behind config switches | 🚧 Tasks 07/11 |
| 7 | Lifecycle (CI/CD, deploy, rollback) | registry rollback now; CI *automation* deferred to Step 7 | 🟡 |
| 8 | Safety & guardrails | minimal PII only; scope/leakage/toxicity + red-teaming deferred to Step 7 | 🟡 |

The decision record + interview Q&A for these eight pillars (written for technical managers and
solution architects) lives in §7 of [`doc/QA_DEEP_DIVES.md`](doc/QA_DEEP_DIVES.md).
Every task doc inherits a short **LLMOps framing** block naming its pillar(s), added as each task
lands — the same incremental pattern as the dual-backend eval seam.

**Key architecture decisions** (recorded in [`doc/PLAN.md`](doc/PLAN.md)):

| Decision | Rationale |
|----------|-----------|
| **Dual-backend evaluation (DeepEval + Ragas)** | DeepEval is the pytest/CI gate (threshold, minimal footprint); Ragas adds the deepest retrieval metric battery + synthetic-testset generator for Steps 5–7. One neutral seam, both engines, same judge. |
| **Framework-neutral eval schemas** | `EvalCase`/`MetricResult`/`Report` decouple our tests from any vendor so the metric framework is swappable; regressions stay stable. |
| **Judge via config (`LLM_BASE_URL` + `LLM_API_KEY`)** | Judge is decoupled from the generate LLM; generation uses Groq → Gemini fallback. Same config drives both DeepEval and Ragas. |
| **Composite prompt keys** (`prompt_id + source_type + version`) | Each source gets a tuned prompt via the shared PromptRegistry with a generic fallback; schema evolves, mechanism stays. |
| **Source metadata propagation** | Every chunk carries its source — routing, retrieval, generation, and per-source eval all depend on it; without it citations and per-source tuning break. |
| **Hybrid retrieval (dense + BM25 fusion)** | Combines semantic and lexical signals; rerank across sources only when eval shows it pays for the latency/cost. |
| **Routing: rules / embedding-sim / LLM waterfall** | Cheap strategies first, elevate to LLM classifier as needed; embedding-sim threshold ~0.45 from class (Task 06). |
| **HNSW + hand-built mini-IVF** | Production-grade Chroma HNSW behind one `IndexConfig`, plus a pedagogical IVF index; Faiss slot-in deferred. |
| **Notebook-first development** | Test loaders/chunking/embeddings/vector-store in `jupyter_notebook/` (plain LangChain cells) before promoting into `src/` — full loop documented in `doc/QA_DEEP_DIVES.md` §6. |

---

## 3. Tech stack

| Area | Tool |
|---|---|
| Language | Python ≥ 3.12 managed by `uv` |
| Embeddings | `Qwen3-Embedding-0.6B` / `Qwen3-Embedding-0.6B-ONNX` (local ONNX) |
| Vector store | ChromaDB (HNSW cosine) + hand-built mini-IVF (`vector_store/mini_ivf.py`) |
| Sparse retrieval | BM25 (`rank-bm25`) |
| Ingestion | LangChain loaders: `TextLoader`, `PyPDFLoader`, `WebBaseLoader`, `CSVLoader`, `JSONLoader` |
| LLM (generate) | Groq (primary) → Gemini (rate-limit fallback) |
| LLM (judge) | OpenAI-compatible endpoint via `LLM_BASE_URL` + `LLM_API_KEY` |
| Framework | LangChain + LangGraph-ready, Typer CLI, Streamlit |
| **Evaluation** | **DeepEval 2.9.3** + **Ragas 0.3.1** behind the `eval/contracts/` seam (eval versions pinned — see §D row #27) |
| Dev / notebook | `ipython`-ready: `ipykernel`, `ipywidgets`, `nbclient`, `nbformat` |

---

## 4. Install & run (for a Junior Developer)

Prerequisite: [Git](https://git-scm.com/) and [uv](https://docs.astral.sh/uv/).

```bash
# 1. Clone
git clone git@github.com:03dipak/step4_multi_source_rag.git
cd step4_multi_source_rag

# 2. Create env + install dependencies (runtime + dev + notebook):
uv sync

# 3. Configure secrets
cp .env.example .env
#  → edit .env: set GROQ_API_KEY, GEMINI_API_KEY, LLM_BASE_URL, LLM_API_KEY, EMBED_MODEL
```

> `.env` is git-ignored. NEVER commit it (it holds API keys).

**What you need in `.env`** (copy from `.env.example`):

| Key | Required? | Purpose |
|---|---|---|
| `GROQ_API_KEY` | yes (or Gemini) | primary generation LLM |
| `GEMINI_API_KEY` | optional | fallback on rate-limit |
| `LLM_BASE_URL` | yes | judge LLM endpoint (`<…>/v1`) |
| `LLM_API_KEY` | yes | judge LLM key |
| `LLM_MODEL` | yes | judge model id (e.g. `Qwen/Qwen2.5-7B-Instruct-AWQ`) |
| `EMBED_MODEL` | yes | embedding model id (auto-downloaded on first run) — **changing this value after the index is built requires a full re-embed; see `GAP_REGISTER.md` #25** |

### Explore in a notebook first

```bash
uv run jupyter notebook jupyter_notebook/exercise.ipynb
```

Run the cells top-to-bottom: **load** (LangChain `TextLoader`) → **chunk**
(`RecursiveCharacterTextSplitter`) → **embed** (`Qwen3-Embedding-0.6B-ONNX` via `qwen3_embed`).
`jupyter_notebook/01_indexing_explore.ipynb` is the full reference walkthrough
(loaders → all five chunk strategies → embeddings → vector store → search). Each notebook has a
SETUP cell that finds the repo root so relative `data/...` paths work no matter where you launch it.

### Web UI / CLI

The CLI (`src/multi_source_rag/cli.py`), the core pipeline assembler
(`src/multi_source_rag/pipeline/pipeline.py`), and the components they wire together
(routing, retrieval, generation) are **scaffolds pending implementation** — see the status
column in §1. What **is** ready today and fully tested:

```bash
# The implemented core: ingestion / chunking / embeddings / vector store
uv run pytest -q                      # 102 unit tests, offline
uv run pytest -m integration          # real ONNX embedding + Chroma roundtrip
```

Once the pipeline assembler lands, the CLI / UI surface below is the intended shape:

```bash
# Streamlit chat UI
uv run streamlit run app.py

# CLI surface (Typer) — pending the pipeline assembler:
uv run multi-source-rag ingest --source text --path data/documents/api_design.txt
uv run multi-source-rag ingest --source web --path data/web/fastapi_docs.md
uv run multi-source-rag ask "What API pattern does FastAPI use?"
uv run multi-source-rag search "session management" --source web
```

---

## 5. Evaluation

Step 4 evaluates the two metrics engines honestly:

1. **Real-engine smoke (integration):** `tests/integration/test_eval_backends_integration.py`
   runs the **same** `EvalCase`s through the **real DeepEval and Ragas** engines via
   `run_backends(...)` — proof both seams work against the configured judge. Skipped when no
   judge is configured.
2. **Offline component eval (unit, no network):** component evals for the implemented core
   run against goldens with injected fakes — ingestion, chunking, embeddings, vector store.

```bash
# Quality gates first
uv run pytest -q                     # unit tests (offline, no model download)
uv run ruff check src/ eval/ tests/
uv run mypy src/ eval/

# Real dual-backend smoke (needs LLM_BASE_URL + LLM_API_KEY + LLM_MODEL in .env)
uv run pytest -m integration tests/integration/test_eval_backends_integration.py

# Component evals — runnable today (ingestion / chunking / embeddings / vector store)
uv run python -m eval.deepeval_suite.ingestion.eval_ingestion
uv run python -m eval.deepeval_suite.chunking.eval_chunking
uv run python -m eval.deepeval_suite.embeddings.eval_embeddings
uv run python -m eval.deepeval_suite.vector_store.eval_index

# Pending (module skeletons only — land with Tasks 07–18):
#   L1:  eval_retriever, eval_retriever_fusion, eval_generator, eval_query
#         (eval_query MUST include a misrouted-source case — see GAP_REGISTER.md #24)
#   L2:  eval_rag_pipeline
#   L3:  eval_application, eval_ops_{latency,cost,reliability,pii}
#   Reg: regression/run_suite --baseline && regression/compare --baseline ... --all
```

### Toolchain

| Tool | Command | What it checks |
|------|---------|----------------|
| **ruff** (lint) | `uv run ruff check src/ eval/ tests/` | style + correctness lint (also lints notebook cells) |
| **mypy** (types) | `uv run mypy src/ eval/` | static typing |
| **pytest** (unit) | `uv run pytest -q` | unit tests (offline, no model download) |
| **pytest -m integration** | `uv run pytest -m integration` | real judging/embedding + Chroma roundtrip |
| **coverage** | `uv run pytest --cov --cov-report=term-missing` | code coverage per module |

**Evaluating the same cases on two engines** is the heart of the change since Step 4's design
sign-off:

```python
from eval.contracts import EvalCase, get_backend, run_backends

samples = [EvalCase(question="What does RAG combine?", response="…",
                    retrieved_contexts=["…"], reference="…")]
reports = run_backends(samples, ["faithfulness", "context_precision", "context_recall"],
                       backends=[get_backend("deepeval"), get_backend("ragas")])
print(reports["deepeval"].summary())   # {metric: score}
print(reports["ragas"].summary())
```

Golden data lives in `eval/golden.jsonl` + `eval/goldens/`; results go to `eval/results/`,
baseline snapshots to `baselines/` (git-ignored). The dual-backend decision, metric table, and
packaging notes are written up for all levels in `doc/QA_DEEP_DIVES.md` §6.

---

## 6. Project layout

```
step4_multi_source_rag/
├── app.py                     # Streamlit UI (scaffold — empty)
├── pyproject.toml             # deps (runtime + dev) + CLI entry — DeepEval/Ragas versions pinned
├── .env.example               # copy → .env, then fill keys
├── data/
│   ├── documents/             # text source documents
│   └── web/                   # web source (markdown)
├── src/multi_source_rag/      # package:
│   ├── chunking/              #   Chunker facade + 5 splitters ➜ implemented
│   ├── ingestion/             #   LangChain loaders → {text, metadata} ➜ implemented
│   ├── embeddings/            #   Embedder interface + qwen3 backend ➜ implemented
│   ├── vector_store/          #   Chroma store + mini-IVF + IndexConfig ➜ implemented
│   ├── retrievers/            #   dense/sparse/hybrid/ensemble/mmr/multi-query/self-query/
│   │                          #   parent-doc/compression/base ➜ scaffold (empty)
│   ├── query_processing/      #   router + querier ➜ scaffold (empty)
│   ├── prompts/               #   registry + adapter (composite source-aware keys) ➜ scaffold (empty)
│   ├── generation/            #   generator (cited answers, streaming) ➜ scaffold (empty)
│   ├── pipeline/              #   pipeline assembler (build_pipeline factory) ➜ scaffold (empty)
│   ├── cli.py                 #   Typer CLI (6 command groups) ➜ scaffold (empty)
│   └── config.py              #   .env-driven config (judge / generate / embed modes)
├── eval/
│   ├── contracts/             #   neutral schemas (EvalCase/Report) + MetricBackend seam + registry ➜ implemented
│   ├── deepeval_suite/        #   DeepEval backend + judge.py + component evals (ingestion/chunking/
│   │                          #   embeddings/vector-store) ➜ implemented; retriever/generation/query/
│   │                          #   pipeline/ops evals ➜ scaffold (empty)
│   ├── ragas_suite/           #   Ragas backend + synthetic-testset generator ➜ implemented
│   ├── regression/            #   metric_registry, run_suite, compare ➜ scaffold (empty)
│   ├── golden.jsonl           #   goldens + goldens/*.json
│   └── results/               #   timestamped eval reports (ignored)
├── scripts/run_all_evals.py   # orchestrates the whole eval run ➜ scaffold (empty)
├── jupyter_notebook/          # notebook-first testing: exercise + 01 indexing walkthrough
├── tests/                     # unit + integration (incl. dual-backend real-engine smoke)
└── doc/                       # PLAN, GAP_REGISTER, INTERVIEW_QA, EVAL_STUDY_MATERIAL,
    │                          #   CLASS_NOTES, QA_DEEP_DIVES, task/ (18 task docs)
```

Legend: `➜ implemented` = real code + tests; `➜ scaffold (empty)` = file skeleton only, task pending.

---

## 7. Where to go next / learn more

- **Roadmap & status:** `doc/PLAN.md`
- **Sprint plan (management view — no code):** `doc/SPRINT_PLAN.md`
- **LLMOps spine + technical-manager/architect Q&A:** `doc/QA_DEEP_DIVES.md` §7
- **Eval framework decision + metric table + packaging notes:** `doc/QA_DEEP_DIVES.md` §6
- **Step-4 concept interview prep:** `doc/INTERVIEW_QA.md`
- **Eval study material (multi-source lens):** `doc/EVAL_STUDY_MATERIAL.md`
- **Gap & deferral register (everything NOT covered, incl. verified blind spots):** `doc/GAP_REGISTER.md`
- **Class-derived mentor notes (Modules 1–3) + module interview Q&A:** `doc/CLASS_NOTES.md`
- **Code-grounded deep-dive Q&A (per task, interviewer-checks):** `doc/QA_DEEP_DIVES.md`
- **Next step:** `step5_agentic_rag` — turn the router into an agent (retrieve → grade → retry).
<!-- --- -->

# AGENTS.md — house rules & role map (Multi-Source RAG, Step 4)

## Role map (keyword → role)

Typing a trigger word at the start of a message switches the agent to that role.
Default (no keyword) = the builder role from the current session.

| Say | Role | Behavior |
|---|---|---|
| `review` / `reviewer mode` | **Reviewer** | Read-only verification. Verify every claim against the actual files (docs, tests, eval, file:line). Produce a verdict table + findings. Never edit while reviewing. External claims are checkpoints, not verdicts. |
| `writer md` / `writer` / `write docs` | **Tech writer** | Update the doc suite (README, PLAN, GAP_REGISTER, task docs, SPRINT_PLAN) following the repo's documentation conventions. Never state a count/path/line you haven't checked. |
| `mentor` / `architect` / `tech lead` | **Mentor** | Technical lead / solutions architect. Evaluate suggestions against actual repo constraints; scope discipline (named+registered gap = decision); proportionate sizing; reject mis-scoped ideas with reasons. |
| `builder` / `implement` / `code` | **Builder** (implementer) | Produce code matching the task contract (doc/task/*) — file list, key behavior, completion criteria — with tests and types. Notebook-first prototypes promoted into src/. |
| `tester` / `qa` / `eval` | **Tester** (QA/Eval) | Author L1/L2/L3 evals behind eval/contracts. Goldens include misroute (#24), conflict (#29), citation-resolution (#28). Ragas alongside DeepEval, offline-first where possible. |
| `planner` / `pm` | **Planner** (delivery lead) | Split tasks into sprintable units, dependencies, exit criteria. Execution order comes from SPRINT_PLAN.md / PLAN.md only — never invent an order that contradicts them. |
| `security` / `guardrails` | **Security & guardrails** | Track safety scope. Step-4 slice: PII minimal (Task 14), abstention gate (Task 10), per-source circuit breaker (Task 11), citation allowlist (Task 10). Step-7 items (#19/#22/#23) stay registered OUT. |
| `ops` / `sre` / `observability` | **SRE** (observability) | Latency (TTFT, P95/P99), derived cost, reliability per Task 14; early-error diagnostics side-channel + per-source health hooks. metrics-to-compute are Step 4; alerting is Step 7. |
| `data` / `ingestion` | **Data engineer** | Loaders (Task 03), chunking (Task 02), `{text, metadata}` schema, correct source tag. Re-embed migration path for EMBED_MODEL drift (#25); freshness is Row #21 (Step 7). |
| `ux` / `product` | **Product / UX** | Interface spec (Task 16): chat-log schema, batch citations after streamed text, degraded-source + abstention states, conflict surfacing. No feedback capture in Step 4. |

## Task → role quick map

Built from doc/SPRINT_PLAN.md (18 tasks, 5 sprints). Primary role is what to type;
cross-cutting roles are when the situation calls for them.

| Task | Primary | Cross-cutting |
|---|---|---|
| 01 Scaffold & judge | `builder` | `review` the judge before relying on it |
| 02 Chunking | `data` | `tester` for goldens, `review` the doc |
| 03 Ingestion | `data` | `tester` for loader cases |
| 04 Embeddings | `data` | `ops` for cost/latency notes |
| 05 Vector store + indexing | `data` | `review` before storing |
| 06 Store maintenance | `data` | `ops` for health hooks |
| 07 Retrievers (basic) | `builder` | `data` for schema constraints |
| 08 Retrievers (advanced) | `builder` | `mentor` if a new pattern is proposed |
| 09 Query routing | `builder` | `planner` (order), `tester` for misroute #24 |
| 10 Generation + "I don't know" | `builder` + `security` | `ux` for abstention surfacing |
| 11 Pipeline | `builder` + `ops` | `planner` for dependencies |
| 12 Eval component | `tester` | `review` goldens |
| 13 Eval pipeline triad | `tester` | `review` the 3 runtimes |
| 14 Eval system & ops | `ops` + `tester` | `security` for PII metric |
| 15 CLI | `builder` | `ux` for UX decisions |
| 16 Minimal UI | `ux` | `builder` to wire the engine |
| 17 Closure | `planner` + `writer md` | `ops` for baseline snapshot |
| 18 Regression watchdog | `ops` + `tester` | `planner` for gate policy |

Cross-cutting habits: end any task with `review`; fold decisions into docs with
`writer md`; use `mentor` whenever a suggestion arrives.

## House rules (all roles)

- **Verifiable claims only** — a line number, test count, or path is always checked before it is written or cited.
- **External reviews are checkpoints, not verdicts.** Verify before acting. Most review claims are already decisions.
- **Updates but no scope creep.** When a review adds genuinely-new gaps, register them with a decision (IN Step / deferred) and fold into existing tasks rather than spawning new work.
- **Keep internal links green** — renaming/reflowing a section means updating its cross-references.
- **Manager-facing docs stay code-free; task docs carry the spec.** Assume the reader cannot run anything; a runnable Verify block is included where useful.
- **No secrets.** Never write API keys / tokens into files.
<!-- --- -->

# Step 9 — LLMOps (the capstone map)

**One-line thesis:** *"Boring infra, smart gates."* Step 9 re-reads the entire journey
(step1–step8) through the LLMOps operating layer, so that LLMOps is the **spine** of the
story, not a chapter bolted on at the end.

> **House rule for this repo: agents write markdown only.** Every line of application code
> is written by you (the learner) — notebook first, then promoted into the package.
> Agents write task docs, interview Q&A, review checklists, and verdicts — never code.

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
<!-- --- -->

# AGENTS.md — house rules & role map (Step 9, LLMOps capstone)

## Non-negotiable rule for this repo

**Agents write markdown only. The learner writes every line of application code.**
Agents may: write docs, task contracts, interview Q&A, review verdicts, run read-only
checks. Agents never write code into `src/`, `tests/`, `jupyter_notebook/`, or CI workflows.

## Role map (keyword → role)

| Say | Role | Behavior here |
|---|---|---|
| `review` / `reviewer mode` | **Reviewer** | Read-only verification against actual files. Verdict table + findings. Never edits. External claims = checkpoints, not verdicts. |
| `writer md` / `writer` / `write docs` | **Tech writer** | Doc suite (README, JOURNEY_MAP, task docs, INTERVIEW_Q&A). No count/path/line stated unchecked; internal links stay green. |
| `mentor` / `architect` / `tech lead` | **Mentor** | Evaluate suggestions vs step9 + step4 reality; scope discipline; named+registered gaps are decisions. |
| `builder` / `implement` / `code` | **The learner (user)** | Notebook-first in `jupyter_notebook/`; promote into `src/llmops/` with types + tests. |
| `tester` / `qa` / `eval` | **Tester** | L1/L2 eval contracts for the learner's code; asserts inside notebooks; offline gates. |
| `planner` / `pm` | **Planner** | Module order from README / task docs only — never invented. Exit criteria per module. |
| `security` / `guardrails` | **Security** | No secrets; content-free logs; abstention + citation allowlist + circuit breaker in scope; #19/#22/#23 registered OUT. |
| `ops` / `sre` | **SRE** | Metrics-to-compute: latency, TTFT/P95, cost, reliability. Alerting/drift = Step 7. |
| `data` / `ingestion` | **Data** | `{text, metadata}` schema, source tags; corpus = self-authored step-series doc bundles (S1–S5, D14); #25 embedding-drift playbook mapped. |
| `ux` / `product` | **UX** | Chat-log schema, batch citations, abstention / degraded / conflict states; no feedback capture in Step 4/9. |

## Task → role quick map

| Mod | Primary | Cross-cutting |
|---|---|---|
| 00 Foundations | `mentor` | `writer md` for the notes contract |
| 01 Data & testset | `data` | `tester` for golden quality, `review` the corpus |
| 02 Prompts & judge | `builder`(learner) | `security` (no secrets), `review` the judge probe |
| 03 Regression gates | `tester` | `ops` for gate policy, `planner` for order |
| 04 Observability & cost | `ops` | `security` for PII metric, `data` for `where`-filter cost |
| 05 Guardrails | `security` | `ux` for abstention surfacing |
| 06 Lifecycle | `planner` + `ops` | `writer md` for the snapshot narrative |
| 07 Demo & surfacing | `ux` | `builder`(learner) wires it, `ops` for baseline-ish numbers |

## House rules (inherited from the step series)

- **Verifiable claims only** — a line number, test count, or path is checked before it is
  written or cited.
- **External reviews are checkpoints, not verdicts.**
- **Updates but no scope creep** — genuinely-new gaps get registered as decisions (IN / deferred).
- **Keep internal links green.**
- **Manager-facing docs stay code-free; task docs carry the spec.**
- **No secrets.** Never write API keys / tokens into files.
- **`data` vs `data/`** — `data` (no slash) is always the role trigger; `data/` (slash) is always the corpus folder path. Never mix the two.