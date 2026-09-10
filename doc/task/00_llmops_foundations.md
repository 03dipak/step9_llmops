# Task 00 — LLMOps Foundations (Mod 0)

## LLMOps framing (the lead — this is the whole point)

Step 9's pedagogy fixes a defect in the step series: LLMOps was added *after* the build.
This module makes the operating layer the frame. One line to memorize (source:
`step4/doc/QA_DEEP_DIVES.md §7`): **an eval framework measures; LLMOps decides and operates
(gate, rollback, cost).**

| | Evaluation (DeepEval/Ragas) | LLMOps |
|---|---|---|
| Question | "Is this response good?" | "Would I ship this? What does a regression cost? How do I roll back?" |
| Unit | a metric score 0–1 | a **decision** (PASS/REVIEW/FAIL), a budget, a policy |
| Output | `Report` | `snapshot` + verdict + cost model + lifecycle rule |
| Owner | eval task | the whole pipeline + the team |

## The 8 pillars (verbatim from step4 §7, with step9 mapping)

| # | Pillar | step4 evidence (verified) | step9 module |
|---|---|---|---|
| 1 | Data & testset (goldens) | `eval/goldens/` — grounded, verbatim-`must_contain` | Mod 1 |
| 2 | Prompt & template mgmt | `src/multi_source_rag/prompts/prompt_registry.json` — composite key `prompt_id+source_type+version`, approve/rollback | Mod 2 |
| 3 | LLM-as-judge | `eval/judge.py` — pinned endpoint, throttle (~20 req/min), JSON-mode + salvage | Mod 2 |
| 4 | Regression & quality gates | `eval/regression/` — `run_suite`→snapshot, `metric_registry` (direction/kind/tolerance), `compare`→PASS(0)/FAIL(1)/REVIEW(2) | Mod 3 |
| 5 | Observability / SLOs | Task 14 — `SLO_P95_MS=3000`, `SLO_TTFT_P95_MS=1200`, reliability, cost projection | Mod 4 |
| 6 | Cost ladder / efficiency | Groq→Gemini fallback; per-source `where` filters; rerankers gated by eval | Mod 4 |
| 7 | Lifecycle (CI/CD, deploy, rollback) | prompt registry approve/rollback; baseline snapshot; `compare` exit code = CI gate | Mod 3 + 6 |
| 8 | Safety & guardrails | minimal PII (`eval_ops_pii`); abstention gate; full suite → Step 7 | Mod 5 |

## Deliverables (markdown only — you write no code this module)

1. Read `doc/JOURNEY_MAP.md` and step4's `doc/QA_DEEP_DIVES.md` §6 + §7.
2. Write a personal 10-line "LLMOps in my words" note into `doc/notes/00_my_definition.md`
   (the folder exists — see `doc/notes/README.md`, convention D13). Include: the
   measure-vs-decide line, the 8 pillars, and *one* deferral (#8, #10, #13/#19, #14,
   #15) you can explain.
3. Complete the diff exercise from the AI consultations (answers live in `doc/notes/00_...`):

   - Gemini's 4 sections → which pillars do they hit? (You'll find: 1, 3, 6, 8 — never 4 or 7.)
   - Claude.ai's 10 modules → map each to a step1–8 repo (the Journey Map already does this).
   - Perplexity's 5 phases → which one is the "decision layer"? (Phase 3, Gate & Promote.)

## Depends on

- **None hard.** Read-only inputs: the step4 repo (its `doc/QA_DEEP_DIVES.md` §6/§7 and
  `eval/` tree) and `doc/JOURNEY_MAP.md` — both verified present (2026-09-10).

## Contracts (reference, don't redefine)

- Markdown-only this module: the note lives in `doc/notes/00_my_definition.md`, ≤ 20 lines,
  code-free, every claim verifiable against step4 files or the Journey Map.
- Deferrals are named with *why* — and `doc/DECISIONS.md` is the single source of truth for
  IN/OUT status. No ad-hoc deferrals outside the register.

## Exit criteria

- [ ] `doc/notes/00_my_definition.md` exists, ≤ 20 lines, contains the measure-vs-decide line
- [ ] You can name all 8 pillars and which step9 module owns each
- [ ] You can name 3 deferrals (#8/#10/#13-19/#14/#15) and say *why* they're deferred, not forgotten
- [ ] You can answer every Interview-Q&A below without notes

## Verify

Ask `review` to check: "did the notes stay code-free and claims verifiable?" Reviewer will
verify any path/quote you cite against step4's files.

## Interview-Q&A (Mod 0)

**Q1. "What is LLMOps, and how is it different from an eval framework?"**
**A:** An eval framework measures — it returns a score (0.82). LLMOps decides and operates on
that score: gate, rollback, cost budget, lifecycle. Concretely: Ragas says "0.675";
`metric_registry → compare` says "gate regressed → FAIL, exit 1". My stack separates the two
layers deliberately: `eval/` measures, `eval/regression/`+CI decides.
**Check:** interviewer hears "measure vs decide", not "it's monitoring".

**Q2. "Walk me through how you'd develop an LLM application from scratch."**
**A:** Five phases. Develop (notebook-first: prove each piece with simple LangChain code
before promoting to a package) → Evaluate (goldens + L1 deterministic rules + L2 metric
engines, offline-capable) → Gate & Promote (offline-only regression gate with baseline
snapshot; exit code = verdict) → Deploy (versioned prompts/models, thin demo surface) →
Monitor (metrics-to-compute: latency, cost, reliability; alerting deferred to Step 7).
**Check:** the phases come in dependency order and the *gate* is mid-course, not an epilogue.

**Q3. "Why notebook-first? Isn't that slow?"**
**A:** It's the fastest way to learn failure modes — you watch the free-tier API rate-limit,
watch a judge return malformed JSON, watch retrieval return nothing, *before* any of it is
hidden inside a package. Promotion then hardens the same cells into typed, tested modules.
My step-series is the evidence: every repo's `jupyter_notebook/` produced the `src/` it ship.

**Q4. "Why a code-free task doc? Where's the value?"**
**A:** The task doc is the contract (objective, LLMOps framing, exit criteria, interview Q&A)
— like a ticket. The code is mine to write. That split is itself an LLMOps lesson:
requirements-as-verifiable-contracts vs implementations-as-plumbing.

## Next module

Mod 1 ("Data & testset") — after `review` passes this module's notes.