# Technical Deep-Dive Q&A (merged) — Step 4 internals, decision records & LLMOps

Senior-level questions that dig into the **why** and the **tradeoffs** behind the code we
actually built — not definitions. Each entry has the question, the model answer, and an
"interviewer checks" line: what a passing answer must cover. Consolidated 2026-09 from the former `doc/opencode_qa/01..07` files.

> **How to use:** answer out loud first, then open the answer. Every answer cites code so you
> can verify against the repo. Sections:
> 1. Scaffold & Judge (`config.py`, `eval/judge.py`)
> 2. Chunking (`chunking/{splitter,chunker,metadata}.py`)
> 3. Course grounding — the professor on chunking & embeddings (Module-2 transcripts)
> 4. Embeddings (`embeddings/embedding.py`)
> 5. Vector Store (`vector_store/{store,index,mini_ivf}.py`)
> 6. **Decision record: why run BOTH DeepEval and Ragas** (`eval/contracts`)
> 7. **LLMOps spine — 8 pillars, the operating system around eval**

---

## 1. Scaffold & Judge

Technical deep-dive questions on `config.py`, `eval/judge.py`, and the offline test setup.

**Q1. Why is the config a "hub" instead of scattered hardcoded values?**
**A:** Every downstream module (embeddings, retriever, pipeline, evals) needs the same three
inputs: API keys, model names, storage paths. Centralizing in `config.py` means one import
instead of ten; env overrides read once at startup; a single `ensure_dirs()` creates all
runtime folders. Accessors (`generate_llm()`, `judge_llm()`, `embed_model_name()`) expose
*behavior*, so later tasks consume them without touching secrets.
**Interviewer checks:** names a concrete consumer (embed model name delegate), not just "clean".

**Q2. Why is `generate_llm()` memoized?**
**A:** Constructing the provider (clients, retries, keys) is expensive/stateful; per-request
construction would re-init network clients every time. Memoization = constructed once per
process, reused. Tests reset via singleton-reset fixtures.
**Interviewer checks:** lazy init vs impure global; knows the reset path.

**Q3. Why "Groq primary → Gemini fallback", and why ONLY on rate-limit errors?**
**A:** Groq is fast+cheap for generate; Gemini is the resilience net. The fallback is **narrow**
by design: rate limits are transient/expected (Groq throttles) → retry-once-then-fallback is
correct. But a 400 (malformed prompt) or auth failure won't succeed elsewhere — falling through
there masks real bugs, so those propagate. `RATE_LIMIT_ERRORS` is a tuple because
`groq.RateLimitError` is NOT a subclass of `openai.RateLimitError`.
**Interviewer checks:** explains WHY only rate-limit triggers fallback — "don't mask permanent
errors"; mentions the tuple bug class.

**Q4. Why does the judge use one LLM (`LLM_BASE_URL`/`LLM_API_KEY`) separate from the generator?**
**A:** Eval scores must be **consistent and reproducible**. The generate path (Groq→Gemini) can
switch models; if the judge followed that chain, a run could be scored by a different judge than
the baseline — invalidating A/B comparisons. A single fixed judge
(`Qwen/Qwen2.5-7B-Instruct-AWQ`) keeps scores comparable across runs.
**Interviewer checks:** connects judge stability to eval *comparability*, not just cost.

**Q5. Why is `DeepEvalJudge` built on `DeepEvalBaseLLM`, and why does `generate()` return `(payload, latency_seconds)`?**
**A:** `DeepEvalBaseLLM` is the hook DeepEval uses to call *our* model for LLM-as-judge metrics.
Returning payload + latency is the contract the 3-level suite needs — payload is the raw JSON to
log, latency feeds regression (Task 18). Single-invoke design does one JSON-mode call and
salvages `{"output": text}` on malformed output instead of retrying the judge.
**Interviewer checks:** knows payload is for audit, latency for regression; JSON-mode + salvage.

**Q6. Why are the 17 `test_config.py` tests offline, and what's the tradeoff?**
**A:** No network/keys in CI. Provider/persistence tested with mocks and deterministic inputs.
Tradeoff: we do NOT test real API behavior — a real-response smoke lives behind env vars.
Offline tests catch wiring/caching/contract bugs; they can't catch a changed upstream API.
**Interviewer checks:** accepts offline-first but is honest integration risk is deferred.

