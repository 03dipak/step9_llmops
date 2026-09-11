# DECISIONS — Step 9 decision & deferral log

Purpose: every gap or fork is a **named decision**, never a surprise. Format:
`D### | decision | status (IN / OUT / mapped) | evidence`. Statuses are checked at each
module review.

## Decisions

| # | Decision | Status | Evidence / cross-ref |
|---|---|---|---|
| D1 | **LLMOps-first pedagogy** — the 8-pillar spine is the curriculum frame (measure vs decide: "a framework measures; LLMOps decides") | IN | `README.md`, `INTERVIEW_Q&A.md`, step4 §7 |
| D2 | **Agents write markdown only; learner writes every line of code** (notebook-first → promote) | IN | `AGENTS.md` (non-negotiable) |
| D3 | **Free stack**: local-first + Groq→Gemini + OpenAI-compatible judge + HF Spaces + GH Actions offline gate | IN | `README.md`, `SPRINT_PLAN.md` |
| D4 | **Goldens**: step4's sets stay frozen (green repo); step9 grows its own with a new `category` field | IN | `doc/task/01_data_testset.md`; step4 `eval/goldens/` |
| D5 | **Live evals are OUT of the gate** — gate = offline deterministic only; live subset = nightly informational | IN | Rejected external proposal (Perplexity "live eval in gate"); `SPRINT_PLAN.md` gate policy |
| D6 | **Judge**: pinned, shared across backends, throttled, JSON-mode + schema + salvage; excluded from the gate | IN | step4 `eval/judge.py:26-27`; `doc/task/02_prompts_judge.md` |
| D7 | **CLI entry deferred** — no `[project.scripts]` unless Mod 7 needs it | OUT | `doc/task/00b_uv_scaffold.md` |
| D8 | **Toolchain = uv**, mirroring step4 (uv_build src-layout, `[dependency-groups] dev`, pytest addopts `-m 'not integration'`) | IN | `doc/task/00b_uv_scaffold.md`; step4 `pyproject.toml` |
| D9 | **Judge endpoint for step9**: default `Qwen/Qwen2.5-7B-Instruct-AWQ` via `LLM_BASE_URL`; local Ollama `/v1` candidate — **verify in NB, not assumed** | **✅ verified** at Mod 00b (NB-000), 2026-09-10 — hosted endpoint PASS on first attempt; Ollama fallback documented, not exercised | step4 `config.py:43`; `doc/notes/00b_probe_notes.md` |
| D10 | **CLI gate numbers**: step4 SLO values (`SLO_P95_MS=3000`, `SLO_TTFT_P95_MS=1200`) are the starting baseline; recalibrate only with collected data | IN | step4 §7 pillar 5 |
| D11 | **Logs carry metadata/counts/ids, never content** (logutil invariant) — applies to the learner's logs too | IN | step4 `src/multi_source_rag/logutil/` + `step4:doc/task/00_logutil.md`; rejected Perplexity "log inputs/outputs" advice |
| D12 | **Per-module design + test-contract docs** live in `doc/design/0X_*.md` (LLD: files/interfaces/data flow + test-case matrix, contracts only, no code). Land **just-in-time** when the learner starts each module (00b, 01–07); Mod 0 has no LLD (read-only, `review` checklist instead). Reviewed by the module's primary role before build | IN | `doc/task/*.md` remain the binding contracts; design docs are implementation guides |
| D13 | **`doc/notes/` = the learner's workspace**, indexed in `doc/notes/README.md`: files land when their module runs; absent-until-produced is by design (not a broken link); committed as review evidence; markdown-only, no keys | IN | `doc/notes/README.md`; module references in `doc/task/00..07` |
| D14 | **Corpus = self-authored step-series docs only** (S1–S3: step1–8 README/doc bundles · S4: step4 `QA_DEEP_DIVES.md` · S5: step4/step9 README+AGENTS). External course material stays **out of the public repo** — zero provenance risk, fully interview-showable, no overlap between sources | IN | `doc/task/01_data_testset.md` (Source ids) |
| D15 | **Multi-source golden ids use `MS-Q\d+`** with union convention (`source: "S1+S3"`, `path` joined with ` + `, `ideal_context` = one contiguous excerpt per row; `must_contain` validated across the union). T-01-4 regex amended to accept `MS-Q\d+` | IN | `doc/design/01_lld_tests.md` (T-01-4); `doc/notes/01_corpus_plan.md` rule 5 |
| D16 | **Golden rows are authored by the `data`/`tester` roles** — `eval/goldens/*.json` is eval data, not application code; D2's no-go zones (`src/`, `tests/`, `jupyter_notebook/`, CI) do not cover it. Learner lane: NB-01 anchor-check script + all application code + interview defense of the golden design (task 01 Q1/Q2). design/01:5 amended | IN | `doc/design/01_lld_tests.md` (header); `AGENTS.md` role map (`tester`, `data`) |
| D17 | **External AI advisor replies are external reviews = checkpoints, not verdicts** — every claim verified against the actual repo before adoption; adopted claims fold into docs. Tracked in `doc/learn/02_external_advisor_replies.md` (replies to claude.ai & perplexity.ai, 2026-09-11) | IN | `AGENTS.md` house rule (external reviews); `doc/learn/02_external_advisor_replies.md` |
| D18 | **`tools/goldens/*.py` = eval-data build tooling** — idempotent, portable (walk to `pyproject.toml`, zero hardcoded absolute paths), agent-maintainable, committed in-repo so a lost session never loses the recipes | IN | `tools/goldens/` (batch3/batch_routing/batch_correctness/t01_verify); `doc/learn/01_golden_dataset_authoring.md` §8 |
| D19 | **Committed golden set is closed** (retriever 139 / routing 67 / correctness 107, all in-band, `FAILURES: NONE`) — new rows only via a registered gap; practice goldens belong in a toy sandbox **outside** `eval/goldens/` (adopted from perplexity.ai's sandbox suggestion, declined its commit-file row drafting) | IN | `doc/DECISIONS.md` D16; `doc/learn/01_golden_dataset_authoring.md` §1 scope note |

## Deferral register (copied from step4 `GAP_REGISTER.md`, all OUT for step9)

| # | Item | Destination | Note |
|---|---|---|---|
| 8 | Semantic caching | Step 7 | Named, designed (front of pipeline), not built |
| 10 | LangSmith prod tracing | Step 7 | step9 ships metrics-to-compute |
| 13 / 19 | Full safety / injection / red-team suite | Step 7 | step9 slice: abstention + citation allowlist + circuit breaker |
| 14 | CI automation beyond the offline gate | Step 7 | step9 owns the offline gate workflow itself |
| 15 | Drift / MLflow monitoring | Step 7 | #25 embedding-drift *playbook* mapped, not built |
| 21 | Freshness / document versioning | Step 7 | named, not built |
| 22 / 23 | (step-7 items) | Step 7 | stay registered OUT |