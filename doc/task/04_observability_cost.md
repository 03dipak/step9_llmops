# Task 04 — Observability & Cost (Mod 4)

## LLMOps framing

- **Pillar(s):** 5 (observability / SLOs) + 6 (cost ladder / efficiency).
- **Why it matters:** you can only decide (gate, rollback, budget) on what you measure with
  numbers. step9 ships **metrics-to-compute** (latency, TTFT, reliability, derived cost) —
  platform tracing (LangSmith **#10**) and drift (**#15**) stay Step 7, named not built.
- **Cross-ref:** `doc/DECISIONS.md` D10/D11 · step4 §7 pillars 5/6 · step4 Task 14
  (`SLO_P95_MS=3000`, `SLO_TTFT_P95_MS=1200`) · step4 `config.py` (Groq→Gemini ladder).

## Deliverables (your code; agents write docs + review)

1. **`src/llmops/ops/metrics.py`** (promote from NB-004) — stage-split timing hooks:
   retrieval / rerank / generation, plus TTFT and total latency; counts (queries, sources hit,
   tokens); **no content ever** — logs carry ids/counts/keys only (D11, logutil invariant).
2. **Cost accounting** — per-source `where`-filter cost (cheap routing), per-stage derived
   cost (input/output tokens × provider price), exposed as `cost/query` per source.
   **Free-tier quotas are the budget**: the constraint is the pillar-6 lesson.
3. **SLO report** — `SLO_P95_MS=3000`, `SLO_TTFT_P95_MS=1200` (step4 values as the starting
   baseline D10 — recalibrate only from your own collected data); reliability = successful
   responses / total. Output: a JSON report the gate's `info` metrics consume.
4. **Cost ladder in config** — Groq primary → retry once → Gemini fallback (mirror step4
   `LLMProvider`, `config.py:132-206`); record which provider served each query (provenance).
5. `tests/test_metrics.py` — timing hooks deterministic with a stub clock; cost math unit
   tests; a no-content-in-logs assertion.

## Depends on

- Task 03 (gate consumes `info` metrics from the SLO report).

## Contracts (reference, don't redefine)

- Logging invariant: metadata/counts/ids only — **never** query text, documents, or answers
  (step4 logutil; rejected Perplexity advice D11).
- SLO values are starting baselines (D10), not carved in stone.
- Generation model defaults (`GROQ_MODEL`/`GEMINI_MODEL`) are grounded in the model-selection
  matrix (`doc/notes/03_model_selection.md`, D24) — the ladder's two rungs are chosen per
  use-case evidence, not picked by hand.

## Exit criteria

- [ ] Stage-split timing + TTFT + reliability computed and reported (JSON)
- [ ] `cost/query` per source with provenance (provider recorded per query)
- [ ] Free-tier quota budget documented in `doc/notes/04_cost_notes.md` (measured, not guessed)
- [ ] SLO report feeds the registered latency rows into the Task-03 gate: `eval.info.latency.ttft_p95` (info) + `eval.guardrail.latency.p95` (guardrail → REVIEW, exit 2) — both named in `doc/design/03_lld_tests.md` registry (H15)
- [ ] `tests/test_metrics.py` green incl. no-content-in-logs; ruff + mypy clean

## Verify

```
uv run pytest tests/test_metrics.py -q
# then, live (1 query): the SLO report JSON prints stage latencies + cost/query + reliability
```

## Interview-Q&A (Mod 4)

**Q1. "How do you control LLM cost?"** — A ladder, not one API: Groq free tier primary with
retry-once, Gemini fallback; judge pinned to a cheap model; offline evals cost nothing;
per-source `where` filters make cheap routing the default. Semantic caching is the next rung —
deferral **#8**, designed, not built. In step9 the free-tier quotas *are* the budget, so cost
governance is exercised, not theorized.
**Check:** cost as *decisions* (ladder, routing, deferral), not "we watch the bill".

**Q2. "What are your SLOs?"** — P95 total latency 3000 ms, TTFT P95 1200 ms (step4 values as
starting baseline), reliability = success rate, cost/query per source. Latency is a
**guardrail** (REVIEW if it slips ~20%) — soft target, not a hard gate.
**Check:** numbers + gate-vs-guardrail classification on the spot.

**Q3. "Why don't you log inputs and outputs?"** — The logutil invariant: metadata, counts,
ids — never content. Content logging is a PII and leak risk; you can debug a bad answer from
ids + scores + provenance without storing the words. (This directly contradicts common "log
everything" advice — and I chose the safer side deliberately.)
**Check:** security instinct + a *decision* against a popular pattern (D11).

**Q4. "No LangSmith? Really?"** — Platform tracing is deferral #10, Step 7. step9 ships
metrics-to-compute — the numbers the gate needs. Naming the boundary and why (Step-4 scope,
and step2 of my series already proved tracing's value) answers this better than pretending to
have a dashboard.
**Check:** honest scoping with a register reference.

## Next module

Task 05 (Guardrails) — needs judge (02); metrics hook into Mod 6 lifecycle.