**Q7. Why are secrets env-only and `.env` gitignored, with defaults in code?**
**A:** Keys must never be committed. `.env` holds real values for manual runs; `config.py` holds
model-name **defaults** (no keys). Keeps "safe to commit" vs "never commit" crisp.
**Interviewer checks:** says where keys live vs where defaults live; `.env.example` documents shape.

**Q8. Why does persistence (directories/logs) have an accessor in Task 01?**
**A:** Eval and chat-log paths are write targets for Tasks 12–18. Creating them up front
(`ensure_dirs`) means tests/evals rely on paths existing, and any writer imports one function
instead of re-deriving a path. Also makes cleanup targets explicit in `.gitignore`.
**Interviewer checks:** sees the accessor as cross-task stability, not vanity.

---

## 2. Chunking (splitter strategies, facade, Layer-1 eval)

Every answer leads with an **As per code/comment:** line quoting exact source + `file:line`.
Trap questions marked **TRAP**.

**Q1. Why two layers — `splitter.py` (pure text→list) and `chunker.py` (facade)?**
**A:** Splitters are pure functions of text — unit-testable, no pipeline knowledge. The facade
owns strategy dispatch, `{text, metadata}` contract, index attachment, embedder injection for
`semantic`. Without the split, metadata logic leaks into all five functions.
**Interviewer checks:** names the *contract boundary*, not just "clean code".

**Q2. Why is `recursive_split` the default strategy?**
**A:** It recurses down `_RECURSIVE_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]` (paragraphs →
sentences → words → chars), respecting natural boundaries. Keeps chunks readable/coherent for
generic content; the other four strategies are for known content types.
**Interviewer checks:** explains the separator ordering, not just "it's default".

**Q3. How does `markdown_split` keep context across chunks?**
**A:** Splits on H1–H3, injecting the **header path into every chunk** (headers never standalone,
never bleed). The section path in every chunk tells the generator *where* it came from — no
parent lookup. A/B: 87→86 chunks with header injection.
**Interviewer checks:** knows the rejected alternative (parent-child retrieval) and why.

**Q4. Why is `deterministic_embedder` a *function*, not a strategy?** — **TRAP**
**A:** It's the offline pseudo-embedding for Layer-1 structural evals — hash-projects each word
into a fixed-dim vector, normalizes. `SPLITTERS` keys exactly five strategies
(`recursive, character, semantic, markdown, code`); `strategy='deterministic_embedder'` raises
`ValueError`. It's the **default embedder the `semantic` strategy uses** when none is injected.
**Interviewer checks:** distinguishes "embedder used by a strategy" from "strategy".

**Q5. Semantic is offline-deterministic — why still excluded from `chunking_goldens.json`?**
**A:** Golden bounds written against the stub would mislead once real embedder boundaries differ.
Semantic is gated by (a) determinism unit tests now, (b) a Layer-2 cost/quality decision with
the real embedder later. Goldens are *contracts with reality*.
**Interviewer checks:** goldens = contracts with reality; semantic's reality isn't fixed yet.

**Q6. Why can goldens (Layer 1) never tell you "which strategy retrieves best"?**
**A:** Golden schema is structural (`chunk-count ∈ [min,max]`, `must_contain` substring survives
*in a single chunk*). It verifies "didn't break", not ranking. Ranking is Layer-2 (Tasks 12/13):
hold everything constant, vary strategy, read Contextual Recall vs Precision/Relevancy.
**Interviewer checks:** separates "didn't break" (L1) from "better for retrieval" (L2).

**Q7. Why char-based `chunk_size` and no tiktoken/token counting?**
**A:** The four LangChain-backed splitters use `length_function=len`; `semantic_split` is char-greedy
via `_greedy_sentences`. `tiktoken` is OpenAI's vocab — wrong for a qwen3
pipeline; true qwen3 tokens need a `transformers` download, breaking offline testability and the
goldens' char-based bounds. Deliberate stack tradeoff, not laziness.
**Interviewer checks:** knows this is a qwen3-embed stack decision.

