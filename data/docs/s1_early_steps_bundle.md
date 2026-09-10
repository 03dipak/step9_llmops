<!-- Bundle S1 (D14): sources = step1_basic_rag/README.md + step2_rag_eval/README.md -->

# Step 1 — Basic RAG (Hand-Written, No Framework)

Build a simple Q&A bot over a small document set. **Zero LangChain, zero LlamaIndex** — just pure Python, fastembed for embeddings, numpy for similarity, and Groq API for generation.

> **Why this step matters:** You need to feel the mechanics — chunking tradeoffs, embedding quality, retrieval failure modes — before a framework hides them from you.

---

## Learning Objectives

By completing this step, you will understand:

1. **Chunking tradeoffs** — fixed-size vs sentence-based vs semantic; overlap; chunk size impact on retrieval
2. **Embedding quality** — how embeddings capture meaning; why similar texts cluster together
3. **Retrieval failure modes** — when cosine similarity fails; keyword vs semantic mismatch
4. **Context window budgeting** — how much context fits; what happens when you exceed limits
5. **Generation grounding** — how to prompt LLM to answer from context; refusal when context is insufficient
6. **Prompt versioning** — registry, status lifecycle, approved-only lookup, audit trail ⭐ NEW

---

## Architecture

```
User Question
      │
      ▼
┌─────────────────────────────────────────────────┐
│                  PIPELINE                        │
│                                                  │
│  1. CHUNKER                                      │
│     data/*.txt → list of text chunks             │
│     Strategy: fixed-size (512 tokens)            │
│     Overlap: 50 tokens                           │
│                                                  │
│  2. EMBEDDER                                     │
│     chunks → numpy arrays (768-dim)              │
│     Model: bge-base-en-v1.5 (fastembed, local)  │
│                                                  │
│  3. STORE                                        │
│     Embeddings + chunks → in-memory numpy        │
│     Indexed for cosine similarity search          │
│                                                  │
│  4. RETRIEVER                                    │
│     question → top-k similar chunks              │
│     Method: cosine similarity                    │
│     k: 3 (configurable)                          │
│                                                  │
│  5. GENERATOR                                    │
│     question + context → LLM answer              │
│     Model: Groq llama-3.3-70b-versatile (free)  │
│     Prompt: from PROMPT_REGISTRY (approved only) │
│                                                  │
│  6. PROMPT REGISTRY ⭐                           │
│     Versioned prompts with status lifecycle       │
│     draft → testing → approved → retired          │
│     Approved-only lookup, no-overwrite guard      │
│     STATUS_HISTORY audit trail                    │
│                                                  │
└─────────────────────────────────────────────────┘
      │
      ▼
  Cited Answer
```

---

## File Structure

```
step1_basic_rag/
├── README.md                 ← YOU ARE HERE
├── pyproject.toml            ← Dependencies (uv-managed)
├── .env                      ← GROQ_API_KEY (free tier)
├── .gitignore
│
├── data/                     ← Sample documents
│   ├── python_basics.txt     ← Python fundamentals
│   ├── machine_learning.txt  ← ML concepts
│   ├── rag_concepts.txt      ← RAG explanation
│   └── api_design.txt        ← API design patterns
│
├── src/basic_rag/            ← Core implementation
│   ├── __init__.py
│   ├── chunker.py            ← Text → chunks
│   ├── embedder.py           ← Chunks → vectors
│   ├── store.py              ← In-memory vector store
│   ├── retriever.py          ← Query → top-k chunks
│   ├── generator.py          ← Context → LLM answer
│   ├── pipeline.py           ← Orchestrates all above
│   └── prompt_registry.py    ← Versioned prompts ⭐ NEW (created here → shared by Steps 2–7)
│
├── app.py                    ← Streamlit UI
│
├── tests/
│   ├── __init__.py
│   └── test_basic.py         ← Unit tests
│
└── eval/
    └── golden.jsonl          ← 20-30 Q&A pairs for eval
```

---

## Component Details

### 1. `chunker.py` — Text Chunking

**Purpose:** Split documents into smaller pieces for embedding and retrieval.

**Strategy:** Fixed-size chunking with overlap.

```
Input:  "Python is a high-level language. It supports OOP. Functions are first-class."
        (if chunk_size=10 words, overlap=3)

Output: ["Python is a high-level language. It supports OOP. Functions",
         "supports OOP. Functions are first-class. Python is a",
         "are first-class. Python is a high-level language."]
```

**Key decisions:**
| Parameter | Value | Why |
|-----------|-------|-----|
| `chunk_size` | 512 tokens | Balances context richness vs retrieval precision |
| `chunk_overlap` | 50 tokens | Prevents information loss at chunk boundaries |
| `separator` | `\n\n` | Prefer paragraph breaks over mid-sentence splits |

**Functions:**
- `chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]` — Splits text into overlapping chunks
- `chunk_file(file_path: Path) -> list[dict]` — Reads file, chunks it, returns chunks with metadata

**Failure modes to watch:**
- Chunks too small → lose context, retrieval returns fragments
- Chunks too large → dilute relevance, context window overflow
- No overlap → split sentences lose meaning across chunks

---

### 2. `embedder.py` — Text Embedding

**Purpose:** Convert text chunks into dense vector representations (768-dimensional).

**Model:** `BAAI/bge-base-en-v1.5` via fastembed (local ONNX, no API needed).

**Why fastembed:**
- Runs locally on CPU (no API calls, no cost)
- ~110 MB model, loads in ~2 seconds
- Same quality as HuggingFace transformers but faster
- No GPU required

**Functions:**
- `embed_texts(texts: list[str]) -> list[list[float]]` — Batch embed multiple texts
- `embed_query(query: str) -> list[float]` — Embed a single query

**Key insight:** Queries and documents use the same embedding model. The model learns that semantically similar texts have similar vectors, even if they use different words.

**Example:**
```
"gradient descent optimization" → [0.12, -0.34, 0.56, ...]  (768 floats)
"how does the optimizer learn"   → [0.11, -0.33, 0.55, ...]  (similar vectors!)
"what is Python"                 → [0.87, 0.12, -0.45, ...]  (different topic)
```

---

### 3. `store.py` — In-Memory Vector Store

**Purpose:** Store embeddings and enable fast similarity search.

**Implementation:** Pure numpy — no Qdrant, no Chroma, no external DB.

**Why numpy:**
- Simplest possible implementation
- No server setup needed
- Perfect for learning the mechanics
- In production, you'd swap this for Qdrant/Pinecone

**Data structure:**
```python
{
    "embeddings": np.array,  # shape: (n_chunks, 768)
    "chunks": list[str],     # original text chunks
    "metadata": list[dict],  # file source, chunk index, etc.
}
```

**Functions:**
- `add(embeddings: list[list[float]], chunks: list[str], metadata: list[dict])` — Store chunks
- `search(query_embedding: list[float], top_k: int) -> list[dict]` — Cosine similarity search
- `count() -> int` — Number of stored chunks
- `clear()` — Reset store

**Cosine similarity formula:**
```
cosine_sim(A, B) = (A · B) / (||A|| × ||B||)

Range: -1 (opposite) to 1 (identical)
Typical threshold: > 0.7 = relevant
```

**Failure modes:**
- All chunks have similar embeddings → retrieval returns random chunks
- Query is very different from any chunk → low similarity scores
- No threshold filter → irrelevant chunks returned as "relevant"

