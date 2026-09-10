# Task 07 — Demo & Surfacing (Mod 7)

## LLMOps framing

- **Pillar 7** (surfacing) — the product face of the operating layer. The demo renders the
  **states the operating layer produces**: abstention, degraded source, conflict — plus
  citations. No feedback capture in Step 4/9 (registered OUT). The live URL + green CI badge
  is the interview artifact.
- **Cross-ref:** `doc/DECISIONS.md` D3 (HF Spaces) · step4 Task 16 (minimal UI: chat-log
  schema, batch citations after streamed text, degraded-source + abstention states, conflict
  surfacing).

## Deliverables (your code; agents write docs + review)

1. **`app_ui/gradio_app.py`** (thin — this is a *surface*, the engine is `src/llmops/`) —
   three renderable states:
   - **abstention** — "I don't know" verdict shown distinctly (not an error, a state);
   - **degraded source** — circuit-breaker case surfaced with which source is degraded;
   - **conflict** — multiple sources disagree (step4 conflict surfacing pattern);
   plus batch citations shown *after* the streamed text (step4 Task-16 UX contract).
2. **Chat-log schema** — session/query/answer-id/score/citations/provenance (ids only, no
   content in persistent logs — D11).
3. **HF Spaces deploy config** — `spaces` README + app entry; DEMO_KEY-free (public demo
   uses env-seeded judge; no secrets).
4. `tests/test_ui_states.py` — the three states render given seeded engine responses
   (deterministic, offline — no live calls in tests).

## Depends on

- Task 05 (guardrail states) · Task 06 (lifecycle — the demo runs the promoted artifact).

## Contracts (reference, don't redefine)

- Citations batch after text (streaming-first, cite-after UX) — step4 Task-16 contract.
- No feedback capture (thumbs/ratings) in Scope: registered OUT for Step 4/9.

## Exit criteria

- [ ] Gradio app renders all three states from seeded inputs (deterministic)
- [ ] Chat-log schema honored (ids/counts/provenance; no content)
- [ ] HF Spaces URL live (public, no secrets) — or local `gradio` demo scripted if Spaces not yet reachable (recorded)
- [ ] `tests/test_ui_states.py` green; ruff + mypy clean
- [ ] 5-minute demo script written in `doc/notes/07_demo_script.md` (the story order you will actually say)

## Verify

```
uv run pytest tests/test_ui_states.py -q
# manual: gradio app up — show abstention, degraded, conflict, citations — live URL or scripted
```

## Interview-Q&A (Mod 7)

**Q1. "Show me / demo this in five minutes."** — Fixed order: grounded answer with batch
citations → abstention state ("this is the gate I engineered, not a prompt trick") →
degraded source (breaker working) → conflict surfacing → green CI badge + live URL next to
README. Every state maps to a module: gates, guardrails, ops, lifecycle.
**Check:** demo *narrates the operating layer*, not just RAG output.

**Q2. "How do you surface an LLM's uncertainty?"** — Abstention is a first-class product
state: the gate emits a structured "I don't know", and the UI renders it distinctly — the
user sees the boundary of what the system knows. Same for conflicts between sources: rendered,
not hidden.
**Check:** uncertainty/conflict as designed states (Task-16 UX pattern), not apologies.

**Q3. "Why no feedback buttons?"** — Feedback capture is registered OUT of Step 4/9 scope
(it implies a data flywheel + ML ops on the ratings). In scope: the states, citations,
scores, provenance. Naming what you deliberately did *not* build is as important as what you
did.
**Check:** scope discipline — the "not in scope, here's the boundary" answer.

## Next module

None — Mod 7 closes the spine. End every module with `review`; fold the closure pass
(deferral register re-check) into the final `review` per `SPRINT_PLAN.md`.