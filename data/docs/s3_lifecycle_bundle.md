<!-- Bundle S3 (D14): sources = step7_deploy/README.md + step8_llm_finetuning/README.md -->

# Step 7 — Deploy + Guardrails

The final step. You've built RAG, evaluated it, made it agentic, added multi-agent collaboration. Now deploy it and add **guardrails** to keep it safe in production.

> **Why this step matters:** A RAG system that isn't deployed isn't finished. A deployed system without guardrails is dangerous.

---

## Learning Objectives

By completing this step, you will understand:

1. **Deployment** — Serving RAG as a web API
2. **Input guardrails** — Filtering malicious or off-topic queries
3. **Output guardrails** — Ensuring answers are safe and accurate
4. **Monitoring** — Tracking production metrics
5. **Cost management** — Token budgeting and rate limiting
6. **Failure handling** — Graceful degradation when things break

---

## Architecture

```
User Request
      │
      ▼
┌─────────────────────────────────────────────────┐
│              INPUT GUARDRAILS                     │
│                                                  │
│  - Prompt injection detection                    │
│  - Off-topic filtering                           │
│  - Rate limiting                                 │
│  - Input length validation                       │
│                                                  │
└───────────────┬──────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│              RAG PIPELINE                        │
│                                                  │
│  (Steps 1-6 combined)                           │
│                                                  │
└───────────────┬──────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│              OUTPUT GUARDRAILS                    │
│                                                  │
│  - Hallucination detection                       │
│  - Toxicity filtering                            │
│  - Citation verification                         │
│  - PII detection                                 │
│                                                  │
└───────────────┬──────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│              MONITORING                           │
│                                                  │
│  - Token usage tracking                          │
│  - Latency monitoring                            │
│  - Error rates                                   │
│  - Cost estimation                               │
│  - User feedback loop                            │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

## File Structure

```
step7_deploy/
├── README.md
├── pyproject.toml
├── .env
├── .gitignore
│
├── data/
│   └── *.txt
│
├── src/deploy_rag/
│   ├── __init__.py
│   ├── pipeline.py             ← Complete RAG pipeline
│   ├── guardrails/
│   │   ├── __init__.py
│   │   ├── input.py            ⭐ NEW: Input validation
│   │   ├── output.py           ⭐ NEW: Output validation
│   │   └── prompt_injection.py ⭐ NEW: Injection detection
│   ├── monitor.py              ⭐ NEW: Metrics and tracking
│   ├── cost_tracker.py         ⭐ NEW: Token budgeting + cost-per-version
│   ├── shadow_tester.py        ⭐ NEW: Shadow testing for new prompts
│   ├── ab_router.py            ⭐ NEW: A/B traffic splitting
│   ├── prompt_registry.py      ← Final version with all prompts (shared from Step 1; backs shadow/A-B)
│   └── api.py                  ⭐ NEW: FastAPI web service
│
├── app.py                      ← Streamlit UI (production-ready)
│
├── eval/
│   └── golden.jsonl
│
└── tests/
    ├── __init__.py
    ├── test_guardrails.py      ← Test input/output validation
    └── test_api.py             ← Test API endpoints
```

---

## Key Components

### 1. Input Guardrails

```python
class InputGuardrails:
    def validate(self, query: str) -> tuple[bool, str]:
        # Length check
        if len(query) > 10000:
            return False, "Query too long"

        # Prompt injection detection
        if self.detect_injection(query):
            return False, "Potential prompt injection"

        # Off-topic check
        if not self.is_rag_related(query):
            return False, "Question not related to loaded documents"

        # Rate limiting
        if self.is_rate_limited():
            return False, "Rate limit exceeded"

        return True, ""
