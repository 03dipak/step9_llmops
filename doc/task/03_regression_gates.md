# Task 03 — Regression Gates (Mod 3 — the mid-course core)

## LLMOps framing

- **Pillar 4** (regression & quality gates). This is the module that makes step9 *LLMOps*:
  measurement (Tasks 01–02) becomes **decision** — `metric_registry` → `compare` →
  PASS(0)/FAIL(1)/REVIEW(2), enforced by an **offline-only** CI gate (D5).
- **Why it matters:** "a framework measures; LLMOps decides." The green CI badge next to the
  README is the artifact interviewers believe.
- **Cross-ref:** `doc/DECISIONS.md` D5 · `doc/SPRINT_PLAN.md` gate policy · step4
  `eval/regression/` (run_suite → snapshot, metric_registry, compare) · step4 §7 Q2/Q3/Q5.

## Deliverables (your code; agents write docs + review)

1. **`src/llmops/eval/metric_registry.py`** (promote from notebook) — each metric carries
   `direction` (higher/lower) + `kind` (gate / guardrail / info) + `tolerance`; tolerances
   start at **±0.03 (judge metrics)** and **±20% (latency)** above measurement noise (step4
   §7). Gate = hard fail; guardrail = soft REVIEW; info = tracked.
2. **`src/llmops/eval/compare.py`** — diff candidate vs committed **baseline snapshot** →
   PASS(0) / FAIL(1) / REVIEW(2); exit code is the verdict. Error classes exit distinctly:
   3=eval/input error, 4=config/baseline error (D36).
3. **`src/llmops/eval/snapshot.py`** — serialize all metric scores + provenance into
   `eval/baselines/<id>.json` (step4's `run_suite`→snapshot pattern).
4. **`.github/workflows/llm_eval_gate.yml`** (you write it; contract here) — on PR:
   `uv sync` (pinned by `uv.lock`) → run offline L1 golden rules + offline L2 (stub
   evaluators, deterministic) → `compare` against baseline → required check.
   **No live API keys in this job.**
5. **`.github/workflows/live_eval_nightly.yml`** — scheduled, informational only: live judge
   run on a golden subset. **Never a merge gate.**
6. `tests/test_gates.py` — registry/compare/snapshot unit tests incl. one FAIL and one
   REVIEW reproduction.

## Depends on

- Task 01 (goldens = gate input) · Task 02 (judge harness for the nightly live subset).

## Gate policy (inherited, do not redefine)

| Kind | Meaning | Verdict | Exit |
|---|---|---|---|
| gate | must not regress | FAIL → block merge | 1 |
| guardrail | soft target | REVIEW (visible, non-blocking) | 2 |
| info | tracked only | never drives verdict | — |

## Exit criteria

- [ ] Offline gate workflow runs end-to-end in your repo (locally executable equivalent documented, since CI wiring is yours)
- [ ] Baseline snapshot committed; `compare` reproduces PASS and FAIL deterministically (unit-tested)
- [ ] A live nightly workflow exists (contract), flagged never-a-gate
- [ ] `uv run pytest tests/test_gates.py -q` green; ruff + mypy clean
- [ ] Goldens from Task 01 actually feed the gate (≥3 metrics surfaced per source)
- [ ] Gate error taxonomy asserted (D36): eval/input (3) and config/baseline (4) errors exit distinctly from verdicts; exit 2 = REVIEW non-blocking in CI

## Verify

```
uv run python -m llmops.eval.compare --baseline eval/baselines/<id>.json --candidate <report>
echo $?        # 0=pass, 1=fail, 2=review, 3=eval/input error, 4=config/baseline error (D36) — deterministic in CI
```

## Interview-Q&A (Mod 3)

**Q1. "How do you stop a regression before users see it?"** — Three layers: committed
baseline snapshot; every metric with direction/kind/tolerance; `compare` → exit code as the
required check. Judge pinned so drift is signal, not noise; tolerances sized above measurement
noise (±0.03 judge, ±20% latency) so the gate reacts to real regressions.
**Check:** they hear snapshot + verdict + tolerance, not "we run evals sometimes".

**Q2. "Why are gates offline-only when you have live APIs?"** — Determinism. Live LLM output
carries judge noise and rate limits; a flaky gate is worse than no gate (teaches bypassing).
Live subset runs nightly and informs; only deterministic evidence blocks merges (D5 — this
decision rejected an external AI's suggestion to gate on live evals).
**Check:** they hear a *decision* with a rejected alternative.

**Q3. "Gate vs guardrail?"** — Gate hard-fails (faithfulness pass-rate → FAIL, exit 1).
Guardrail is a soft target (latency P95 → REVIEW, exit 2). Info never drives the verdict.
Separating them keeps the signal honest: hard errors block, soft targets alert.
**Check:** they can classify any metric on the spot.

## Next module

Task 04 (Observability & cost) — after gate green.