---

### 4. `retriever.py` — Top-k Retrieval

**Purpose:** Given a user question, find the most relevant chunks from the store.

**Process:**
1. Embed the query using the same model as chunks
2. Compute cosine similarity against all stored chunks
3. Sort by similarity score (descending)
4. Return top-k chunks with scores

**Functions:**
- `retrieve(query: str, top_k: int = 3) -> list[dict]` — Returns chunks with scores

**Output format:**
```python
[
    {
        "text": "Gradient descent is an optimization algorithm...",
        "score": 0.89,
        "metadata": {"source": "machine_learning.txt", "chunk_index": 5}
    },
    {
        "text": "Neural networks use gradient descent to...",
        "score": 0.82,
        "metadata": {"source": "machine_learning.txt", "chunk_index": 12}
    },
    ...
]
```

**Key decisions:**
| Parameter | Value | Why |
|-----------|-------|-----|
| `top_k` | 3 | Balances context richness vs noise |
| `score_threshold` | None | Keep all results; let generator decide |

**Failure modes:**
- `top_k` too small → miss relevant chunks
- `top_k` too large → context overflow, noise dilutes answer
- No score filtering → irrelevant chunks included

---

### 5. `generator.py` — LLM Answer Generation

**Purpose:** Take question + retrieved context, generate a cited answer.

**Model:** Groq `llama-3.3-70b-versatile` (free tier: 30 RPM, 1K RPD).

**Prompt template:**
```
You are a helpful assistant. Answer the question based ONLY on the
provided context. If the context doesn't contain the answer, say
"I don't have enough information to answer this question."

Cite your sources using [1], [2], etc. corresponding to the
context chunks provided.

CONTEXT:
[1] {chunk_1_text}
[2] {chunk_2_text}
[3] {chunk_3_text}

QUESTION: {user_question}

ANSWER:
```

**Functions:**
- `generate(question: str, context_chunks: list[dict]) -> str` — Generate answer
- `build_context(chunks: list[dict]) -> str` — Format chunks into prompt
- `refusal_response(question: str) -> str` — Generate polite refusal

**Key decisions:**
| Parameter | Value | Why |
|-----------|-------|-----|
| `max_tokens` | 1024 | Leave room for context in prompt |
| `temperature` | 0.1 | Low creativity for factual answers |
| `top_p` | 0.9 | Focus on most probable tokens |

**Failure modes:**
- LLM hallucinates beyond context → need better system prompt
- Context too long → truncated, loses relevant info
- LLM refuses to answer even when context is sufficient → prompt tuning

---

### 6. `pipeline.py` — Orchestrator

**Purpose:** Wire all components together into a single pipeline.

**Flow:**
```
load_documents(data_dir)
    → chunk all files
    → embed all chunks
    → store in vector store
    → (ready for queries)

ask(question, top_k=3)
    → embed question
    → retrieve top-k chunks
    → generate answer with context
    → return answer + citations
```

**Functions:**
- `load_documents(data_dir: Path) -> None` — Ingest all .txt files
- `ask(question: str, top_k: int = 3) -> dict` — Full pipeline
- `get_stats() -> dict` — Index stats (chunk count, file count)

**State management:**
The pipeline holds:
- `chunker` — for text splitting
- `embedder` — for vectorization
- `store` — for similarity search
- `generator` — for LLM calls

---

### 7. `prompt_registry.py` — Prompt Versioning ⭐ NEW

**Purpose:** Manage prompt templates as **immutable versioned artifacts** with lifecycle, evidence, and rollback.

**Why this matters:**
- Prompts are code — they need version control just like functions
- When you tune a prompt and answers improve, you need to know which version produced which result
- In production, you can't just overwrite a working prompt — you need approval workflow
- **Immutable versions** mean changing a template creates a new version, never overwrites

#### Three-Part Separation

Every prompt version record is split into three distinct concerns:

```
┌─────────────────────────────────────────────────────────┐
│  CONTENT  — The actual template string + variables      │
│  POLICY   — Model, temperature, tools, budget, safety   │
│  EVIDENCE — Trace, eval scores, sources, feedback       │
└─────────────────────────────────────────────────────────┘
```

**Why this matters:** When quality drops, you can answer precisely:
- "Did the template change?" → Content diff
- "Did the model change?" → Policy diff
- "Did the retriever change?" → Evidence diff (different source docs)

#### Minimum Schema (Step 1)

```python
PROMPT_VERSION_RECORD = {
    # --- CONTENT ---
    "prompt_id": "RAG_ANSWER",          # Stable identifier across versions
    "version": "1.0.0",                  # Semantic version (immutable once created)
    "template": "Answer from context: {context}\nQuestion: {question}\nAnswer:",
    "input_variables": ["context", "question"],

    # --- POLICY ---
    "model": "llama-3.3-70b-versatile",
    "temperature": 0.1,
    "max_tokens": 1024,

    # --- EVIDENCE (empty at registration, filled after eval/production use) ---
    "eval_scores": {},                   # {recall: 0.65, faithfulness: 0.85}
    "run_count": 0,                      # How many times used in production
    "last_run_at": None,

    # --- LIFECYCLE ---
    "status": "draft",                   # draft → testing → approved → retired
    "author": "dipak",
    "created_at": "2026-08-25T10:00:00",
    "change_note": "Initial version",
    "parent_version": None,              # None for V1, "1.0.0" for V2
}
```

#### Status Lifecycle

```
    ┌──────────┐
    │  DRAFT   │  ← Initial state, authoring
    └────┬─────┘
         │ promote()
         ▼
    ┌──────────┐
    │ TESTING  │  ← Under evaluation
    └────┬─────┘
         │ promote()
         ▼
    ┌──────────┐
    │ APPROVED │  ← Active, used in production
    └────┬─────┘
         │ promote()           OR    rollback(to_version="1.0.0")
         ▼                            ▼
    ┌──────────┐              ┌──────────┐
    │ RETIRED  │              │ RETIRED  │  ← Previous approved version
    └──────────┘              └──────────┘
```

**Rules:**
- `DRAFT → TESTING → APPROVED → RETIRED` (forward only)
- Cannot promote from RETIRED (terminal state)
- **Immutable:** changing a template creates a new version, never overwrites
- Every status change recorded in `STATUS_HISTORY`

#### Rollback Action

```python
def rollback(self, prompt_id: str, to_version: str) -> dict:
    """Rollback to a previous approved version.

    1. Retires the current approved version
    2. Promotes the target version back to approved
    3. Records rollback in STATUS_HISTORY with reason

    Raises:
        ValueError: If target version is not approved or doesn't exist
    """
    current = self.get_current_approved(prompt_id)
    target = self.get(prompt_id, to_version)

    # Retire current
    self._set_status(current["key"], "retired", reason=f"Rollback to {to_version}")

    # Promote target back to approved
    self._set_status(target["key"], "approved", reason=f"Rolled back from {current['version']}")

    return target
```

#### Immutable Versioning

```python
def register(self, prompt_id: str, template: str, ...) -> str:
    """Register a new version. Never overwrites existing.

    Auto-increments version: V1 → V2 → V3
    Sets parent_version to the current approved version's version.
    Returns the new version key.
    """
    current_approved = self.get_current_approved(prompt_id)
    new_version = self._increment_version(current_approved["version"])

    record = {
        "prompt_id": prompt_id,
        "version": new_version,
        "template": template,
        "parent_version": current_approved["version"] if current_approved else None,
        "status": "draft",
        ...
    }
    self._store(record)
    return f"{prompt_id}_V{new_version}"
```