**Q8. What happens if you call `Chunker().split(... strategy='code', language='go')`?**
**A:** The facade special-cases `semantic`; the `else` branch forwards `text, chunk_size, overlap`
plus `language` for `code` (`chunker.py:52-53`), matching its docstring. `code_split` maps the alias
to language-aware separators, falling back to generic recursive for unknown languages.
**Interviewer checks:** reads the facade's `extras` handling critically.

**Q9. Edge cases you rely on?**
**A:** Empty/whitespace → `[]` for every splitter; unknown `code` language → generic recursive;
`character_split` on a huge separator-free span yields one oversized chunk (LangChain behavior).
**Interviewer checks:** can enumerate ≥2 real edge behaviors.

**Q10. What drives `Chunker.split`'s metadata and why is `source` non-optional?**
**A:** `build_metadata` always sets `{"source": ...}` + optional `page`/`url`/`domain`/`headers`;
`attach_chunk_index` adds per-chunk `index`. `source` is the contract for routing/filtering/
citing; a chunk without it can't be traced to its corpus asset.
**Interviewer checks:** connects metadata to routing/where-filters/citation/per-source eval.

---

## 3. Course grounding — what the professor teaches on chunking & embeddings

Source: our IIT-Kharagpur lecture transcripts. Maps his teaching onto Step-4 code so choices
are course-grounded, not random.

### The professor on chunking
- **No single formula**: "match chunk size to your content — small for QA, large for narrative.
  You will have to **reiterate** the process."
- **Five standard strategies** (explicitly): fixed / sentence-paragraph / **sliding-window
  overlap** (the go-forward second baseline, cheap) / **semantic** (embedding-similarity shift,
  expensive) / **hierarchical parent-chain**.
- **Cost gate**: "Start with sliding-window and move to semantic only when retrieval quality
  justifies the cost."
- **Content-type rule**: markdown/legal → structure-aware headings; mixed → semantic.
- **Size sweet spot**: too small loses context; too large, mediocre recall.
- **Classic failure-mode exam question**: recall mediocre after swapping to a fancier embedder —
  most likely **chunks too large / Euclidean distance / forgot query-passage prefix**; or the
  document-parsing/chunking step is losing structure.

### The professor on embeddings
- Dense (semantic) vs sparse BM25 (exact term) are **complementary**.
- Embeddings are contextual ("bank" = finance vs river).
- Model choice by **MTEB benchmarks, domain quality, privacy, latency, cost**.
- Indices: IVF, PQ, IVF+PQ, HNSW; "Faiss scales to billions, **ChromaDB to millions**."
- Quality checks: hit-rate/recall@1 + **citation/verifiability**.

### Mapping his teaching → our code
| Professor | Step-4 implementation |
|---|---|
| Start fixed/sliding; semantic only when justified | `recursive_split` default + `character_split`; `semantic_split` gated behind `deterministic_embedder` stub + Layer-2 decision |
| Markdown/legal → structure-aware | `markdown_split` H1–H3 + header-path injection |
| Mixed code → per-language grammar | `code_split` with per-language separator tables |
| Semantic = group related sentences | `_embedding_groups` cosine-gated greedy grouping, `threshold` knob |
| Chunk size ↔ content, reiterate | Task-12 knob-map sweeps chunk_size first; goldens per strategy |
| Euclidean is a failure mode → cosine | all vectors L2-normalized; Task-04 embedder asserts unit norm |
| Dense + sparse complementary | Task 07 hybrid/ensemble dense+BM25 with RRF |
| MTEB-driven choice, domain-fit | `get_embedder(name)` factory + `EMBED_MODEL` config |
| IVF/PQ/HNSW indices | `vector_store/mini_ivf.py` (build-by-hand) |
| Citation/recall checks | source-carrying metadata + L1 vs L2 evals |
| Parent-chain chunking | **deferred** (deliberate), via header-path injection |

### Deep-dive Q&A
**Q1. The exam failure-mode question — how does it map to our eval design?**
**A:** It's the *prediction* behind the knob-map (Task 12): when recall is mediocre you turn
**chunk_size, then similarity/prefix, then top_k** — the embedding model is almost the *last*
knob. L1 structural goldens catch "chunking loses structure" cheaply; L2 sweeps strategy/size
before re-evaluating the model.
**Interviewer checks:** chunk_size and prefix before "get a better embedding model".

