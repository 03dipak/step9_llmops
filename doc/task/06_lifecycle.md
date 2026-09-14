# Task 06 — Lifecycle (deploy / rollback) (Mod 6)

## LLMOps framing

- **Pillar 7** (lifecycle: CI/CD, deploy, rollback) — the LLM-aware CI story. step9 owns the
  **offline gate workflow** (D5); CI *automation beyond it* stays Step 7 (**#14**).
- **Why it matters:** the lifecycle closes the loop the class never taught (transcripts
  cover eval/safety/cost; pillars 4 & 7 are the gap step9 exists to fill).
- **Cross-ref:** `doc/DECISIONS.md` D5/D7 · `doc/task/03_regression_gates.md` ·
  step4 Task 17/18 (closure: baseline snapshot + verdict + deferral review).

## Deliverables (your code; agents write docs + review)

1. **Promote/rollback flow** — a change follows: branch → offline gate (Task 03) → if PASS,
   promote baseline snapshot (`eval/baselines/<new>.json` becomes canonical — the canonical switch rewrites `eval/baselines/active.json` atomically in the same commit as the new baseline (registered Mod 3, H15/D36)) → record in the
   prompt registry (Task 02 approve step). **Rollback exercised once**: revert a promoted
   change and show the gate re-verdicts the old baseline.
2. **Snapshot provenance** — every snapshot stamps source commit + goldens version + judge id
   (from registry provenance) so "which verdict belongs to which system state" is answerable.
3. **Deploy thin** — the promoted artifact runs the Mod-7 demo surface; no server
   management (HF Spaces). Deployment = registry approve + snapshot promote + gate green.
4. `tests/test_lifecycle.py` — a simulated lifecycle: change → gate → promote → rollback →
   gate; asserts snapshot identity changes and verdicts are deterministic.

## Depends on

- Task 03 (gate verdicts) · Task 04 (SLO info metrics ride along) · Task 05 (guardrails in
  the flow).

## Contracts (reference, don't redefine)

- A snapshot without provenance is not reviewable — provenance is required (source commit +
  goldens version + judge id).
- Rollback is a **demoed capability**, not a theory: one real rollback recorded in
  `doc/notes/06_lifecycle_notes.md`.

## Exit criteria

- [ ] Promote flow green end-to-end: branch → gate → snapshot promote → registry approve
- [ ] Rollback exercised once and recorded (with the gate re-verdict)
- [ ] Snapshot provenance fields present and asserted in tests
- [ ] Deploy thin story documented (registry + snapshot + gate = shipped)
- [ ] `uv run pytest tests/test_lifecycle.py -q` green; ruff + mypy clean

## Verify

```
uv run pytest tests/test_lifecycle.py -q
# manual: change a prompt → run offline gate → FAIL recorded → rollback → gate green again; baseline switch rewrites active.json in the same commit
```

## Interview-Q&A (Mod 6)

**Q1. "How is deploying an LLM app different from deploying normal software?"** — The unit of
deployment is a *verdict*, not just code: a change ships when the offline gate PASSes against
a committed baseline, the snapshot is promoted, and the prompt registry approves the version.
Rollback = revert registry + re-run gate. Normal CI deploys code; LLMOps deploys
code+prompts+goldens+judge as one *measured state*.
**Check:** "measured state" framing — system state, not just files.

**Q2. "How would you roll back a bad prompt/prod change?"** — Registry approve/rollback
lifecycle + baseline snapshots: roll the registry key back, re-run the offline gate against
the previous baseline, and the verdict tells you whether the rollback restored the numbers —
with provenance stamps so the audit answer is "commit X, goldens Y, judge Z".
**Check:** registry + snapshot + provenance, concrete.

**Q3. "What does 'done' mean in your lifecycle?"** — Gate PASS (hard) + guardrail REVIEW
reviewed (soft) + snapshot promoted + registry approved + demo state verified. And the
deferral register re-checked — closure is a review, not a checkbox (step4 Task-17 pattern).
**Check:** they hear closure-as-review (pillar 4 habit).

## Next module

Task 07 (Demo & surfacing) — renders everything above for an interviewer in 5 minutes.