#### Functions

```python
class PromptRegistry:
    """Versioned prompt registry with immutable versions and rollback."""

    def register(self, prompt_id: str, template: str, input_variables: list[str],
                 model: str = "llama-3.3-70b-versatile", temperature: float = 0.1,
                 change_note: str = "") -> str:
        """Register a new version. Never overwrites. Auto-increments version.
        Returns the new version key (e.g., 'RAG_ANSWER_V2')."""

    def get(self, prompt_id: str, *, version: str = None, approved_only: bool = True) -> dict:
        """Get a prompt version.
        If version=None + approved_only=True → return current approved version.
        If version specified → return that exact version regardless of status."""

    def promote(self, key: str, reason: str = "") -> dict:
        """Promote a prompt to the next status.
        DRAFT → TESTING → APPROVED → RETIRED
        Raises ValueError for invalid transitions."""

    def rollback(self, prompt_id: str, to_version: str, reason: str = "") -> dict:
        """Rollback to a previous approved version.
        Retires current, promotes target, records in STATUS_HISTORY."""

    def list_versions(self, prompt_id: str) -> list[dict]:
        """List all versions of a prompt. Returns sorted by version."""

    def get_status_history(self, key: str) -> list[dict]:
        """Get audit trail of status changes."""

    def snapshot(self) -> dict:
        """Export entire registry state for backup/audit."""
```

#### Runtime Logging (What Happens When a Prompt Is Used)

Every time a prompt is used, log:

```python
RUN_LOG = {
    "run_id": "run_20260825_143022",
    "prompt_key": "RAG_ANSWER_V2",
    "prompt_version": "1.1.0",
    "rendered_hash": "a3f2b1...",        # SHA-256 of the rendered prompt
    "model": "llama-3.3-70b-versatile",
    "retrieved_doc_ids": ["chunk_1", "chunk_5"],
    "output": "Gradient descent is...",
    "latency_ms": 1200,
    "token_usage": {"input": 450, "output": 200},
    "error": None,
    "timestamp": "2026-08-25T14:30:22",
}
```

**Why this matters:** If a bad answer appears, you can trace it back to the exact prompt version, model config, and retrieved documents that produced it.

#### STATUS_HISTORY Audit Trail

```python
STATUS_HISTORY = [
    {
        "key": "RAG_ANSWER_V1",
        "from_status": None,
        "to_status": "draft",
        "timestamp": "2026-08-25T10:00:00",
        "reason": "Initial registration",
    },
    {
        "key": "RAG_ANSWER_V1",
        "from_status": "draft",
        "to_status": "testing",
        "timestamp": "2026-08-25T11:00:00",
        "reason": "Ready for eval",
    },
    {
        "key": "RAG_ANSWER_V1",
        "from_status": "testing",
        "to_status": "approved",
        "timestamp": "2026-08-25T12:00:00",
        "reason": "Eval scores: recall=0.72, faithfulness=0.88",
    },
]
```

#### How Generator Uses the Registry

```python
class Generator:
    def __init__(self, llm, registry: PromptRegistry):
        self.llm = llm
        self.registry = registry

    def generate(self, question: str, context_chunks: list[dict]) -> str:
        # Get approved prompt from registry
        prompt_config = self.registry.get("RAG_ANSWER_V1", approved_only=True)
        prompt_template = prompt_config["prompt"]

        # Format with context
        context = self.build_context(context_chunks)
        prompt = prompt_template.format(context=context, question=question)

        # Generate
        return self.llm.generate(prompt)
```

#### Why Not Just Hardcode Prompts?

| Hardcoded | With Registry |
|-----------|---------------|
| "I'll just change the prompt string" | Immutable versions — changing creates V2, V1 preserved |
| No record of what worked | Eval scores + runtime logs linked to version |
| Overwrite risk (break production) | No-overwrite guard, approval workflow, rollback |
| Can't compare prompt versions | List all versions, compare side-by-side |
| "Which prompt produced this answer?" | Full evidence: prompt hash + model + retrieved docs |
| "Why did quality drop?" | Three-part separation: Content / Policy / Evidence |

#### The Shared Registry Strategy ⭐ (cross-cutting)

> The `PromptRegistry` is not a Step 1 feature — it is a **cross-cutting component that now belongs to every step**. You build it **once** here, then import (never re-copy) it in Steps 2–7.

**Five rules that hold from this step forward:**

1. **Lives outside any single step** — the registry is shared code; every step imports the same module and only adds *records and policy*, never a new implementation.
2. **Code ≠ Data** — the *mechanism* (the `PromptRegistry` class, git-versioned) is separate from the *state* (`registry.json`). `promote()` / `rollback()` only flip data fields, so a rollback is a **data operation, not a code redeploy**.
3. **Evidence-driven transitions** — a version only becomes `approved` after recorded eval evidence says it won. Step 2 adds that scoring; Steps 4–6 add source-, node-, and agent-level evidence.
4. **Approved versions are immutable** — never edit an approved template. Add a newer version and supersede it; this is what keeps rollback and eval history meaningful.
5. **Backing store for shadow/A-B (Step 7)** — candidates live as `draft`/`staging` records in this same store until live evidence promotes them.

```python
# Same class, everywhere — imported, never duplicated:
from prompt_registry import PromptRegistry        # shared module (all steps)

# State lives in registry.json — rollback = point the data back one version
registry.rollback("RAG_ANSWER", reason="V2 regressed in production")
```

---

### 8. `app.py` — Streamlit UI

**Features:**
- Chat interface with message history
- Sidebar: chunk_size, top_k sliders
- Source citations with expandable details
- Index stats (total chunks, files)
- Clear chat button

**Layout:**
```
┌──────────────────────────────────────────┐
│  📚 Basic RAG Assistant                  │
│  Ask questions about the documents.      │
├──────────────┬───────────────────────────┤
│  Sidebar     │  Chat Area                │
│  - Chunk size│  [User: What is RAG?]     │
│  - Top-k     │  [Bot: RAG combines...]   │
│  - Index info│  📎 Sources [expand]      │
│  - Clear     │                           │
└──────────────┴───────────────────────────┘
```

---

## Tech Stack (All Free)

| Component | Tool | Cost | Why |
|-----------|------|------|-----|
| **Embeddings** | fastembed `bge-base-en-v1.5` | Free (local) | No API needed, 768-dim, CPU |
| **Vector Store** | numpy cosine similarity | Free (local) | Simplest possible, no server |
| **LLM** | Groq `llama-3.3-70b-versatile` | Free (30 RPM) | 200-350 tok/s, 70B quality |
| **UI** | Streamlit | Free | Browser-based chat |
| **Package Manager** | uv | Free | Fast Python package manager |

---

## Setup

```bash
# Create virtual environment
cd step1_basic_rag
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"

# Set up API key
cp .env.example .env
# Edit .env: GROQ_API_KEY=gsk_...

# Ingest documents
uv run python -c "from basic_rag.pipeline import load_documents; load_documents('data')"

# Run UI
uv run streamlit run app.py
```

---

## Sample Data