**Q2. Why is our semantic offline-deterministic while he grades it highest quality?** — **TRAP**
**A:** Because he also sets the **cost gate**: move to semantic only when quality justifies cost.
Semantic embeds *every sentence* and forces a *downstream re-index* (new boundaries). We match:
`semantic_split` runs on a stable hash-projected stub today; the real embedder becomes the
default only after Layer-2 measurement says the gain beats slide/recursive.
**Interviewer checks:** restates the cost gate + re-index churn, not just "more accurate".

**Q3. He lists parent-chain as standard. We deferred it. Defend.** — **TRAP**
**A:** Parent-child solves "small for retrieval, large for generation", but header-path injection
puts the section identity *inside every chunk* — generation gets the "parent" without an extra
storage/lookup layer. Parent-child is a documented deferred upgrade, reserved behind an eval
trigger if injection can't carry the structure.
**Interviewer checks:** we didn't "forget" — we traded a storage layer for injected context.

**Q4. Dense + sparse complementarity — where, and why RRF?**
**A:** Task 07 hybrid/ensemble fuse dense (cosine) + BM25 with **RRF** — rank-based fusion that
needs no score calibration, because dense cosine and BM25 scores aren't comparable.
**Interviewer checks:** *why* RRF over score-fusion, not "RRF is popular".

**Q5. "Faiss scales to billions, ChromaDB to millions" — we picked Chroma + mini-IVF. Defend.**
**A:** Corpus is far below the million-vector boundary; Chroma gives local privacy, per-point JSON
metadata (the `source` `where`-filters need), stable Python API. mini-IVF is pedagogical (prove
the mechanics); Faiss is the documented scale-out behind `IndexConfig`.
**Interviewer checks:** justifies by corpus *size*, not hype; metadata-`where` is the real constraint.

**Q6. Why don't we have ColBERT late interaction?**
**A:** Documented deferral, not omission. ColBERT needs per-token embeddings persisted (2–3× store
size) + a max-interaction step. For a single-source corpus already served by dense+BM25+RRF, the
added accuracy isn't justified yet. Upgrade path (Task 08): cosine rerank → cross-encoder →
ColBERT-style max-sim.
**Interviewer checks:** can *order* rerankers by cost; knows ColBERT's storage footprint.

---

## 4. Embeddings (interface, cosine, config wiring, factory)

**Q1. Why a pure `Embedder` interface instead of importing `qwen3_embed` everywhere?**
**A:** Consumers (vector store, semantic splitter, dense retriever) code against
`Embedder.embed_documents / embed_query`. Swapping hosted→OSS or BGE→Qwen3 is a one-line
`EMBED_MODEL` change or a new `EMBEDDERS` entry. Framework-agnostic (lean-deps rule).
**Interviewer checks:** names consumers + config-driven swap.

**Q2. Why is L2-normalization inside the embedder?**
**A:** Similarity is **cosine** = dot product of normalized vectors. Normalizing in one place
means every consumer gets unit vectors for free and can't forget — and the norm is assertable
in Layer-1 evals. Zero vector stays all-zero (norm 0 → no NaN).
**Interviewer checks:** cosine = dot of unit vectors; NaN guard.

**Q3. How is dimension handled — declared or observed?** — **TRAP**
**A:** **Observed, not declared.** `dim()` returns None before the first embed; `_coerce` records
it. No `dimension=1024` constant. Mixed dims or drift raise `ValueError`. The contract must
survive a swapped model (e.g. a future 768-d entry).
**Interviewer checks:** dim is incompatible-guardable data, not a constant.

**Q4. Where does `Qwen3Embeddings` get its model name? How would you swap it?**
**A:** `embed_model_name()`: `EMBED_MODEL` env override, else default
`n24q02m/Qwen3-Embedding-0.6B-ONNX`. Change `EMBED_MODEL` → everything rebuilds via
`get_embedder("qwen3")`. New provider = register class in `EMBEDDERS`, `get_embedder(name)`
(unknown → `ValueError`). Same registry pattern as `SPLITTERS`.
**Interviewer checks:** "change the model" (config) vs "add a provider" (registry).