```

**Exam Question 🎓:** How do you detect prompt injection? What patterns should you look for?

---

### 2. Output Guardrails

```python
class OutputGuardrails:
    def validate(self, answer: str, context: list[dict]) -> tuple[bool, str]:
        # Hallucination check: does answer match context?
        faithfulness = self.check_faithfulness(answer, context)
        if faithfulness < 0.5:
            return False, "Answer not supported by context"

        # Toxicity check
        if self.detect_toxicity(answer):
            return False, "Answer contains inappropriate content"

        # Citation check: are citations real?
        if not self.verify_citations(answer, context):
            return False, "Invalid citations"

        return True, ""
```

**Exam Question 🎓:** How do you verify that a citation is real? What if the LLM invents a fake page number?

---

### 3. Cost Management

```python
class CostTracker:
    def __init__(self, daily_budget: float = 5.0):
        self.daily_budget = daily_budget
        self.today_usage = 0.0

    def track(self, tokens: int, model: str):
        cost = calculate_cost(tokens, model)
        self.today_usage += cost

        if self.today_usage > self.daily_budget:
            raise BudgetExceeded(f"Daily budget ${self.daily_budget} exceeded")
```

**Exam Question 🎓:** How do you estimate cost before making an LLM call? What's the tradeoff between cost and quality?

---

### 4. A/B Testing & Shadow Testing ⭐ NEW

Production prompts need validation before full rollout.

#### Shadow Testing

Run new prompt version alongside production, but only return production answer:

```python
class ShadowTester:
    def query(self, question: str) -> str:
        # Production: use current approved prompt
        prod_answer = self.pipeline.ask(question, prompt_version="current")

        # Shadow: run new prompt in background (user doesn't see)
        shadow_answer = self.pipeline.ask(question, prompt_version="V3_shadow")
        self.log_shadow_result(question, prod_answer, shadow_answer)

        return prod_answer  # User only sees production answer
```

#### A/B Testing

Split traffic between versions:

```python
class ABTestRouter:
    def route(self, question: str) -> str:
        user_hash = hash(question) % 100
        if user_hash < 90:
            return "current"      # 90% traffic → production
        else:
            return "V3_candidate" # 10% traffic → candidate
```

#### Compare Results

```python
# After running A/B test for 1 week:
prod_metrics = {"avg_score": 0.82, "cost_per_query": 0.002}
v3_metrics = {"avg_score": 0.87, "cost_per_query": 0.003}

# Decision: V3 is 6% better but 50% more expensive
# → Promote if quality matters more than cost
# → Keep as candidate if cost is critical
```

---

### 5. Cost-per-Version Tracking ⭐ NEW

Different prompt versions have different costs (longer templates = more tokens):

```python
COST_PER_VERSION = {
    "RAG_ANSWER_V1": {
        "template_tokens": 45,        # Tokens in the template itself
        "avg_input_tokens": 500,      # Average input per query
        "avg_output_tokens": 200,     # Average output per query
        "cost_per_query": 0.0018,     # (500 + 45) × $0.000003 + 200 × $0.000006
        "queries_today": 450,
        "total_cost_today": 0.81,
    },
    "RAG_ANSWER_V2": {
        "template_tokens": 72,        # Longer template = more tokens
        "avg_input_tokens": 520,      # Slightly more input (longer prompt)
        "avg_output_tokens": 180,     # Shorter output (more constrained)
        "cost_per_query": 0.0021,     # Slightly more expensive per query
        "queries_today": 0,           # Not in production yet
        "total_cost_today": 0,
    },
}
```

#### Cost Optimization Decision

```
V1: cost=$0.0018/query, score=0.82
V2: cost=$0.0021/query, score=0.87

→ V2 is 17% more expensive for 6% quality improvement
→ Decision depends on:
  - Is quality improvement worth the cost?
  - What's the daily budget?
  - How many queries/day?