| File | Content | Chunks (approx) |
|------|---------|-----------------|
| `python_basics.txt` | Variables, lists, dicts, functions, classes, error handling | ~12 |
| `machine_learning.txt` | Supervised/unsupervised learning, neural networks, training | ~15 |
| `rag_concepts.txt` | Chunking, embeddings, vector DB, retrieval, reranking | ~18 |
| `api_design.txt` | REST design, auth, rate limiting, versioning, error handling | ~14 |

**Total: ~60 chunks** — small enough to test quickly, large enough to see retrieval behavior.

---

## What You'll Learn

### Chunking Tradeoffs
- **Too small (100 tokens):** Retrieval returns fragments, LLM lacks context
- **Too large (2000 tokens):** Multiple topics in one chunk, dilutes relevance
- **Sweet spot (500 tokens):** One concept per chunk, enough context for answer

### Embedding Quality
- **Semantic similarity works:** "gradient descent" matches "optimization algorithm"
- **Keyword mismatch fails:** "how does it learn" might not match "training process" well
- **Domain specificity:** General embeddings work okay for technical text

### Retrieval Failure Modes
- **No relevant chunk in top-k:** Question too specific for document set
- **Multiple similar chunks:** Redundant information wastes context budget
- **Low similarity scores:** All chunks are somewhat relevant, none are great

### Generation Grounding
- **"Answer from context only"** reduces hallucination
- **Refusal when insufficient** prevents wrong answers
- **Citations [1][2]** trace answer to source chunks

---

## Comparison with Later Steps

| Aspect | This Step | With LangChain | With LangGraph |
|--------|-----------|----------------|----------------|
| Code volume | ~250 lines | ~80 lines | ~150 lines |
| Debugging | Easy (see everything) | Hard (framework internals) | Medium |
| Flexibility | Full control | Limited by abstractions | Full control + orchestration |
| Prompt versioning | ✅ Built-in registry | LangChain PromptTemplate | Same + graph orchestration |
| Learning value | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Production ready | No | Yes | Yes |

---

## Exercises

1. **Change chunk_size** to 200 and 1000 — how does retrieval quality change?
2. **Change top_k** to 1 and 10 — what happens to answer quality?
3. **Add a score threshold** (e.g., 0.5) — does refusing low-score chunks improve answers?
4. **Try a question** about something NOT in the docs — does the refusal work?
5. **Add a 5th document** — does the pipeline handle multiple sources?
6. **Create a V2 prompt** — register it as DRAFT, run eval, compare with V1, promote if better ⭐ NEW
7. **Try to overwrite an APPROVED prompt** — does the no-overwrite guard work? ⭐ NEW
8. **Check STATUS_HISTORY** — does it record all transitions correctly? ⭐ NEW

---

## Next Step

Before moving on, **validate the happy path** in the current app with questions drawn from the docs (things that should score ≥ 0.5 and return cited answers):

| Topic | Example questions |
|-------|-------------------|
| RAG | "What is Retrieval-Augmented Generation?", "What is hybrid retrieval?", "How is retrieval quality evaluated?" |
| API | "What HTTP status codes should I use?", "What are the authentication methods?", "How do I implement rate limiting?" |
| ML | "What is gradient descent?", "What is overfitting and how to prevent it?" |
| Python | "What is a decorator in Python?", "What is the difference between a list and a tuple?" |
| Negative tests | "What is the capital of France?" (not in docs → should refuse) |

## Recommended Direction for Step 2: Real Chat-Log RAG (user-driven)

The production goal is a **company RAG chatbot over historical chat logs** (past customer-service/support conversations). Step 1 uses generic `.txt` docs; Step 2 should center the evaluation on **real chat history** so we measure performance on the actual use case, not toy data. Plan:

1. **Add a sample chat-log dataset + loader** — e.g. `data/chat_logs/` (CSV/JSON of conversations: `{user_query, agent_response, timestamp, category}`) plus a `load_chat_logs()` ingestion path so the index answers from real chat history.
2. **Build the LangSmith eval harness around that** — a golden set of Q&A pairs over the chat logs; measure retrieval precision/recall and answer faithfulness on the chat-log index (not just the tutorial docs).
3. Keep existing Step 2 goals, now grounded in the chat-log scenario:
   - Add a golden dataset (20-30 Q&A pairs **from chat logs**)
   - Measure retrieval precision/recall
   - Add LangSmith tracing
   - Link prompt versions to eval scores
   - Identify why answers go wrong

This makes each later step map directly to the production chatbot (see roadmap):

| Step | Contribution to the chat-log bot |
|------|----------------------------------|
| 1 (now) | Core RAG mechanics |
| 2 (next) | Eval harness over real chat logs + tracing |
| 3 | Custom vs LangChain gap analysis |
| 4 | Route across chat-log / docs / FAQ indexes |
| 5 | Self-correction + clarifying questions |
| 6 | Specialized agents (history retriever, escalation) |
| 7 | Rate limits, fallbacks, cost controls, deploy |

---

## Mentor's Note 🎓

> This step builds the foundation. Every concept here (chunking, embedding, retrieval, generation, prompt versioning) will be tested in later steps. Don't rush — understand **why** each component exists.
>
> The prompt registry is not optional. It's the difference between "I tried some prompts" and "I systematically improved prompts with version control." Interviewers notice this.

## Exam Questions 🎓

Test yourself before moving to Step 2:

1. **Chunking:** Why does chunk_size=200 perform worse than chunk_size=500 for retrieval?
2. **Embeddings:** Why do "gradient descent" and "optimization algorithm" have similar vectors?
3. **Retrieval:** When does cosine similarity fail? Give an example.
4. **Generation:** Why does the system prompt say "answer from context only"?
5. **Prompt Registry:** What happens if you try to promote a RETIRED prompt?
6. **Prompt Registry:** Why is no-overwrite guard important for production?
7. **Prompt Registry:** What's the difference between `get(key)` and `get(key, approved_only=True)`?

**If you can't answer 5-7, re-read the prompt_registry.py section.**

<!-- --- -->

# Step 2 — RAG with Evaluation + LangSmith Tracing

Same RAG as Step 1, but now with **evaluation** and **tracing**. Add a golden dataset (20-30 Q&A pairs), measure retrieval precision/recall, measure answer quality, and use LangSmith to trace what actually gets retrieved and why answers go wrong.

> **Why this step matters:** This is where most people skip a step and later can't debug production RAG. Tracing early builds the instinct.

---

## Quickstart (clone → run in ~2 min)

```bash
# Prerequisites: git, uv (https://docs.astral.sh/uv/) — Python 3.12+

git clone https://github.com/03dipak/step2_rag_eval.git
cd step2_rag_eval

uv sync                       # installs deps (incl. dev group: deepeval, qwen3-embed, ruff, pytest)
cp .env.example .env         # then fill in your GROQ_API_KEY (+ optional LANGSMITH_API_KEY)

uv run streamlit run app.py  # Chat + Eval Dashboard + Traces
```

First run of `app.py` (or `evaluate.py`) downloads the embedding model and builds the index — that's expected; subsequent runs are fast. See [Setup](#setup) for the full detail.

---

## Learning Objectives

By completing this step, you will understand:

1. **Evaluation metrics** — Context Recall, Context Precision, Faithfulness, Answer Relevance
2. **Golden datasets** — How to curate Q&A pairs for evaluation
3. **Failure analysis** — Using traces to understand WHY answers are wrong
4. **LangSmith tracing** — Observability for RAG pipelines
5. **Iterative improvement** — How to use eval results to improve chunking, retrieval, generation
6. **Prompt registry + eval** — Track which prompt version produced which scores ⭐ NEW

