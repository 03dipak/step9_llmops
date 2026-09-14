# Interview-Q&A — Step 9 rehearsal deck

Purpose: every answer is grounded in repos you actually built (step1–8, especially step4)
and decisions you actually made (gap register, deferrals, judge pinning). Rehearse out
loud. If an answer cites a path or number, verify it before the interview — the reviewer
role can check any of them.

---

## A. The "from scratch" narrative (the phase pipeline)

**Q. "How would you develop an LLM application from scratch?"** — the 8-stage story, each
stage with its artifact and its one-line answer:

| Stage | Artifact (yours) | One-liner |
|---|---|---|
| 1 LLD / design | `doc/JOURNEY_MAP.md`, package diagram (`src/llmops/config/`) | Three-model split (generation / judge / embedding), provider fallback ladder, src-layout package, notebook-first discipline |
| 2 Stack probe | NB-000 (`config_probe.ipynb`) | Prove the free stack *before* building: one Groq call, one Gemini call, one judge JSON call — evidence, not hope |
| 3 Build | `src/llmops/` package + thin engine | Config-as-package (six concerns), facade `__init__`, env-driven models, same public API as step4 (`generate_llm`, `judge_llm`, `embed_model_name`) |
| 4 Test cases | NB asserts + `tests/test_config.py` + L1/L2 offline evals | Golden rules first; offline determinism; gate exit codes; the 148-test precedent in step4 |
| 5 Gate / ops | `llm_eval_gate.yml` (offline-only) + nightly live | Baseline snapshot + `compare` → PASS(0)/FAIL(1)/REVIEW(2); tolerance ±0.03 judge, ±20% latency |
| 6 Cost | cost ladder in config; quotas-as-budget | Groq→Gemini fallback; judge pinned cheap; offline evals free; caching named-deferred (#8) |
| 7 Security | guardrails slice + no-secret rule | Env-only keys, content-free logs, abstention gate, injection suite deferred (#19) — honesty about scope |
| 8 Demo | HF Spaces Gradio + green CI badge + README | Three states visible: abstention, degraded source, conflict |

---

## B. Concept Q&A (per topic)

**Q. What's the difference between evaluation and LLMOps?**
**A:** A framework measures ("0.675"); LLMOps decides ("gate regressed → FAIL, exit 1") and
operates (budget, rollback, lifecycle). I keep the layers split: `eval/` measures,
`eval/regression/` + CI decides (§7 table).

**Q. Why is your judge pinned to one endpoint/model?**
**A:** The judge is the measurement instrument. If it drifts, metric changes look like
answer regressions. Pinned judge + throttle (~20 req/min, lock + spacing) + JSON-mode with
schema validation and salvage = a stable yardstick. One judge is shared by both DeepEval and
Ragas so backend swaps never change the instrument.

**Q. How did you pick which models to use?**
**A:** It's an LLMOps decision, not a preference: a **model-selection matrix** (D24) — I took
the free-tier leaderboard candidates within budget, ran them through the router API under the
same judge, scored them into a matrix, and picked the best per use-case per role (judge /
generation / embedding). Evidence lives in `doc/notes/03_model_selection.md`. Any later model
change is a registered decision, not a silent swap — same discipline as the judge pin.
**Check:** they can see the matrix is evidence-backed, not vibes.

**Q. How do you know the system got worse before a user complains?**
**A:** Three layers: (1) baseline snapshot from the last green run; (2) regression gate —
every metric has direction, kind (gate/guardrail/info) and tolerance (±0.03 judge, ±20%
latency) → verdict PASS/FAIL/REVIEW with an exit code; (3) SLO numbers (`SLO_P95_MS=3000`,
`SLO_TTFT_P95_MS=1200`) from Task-14 metrics-to-compute. Judge pinned so drift is signal,
not noise.

**Q. What happens when the gate itself breaks?**
**A:** The gate distinguishes a *regression* from a *broken measurement* (D36): exit code 3 = evaluation/input error (malformed report, unknown metric), exit 4 = configuration/baseline error (missing baseline, unresolvable `active.json` pointer). A broken gate fails loudly with diagnostics — it never silently passes and never masquerades as a regression. Guardrail REVIEWs (exit 2) are non-blocking by policy: CI maps them to a green job with a warning annotation, so soft targets alert without blocking merges.
**Check:** they can separate "the answer got worse" (exit 1) from "the gate can't measure" (exit 3/4) and know REVIEW is visible-but-green.

**Q. Why is the CI gate offline-only? You have real APIs available.**
**A:** A gate must be deterministic. Live LLM output has noise (±0.03 judge) and rate limits —
a flaky gate trains people to ignore it. So: L1 golden rules + L2 offline (deterministic
stub evaluators) block merges; a *live* eval subset runs nightly and is informational.
This exact trap ("put live evals in the gate") was proposed by an external AI consultation
and rejected for that reason.

**Q. How do you control LLM cost?**
**A:** A cost ladder, not a single API: Groq (fast free tier) primary with retry-once, Gemini
fallback; the judge is a cheap pinned model; offline evals cost nothing; rerankers are gated
by eval before they're enabled. Semantic caching is the next rung — registered as deferral
#8, deliberately not built in Step 4. Free-tier quotas in step9 *are* the budget — the
constraint teaches pillar 6.

**Q. How do you version prompts?**
**A:** A prompt registry with a composite key `prompt_id + source_type + version` and an
approve/rollback lifecycle — step4's `src/multi_source_rag/prompts/prompt_registry.json`.
Prompts are code:
versioned, reviewable, rollback-able, and the generation pipeline reads from the registry,
never from literals in `app.py`.

**Q. How do you secure an LLM application?**
**A:** Defense in layers, and honest scope: env-only secrets (never in files/notebooks), logs
carry metadata/counts not content, generation has an abstention gate ("I don't know"), a
citation allowlist, and per-source circuit breakers (Step-4 slice). The full injection /
toxicity / red-team suite is registered as #13/#19 and lives in Step 7 — saying "not in
scope, here's the register" is the answer they want.

**Q. Why config as a package, not a `config.py` file?**
**A:** The file crossed the one-concern threshold: env loading/validation, paths, provider
factory with fallback, judge wiring, embed naming, model defaults — six concerns in 232
lines. Package split with a facade `__init__` keeps `from llmops.config import generate_llm`
stable forever. Naming axis (D22): one module per **model role** — `judge.py`, `generation.py`,
`embedding.py` — plus cross-cutting `env.py`/`paths.py`; never vendor-named files
(`groq.py`/`gemini.py` would split one ladder into two and mix role+provider axes). Same
public API as step4 — the cross-references stay honest.

**Q. What's your testing strategy for an LLM system?**
**A:** Three layers. L1: deterministic golden rules (e.g., "must cite source", verbatim
`must_contain`) — no LLM, no flakes. L2: metric engines (DeepEval + Ragas, dual-backend over
the *same* pinned judge) with offline-capable evaluators for CI. Regression: baseline
snapshot + `compare` with tolerance. step4 sat at 148 tests / 93% coverage (verified 2026-09-10), with coverage
tracked but not gated — the gate is the verdict, not the percentage.
> Re-verify before interview day, don't cite from memory: run `uv run pytest -m 'not integration'`
> and `uv run pytest --cov=src/multi_source_rag -m 'not integration'` inside the step4 repo and
> read the numbers off the output.

**Q. RAG is especially vulnerable to prompt injection — what do you do?**
**A:** Acknowledge it, then scope it: the Step-4/step9 slice is abstention + citation
allowlist + circuit breaker + content-free logging. The *tested* injection/red-team suite is
deferral #19 to Step 7. In an interview, naming the threat and the register beats pretending
you've solved it.

**Q. How would you demo this in five minutes?**
**A:** One live URL (HF Spaces Gradio) showing three states — a grounded answer with
citations, an abstention ("I don't know") case, a degraded-source case — plus the green CI
badge next to README. The demo *is* the artifact: it renders the operating layer, not just
the RAG.

---

## C. The "say this about the series" answers

**Q. Your repos look like a course. What did you actually decide, not just build?**
**A:** (Pick three, always with the register reference.) (1) Platform tracing
(LangSmith/MLflow) deferred to Step 7 — step4 ships metrics-to-compute, and step2's early
tracing taught me *why* the series changed stance. (2) Semantic caching deferred (#8) —
named, designed in front of `build_pipeline()`, not built. (3) Live evals out of the gate —
deterministic gates only. Every one of these is a *decision* in `GAP_REGISTER.md`, which is
the point: gaps are decisions, not surprises.

**Q. What does your classroom teach that most courses skip — and what does it skip?**
**A:** The course taught eval metrics, LLM-as-judge, safety/jailbreaks, and gateway
observability deeply (18 transcripts verified). It never taught regression gates, baselines,
tolerances, or lifecycle rollback — pillars 4 and 7. Step 9 exists to close exactly that
gap, and so does step4's §7.

---

*House rule: every path, count, and number above was verified at writing time. Re-verify
before interview day; the `review` role can run a verdict pass on this whole deck.*