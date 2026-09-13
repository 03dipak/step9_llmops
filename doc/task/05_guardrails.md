# Task 05 — Guardrails (Mod 5)

## LLMOps framing

- **Pillar 8** (safety & guardrails). Step-4/step9 slice: **abstention gate** ("I don't
  know"), **citation allowlist**, **per-source circuit breaker**, **PII-minimal metric**.
  The full injection / toxicity / red-team suite is **#13/#19, Step 7** — named, mapped,
  deferred (never built, never forgotten).
- **Cross-ref:** `doc/DECISIONS.md` deferral register · step4 Tasks 10/11 (abstention gate,
  citation allowlist, circuit breaker) · step4 `eval_ops_pii` (PII metric).

## Deliverables (your code; agents write docs + review)

1. **Abstention gate** — generation returns a structured **"I don't know"** verdict (not a
   hallucination) when retrieval confidence / source coverage is below threshold; the demo
   (Mod 7) surfaces this as a distinct UI state. Threshold is a **tuned knob** — you must
   collect its effect on the Task-03 gate before and after.
2. **Citation allowlist** — every answer cites sources; a rule verifies cited ids exist in
   the retrieved set (unresolvable-citation rate folds into reliability metrics, Task-14
   pattern). Answers that cite nothing = abstain, not answer.
3. **Per-source circuit breaker** — a failing source (repeated errors / degraded) is isolated
   and the router degrades gracefully; surfaced as a "degraded source" state in the demo.
4. **PII-minimal metric** — an `info` metric scanning **generation outputs only** for
   PII-like patterns (emails, phone numbers); minimal by design — the *full* PII/red-team
   suite is #13/#19, Step 7. Source-side PII (raw transcript/OCR/video/text ingestion) is
   **out of Mod-5 scope** — it belongs to the Step-7 red-team suite, never into this metric.
5. `tests/test_guardrails.py` — abstain-on-low-confidence, citation-allowlist reject,
   breaker trip/recover, PII-flag; all deterministic, no network.

## Depends on

- Task 02 (judge + prompts feed the abstention decision) · Task 04 (reliability hooks).

## Contracts (reference, don't redefine)

- Abstention and citations are **product-visible states** (see Task 07 — the UI renders
  them) — the guardrail is not a silent filter, it is surfacing (step4 Task-16 pattern).
- Circuit breaker is per-source, not global (a bad web source must not kill the text source).

## Exit criteria

- [ ] Abstention triggers a structured verdict; threshold effect on gate measured (before/after recorded in `doc/notes/05_guardrail_notes.md`)
- [ ] Citation allowlist rejects unresolvable citations; unresolved rate in reliability report
- [ ] Circuit breaker trips on injected per-source errors (test), recovers, routes around the source
- [ ] PII-minimal metric flags (test case: email/phone in output); full suite named OUT (#13/#19)
- [ ] `uv run pytest tests/test_guardrails.py -q` green; ruff + mypy clean

## Verify

```
uv run pytest tests/test_guardrails.py -q
# demo script: 1 abstain case, 1 bad-citation case, 1 degraded-source case — all rendered
```

## Interview-Q&A (Mod 5)

**Q1. "How do you make an LLM say 'I don't know'?"** — An abstention gate before generation:
retrieval confidence + source coverage below threshold → structured "I don't know" verdict,
surfaced as a UI state, never a hallucination. The threshold is a tuned knob whose effect on
the regression gate I measured before/after — it is a *decision with data*.
**Check:** abstention as an engineered state, not a prompt instruction.

**Q2. "RAG is especially vulnerable to prompt injection. What do you do?"** — Name the threat,
then scope honestly: my production slice is abstention + citation allowlist + per-source
circuit breaker + content-free logs. The tested injection/red-team suite is deferral #13/#19
to Step 7 — saying "it's in the register, with where it goes" beats claiming I solved it.
**Check:** threat named + register referenced, no overclaiming.

**Q3. "How do you prevent citation fabrication?"** — A citation allowlist: every cited id
must exist in the actual retrieved set; unresolvable-citation rate is a reliability metric,
and an answer with zero citable context abstains instead. Fabricated-looking citations are
therefore structurally rejected, not post-hoc caught.
**Check:** structural prevention, not "we LLM-check it".

## Next module

Task 06 (Lifecycle) — after guardrail states exist (Mod 7 renders them).