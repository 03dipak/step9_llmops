<!-- Bundle S2 (D14): sources = step3_langchain_rag/README.md + step5_agentic_rag/README.md + step6_multi_agent/README.md -->

# Step 3 — LangChain RAG (Framework Comparison)

A complete, **dense-only** Retrieval-Augmented Generation (RAG) pipeline rebuilt on
**LangChain** — the same documents, embedding model, golden dataset, evaluation metrics, and
query interface as the hand-written pipeline (Step 2), so the two can be compared
apples-to-apples.

> **In one line:** prove *what a framework earns you and what it hides* by rebuilding the same
> RAG twice — by hand (Step 2) and with LangChain (this step).

---

## 1. What this is (for a Business Analyst / Product person)

**The problem:** we're deciding *when to use a framework versus writing it by hand*. That's a
business decision, not a gut call — so this step produces a **measured answer** (code volume,
debugging cost, flexibility, and whether they help or hurt eval scores).

**What this project delivers:**

| Deliverable | What it is |
|-------------|-----------|
| **RAG pipeline** | Split → Embed → Store → Retrieve → Rerank → Generate |
| **Prompt Registry** | Versioned, reviewable prompt lifecycle with eval evidence (audit trail) |
| **Evaluation harness** | 4 quality scores per query + an LLM-judged DeepEval suite |
| **CLI** | `ingest` / `search` / `ask` / `eval` + read-only `prompt` (current/list) + admin `rollback` (fail-closed, dry-run, confirm) from the terminal |
| **Web app** (Streamlit) | Chat UI + Eval Dashboard + Trace viewer |
| **Tests** | Unit + integration suites (run offline) |

**Scope (in / out):**
- ✅ **In scope:** dense retrieval, cross-encoder reranking, prompt versioning, keyword +
  LLM-judged evaluation, CLI, web app, tests.
- ❌ **Out of scope (deferred to Step 4):** hybrid dense+sparse (BM25), RRF fusion, multi-source
  routing.
- 🎯 **North star:** same data, same model, same metrics as Step 2 ⇒ the **only** difference is
  the framework, so score changes are attributable.

---

## 2. How it works (for a Solution Architect)

```
data/documents/*.txt
   │  RecursiveCharacterTextSplitter (Chroma metadata: source=basename)
   ▼
[{text, metadata}]
   │  Qwen3Embeddings.embed_documents()   (custom LangChain Embeddings)
   ▼
Chroma (persisted, cosine default)          LangChainStore.search() → {text, metadata, score}
   │                                         (scores recovered via _collection.query, 1−distance)
   ▼
Retriever.retrieve(question, top_k, min_score) → top_k dicts
   │
   ▼
Reranker.rerank(question, candidates)       (cross-encoder 2nd stage)
   │                                            ms-marco-MiniLM-L-6-v2, re-sort → top_n
   ▼
LangChainGenerator.generate(question, reranked)   (LCEL chain)
   │                                            ChatOpenAI → same Qwen as Step 2
   ▼
{ answer, sources, prompt_key, rendered_hash }    ← identical shape to Step 2
```

**The core design insight ⭐**
LangChain's `PromptTemplate` is an **adapter over a shared PromptRegistry — not the source of
truth.** The registry owns Content (template), Policy (model/temperature), and Evidence (eval
scores, run log). LangChain only *executes* the approved prompt via `LangChainPromptAdapter.build_chain(...)`.

```
Your Registry (source of truth)     LangChain (adapter)
──────────────────────────          ──────────────────
template, model, temp      ──→      PromptTemplate + ChatOpenAI
output_schema (rules)      ──→      injected into the rendered prompt
eval scores, run log       ──→      (stays in the registry)
```

Version a prompt in the registry → the LCEL chain changes with **zero code edits**. Each version
carries an **`output_schema`** (format/length/citation/refusal rules) so *how the answer is
produced* is versioned and rolled back with the prompt.