**Q5. How do L1 evals test a 1024-d neural model without downloading it?**
**A:** `Qwen3Embeddings.__init__(backend=...)` is the test seam; the real `TextEmbedding` builds
**lazily on first use**. `eval_embeddings.py` injects `_HashBackend` wrapping the 128-d
`deterministic_embedder`. Structural contract (count/dim/unit-norm/query-parity/factory/config)
verified at zero cost; real-model quality is measured in Task 12 (Layer-2).
**Interviewer checks:** the seam + three-layer gate, not just "mock it".

**Q6. Why cosine, and what would change with L2?** — **TRAP**
**A:** Cosine ignores magnitude (two texts, same direction, different scale/verbosity still
match). Vectors are unit-norm → here `cosine == dot`, so a pure dot-product index (Faiss IP) is
correct and faster. Switching to L2 would drop normalization and need `METRIC_L2`.
**Interviewer checks:** cosine ignores magnitude; unit-norm ⇒ dot == cosine.

---

## 5. Vector Store (HNSW knobs, Chroma facade, mini-IVF)

**Q1. Why raw `chromadb` instead of the LangChain wrapper you copied from?**
**A:** Lean-deps rule — trades the `langchain_chroma`/`Document` plumbing for raw
`chromadb.PersistentClient`. Same `{text, metadata, score}` contract + cosine fix as Step 3, but
one fewer heavy dependency; embeddings injected from outside (Task 04).
**Interviewer checks:** dependency justification + same contract.

**Q2. How is HNSW tuned, and who sets the knobs?**
**A:** `IndexConfig.chroma_metadata` → `hnsw:space / M / construction_ef / search_ef` applied at
`get_or_create_collection` time. Knob changes = config, not code. **Trap: metadata honored only
at collection creation** — a persisted collection keeps original knobs.
**Interviewer checks:** knobs apply at creation time — that's the real trap.

**Q3. What does `create_index` return, and why "store/search pair"?**
**A:** A single facade (`VectorStore`) exposing both halves: `add_documents` (index) + `search`
(retrieval) on one object. `embedding=None` defers to the Task-04 default built lazily — calling
`create_index` never downloads a model.
**Interviewer checks:** one facade, two halves, not two classes.

**Q4. How does `search` turn Chroma distances into scores?** — **TRAP**
**A:** `similarity = float(1.0 - distance)`, filtered `if similarity < min_score: break`
(ascending-distance-sorted break), returned as `{text, metadata, score}`. Because the collection
is cosine + vectors normalized, distance = `1 - cosine`, so similarity is exactly cosine. The
`break` needs distance-ascending order; `top_k` clamped to `collection.count()`.
**Interviewer checks:** distance vs similarity; `break` needs sorted order.

**Q5. Why does `query` use `embed_query` while `add_documents` uses `embed_documents`?**
**A:** Task-04 instruction-prefix asymmetry (FastEmbed/Qwen3): documents get the doc prefix via
`embed()`; queries get the task-instruction prefix via `query_embed()`. Flipping either side
pollutes Layer-2 A/B with ~1–5% retrieval-quality noise on every strategy.
**Interviewer checks:** connects call-sites to the Task-04 asymmetry rule.

**Q6. Why write a mini-IVF by hand when Chroma (HNSW) is production?** — **TRAP**
**A:** Build-it-by-hand companion to "how does the production index work". `fit` runs k-means++;
`query` probes `nprobe` nearest centroids and scans only those buckets; at `nprobe == nlist` it
equals brute force. Eval sweep turns it into a number (nlist=16: 0.930@1 probe → 1.000@4).
Faiss-IVF stays a documented slot-in.
**Interviewer checks:** *why* (learning) not just *what*; coarse quantizer + bucket scan.

**Q7. Is mini-IVF deterministic? Reloadable?**
**A:** `fit(vectors, nlist, seed=0, iters=8)` pins rng; `save` snapshots centrids/data/buckets to
`.npz` (default `config.index_path()`, `index.npz`), `load` restores — the production analog of
round-tripping a trained IVF index.
**Interviewer checks:** determinism via seed; npz persistence path.

**Q8. What would you change to scale really large?**
**A:** mini-IVF exactly scans probed buckets; Faiss adds SIMD PQ/IVF compression + HNSW over
centroids. Same parameters, production-grade math. Deep lesson: separate teaching impl from the
production slot-in.
**Interviewer checks:** teaching vs production separation.