---

## Architecture

```
                    ┌─────────────────────────┐
                    │    Golden Dataset        │
                    │    (20-30 Q&A pairs)     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     EVALUATION           │
                    │                          │
                    │  For each Q&A pair:      │
                    │  1. Run pipeline         │
                    │  2. Compare retrieval    │
                    │  3. Compare answer       │
                    │  4. Log prompt version   │ ⭐ NEW
                    │  5. Log to LangSmith     │
                    │                          │
                    └────────────┬────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Context Recall  │  │   Faithfulness  │  │Answer Relevance │
│                 │  │                 │  │                 │
│ Did we retrieve │  │ Is the answer  │  │ Does it answer  │
│ the right chunks│  │ supported by   │  │ the actual      │
│ for this question│  │ the context?   │  │ question?       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     PROMPT REGISTRY ⭐   │
                    │                          │
                    │  Eval results linked to  │
                    │  prompt version:         │
                    │                          │
                    │  V1 (approved):          │
                    │    recall: 0.65          │
                    │    faithfulness: 0.85    │
                    │                          │
                    │  V2 (draft):             │
                    │    recall: 0.78          │
                    │    faithfulness: 0.91    │
                    │                          │
                    │  → Promote V2 if better  │
                    │                          │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     LangSmith Traces     │
                    │                          │
                    │  Each evaluation run:    │
                    │  - Input question        │
                    │  - Retrieved chunks      │
                    │  - LLM prompt (version)  │ ⭐ NEW
                    │  - Generated answer      │
                    │  - Scores                │
                    │  - Timing                │
                    │                          │
                    └─────────────────────────┘
```

---

## File Structure

```
step2_rag_eval/
├── README.md                 ← YOU ARE HERE
├── pyproject.toml
├── .env
├── .gitignore
│
├── data/
│   ├── documents/            ← Source documents (same as step1)
│   │   ├── python_basics.txt
│   │   ├── machine_learning.txt
│   │   ├── rag_concepts.txt
│   │   └── api_design.txt
│   ├── golden.jsonl          ← 20-30 Q&A pairs for evaluation
│   └── chat_logs/            ← App-persisted chat logs (gitignored *.jsonl) + sample CSVs
│
├── src/rag_eval/
│   ├── __init__.py
│   ├── chunker.py            ← Text → chunks
│   ├── embedder.py           ← Chunks → vectors
│   ├── store.py              ← In-memory vector store
│   ├── retriever.py          ← Query → top-k chunks
│   ├── generator.py          ← Context → LLM answer
│   ├── pipeline.py           ← Full RAG pipeline
│   ├── prompt_registry.py    ← Versioned prompts ⭐ NEW (shared from Step 1)
│   ├── evaluator.py          ← Evaluation metrics ⭐ NEW
│   └── tracer.py             ← LangSmith integration ⭐ NEW
│
├── app.py                    ← Streamlit UI with eval dashboard
│
├── eval/
│   ├── deepeval_suite/       ← LLM-judged evaluation (Groq) ⭐ NEW
│   │   ├── judge.py          ← GroqJudge (DeepEvalBaseLLM)
│   │   └── evaluate.py       ← DeepEval metrics runner
│   └── results/              ← Timestamped eval results
│
└── tests/
    ├── __init__.py
    └── test_eval.py          ← Tests for evaluation metrics
```

---

## Component Details

### 1. `evaluator.py` — Evaluation Metrics ⭐ NEW

**Purpose:** Measure pipeline quality using standardized RAG metrics.

#### Metric 1: Context Recall

**Definition:** What fraction of the gold answer's key points are covered by the retrieved chunks?

```
Gold answer mentions: [chunking, embeddings, vector DB]
Retrieved chunks cover: [chunking, embeddings]
Context Recall = 2/3 = 0.67
```

**Implementation (keyword-based):**
```python
def context_recall(gold_answer: str, retrieved_chunks: list[str]) -> float:
    gold_keywords = extract_keywords(gold_answer)
    context_text = " ".join(retrieved_chunks)
    covered = sum(1 for kw in gold_keywords if kw in context_text)
    return covered / len(gold_keywords) if gold_keywords else 0.0
```

**Implementation (LLM-based, more accurate):**
```python
def context_recall_llm(gold_answer: str, retrieved_chunks: list[str]) -> float:
    prompt = f"""
    For each statement in the gold answer, check if it's supported
    by the retrieved context. Return a JSON list of booleans.

    Gold answer: {gold_answer}
    Context: {retrieved_chunks}

    Return: [true, false, true, ...]
    """
    # LLM judges each statement
```

**Target:** ≥ 0.7 (70% of gold answer points should be in retrieved chunks)

---

#### Metric 2: Context Precision

**Definition:** What fraction of the retrieved chunks are actually relevant to the question?

```
Retrieved 3 chunks:
  [1] Relevant (score: 0.89)
  [2] Relevant (score: 0.82)
  [3] Irrelevant (score: 0.45)

Context Precision = 2/3 = 0.67
```

**Implementation:**
```python
def context_precision(question: str, retrieved_chunks: list[dict], gold_source: str) -> float:
    relevant = 0
    for chunk in retrieved_chunks:
        if chunk["metadata"]["source"] == gold_source:
            relevant += 1
    return relevant / len(retrieved_chunks) if retrieved_chunks else 0.0
```

**Target:** ≥ 0.6 (60% of retrieved chunks should be relevant)

---

#### Metric 3: Faithfulness

**Definition:** Is every claim in the generated answer supported by the retrieved context?

```
Answer: "Python is dynamically typed and supports OOP."
Context mentions: "dynamically typed" ✓, "object-oriented" ✓
Faithfulness = 1.0 (all claims supported)

Answer: "Python was created in 1991 by Guido van Rossum."
Context doesn't mention creation date
Faithfulness = 0.5 (one claim unsupported)
```

**Implementation (LLM-based):**
```python
def faithfulness(answer: str, context_chunks: list[str]) -> float:
    prompt = f"""
    For each claim in the answer, check if it's supported
    by the context. Return a JSON list of booleans.

    Answer: {answer}
    Context: {context_chunks}

    Return: [true, false, true, ...]
    """
    # LLM judges each claim
```

**Target:** ≥ 0.8 (80% of answer claims should be grounded)

---

#### Metric 4: Answer Relevance

**Definition:** Does the generated answer actually address the question?

**Implementation (question regeneration):**
```python
def answer_relevance(question: str, answer: str) -> float:
    # Ask LLM to regenerate the question from the answer
    regenerated = llm.generate(f"Generate a question that this answer addresses: {answer}")
    # Compute similarity between original and regenerated question
    original_emb = embed(question)
    regenerated_emb = embed(regenerated)
    return cosine_similarity(original_emb, regenerated_emb)
```

**Target:** ≥ 0.7 (answer should be relevant to the question)

---

#### Combined Score

```python
def evaluate_single(question: str, gold_answer: str, gold_source: str, pipeline) -> dict:
    result = pipeline.ask(question)

    return {
        "question": question,
        "context_recall": context_recall(gold_answer, result["chunks"]),
        "context_precision": context_precision(question, result["chunks"], gold_source),
        "faithfulness": faithfulness(result["answer"], result["chunks"]),
        "answer_relevance": answer_relevance(question, result["answer"]),
    }
```