**Key architecture decisions** (recorded in `doc/notes.md`):

| Decision | Rationale |
|----------|-----------|
| **Same embedding as Step 2** (qwen3-embed, 1024-dim) | Apples-to-apples A/B — not `HuggingFaceEmbeddings`/bge |
| **Custom `Qwen3Embeddings(Embeddings)` adapter** | qwen3 isn't a HF wrapper; proper abstraction boundary; query uses instruction-aware `query_embed` |
| **Score recovery via Chroma `_collection`** | `similarity_search` hides scores; we need `min_score` + Step-2 shape |
| **Reranker = direct cross-encoder, not `ContextualCompressionRetriever`** | That API needs a `Document`-based `BaseRetriever`; our retriever is dict-shaped, and the import path isn't in the modern `langchain` split |
| **Registry + adapter for prompts** | LangChain has no versioned prompt lifecycle with eval evidence |
| **`output_schema` on each version** | The output *contract* (format/length/citations/refusal) is versioned policy → gets eval + rollback; editing it on an approved version forces re-eval (no silent change) |
| **Dense-only** | Hybrid fusion is a Step 4 concern; deferred deliberately |

---

## 3. Tech stack

| Area | Tool |
|---|---|
| Language | Python ≥ 3.12, `uv` package manager |
| Embeddings | `Qwen3-Embedding-0.6B` (ONNX, local) |
| Vector store | ChromaDB (cosine, persisted) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| LLM / judge | OpenAI-compatible endpoint (`LLM_BASE_URL`) + Groq LLM-judge |
| Framework | LangChain, LangGraph-ready, Typer CLI, Streamlit |
| Evaluation | DeepEval 2.9.3 |

---

## 4. Install & run (for a Junior Developer)

