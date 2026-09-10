# SPRINT_PLAN — Step 9 (LLMOps capstone map)

Execution order comes from this file only. Each module = one task doc + one notebook
(your code) + promotion + review.

## Module plan

| Mod | Task doc | Primary role | Cross-cutting | Depends on | Exit criteria (summary) |
|---|---|---|---|---|---|
| 0 | `00_llmops_foundations.md` | `mentor` | `writer md` | — | notes file: measure-vs-decide, 8 pillars, 3 deferrals; Interview-Q&A answerable |
| 0b | `00b_uv_scaffold.md` | `builder` (you) | `review` | 0 (learning sequence — no technical dep) | `uv init` src-layout; `uv sync` green; ruff+mypy clean; `.env` never committed; NB-000 stack probe (D9 decided) |
| 1 | `01_data_testset.md` | `data` | `tester`, `review` | 0b (package for anchor checks) | goldens: 120–160 retrieval, 60–75 routing, 100–120 correctness; 100% grounded; categories present |
| 2 | `02_prompts_judge.md` | `builder` (you) | `security`, `review` | 0b, 1 | prompt registry slice; judge probe green; judge excluded from gate (recorded) |
| 3 | `03_regression_gates.md` | `tester` | `ops`, `planner` | 1, 2 | offline gate workflow; baseline snapshot; compare → exit code; nightly live informational |
| 4 | `04_observability_cost.md` | `ops` | `data`, `security` | 3 | SLO metrics (stage-split latency, TTFT, cost/query); cost ladder; free-tier quotas as budget |
| 5 | `05_guardrails.md` | `security` | `ux` | 2 | abstention gate; citation allowlist; circuit breaker; PII-minimal metric; #19 named OUT |
| 6 | `06_lifecycle.md` | `planner` + `ops` | `writer md` | 3, 4 | prompt approve/rollback demo; snapshot→verdict→promote flow; rollback exercised once |
| 7 | `07_demo_ui.md` | `ux` | `builder` (you) | 5, 6 | Gradio on HF Spaces showing abstention / degraded / conflict states; batch citations |

## Execution order (dependency-first)

```
00 → 00b → 01 → 02 → 03 → 04 → 05 → 06 → 07
        └────┬────┘    │     │     └──┬───┘
             └── 01 feeds 03 & 04; 02 feeds 03 & 05
```

No module may start before its dependencies are green. `review` ends every module
(cross-cutting habit from the house rules).

## Standing decisions (details in `doc/DECISIONS.md`)

- Agents write markdown only; **you write all code** (notebook-first → promote).
- Free stack: local-first (`uv` + `src/llmops/`) · Groq primary → Gemini fallback ·
  judge via OpenAI-compatible endpoint (local Ollama candidate — verify in NB, not assumed) ·
  HF Spaces demo · GitHub Actions offline-only gate.
- `deepeval==2.9.3` / `ragas>=0.3.1` enter at Mod 2/3 (same pins as step4).
- Deferrals carried OUT: #8 semantic caching · #10 LangSmith · #13/#19 safety+injection ·
  #14 CI automation (step9 owns the *offline* gate) · #15 drift/MLflow · #21 freshness ·
  #22/#23 step-7 items.

## Gate vs guardrail policy (inherited, step4 §7)

**Gate** must not regress (hard fail → exit 1). **Guardrail** = soft target (REVIEW → exit 2).
**Info** = tracked, never drives verdict. Tolerances: ~±0.03 judge, ~±20% latency — above
measurement noise.