---

### 2. `tracer.py` — LangSmith Integration ⭐ NEW

**Purpose:** Trace every pipeline execution for debugging and analysis.

**What LangSmith captures:**
```
┌─────────────────────────────────────────────────┐
│ LangSmith Trace                                 │
│                                                 │
│ Input: "What is RAG?"                           │
│                                                 │
│ Steps:                                          │
│ 1. Chunker: 4 files → 60 chunks                │
│    Duration: 0.12s                              │
│                                                 │
│ 2. Embedder: 1 query → 1024-dim vector           │
│    Duration: 0.08s                              │
│                                                 │
│ 3. Retriever: 60 chunks → top 3                 │
│    [chunk_12, score: 0.89]                      │
│    [chunk_34, score: 0.82]                      │
│    [chunk_07, score: 0.75]                      │
│    Duration: 0.01s                              │
│                                                 │
│ 4. Generator: prompt → answer                   │
│    Prompt tokens: 850                           │
│    Completion tokens: 256                       │
│    Duration: 1.2s                               │
│                                                 │
│ Output: "RAG combines retrieval with generation"│
│ Total duration: 1.41s                           │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Setup:**
```python
# tracer.py
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-langsmith-key"
os.environ["LANGCHAIN_PROJECT"] = "step2-rag-eval"

# In pipeline.py, wrap each step with tracing
from langsmith import traceable

@traceable(name="retrieve")
def retrieve_with_trace(query: str, top_k: int):
    # retrieval logic
    pass
```

**Free tier:** LangSmith offers 5,000 traces/month free. More than enough for learning.

**What you'll see in LangSmith dashboard:**
- Timeline view of each pipeline execution
- Input/output for each step
- Latency breakdown
- Token usage
- Error traces

---

### 3. `golden.jsonl` — Evaluation Dataset

**Format:** JSON Lines (one JSON object per line)

```json
{"question": "What is Python?", "answer": "Python is a high-level, interpreted programming language known for its simplicity and readability.", "source": "python_basics.txt", "difficulty": "easy"}
{"question": "How does gradient descent work?", "answer": "Gradient descent minimizes a loss function by iteratively updating model parameters in the direction of steepest descent.", "source": "machine_learning.txt", "difficulty": "medium"}
{"question": "What is the difference between RAG and fine-tuning?", "answer": "RAG retrieves external documents for context, while fine-tuning updates model weights. RAG is cheaper and allows knowledge updates without retraining.", "source": "rag_concepts.txt", "difficulty": "hard"}
```

**Fields:**
| Field | Purpose |
|-------|---------|
| `question` | The input question |
| `answer` | Gold standard answer |
| `source` | Which document contains the answer |
| `difficulty` | easy/medium/hard (for stratified eval) |

**Target:** 20-30 pairs covering:
- 10 easy (direct fact lookup)
- 10 medium (requires understanding)
- 5-10 hard (multi-hop reasoning, cross-document)

---

### 4. Evaluation Runner (`evaluator.py`)

**Purpose:** Run all Q&A pairs through the pipeline and collect metrics. This lives in `src/rag_eval/evaluator.py` (`run_full_eval`), and is invoked from the Streamlit **Eval Dashboard** tab ("Run Evaluation" button).

```python
def run_full_eval(pipeline, golden_path: str) -> dict:
    results = []
    with open(golden_path) as f:
        for line in f:
            qa = json.loads(line)
            metrics = evaluate_single(
                qa["question"],
                qa["answer"],
                qa["source"],
                pipeline,
            )
            results.append(metrics)

    return {
        "results": results,
        "summary": {
            "context_recall_avg": mean([r["context_recall"] for r in results]),
            "context_precision_avg": mean([r["context_precision"] for r in results]),
            "faithfulness_avg": mean([r["faithfulness"] for r in results]),
            "answer_relevance_avg": mean([r["answer_relevance"] for r in results]),
        },
        "timestamp": datetime.now().isoformat(),
    }
```

**Output:** Saved to `eval/results/<timestamp>.json` via the app's **"Run Evaluation"** button. The original empty `eval/run_eval.py` script was removed as unused (the suite runs from the app or `eval/deepeval_suite/evaluate.py`).

---

### 4a. `eval/deepeval_suite/` — DeepEval LLM-Judged Metrics ⭐ NEW

**Purpose:** Add an **LLM-as-judge** evaluation layer. The keyword-based `evaluator.py` metrics are fast and offline, but DeepEval's metrics use a judge LLM to reason about answer/context quality — more accurate, at the cost of API calls.

**Judge: Groq (free tier).** The suite uses `openai/gpt-oss-120b` — the only freely-accessible model verified on this Groq account. The free tier is TPM-limited (~8000 tokens/min), so judge calls are serialized through a shared async semaphore (`JUDGE_MAX_CONCURRENT`, default `1`) and 429s are retried (up to 10×) sleeping the exact retry-after seconds parsed from the error message.

| File | Purpose |
|------|---------|
| `eval/deepeval_suite/judge.py` | `GroqJudge` — `DeepEvalBaseLLM` adapter over Groq, schema-aware output parsing, TPM-aware rate-limit handling |
| `eval/deepeval_suite/evaluate.py` | Builds `LLMTestCase`s from `golden.jsonl`, runs DeepEval metrics, persists results to `eval/results/deepeval_*.json` |

**Metrics:** `ContextualRecallMetric`, `ContextualPrecisionMetric`, `FaithfulnessMetric` (threshold `0.7`, `include_reason` toggle via `--no-reason`).

**Run:**
```bash
uv run python eval/deepeval_suite/evaluate.py --k 3 --limit 2 --no-reason
```
- `--k N` — chunks retrieved per query (default 3)
- `--limit N` — only first N golden entries (the free TPM quota can't fit a full 20-case × 3-metric run in one window; use a small limit)
- `--no-reason` — skip per-score reasoning strings to roughly halve output tokens (default in the app UI)

**Dependencies:** `uv add deepeval langchain-core langchain-groq` (resolves to `deepeval 2.9.3`, which coexists with qwen3-embed).

**In the app:** the Eval Dashboard tab has a "DeepEval (LLM-judged via Groq)" expander with `top_k`, a case-limit input, and a "Skip per-score reasoning" checkbox plus a **Run DeepEval** button. Because Streamlit script threads can't import DeepEval (its `signal.signal()` calls need the main thread), the button launches `evaluate.py` as a **subprocess** and renders the persisted summary in a "DeepEval Results" section.

See `doc/TASK_15_DEEPEEVAL.md` for full details.

---

### 5. `prompt_registry.py` — Prompt Registry + Runtime Evidence ⭐ NEW

**Purpose:** Track which prompt version produced which results — eval scores AND runtime evidence.

#### Three-Part Separation in Action

```
CONTENT (what changed)
  V1: "Answer from context: {context}"
  V2: "Answer ONLY from context: {context}. Cite sources."

POLICY (how it runs)
  V1: model=llama-3.3-70b, temperature=0.1
  V2: model=llama-3.3-70b, temperature=0.05  ← lower temp

EVIDENCE (what happened)
  V1: eval_scores={recall: 0.65, faithfulness: 0.85}, run_count=142
  V2: eval_scores={recall: 0.78, faithfulness: 0.91}, run_count=38