---

## 6. Decision record — why run BOTH DeepEval and Ragas

**Audience:** tech lead can skim TL;DR + "when to reach for which"; junior reads the schema
walkthrough; trainee leans on the study sheet. Question answered: *"we already have DeepEval —
why also bolt on Ragas?"*

### TL;DR
Step 4 ships **two metric engines — DeepEval and Ragas — behind a single framework-neutral
seam** (`eval/contracts/`). Not "either/or": the frameworks barely overlap.

| Need | Winner |
|---|---|
| Cheap always-on CI gate over golden tests (assert thresholds in pytest) | **DeepEval** |
| Deep RAG metric battery (20+, e.g. contextual precision) + synthetic testset gen (Steps 5–7) | **Ragas** |

Both use the same config-driven judge (`judge_llm()`), both score the same 4 core metrics now,
both produce the same neutral `Report`. Swapping/adding a third is a one-file change in
`registry.py`.

### 1. The question in plain words
- **DeepEval** (`deepeval==2.9.3`): pytest-for-LLMs. Test cases + threshold asserts; small metric
  set, tight CI. Opinionated.
- **Ragas** (`ragas==0.3.1`): research-grade RAG metric lab. More metrics, deeper retrieval
  diagnostics, **testset generator**. Historically LangChain-tied in this version.

We chose the third option that makes the framework a **pluggable detail**: ship both, instantly,
behind a seam that hides them.

### 2. Why "keep both" is not indecision
A seam removes the cost of a wrong guess. We defined **our own vocabulary** (`EvalCase` +
`Report`) and made each framework a translator on the edges. The bet becomes *"our schema is
stable."* Same idea as an interface: code against the abstraction, plug in implementations.

### 3. What we built
```
eval/
├── contracts/                     # the seam — NO vendor imports at this layer
│   ├── schema.py                  #   EvalCase, MetricResult, Report (neutral shapes)
│   ├── mappers.py                 #   EvalCase → deepeval LLMTestCase | ragas SingleTurnSample
│   ├── backend.py                 #   MetricBackend protocol + run_backends()
│   ├── registry.py                #   get_backend("deepeval"|"ragas"), DEFAULT_BACKEND="deepeval"
│   └── __init__.py
├── deepeval_suite/
│   ├── backend_deepeval.py        # DeepEvalBackend (original engine behind the seam)
│   └── embeddings/ vector_store/ …# existing Layer-1 suites — untouched
└── ragas_suite/
    ├── backend_ragas.py           # RagasBackend (Faithfulness, AnswerRelevancy, Context*)
    └── testset.py                 # synthetic golden generation for Steps 5–7 (integration-only)
```
`pyproject.toml`: pytest `pythonpath = ["src", "eval"]`; mypy override for `ragas` (no py.typed).

### 4. The neutral schema
```python
@dataclass(frozen=True)
class EvalCase:
    question: str
    response: str = ""                 # pipeline's live answer
    retrieved_contexts: list[str] = []  # what retrieval returned (verbatim)
    reference: str = ""                # golden/expected answer
    difficulty: str = ""
    source: str = ""
```
Mappers map onto each vendor's sample type; nothing about `EvalCase` mentions a vendor; `Report`
shape is shared, so Task 18 reads the same JSON either way.

### 5. Metric vocabulary — ours, then each vendor's
| Ours | DeepEval | Ragas 0.3.1 | Needs embeddings? |
|---|---|---|---|
| `faithfulness` | `FaithfulnessMetric` | `Faithfulness` | No |
| `answer_relevancy` | `AnswerRelevancyMetric` | `AnswerRelevancy` | **Yes (Ragas)** |
| `context_precision` | `ContextualPrecisionMetric` | `ContextPrecision` | No |
| `context_recall` | `ContextualRecallMetric` | `ContextRecall` | No |

DeepEval spells "Context**ual**", Ragas "Context" — same math, different casing. Ragas
`answer_relevancy` needs an embeddings adapter; the seam **refuses loudly** (`ValueError`) rather
than failing inside the vendor.