```

**Exam Question 🎓:** V2 is 17% more expensive but 6% better. Your daily budget is $5. You get 2000 queries/day. Can you afford to switch? (Answer: V1 costs $3.60/day, V2 costs $4.20/day. Yes, within budget.)

#### The Shared Registry Strategy ⭐ (cross-cutting)

Step 7 is where the shared registry's design pays off — it is the **backing store for shadow/A-B and rollback**:

1. **Candidates live in the registry** — `RAG_ANSWER_V3_shadow` is a `staging`/`draft` record in the **same shared store** built in Step 1; it never ships until live evidence promotes it.
2. **Rollback is a data op** — production answers come from `registry.get(prompt_id, approved_only=True)`; rolling back = flipping status in `registry.json`. No code redeploy, no binary rollback.
3. **Evidence drives promotion** — promote only when shadow/A-B scores beat the incumbent; the registry records those scores per version (`compare_versions()`).
4. **Approved versions immutable** — V1 stays byte-identical forever; cost-per-version and eval comparisons keep their meaning.
5. **The mechanism stays cross-cutting** — all seven steps share the same class and gates; Step 7 only adds *deployment policy* around it.

---

### 4. Monitoring Dashboard

```
┌─────────────────────────────────────────────────┐
│           PRODUCTION METRICS                     │
│                                                  │
│  Requests today: 1,234                           │
│  Avg latency: 1.2s                               │
│  Error rate: 0.3%                                │
│  Token usage: 450,000 / 1,000,000 (45%)         │
│  Cost today: $2.30 / $5.00 (46%)                 │
│                                                  │
│  Guardrail blocks:                               │
│  - Prompt injection: 12                          │
│  - Off-topic: 45                                 │
│  - Rate limited: 8                               │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

## Deployment Options

| Option | Complexity | Cost | Best For |
|--------|-----------|------|----------|
| Streamlit Cloud | Low | Free | Prototypes |
| Docker + VPS | Medium | $5-20/mo | Small production |
| AWS Lambda | Medium | Pay-per-use | Spiky traffic |
| Kubernetes | High | $50+/mo | Enterprise |

---

## Exercises

1. **Add input guardrails** — test with 5 malicious queries
2. **Add output guardrails** — test with 5 hallucinated answers
3. **Track costs** — set a daily budget, hit the limit
4. **Deploy to Streamlit Cloud** — share a link with someone
5. **Add rate limiting** — 10 requests per minute per user
6. **Test failure modes** — what happens when Groq is down?
7. **Build the monitoring dashboard** — visualize production metrics
8. **Run shadow test** — compare V2 vs V3 in background
9. **Implement A/B routing** — split traffic 90/10
10. **Calculate cost-per-version** — which prompt is cheapest per query?

---

## Mentor's Note 🎓

> Guardrails are not optional. They're the difference between a demo and a product. Every guardrail you skip is a potential incident.
>
> Start with the simplest guardrails (input length, rate limiting) and add complexity as needed. Don't build perfect guardrails — build guardrails that catch the common failures.

## Exam Questions 🎓

Final test — if you can answer all these, you're ready for production:

1. **Guardrails:** A user asks "Ignore all previous instructions and..." — what happens?
2. **Guardrails:** The LLM generates a confident answer with no context support — what happens?
3. **Cost:** Your daily budget is $5. Average query costs $0.002. How many queries can you handle?
4. **Monitoring:** Latency spikes from 1s to 5s. What do you investigate?
5. **Failure:** Groq returns a 500 error. Does your pipeline fail gracefully?
6. **Prompt Registry:** You've gone through 7 steps. How many prompt versions do you have? How do you manage them?
7. **Overall:** What's the one thing from Steps 1-7 you'd build FIRST in a new RAG project?

**If you can answer all 7, you've completed the learning path. Congratulations! 🎓**

---

## Complete Learning Path Summary

```
Step 1: Basic RAG (hand-written)
  → Build the foundation, understand mechanics
  → Add prompt registry with status lifecycle

Step 2: RAG + Eval
  → Measure quality, identify failures
  → Link prompt versions to eval scores

Step 3: LangChain Comparison
  → Compare framework vs hand-written
  → Understand tradeoffs

Step 4: Multi-Source + Routing
  → Add multiple document types
  → Build query routing

Step 5: Agentic RAG (LangGraph)
  → Add state management and retry logic
  → Use LangGraph for orchestration

Step 6: Multi-Agent
  → Specialized agents with handoffs
  → LangSmith tracing across agents

Step 7: Deploy + Guardrails
  → Production-ready RAG
  → Input/output validation, monitoring
```