```

**The debugging question:** "Why did quality drop?"
- Content changed? → Compare templates
- Policy changed? → Compare temperature/model
- Evidence changed? → Compare retrieved documents (different corpus?)

#### Eval-Linked Records (from Step 1 schema, now with evidence)

```python
# V1: retired after eval showed V2 is better
{
    "prompt_id": "RAG_ANSWER",
    "version": "1.0.0",
    "template": "Answer from context: {context}\nQuestion: {question}",
    "input_variables": ["context", "question"],
    "model": "llama-3.3-70b-versatile",
    "temperature": 0.1,
    "status": "retired",
    "parent_version": None,
    "eval_scores": {
        "context_recall": 0.65,
        "faithfulness": 0.85,
        "evaluated_at": "2026-08-25T12:00:00",
        "eval_run_id": "eval_20260825_120000",
    },
    "run_count": 142,           # ⭐ NEW: how many times used
    "last_run_at": "2026-08-25T12:00:00",
}

# V2: promoted after better eval scores
{
    "prompt_id": "RAG_ANSWER",
    "version": "1.1.0",
    "template": "Answer ONLY from context: {context}. Cite [1], [2].",
    "input_variables": ["context", "question"],
    "model": "llama-3.3-70b-versatile",
    "temperature": 0.05,       # ⭐ NEW: different policy
    "status": "approved",
    "parent_version": "1.0.0",
    "eval_scores": {
        "context_recall": 0.78,
        "faithfulness": 0.91,
        "evaluated_at": "2026-08-25T14:00:00",
        "eval_run_id": "eval_20260825_140000",
    },
    "run_count": 38,
    "last_run_at": "2026-08-25T16:30:00",
}
```

#### Runtime Evidence Log (new in Step 2)

Every pipeline run logs evidence that ties back to the prompt version:

```python
RUN_LOG_ENTRY = {
    "run_id": "run_20260825_143022",
    "prompt_key": "RAG_ANSWER_V2",         # Which version was used
    "rendered_hash": "a3f2b1c4d5e6...",    # SHA-256 of the rendered prompt
    "model": "llama-3.3-70b-versatile",
    "temperature": 0.05,
    "retrieved_doc_ids": ["chunk_12", "chunk_45", "chunk_67"],
    "output": "Gradient descent is an optimization algorithm...",
    "latency_ms": 1200,
    "token_usage": {"input": 450, "output": 200},
    "error": None,
}
```

**Why this matters:** If V2 starts producing bad answers, you can check:
- Did the template change? (Content)
- Did the model change? (Policy)
- Did the retriever return different docs? (Evidence)

#### New Function: `record_eval_scores()`

```python
def record_eval_scores(
    self,
    key: str,
    scores: dict[str, float],
    eval_run_id: str,
) -> None:
    """Link eval results to a prompt version (Evidence field).

    Args:
        key: Prompt key (e.g., 'RAG_ANSWER_V2')
        scores: Dict of metric scores (recall, precision, faithfulness, relevance)
        eval_run_id: Unique ID for this eval run

    Raises:
        KeyError: If prompt not found
        ValueError: If prompt is retired
    """
    prompt = self._registry[key]
    if prompt["status"] == "retired":
        raise ValueError(f"Cannot record eval for retired prompt: {key}")

    prompt["eval_scores"] = {
        **scores,
        "evaluated_at": datetime.now().isoformat(),
        "eval_run_id": eval_run_id,
    }
```

#### New Function: `log_run()` (Runtime Evidence)

```python
def log_run(
    self,
    key: str,
    rendered_hash: str,
    retrieved_doc_ids: list[str],
    output: str,
    latency_ms: int,
    token_usage: dict,
    error: str = None,
) -> None:
    """Log a production run. Increments run_count, updates last_run_at.

    The rendered_hash enables tracing a bad answer back to the exact prompt.
    """
    prompt = self._registry[key]
    prompt["run_count"] = prompt.get("run_count", 0) + 1
    prompt["last_run_at"] = datetime.now().isoformat()

    # Append to run history (kept in separate file for scale)
    self._append_run_log({
        "run_id": f"run_{datetime.now():%Y%m%d_%H%M%S}",
        "prompt_key": key,
        "rendered_hash": rendered_hash,
        "retrieved_doc_ids": retrieved_doc_ids,
        "output": output,
        "latency_ms": latency_ms,
        "token_usage": token_usage,
        "error": error,
    })
```

#### New Function: `compare_versions()`

```python
def compare_versions(self, prompt_id: str) -> list[dict]:
    """Compare all versions of a prompt by eval scores.

    Returns sorted by faithfulness (best first).
    Shows Content (template diff), Policy (model/temp diff), Evidence (scores).
    """
    versions = self.list_versions(prompt_id)
    return sorted(
        [v for v in versions if v.get("eval_scores")],
        key=lambda x: x["eval_scores"]["faithfulness"],
        reverse=True,
    )
```

#### New Function: `rollback()` (from Step 1, now with evidence)

```python
def rollback(self, prompt_id: str, to_version: str, reason: str = "") -> dict:
    """Rollback to a previous version. Retires current, promotes target.

    After rollback, the old version's Evidence (eval_scores, run_count)
    is preserved — you know exactly what you're reverting to.
    """
    # ... implementation from Step 1 ...
```

#### How Evaluator Uses the Registry

```python
def evaluate_with_registry(
    pipeline,
    golden_path: str,
    registry: PromptRegistry,
    prompt_key: str,
) -> dict:
    """Run eval and link results to prompt version."""

    # Run eval
    results = run_full_eval(pipeline, golden_path)

    # Record scores in registry (Evidence)
    registry.record_eval_scores(
        key=prompt_key,
        scores=results["summary"],
        eval_run_id=f"eval_{datetime.now():%Y%m%d_%H%M%S}",
    )

    return results
