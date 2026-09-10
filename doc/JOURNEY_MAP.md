# Journey Map — step1→step8 under the LLMOps spine

Purpose: every concept from the step series, filed under its LLMOps pillar and lifecycle
phase, with the step9 treatment (map / exercise / build). Source of truth for "step9 covers
everything" claims — each row is checked against the step repo's README, not remembered.

## Lifecycle phases (Perplexity's model, adopted)

**Develop → Evaluate → Gate & Promote → Deploy → Monitor**

## The map

| Step | Core concepts (verified from each README) | Feeds pillar(s) | Phase | step9 treatment |
|---|---|---|---|---|
| 1 · basic RAG | Chunking tradeoffs, embedding quality, retrieval failure modes, numpy similarity, Groq API | 1, 6 | Develop | Map + exercise: re-read chunking through the golden-testset lens |
| 2 · eval + LangSmith tracing | Golden dataset (20–30 Q&A), retrieval precision/recall, answer quality, tracing | 1, 3, 5 | Evaluate | Map + teach the tension: step2 traces; step4 defers platform tracing to Step 7. *Why did the series change stance?* (metrics-to-compute in, LangSmith out) |
| 3 · LangChain RAG | Framework comparison, LCEL, apples-to-apples vs hand-written | 6, 2 | Develop | Map: what frameworks add / hide |
| 4 · multi-source RAG | Routing, citations, dual-engine eval (DeepEval + Ragas), regression harness | 1–8 (anchor) | Evaluate + Gate | **Reference implementation** — most step9 exercises diff against it |
| 5 · agentic RAG | LangGraph, tools, retry, HITL, "retrieve, grade, retry" | 3, 7 | Develop | Map + exercise: agent loop = eval loop; judge-as-grader |
| 6 · multi-agent | Agent teams, LangSmith traces of decisions | 5, 7 | Monitor | Map: agent observability = pillar 5's hardest case |
| 7 · deploy + guardrails | Serving, guardrails in production | 7, 8, 5 | Deploy | Map — where step4's deferrals stop (#13/#19 live here, not in step4) |
| 8 · fine-tuning | SFT / LoRA / QLoRA / RLHF / DPO, alignment | 3, 1 + MLOps bridge | Develop+Evaluate | Map + teach the LLMOps-vs-MLOps line (weights/drift/GPU = MLOps; prompts/eval/production = LLMOps) |

## Classroom transcripts → pillar coverage (checked across all 18 sessions)

- **Covered well by the class:** eval metrics & LLM-as-judge (pillar 3 — M1-S5/S6, M2-S2/S3),
  prompt versioning (pillar 2 — M2-S2), safety/threat models + jailbreaks (pillar 8 — M1-S6,
  M3-S6), gateway observability + semantic caching theory (pillars 5/6 — M2-S5), embeddings
  bake-off / MTEB (pillar 1 — M2-S4).
- **Absent from the class (your moat):** regression gates, baselines, tolerances, rollback,
  CI lifecycle (pillars 4 & 7). This is exactly what step9 Mod 3 & Mod 6 teach, and what the
  three AI consultations (Gemini / Claude.ai / Perplexity) also missed.

## Explicitly OUT of step9 (the deferral register, copied from step4's GAP_REGISTER)

#8 semantic caching · #10 LangSmith prod tracing · #13/#19 full safety/injection/red-team
suite · #14 CI automation (step9 owns the *offline* gate; automation stays CI-native) ·
#15 drift/MLflow monitoring · #22/#23 step-7 items · freshness = Row #21. Everything here is
**named, mapped, and deferred** — not built, not forgotten.