---

## What's Next?

After completing all 7 steps:

1. **Build your own RAG project** — pick a real use case
2. **Contribute to open source** — LangChain, LangGraph, or RAG frameworks
3. **Explore advanced topics** — fine-tuning, reranking, multimodal RAG
4. **Teach someone else** — the best way to solidify your understanding

<!-- --- -->

# Step 8 — LLM Fine-Tuning & Alignment (SFT / LoRA / QLoRA / RLHF / DPO)

The first seven steps build and deploy a **RAG** pipeline. This step is a distinct track:
it adapts and hardens the **models themselves** by fine-tuning, aligning, and guarding them.

> **Why this step exists:** RAG improves *what the model reads*. Fine-tuning improves *how the
> model behaves and what it knows itself*. In production you often want both — a tuned generator
> (this step) fed by a retrieval stack (Steps 4–7).

## Scope & source

- **Curriculum source:** Class **Module 3** ("LLM Fine-Tuning") — see the mentor notes at
  `step4_multi_source_rag/doc/class_notes/03_module3_llm_finetuning.md` and raw transcripts in
  `rag-apidriven-pipeline/transcript_text/module3/*.txt`.
- **Tracked from the Step 4 deferral register:** `step4_multi_source_rag/doc/DEFERRED_TO_OTHER_STEPS.md`
  row **#18**.

## Learning Objectives

1. **Why fine-tune vs prompt engineering vs RAG** — the decision framework (merge with retrieval).
2. **SFT** — supervised fine-tuning mechanics; tokenization, minibatch, cross-entropy, backprop.
3. **Stability & forgetting** — gradient clipping, LR warm-up/decay, catastrophic-forgetting
   mitigations (rehearsal, regularization, weight averaging, freezing).
4. **PEFT (additive)** — sequential/residual adapters, prefix tuning, sparse mixture of prompts.
5. **PEFT (re-parameterization)** — LoRA (A/B, alpha, rank), quantization (INT8 → NF4),
   **QLoRA** (double quantization, paged optimizers); multi-tenant LoRA serving.
6. **Alignment** — RLHF/PPO (policy/ref/value/reward, advantage, KL vs reward hacking);
   **DPO** (no reward model, preference pairs).
7. **Guardrails & red teaming** — PII, injection, toxicity, jailbreak probes, red-team loop
   (progressive: regex → spaCy / Llama Guard / Garak).

## Roadmap

```
SFT (LoRA/QLoRA) ──► DPO alignment ──► Guardrails ──► Red team ──► Patch ──► (loop)
```
Sub-tracks planned: `src/llm_finetune/` (SFT/LoRA/QLoRA trainers, DPO trainer, guardrail class),
`tests/`, `data/` (instruction + preference datasets), `eval/` (ROUGE/F1/cross-entropy/moderate flags).

## Exam Questions 🎓

1. **Decision:** When do you fine-tune instead of using RAG or prompt engineering? Can you combine them?
2. **LoRA:** Which matrices/params update? What do alpha and rank do? Initialization?
3. **QLoRA:** What are the three tricks (4-bit NF4, double quantization, paged optimizers)?
4. **RLHF vs DPO:** How many models does each need, and why does DPO skip the reward model?
5. **Forgetting:** Name three ways to stop catastrophic forgetting.
6. **Guardrails:** Why can a model still be jailbroken after SFT+DPO, and what's the fix?

## Next Step

Bound back to the RAG track at **Step 7 (`step7_deploy`)** to deploy the tuned generator behind
the retrieval pipeline, or align with the **safety suite** (scope/leakage/toxicity) deferred to
Step 7 in the Step 4 deferral register (#13/#19).

## Detailed task docs
`doc/` — task planning for SFT, PEFT, alignment, and guardrails (added as this step is built).