### 6. One judge, two backends
- DeepEval: `DeepEvalJudge` wraps `judge_llm()` (`eval/judge.py:34`).
- Ragas: `LangchainLLMWrapper(judge_llm())` — built **lazily at measure time** so constructing
  `RagasBackend()` never touches the network.
- Migrate model/endpoint = change `config.py` once.

### 7. Environment facts
- **Ragas pinned to 0.3.1** — last of the legacy API line; it imports
  `langchain_community.chat_models.vertexai`, which vanished in 0.4.x → stay on
  `langchain-community==0.3.31` (packaging pin, not a choice). Upgrade path: only
  `backend_ragas.py` changes.
- **Ragas has no `py.typed`** → mypy override `ignore_missing_imports = true`.
- `uv add ragas` pulled transitive deps (`datasets>=5`, `dill`, `diskcache`, `httpx-sse`,
  `sqlalchemy`, moved `fsspec` 2026.7.0→2026.6.0). Do not prune by hand.

### 8. Offline vs gated
- **Always (CI):** `EvalCase`/`Report` round-trips, mappers, registry, per-backend
  mapping/aggregation — tested **without any LLM** (fake evaluator injected; 24 tests). Neither
  backend makes a network call in construction.
- **Integration/Task-12 A/B (`-m integration`):** real `deepeval.evaluate`/`ragas.evaluate` with
  the configured judge — the Layer-2 budget, not CI.
- **Never by accident:** `eval/ragas_suite/testset.py` is integration-only, not imported by the
  eval package.

### 9. When to reach for which (rule for Steps 5–7)
1. Thresholding one eval run in a pipeline → **DeepEval**.
2. Deep retrieval forensics / battery (20+ ragas metrics) → **Ragas** (deferred tail of #5).
3. Generating new goldens from `data/` → `testset.py`; feed back into `golden.jsonl` (neutral
   schema, zero downstream changes).
4. A/B-ing a chunking/retriever change → run **both** backends on the same cases and diff the two
   Reports; agreement strengthens, disagreement flags a probe.

### Interview Q&A
**Q1. Two LLM eval frameworks — overlap you should be ashamed of?**
**A:** Registry calls the seam *"the only place that knows which frameworks exist"*; schema is
neutral. Overlap confined to 4 metrics; each owns non-overlapping value (DeepEval = CI gate;
Ragas = battery + testset). Overlap in *tooling* is cheap when hidden; the seam eliminates
*vocabulary* overlap.
**Interviewer checks:** tooling overlap (cheap) vs vocabulary overlap (eliminated).

**Q2. Where does the judge come from, and can the backends disagree about which model judged?** — **TRAP**
**A:** Both wrap `judge_llm()`. **They can disagree** — latency, context-length effects,
generation randomness differ per framework even with the same endpoint. Cross-backend gap is a
findng, not a bug.
**Interviewer checks:** both use `judge_llm()`; does NOT claim identical scores.

**Q3. Why does `answer_relevancy` fail under Ragas but not DeepEval?**
**A:** Ragas' relevancy compares answer↔question in **embedding space** (needs an embeddings
adapter; guard raises). DeepEval's variant is LLM-judged.
**Interviewer checks:** embedding-vs-LLM judging; fix is an adapter, not deleting the metric.

**Q4. Ragas 0.3.1 pulls `langchain-community==0.3.31` (old). Red flag?**
**A:** A deliberate pin of a *known-good* combination, isolating ragas' legacy API; documented
migration path. Not dangling debt.
**Interviewer checks:** deliberate pin with a migration note.

**Q5. When does the Ragas path first cost money, and how is it kept out of CI?**
**A:** Three gates: judge built lazily; injected fake evaluator in tests; integration marker
`-m integration`. `testset.py` never imported by the rest of the eval package.
**Interviewer checks:** names the three gates.

---

## 7. LLMOps spine — 8 pillars, the operating view

**Purpose:** the DeepEval/Ragas layer answers *"what's the score?"* (measurement). LLMOps answers
*"what do we do about it?"* — the operating system around measurement: verdicts, baselines, cost,
rollback, lifecycle. Frameworks say "0.82"; `metric_registry`→`compare` says *"gate regressed →
FAIL, exit 1."*

