# Portfolio P2 — Brand Guardian Hardening Retrofit (post-step9)

> Status: DRAFT slip (D34/D35) · Owner: learner · Agents: docs + review only (D2).
> This is a **post-step9 portfolio item**, deliberately OUT of step9 Mod 0-7 scope
> (D35: no exit criterion of any step9 task is touched by P2).

## LLMOps framing

- **Pillar 4 (gates) + the trust OS.** The reference repo pulled in
  `Codes_and_docs/.../ComplianceQAPipeline` is a 1050-line production-shaped pipeline
  (FastAPI + LangGraph 2-node linear DAG + Azure Search RAG + Azure Video Indexer) that
  ships **without measurement**. Its five defects are the exact anti-patterns step9's
  machinery exists to fix (D35).
- **Why it matters:** the learner already owns an OS (judge + registry + gate + guardrails).
  P2 is the proof that the OS **retrofits onto someone else's broken pipeline** — the
  strongest possible "I ship LLMOps, not RAG" interview story, and it exercises Mods 2-6
  in one bounded unit.
- **What it is NOT:** the D34-rejected multimodal clone. Video modality is out; the point
  is **verdict-as-mechanism on a real broken pipeline**.

## Verified defect baseline (all evidence from the BG repo, D35)

| # | Defect | Evidence |
|---|---|---|
| BG-5 | Hardcoded f-string system prompt, no registry | `nodes.py:112-136` |
| BG-6 | regex fence-strip + bare `json.loads`, no schema/salvage | `nodes.py:150-162` |
| BG-7 | `final_status` PASS/FAIL is a report *field*, never a mechanism | `state.py:33` · `server.py:191` |
| BG-9 | Logs raw LLM response + `str(e)` to clients | `nodes.py:163-170` · `server.py:206-210` |
| BG-10 | Ghost deps declared, never imported | `pyproject.toml:13,20,21,25,27-29` (firecrawl/streamlit/redis/psycopg2/sqlalchemy) |

## Deliverables (learner code; agents write docs + review)

1. **Fork the OS, don't rebuild the domain**: copy step9's judge facade + registry +
   `metric_registry → compare → PASS(0)/FAIL(1)/REVIEW(2)` (design/03:14-17,127-145) into
   the P2 repo. Change nothing in step9's `src/`.
2. **Registry the auditor prompt** — extract `nodes.py:112-136` into a versioned registry
   prompt (`auditor_generic_1.0.0`, mirroring D31's approve/rollback pattern).
3. **Schema + salvage** — typed audit result (schema validation, 1 re-prompt salvage),
   replacing the regex `json.loads`.
4. **Verdict-as-mechanism** — resolve/compliance verdict becomes a gate exit code, not a
   string field; system-failure ≠ compliance-FAIL (split the FAIL conflation).
5. **D11 sweep** — zero content in logs, no `str(e)` to clients; add `.gitignore` `.env`
   rule (the BG repo lacks it and carries a real `.env` — do NOT copy that file or the
   `:Zone.Identifier` ADS siblings into a repo).
6. **Dependency hygiene** — strip never-imported deps; keep only what the walked code
   actually imports (verified: azure-storage-blob, azure-search-documents, langchain*,
   langgraph, fastapi, uvicorn, pypdf, yt-dlp, opentelemetry-fastapi, python-dotenv).
7. `tests/test_hardening.py` — one test per defect closed + one FAIL and one REVIEW gate
   reproduction.

## Depends on

- step9 Mods 2, 3, 5, 6 **build output** (judge/registry, gate, guardrail concepts,
  lifecyle) — i.e. P2 starts **after step9 Mod 7 closes** (per planner sequencing, D35
  context). Mod 7 is not a hard code dependency.

## Exit criteria

- [ ] All five defects (BG-5/6/7/9/10) closed with at least one red→green test each.
- [ ] Audit endpoint rebuilt on the forked OS; offline gate green on a committed baseline
      snapshot; one deliberately-introduced regression caught → FAIL → rollback shown.
- [ ] `uv run ruff check .` + `uv run mypy .` clean; zero content in logs.
- [ ] No step9 file modified (P2 lives in its own repo / branch).

## Verify block (runnable)

```bash
cd <p2-repo>
uv run pytest tests/test_hardening.py -q
uv run ruff check . && uv run mypy .
uv run python -m llmops.eval.compare --baseline eval/baselines/bg_v1.json --candidate <report>; echo $?   # 0/1/2
```

## Sequel path (D34/D35)

P2's hardened grading pattern is what P1 (vertical grading layer, SEC/finance) transplants;
P3 (eval-runner agent, propose ≠ apply) and P4 (judge LoRA, held-out human labels) sit
parallel/after. Sequence verified in the six-agent synthesis (2026-09-13).