```

#### The Exam Question 🎓

> **Q:** You have V1 (approved, recall=0.65) and V2 (draft, recall=0.78). What do you do?
>
> **A:**
> 1. Record V2's eval scores in registry (Evidence)
> 2. Compare V1 vs V2 using `compare_versions()`
> 3. If V2 is better across all metrics → promote V2 to approved, retire V1
> 4. If V2 is better in some but worse in others → keep V2 as draft, investigate
> 5. If V2 is worse → rollback is NOT needed (V1 is still approved)
> 6. Log the decision in STATUS_HISTORY

#### The Shared Registry Strategy ⭐ (cross-cutting)

Steps 2–7 all import the **same `PromptRegistry`** built in Step 1 — they add records and policy, never a new implementation. In this step the registry gains its **evidence engine**:

1. **Registered evidence** — `record_eval_scores()` / `log_run()` prove what each version actually scored; `compare_versions()` makes promotion a comparison, not an opinion.
2. **Status = data, not code** — `promote()` / `rollback()` only mutate `registry.json`. A `staging` → `approved` transition is a **data operation**, so rollback is a config swap at deploy time.
3. **Evidence is the mock boundary** — Step 2's tests mock the LLM/embedding calls (network), but the registry logic runs un-mocked: promotion decisions must be *provable*, not side-effected.
4. **Approved versions are immutable** — when V2 wins, bump to `1.1.0`; never edit V1 in place.
5. **This store feeds Step 7** — shadow/A-B candidates will sit here as `staging` records until live evidence promotes them.

---

### 6. `app.py` — Streamlit UI with Eval Dashboard

**Tabs:**
| Tab | Purpose |
|-----|---------|
| **Chat** | Interactive Q&A (same as step1) |
| **Eval Dashboard** | Run eval, see metrics, compare runs |
| **Traces** | Link to LangSmith dashboard |

**Eval Dashboard features:**
- "Run Evaluation" button
- Metrics summary (4 scores with gauges)
- Per-question breakdown (table with scores)
- Failed questions highlighted
- Compare two eval runs (before/after tuning)

**Chat features:**
- Sidebar **Settings** (`Top-k`, `Min relevance score`), **Index Stats** (chunk count + index-ready), and **Clear Chat**
- Every user/assistant exchange is appended to `data/chat_logs/chat_log_<YYYY_MM_DD>.jsonl` (JSONL objects: `{timestamp, user_message, agent_message, prompt_key, config, num_sources}`) — a durable, local conversation log that does **not** depend on LangSmith. Gitignored (`data/chat_logs/*.jsonl`).

**Observability split:** LangSmith (Traces tab) captures per-call *retrieval + generation* internals but only when `LANGSMITH_API_KEY` is set and is meant for debugging. The chat-log files capture the *conversation* for product/analytics use and always work locally.

---

## Evaluation Workflow

```
1. Curate golden.jsonl (20-30 Q&A pairs)
         │
         ▼
2. Run evaluation: in the Streamlit app's **Eval Dashboard** tab, click **"Run Evaluation"** (or run `uv run python eval/deepeval_suite/evaluate.py --limit 2 --no-reason` for the DeepEval judge)
         │
         ▼
3. Review results:
   - Context Recall: 0.65 (too low → need better retrieval)
   - Context Precision: 0.72 (okay)
   - Faithfulness: 0.85 (good)
   - Answer Relevance: 0.78 (okay)
         │
         ▼
4. Identify failures:
   - Q: "What is the difference between RAG and fine-tuning?"
   - Retrieved: chunks about RAG only
   - Missed: fine-tuning chunk
   - Root cause: query too vague, retrieval didn't capture comparison
         │
         ▼
5. Fix:
   - Improve chunking (ensure fine-tuning content is in a chunk)
   - Or improve query rewriting (add "comparison" to query)
         │
         ▼
6. Re-run eval → compare scores
         │
         ▼
7. Iterate until metrics meet targets
```

---

## What You'll Learn

### Why Evaluation Matters
- **Without eval:** "It seems to work" → breaks in production
- **With eval:** "Context Recall is 0.65" → know exactly what to fix

### Failure Modes You'll See
| Symptom | Metric | Root Cause | Fix |
|---------|--------|------------|-----|
| Answer is wrong | Low faithfulness | LLM hallucinated | Strengthen system prompt |
| Answer is irrelevant | Low answer_relevance | Bad retrieval | Improve chunking/embeddings |
| Right answer, wrong chunks | Low context_precision | Similar but wrong chunks | Add metadata filters |
| Missing info in context | Low context_recall | Chunks too small | Increase chunk_size |

### LangSmith Insights
- See exactly which chunks were retrieved
- See the full prompt sent to LLM
- See token usage and latency
- Compare traces across different questions

---

## Tech Stack (All Free)

| Component | Tool | Cost |
|-----------|------|------|
| **Embeddings** | `qwen3_embed` Qwen3-Embedding-0.6B (multilingual) | Free (local, ONNX) |
| **Vector Store** | numpy cosine similarity | Free (local) |
| **LLM** | OpenAI-compatible endpoint (`Qwen/Qwen2.5-7B-Instruct-AWQ` via `LLM_BASE_URL`, or Groq) | Free |
| **Tracing** | LangSmith | Free (5K traces/month) |
| **UI** | Streamlit | Free |

---

## Setup

**Prerequisites:** Python 3.12+ and [`uv`](https://docs.astral.sh/uv/) (the project uses `uv` for env + deps).

```bash
# Clone (if you haven't already) and install
git clone https://github.com/03dipak/step2_rag_eval.git
cd step2_rag_eval
uv sync                       # installs deps incl. the dev group (ruff, pytest, mypy, deepeval, qwen3-embed)

# API keys
cp .env.example .env
# The .env is pre-filled with the working LLM config copied from step1_basic_rag:
#   GROQ_API_KEY, LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
# Edit only if you want to switch endpoints/models.
# Edit LANGSMITH_API_KEY=ls_...  (optional, free tier — add a real key for tracing)

# Sanity check: run lint + types + the offline test suite (no network needed)
uv run ruff check
uv run mypy
uv run pytest

# Run evaluation (via Streamlit Eval Dashboard, or DeepEval runner):
uv run python eval/deepeval_suite/evaluate.py --k 3 --limit 2 --no-reason

# Run UI
uv run streamlit run app.py
```

> **First run:** `app.py` and `evaluate.py` download the `qwen3-embed` embedding model and build the in-memory index over `data/documents/`. Allow a minute or three on the first launch; later runs reuse `index.npz` and are fast.

---

## Exercises

1. **Run the eval** — what's the baseline scores?
2. **Change chunk_size** to 200 and 1000 — how do metrics change?
3. **Change top_k** to 1 and 5 — how do metrics change?
4. **Add 10 more Q&A pairs** to golden.jsonl — do metrics hold?
5. **Look at LangSmith traces** for failed questions — what went wrong?
6. **Fix one failure** — does the metric improve?
7. **Register V2 prompt** with stronger grounding rules → run eval → compare with V1 ⭐ NEW
8. **Use compare_versions()** — which version is better? Promote or keep as draft? ⭐ NEW
9. **Check eval_scores** in registry — are scores linked to the correct prompt version? ⭐ NEW
10. **Try to record eval for a retired prompt** — does it raise ValueError? ⭐ NEW

---

## Next Step

After completing this, move to **Step 3: Rebuild with LangChain** where you'll:
- Use LangChain's document loaders, text splitters, retrievers
- Compare code volume and flexibility
- Understand where LangChain helps and where it gets in the way
- Compare LangChain's PromptTemplate with your hand-written registry

---

## Mentor's Note 🎓

> Evaluation is where "works on my machine" becomes "works in production." Without eval, you're guessing. With eval, you're engineering.
>
> The prompt registry + eval integration is the key insight of this step. When you tune a prompt and answers improve, you need to know EXACTLY which version produced which scores. This is what separates junior from senior engineers.

## Exam Questions 🎓

Test yourself before moving to Step 3:

1. **Context Recall:** A gold answer mentions [chunking, embeddings, reranking]. Retrieved chunks cover [chunking, embeddings]. What's the recall score?
2. **Faithfulness:** LLM answer says "Python was created in 1991." Context doesn't mention 1991. What's the faithfulness impact?
3. **LangSmith:** What information does a LangSmith trace capture for each pipeline run?
4. **Prompt Registry + Eval:** V1 has recall=0.65, V2 has recall=0.78. What do you do? What's the process?
5. **Prompt Registry:** Why can't you record eval scores for a RETIRED prompt?
6. **Prompt Registry:** What's the difference between `list_versions(name)` and `compare_versions(name)`?
7. **Iteration:** After promoting V2, you find it's worse for "hard" questions. What do you do?

**If you can't answer 4-6, re-read the prompt_registry.py section in this README.**