### First: the distinction
| | Evaluation (DeepEval/Ragas) | LLMOps (this page) |
|---|---|---|
| Question | "Is this response good?" | "Would I ship this? What does a regression cost? How do I roll back?" |
| Unit | a metric score 0–1 | a **decision** (PASS/REVIEW/FAIL), a budget, a policy |
| Output | `Report` | **`snapshot` + verdict + cost model + lifecycle rule** |
| Owner | eval task | the whole pipeline + the team |

### The 8 pillars, mapped to Step-4 code
| # | Pillar | Step-4 evidence | Status |
|---|---|---|---|
| 1 | **Data & testset (goldens)** | `eval/goldens/` — component-goldens per task, grounded, verbatim-`must_contain` | ✅ real |
| 2 | **Prompt & template mgmt** | `prompts/prompt_registry.json` — composite key `prompt_id+source_type+version`, approve/rollback lifecycle | ✅ real |
| 3 | **LLM-as-judge** | `eval/judge.py` — fixed judge endpoint, throttle, JSON-mode+salvage | ✅ real |
| 4 | **Regression & quality gates** | `eval/regression/` (Task 18) — `run_suite`→snapshot, `metric_registry` (direction/kind/tolerance), `compare`→PASS(0)/FAIL(1)/REVIEW(2) | 🟡 harness in Step 4, CI automation deferred (#14) |
| 5 | **Observability / SLOs** | Task 14 — stage-split latency + TTFT (`SLO_P95_MS=3000`, `SLO_TTFT_P95_MS=1200`), reliability, cost projection | 🟡 SLOs in Step 4; LangSmith/drift deferred (#10/#15) |
| 6 | **Cost ladder / efficiency** | Groq→Gemini fallback; per-source `where` filters (cheap routing); rerankers gated by eval; LangSmith tracing planned | ✅ partial, deferrals #8/#9 |
| 7 | **Lifecycle (CI/CD, deploy, rollback)** | prompt registry approve/rollback; baseline snapshot; `compare` exit code = CI gate | 🟡 in-repo lifecycle real; CI automation deferred (#14) |
| 8 | **Safety & guardrails** | minimal PII (`eval_ops_pii.py`); full suite (scope/leakage/toxicity/injection/red-team) → Step 7 (#13/#19) | 🟡 minimal now |

### Interview Q&A
**Q1. What is LLMOps, and how is it different from an eval framework?** — see table. The one line:
an eval framework measures; LLMOps *decides* and *operates* (gate, rollback, cost).
**Interviewer checks:** can distinguish "0.82" (measurement) from "FAIL, exit 1" (decision).

**Q2. How does the regression harness turn evals into a decision?**
**A:** One pipeline built once, whole suite run, every metric flattened to a dotted id, provenance
stamped into a snapshot JSON (`run_suite.py`). Each metric carries direction (higher/lower),
kind (gate/guardrail/info), tolerance (`metric_registry.py`). `compare.py` diffs candidate vs
baseline → PASS (0) / FAIL (1, gate regressed) / REVIEW (2, guardrail regressed). The exit code
is the CI gate; the CI *automation* is Step 7.
**Interviewer checks:** gate vs guardrail vs info; tolerances above measurement noise (~±0.03
judge, ~±20% latency).

**Q3. What would you make a GATE vs a GUARDRAIL?**
**A:** A **gate** must not regress (faithfulness pass-rate — hard fail). A **guardrail** is a soft
target (latency P95 — drop → REVIEW). Info metrics tracked but never drive the verdict.
**Interviewer checks:** hard-fail vs soft-target reasoning.

**Q4. Where do the deferrals in `GAP_REGISTER.md` fit the pillars?**
**A:** Every ⏭️/🔴 row maps to at least one pillar's production upgrade: safety suite → pillar 8;
LangSmith/MLflow → pillar 5; caching/cost → pillar 6; CI automation → pillar 7.
**Interviewer checks:** can map a deferral to its pillar and destination step.

**Q5. As tech lead, how would you know "the system got worse" before a user complains?**
**A:** Baseline snapshot (Task 18) + gate/guardrail verdict on every change; latency/cost SLOs
(Task 14); judge pinned so drift is signal not noise. The gap register is reviewed at each task
closure so gaps are decisions, not surprises.
**Interviewer checks:** names snapshot, pinned judge, SLO thresholds, gap-register review.