Prerequisite: [Git](https://git-scm.com/) and [uv](https://docs.astral.sh/uv/).

```bash
# 1. Clone
git clone git@github.com:03dipak/step3_langchain_rag.git
cd step3_langchain_rag

# 2. Create env + install dependencies (run + dev)
uv sync

# 3. Configure secrets
cp .env.example .env
#  → edit .env: set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, EMBED_MODEL, GROQ_API_KEY
```

> `.env` is git-ignored (holds API keys). NEVER commit it.

**What you need in `.env`:**

| Key | Required? | Purpose |
|---|---|---|
| `LLM_BASE_URL` | yes | OpenAI-compatible LLM endpoint (`<…>/v1`) |
| `LLM_API_KEY` | yes | LLM key |
| `LLM_MODEL` | yes | model id (same Qwen as Step 2, for fair comparison) |
| `EMBED_MODEL` | yes | embedding model id (auto-downloaded on first run) |
| `GROQ_API_KEY` | yes | DeepEval LLM-judge (free tier) |
| `LANGSMITH_API_KEY` | optional | LangSmith tracing |

### Run it

```bash
# CLI (ingest / search / ask / eval / prompt / rollback)
uv run langchain-rag --help
uv run langchain-rag ingest                       # chunk + embed + index data/documents
uv run langchain-rag ask "how does gradient descent work?" --top-k 2
uv run langchain-rag prompt current               # read-only: what prompt is live
uv run langchain-rag prompt list                  # read-only: versions + rollback targets
uv run streamlit run app.py                       # Web UI (Chat / Eval / Traces)

# admin, authenticated rollback (fail-closed on ADMIN_TOKEN)
uv run langchain-rag rollback --prompt RAG_ANSWER --to 1.0.0 --dry-run   # preview only
ADMIN_TOKEN=... uv run langchain-rag rollback --prompt RAG_ANSWER --to 1.0.0  # apply
```

**First run downloads models** (~60–110 MB ONNX embedder + ~23 MB reranker, cached). After that
everything runs **offline**.

---

## 5. Evaluation & quality gates

```bash
# Keyword eval (same 4 metrics as Step 2)
uv run langchain-rag eval

# DeepEval (Groq LLM-judge) suite
uv run python -m eval.deepeval_suite.eval_retriever
uv run python -m eval.deepeval_suite.eval_generator
# ...full suite in eval/deepeval_suite/

# Quality gates
uv run ruff check src tests eval app.py           # lint
uv run mypy --strict src/langchain_rag            # strict static typing
uv run pytest -v                                  # unit tests (offline, no model download)
uv run pytest -m integration                      # real embedding + Chroma roundtrip
uv run pytest --cov --cov-report=term-missing      # coverage per module
```

### Toolchain
| Tool | Command | What it checks |
|------|---------|----------------|
| **ruff** (lint) | `uv run ruff check src tests eval app.py` | style + correctness lint |
| **mypy** (types) | `uv run mypy --strict src/langchain_rag` | strict static typing |
| **pytest** (unit) | `uv run pytest -v` | unit tests (offline, no model download) |
| **pytest -m integration** | `uv run pytest -m integration` | real embedding + Chroma roundtrip |
| **coverage** | `uv run pytest --cov --cov-report=term-missing` | code coverage per module |

> **Dev/test convention:** unit tests never hit the network, never load models, never call the
> LLM (they mock the boundary). Integration tests are the only ones that load real models — and
> they share a **module-scoped embedder fixture** so a model loads **once**, not per test.

**What's checked per task (Definition of Done):** `ruff` clean, `mypy --strict` clean,
`pytest` passes offline, mentor review passed, findings recorded back in `doc/notes.md`.

---

## 6. Project layout

```
step3_langchain_rag/
├── doc/                      # 19 task specs + SUMMARY + ROADMAP + notes
├── data/
│   ├── documents/            # 4 source docs (same as Step 2)
│   └── chat_logs/            # app chat logs (gitignored)
├── eval/
│   ├── golden.jsonl          # 20 Q&A pairs (same as Step 2)
│   ├── deepeval_suite/       # Groq LLM-judged eval
│   └── results/              # timestamped eval results
├── src/langchain_rag/
│   ├── splitter.py           # RecursiveCharacterTextSplitter
│   ├── embeddings.py         # Qwen3Embeddings(Embeddings)
│   ├── vectorstore.py        # LangChain Chroma store
│   ├── retriever.py          # dict-shaped retriever
│   ├── reranker.py           # cross-encoder 2nd stage
│   ├── prompts.py            # LangChainPromptAdapter + build_llm
│   ├── generator.py          # LangChain LCEL generator
│   ├── prompt_registry.py    # versioned prompt lifecycle (shared)
│   ├── prompt_registry.json  # seeded registry: RAG_ANSWER V1.0.0/1.1.0(retired)/1.2.0(live)
│   ├── pipeline.py           # wires it all together; pipeline.ask()
│   ├── tracer.py             # LangSmith (optional)
│   ├── evaluator.py          # 4 keyword metrics (same as Step 2)
│   └── cli.py                # ingest / search / ask / eval / prompt / rollback
├── tests/                    # unit + integration
├── app.py                    # Streamlit UI
└── pyproject.toml            # uv project (deps, scripts, dev group)
```

---

## 7. Where to go next

```
1  Hand-Written RAG      ✅ step1_basic_rag
2  Eval & Tracing        ✅ step2_rag_eval
3  Framework Comparison  ◀  THIS repo (LangChain rebuild)
4  Multi-Source Routing     step4_multi_source_rag   (hybrid fusion starts here)
5  Agentic RAG (LangGraph)  step5_agentic_rag
6  Multi-Agent systems      step6_multi_agent
7  Production / guardrails  step7_deploy
```

**More:** roadmap & notes in `doc/ROADMAP.md`, `doc/SUMMARY.md`, and per-file task specs in `doc/TASK_*.md`.
<!-- --- -->

# Step 5 — Agentic RAG with LangGraph

The first four steps built a linear pipeline. This step makes it **agentic** — the system can reason, use tools, retry, and even ask for human help. This is where LangGraph enters.

> **Why this step matters:** Agentic RAG is the difference between "retrieve and hope" and "retrieve, grade, retry if needed."

---

## Learning Objectives

By completing this step, you will understand:

1. **Agentic patterns** — retrieve → grade → rewrite → retry
2. **LangGraph state graphs** — Nodes, edges, conditional routing
3. **Tool use** — LLM calling external functions (retriever, search, calculator)
4. **Human-in-the-loop** — When to ask the user for clarification
5. **State management** — Tracking decisions across the pipeline
6. **LangGraph vs hand-written** — When orchestration is worth the framework

---

## Architecture

```
START
  │
  ▼
rewrite ─────────────────────────────────────────────────┐
  │                                                       │
  ▼                                                       │
retrieve ◄──────────────────────────────────────────────┐ │
  │                                                      │ │
  ▼                                                      │ │
grade ──────────┐                                        │ │
                │                                        │ │
                ├── (score ≥ 0.7) ──→ generate ──→ END   │ │
                │                                        │ │
                ├── (score ≥ 0.4) ──→ rewrite ──────────┘ │
                │     (soft retry)                        │
                │                                        │
                └── (score < 0.4) ──→ rewrite ───────────┘
                      (hard retry)
```

---

## File Structure

```
step5_agentic_rag/
├── README.md
├── pyproject.toml
├── .env
├── .gitignore
│
├── data/
│   └── *.txt
│
├── src/agentic_rag/
│   ├── __init__.py
│   ├── state.py                ⭐ NEW: TypedDict state definition
│   ├── nodes.py                ⭐ NEW: Rewrite, retrieve, grade, generate
│   ├── edges.py                ⭐ NEW: Grade → pass/fail/retry logic
│   ├── graph.py                ⭐ NEW: LangGraph StateGraph definition
│   ├── prompt_registry.py      ← Versioned prompts (node-level, shared from Step 1)
│   └── tools.py                ⭐ NEW: Retriever, calculator, web search
│
├── app.py                      ← Streamlit with graph visualization
│
├── eval/
│   └── golden.jsonl
│
└── tests/
    ├── __init__.py
    └── test_graph.py           ← Test state transitions
```

---

## Key Concepts

### 1. State Graph (LangGraph)

```python
from langgraph.graph import StateGraph

class RAGState(TypedDict):
    question: str
    context: list[dict]
    answer: str
    grade: float
    retry_count: int

graph = StateGraph(RAGState)
graph.add_node("rewrite", rewrite_node)
graph.add_node("retrieve", retrieve_node)
graph.add_node("grade", grade_node)
graph.add_node("generate", generate_node)

graph.set_entry_point("rewrite")
graph.add_edge("rewrite", "retrieve")
graph.add_edge("retrieve", "grade")
graph.add_conditional_edges("grade", grade_decision, {
    "pass": "generate",
    "retry": "rewrite",
})
graph.add_edge("generate", END)
```

**Exam Question 🎓:** Why use a TypedDict for state? What happens if you use a regular dict?

---

### 2. Grading Node

```python
def grade_node(state: RAGState) -> RAGState:
    """Grade retrieval quality using LLM."""
    question = state["question"]
    context = state["context"]

    grade = llm.invoke(f"""Rate retrieval quality 0-1:
    Question: {question}
    Context: {context}
    Score:""")

    return {"grade": float(grade)}
```

**Exam Question 🎓:** What's the difference between LLM grading and rule-based grading (e.g., keyword overlap)?

---

### 3. Conditional Edges

```python
def grade_decision(state: RAGState) -> str:
    if state["grade"] >= 0.7:
        return "pass"
    elif state["retry_count"] < 3:
        return "retry"
    else:
        return "pass"  # Give up after 3 retries
```

**Exam Question 🎓:** Why limit retries? What happens if you don't?

---

### 4. Graph-Specific Prompts — Node-Level Versioning ⭐ NEW

Each node in the graph has its own prompt. The composite key now includes `node_name`:

#### Composite Key: `prompt_id + node_name + source_type`

```python
# Each graph node gets its own versioned prompt
GRAPH_PROMPTS = {
    # Rewrite node: improves the query before retrieval
    "REWRITE__query": {
        "prompt_id": "REWRITE",
        "node_name": "rewrite",      # ⭐ NEW: which graph node
        "source_type": None,
        "template": "Rewrite this question to be more specific: {question}",
        "status": "approved",
    },

    # Grade node: evaluates retrieval quality
    "GRADE__retrieval": {
        "prompt_id": "GRADE",
        "node_name": "grade",
        "source_type": None,
        "template": "Rate retrieval quality 0-1:\nQuestion: {question}\nContext: {context}\nScore:",
        "status": "approved",
    },

    # Generate node: creates the final answer
    "GENERATE__answer": {
        "prompt_id": "GENERATE",
        "node_name": "generate",
        "source_type": None,
        "template": "Answer from context: {context}\nQuestion: {question}\nCite sources.",
        "status": "approved",
    },
}
```

#### Lookup by Node

```python
def get_for_node(self, node_name: str, source_type: str = None) -> dict:
    """Get the approved prompt for a specific graph node."""
    for key, record in self._registry.items():
        if (record["node_name"] == node_name and
            record["source_type"] == source_type and
            record["status"] == "approved"):
            return record
    raise KeyError(f"No approved prompt for node={node_name}, source={source_type}")
```

#### Eval by Node

```python
# Now you can evaluate WHICH node is the bottleneck
node_scores = {
    "rewrite": {"quality": 0.85},      # Rewrite is good
    "grade": {"accuracy": 0.72},       # Grade is the bottleneck
    "generate": {"faithfulness": 0.88}, # Generate is good
}

# → Focus improvement on the grade node's prompt
```

**Exam Question 🎓:** The rewrite node has recall=0.90 but the grade node has accuracy=0.70. What's the problem? (Answer: the grade node is incorrectly rejecting good retrievals.)

#### The Shared Registry Strategy ⭐ (cross-cutting)

Node-level prompts are just more records in the **same shared `PromptRegistry`** built in Step 1:

1. **`node_name` / `source_type` are key dimensions, not new code** — `get_for_node()` filters the shared store; the class and lifecycle stay the same across all steps.
2. **Per-node eval gates status** — the scorecard (rewrite 0.85, grade 0.72, generate 0.88) is Evidence recorded in the registry; only an *approved* node prompt is used at run time.
3. **Status = data** — `staging` → `approved` transitions and rollbacks are `registry.json` data ops; never a code redeploy.
4. **Approved versions immutable** — a better grade-node prompt supersedes its version; never edit in place.
5. **This store is Step 7's shadow/A-B home** — candidate node prompts stay `staging` until live evidence promotes them.

---

## Exercises

1. **Build the graph** — visualize with Streamlit graphviz
2. **Test retry logic** — does it improve weak answers?
3. **Add a max retry limit** — what's a good number?
4. **Add human-in-the-loop** — when should the graph pause for user input?
5. **Compare with Step 4** — is the graph worth the complexity?
6. **Add a "refuse" node** — when no good answer exists, say so

---

## Mentor's Note 🎓

> Agentic RAG is where the system starts "thinking" instead of just "retrieving." The grade → retry loop is the simplest form of agent reasoning.
>
> Don't over-engineer. Three nodes (retrieve, grade, rewrite) is enough to understand the pattern. The complexity comes from the grading logic, not the graph.

## Exam Questions 🎓

Test yourself before moving to Step 6:

1. **State:** What information does RAGState carry? What happens if you forget a field?
2. **Grading:** LLM grading adds latency. When is it worth it vs a simple heuristic?
3. **Retry:** You retry 3 times and still get grade=0.3. What do you return to the user?
4. **Human-in-the-loop:** When should the graph pause? Give two examples.
5. **LangGraph vs hand-written:** Could you implement this graph without LangGraph? What would you lose?
6. **Prompt Registry:** Which prompts are used in the graph? How many versions do you need?

**If you can't answer 5-6, re-read the state graph and prompt registry sections.**

---

## Next Step

After completing this, move to **Step 6: Multi-Agent + LangSmith Tracing** where you'll:
- Add specialized agents (researcher, fact-checker, summarizer)
- Trace agent decisions with LangSmith
- Understand agent handoffs and collaboration

<!-- --- -->

# Step 6 — Multi-Agent + LangSmith Tracing

One agent isn't enough for complex RAG. You need a **team of agents**: a researcher, a fact-checker, a summarizer, working together. LangSmith traces their decisions so you can debug and optimize.

> **Why this step matters:** Multi-agent systems are how production RAG handles complex questions that need multiple perspectives.

---

## Learning Objectives

By completing this step, you will understand:

1. **Multi-agent architecture** — Specialized agents with different roles
2. **Agent handoffs** — How agents pass work to each other
3. **LangSmith tracing** — Observability across agent decisions
4. **Evaluation across agents** — Which agent is the bottleneck?
5. **Orchestration patterns** — Sequential vs parallel vs supervisor

---

## Architecture

```
User Question
      │
      ▼
┌─────────────────────────────────────────────────┐
│              SUPERVISOR AGENT                    │
│                                                  │
│  Analyzes question → decides which agents to use  │
│                                                  │
└──────┬──────────────┬──────────────┬────────────┘
       │              │              │
       ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ RESEARCHER  │ │ FACT-CHECKER│ │ SUMMARIZER  │
│             │ │             │ │             │
│ - Retrieves │ │ - Validates │ │ - Condenses │
│   chunks    │ │   claims    │ │   findings  │
│ - Searches  │ │ - Cross-ref │ │ - Creates   │
│   multiple  │ │   sources   │ │   final     │
│   sources   │ │             │ │   answer    │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │              │              │
       └──────────────┼──────────────┘
                      │
             ┌────────▼────────┐
             │  LANGSMITH TRACE │
             │                  │
             │  Each agent:     │
             │  - Input         │
             │  - Decision      │
             │  - Output        │
             │  - Timing        │
             │  - Token usage   │
             │                  │
             └──────────────────┘
```

---

## File Structure

```
step6_multi_agent/
├── README.md
├── pyproject.toml
├── .env
├── .gitignore
│
├── data/
│   └── *.txt
│
├── src/multi_agent/
│   ├── __init__.py
│   ├── supervisor.py           ⭐ NEW: Routes to agents
│   ├── researcher.py           ⭐ NEW: Retrieves from sources
│   ├── fact_checker.py         ⭐ NEW: Validates claims
│   ├── summarizer.py           ⭐ NEW: Condenses findings
│   ├── state.py                ← Shared state across agents
│   ├── graph.py                ← Multi-agent LangGraph
│   ├── prompt_registry.py      ← Agent prompts (bundles + owners, shared from Step 1)
│   └── tracer.py               ⭐ NEW: LangSmith integration
│
├── app.py                      ← Streamlit with agent timeline
│
├── eval/
│   └── golden.jsonl
│
└── tests/
    ├── __init__.py
    └── test_agents.py          ← Test each agent independently
```

---

## Key Concepts

### 1. Agent Roles

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| Supervisor | Decide which agents to use | User question | Agent list + order |
| Researcher | Retrieve relevant chunks | Question + sources | Context chunks |
| Fact-checker | Validate claims in chunks | Context + answer draft | Validated claims |
| Summarizer | Create final answer | Validated findings | Cited answer |

**Exam Question 🎓:** Why separate researcher from fact-checker? Can't one agent do both?

---

### 2. Agent Handoffs

```python
# Supervisor decides: use researcher + fact-checker
state["agents"] = ["researcher", "fact_checker"]

# Researcher runs first
researcher_output = researcher.run(state["question"], state["sources"])
state["context"] = researcher_output

# Fact-checker runs second
fact_checker_output = fact_checker.run(state["context"], state["draft_answer"])
state["validated_claims"] = fact_checker_output

# Summarizer creates final answer
answer = summarizer.run(state["validated_claims"], state["question"])
```

**Exam Question 🎓:** What happens if the fact-checker rejects all claims? Does the pipeline fail?

---

### 3. LangSmith Tracing

```python
import langsmith

# Each agent creates a trace
with langsmith.trace("researcher") as trace:
    trace.input = {"question": question, "sources": sources}
    result = researcher.run(...)
    trace.output = {"chunks": result}
    trace.metadata = {"chunk_count": len(result), "latency_ms": 120}

# View all traces in LangSmith dashboard
# See: which agent is slowest? which fails most?
```

**Exam Question 🎓:** What metrics does LangSmith capture for each agent? How do you use them to optimize?

---

### 5. Agent Prompt Bundling — Matched Sets ⭐ NEW

With multiple agents, each having their own prompts, you need to decide: **independent versioning or bundled promotion?**

#### The Problem

```
Researcher prompt V3 (approved)
Fact-checker prompt V1 (approved)
Summarizer prompt V2 (approved)

→ Are these tested together? Or separately?
→ If you update the researcher prompt, do you need to re-test the fact-checker?
```

#### Solution: Agent Bundles

```python
# A bundle groups agent prompts that are tested and promoted together
AGENT_BUNDLE = {
    "bundle_id": "RAG_V2",
    "description": "Full RAG pipeline V2 — all agents tested together",
    "agents": {
        "researcher": {
            "prompt_id": "RESEARCH",
            "version": "3.0.0",
            "owner": "dipak",           # ⭐ NEW: who owns this prompt
            "allowed_tools": ["retriever", "web_search"],
        },
        "fact_checker": {
            "prompt_id": "FACT_CHECK",
            "version": "1.0.0",
            "owner": "dipak",
            "allowed_tools": ["retriever"],
        },
        "summarizer": {
            "prompt_id": "SUMMARIZE",
            "version": "2.0.0",
            "owner": "dipak",
            "allowed_tools": [],
        },
    },
    "eval_scores": {
        "overall_quality": 0.87,
        "evaluated_at": "2026-08-25",
    },
    "status": "approved",   # Bundle-level status
}
```

#### Bundle Promotion

```python
def promote_bundle(self, bundle_id: str, reason: str = "") -> None:
    """Promote all prompts in a bundle together.

    All agent prompts must be in TESTING status before bundle promotion.
    This ensures the entire pipeline is tested as a matched set.
    """
    bundle = self._bundles[bundle_id]

    # Verify all agents are in TESTING
    for agent_name, agent_config in bundle["agents"].items():
        record = self.get(agent_config["prompt_id"], agent_config["version"])
        if record["status"] != "testing":
            raise ValueError(f"Agent {agent_name} not in TESTING status")

    # Promote all together
    for agent_name, agent_config in bundle["agents"].items():
        self.promote(f"{agent_config['prompt_id']}__{agent_name}")

    bundle["status"] = "approved"
```

#### Independent vs Bundled

| Approach | When to Use | Risk |
|----------|-------------|------|
| **Independent** | Agents are loosely coupled | Mismatched prompts in production |
| **Bundled** | Agents are tested as a unit | Slower promotion (all must pass) |
| **Hybrid** | Core agents bundled, peripheral independent | More complex, more flexible |

**Exam Question 🎓:** The researcher prompt V3 improves recall by 10%, but the fact-checker was tested with researcher V2. Do you promote V3? What do you need to verify first?

---

### 6. Owner & Approval Workflow ⭐ NEW

Each prompt has an owner. Only the owner (or admin) can promote.

```python
PROMPT_RECORD = {
    ...,
    "owner": "dipak",              # Who owns this prompt
    "approval_required": True,      # Does this need admin approval?
    "environment": "staging",       # Current environment (dev/staging/prod)
    "rollback_target": "2.0.0",    # Version to rollback to if needed
}
```

#### Approval Flow

```
Author creates V3 (draft)
    │
    ├── Author promotes to testing
    │
    ├── Eval runs automatically
    │
    ├── If scores improve → Author promotes to staging
    │
    └── Admin promotes to production
        (only after staging validation)
```

**Exam Question 🎓:** Why require admin approval for production? What happens if an author promotes their own prompt directly to prod?

#### The Shared Registry Strategy ⭐ (cross-cutting)

Agent bundles, owners, and approvals are the **policy layer over one shared `PromptRegistry`** — never per-step reimplementations:

1. **One store, matched sets** — bundles group prompt keys that already exist in the shared registry; `promote_bundle()` succeeds only when *all* members have the evaluated evidence to be in `staging`/`testing`, never on vibes.
2. **Status is data, enforced by policy** — `testing` → `staging` (author, on eval evidence) → `production` (owner/admin only) all mutate `registry.json`. Rollback = data flip, no redeploy.
3. **Ownership is a policy column** — `owner`, `approval_required`, `environment`, `rollback_target` live on the record; the mechanism stays cross-cutting.
4. **Approved versions are immutable** — supersede, never edit; that is what makes the `rollback_target` column meaningful.
5. **Step 7 consumes this store** — shadow/A-B mixes one approved bundle against a `staging` candidate in the same registry.

---

### 4. Evaluation Across Agents

```python
def evaluate_agent_bottleneck(eval_results):
    """Find which agent hurts overall quality."""
    for agent_name in ["researcher", "fact_checker", "summarizer"]:
        agent_scores = eval_results[f"{agent_name}_scores"]
        if agent_scores["avg_score"] < 0.5:
            print(f"Bottleneck: {agent_name}")
```

**Exam Question 🎓:** Researcher gets recall=0.9 but fact_checker gets precision=0.3. What's the problem?

---

## Exercises

1. **Build 3 agents** — researcher, fact-checker, summarizer
2. **Add LangSmith tracing** — view traces in dashboard
3. **Find the bottleneck** — which agent is slowest?
4. **Test agent handoffs** — what happens when fact-checker rejects?
5. **Add a 4th agent** (citation checker) — does it improve quality?
6. **Compare with Step 5** — is multi-agent worth the complexity?

---

## Mentor's Note 🎓

> Multi-agent systems are powerful but complex. Don't add agents unless you have a clear reason. The question to ask: "Can a single agent handle this, or do I need specialization?"
>
> LangSmith is essential here. Without tracing, you can't tell which agent is failing.

## Exam Questions 🎓

Test yourself before moving to Step 7:

1. **Agent Design:** Why separate researcher from summarizer? What happens if you combine them?
2. **Handoffs:** Agent A passes to Agent B. What information must be in the shared state?
3. **LangSmith:** A trace shows the fact-checker took 5 seconds. What do you investigate?
4. **Evaluation:** Overall score is 0.6. Researcher=0.9, fact_checker=0.4, summarizer=0.8. What do you fix?
5. **Prompt Registry:** Each agent has its own prompts. How many prompt versions do you need to track?
6. **Scalability:** You have 10 agents. Does the supervisor become a bottleneck?

**If you can't answer 4-6, re-read the evaluation and prompt registry sections.**

---

## Next Step

After completing this, move to **Step 7: Deploy + Guardrails** where you'll:
- Deploy the RAG pipeline as a web service
- Add input/output guardrails
- Handle edge cases and failures in production
