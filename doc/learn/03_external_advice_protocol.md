# External Advice Protocol (D20) — how we use outside input to find gaps

> House rule (D20): **external advice is a standing gap-finding channel** —
> solicited or unsolicited advice from AI advisors, reviewers, other projects,
> course material, or community posts is treated as *input*, never as
> authority. Every genuinely-new gap it surfaces gets registered as a
> decision, even when the advice itself is declined.

## Why this exists

External advice is one of the cheapest, highest-yield gap detectors we have.
Two of this project's decisions were born from **rejected** external
proposals:

- **D5** — "live evals in the gate" (Perplexity proposal) → rejected, but the
  rejection produced the standing gate policy: *gate = offline deterministic
  only; live subset = nightly informational*.
- **D11** — "log inputs/outputs" (Perplexity advice) → rejected on the
  content-free-log invariant, and the rejection *named the invariant* that now
  applies repo-wide.

And from the 2026-09-11 golden-dataset review (both advisors):

- **D19** — perplexity.ai's toy-sandbox suggestion was **adopted** as the
  practice venue; its commit-file row-drafting offer was declined.
- **D17** — the intake/verification/response protocol below became explicit.

**Pattern:** even when the advice is wrong or out of scope, engaging with it
forces us to state *why* — and that statement is often a decision worth
keeping.

## The protocol (any project, any module)

1. **Log it** — capture the advice verbatim (or summarized) in the engagement
   record. Convention: `doc/learn/02_external_advisor_replies.md`-style file
   per engagement, or the DECISIONS row itself for one-off tips.
2. **Verify it** — every factual claim is checked against the actual repo
   (files, line numbers, contracts) before adoption. *Checkpoints, not
   verdicts* (house rule).
3. **Decide, don't drift** — for each claim, one of:
   - **Adopt** → fold into existing docs/tasks. No new work spawned by margin.
   - **Decline** → say why; the reason is the decision.
   - **Register** → genuinely-new gap becomes an IN/OUT decision row (D###),
     with evidence and target where deferred.
4. **Close the loop** — reply to the advisor (if a dialogue) with what was
   adopted vs declined and the evidence; mark the engagement CLOSED.
5. **Carry forward** — registered OUT items are the *starting gap register* of
   the next project. Do not re-litigate: a named+registered gap is a decision.

## Why rejected advice still registers

Scope discipline (house rule) says *updates but no scope creep*. External
advice that is out of scope for the current module is **not** silently
ignored — it is registered OUT with a destination (see the deferral register
in `doc/DECISIONS.md`). That is how this repo turned "don't build this now"
into "this is *decided* to be later, with an owner" rather than "forgotten".

## Boundary conditions

- **D16/D19 stay binding regardless of advice** — e.g. no external advisor's
  row-drafting offer reopens the closed golden set (D19) or overrides the
  authoring lane (D16).
- **Adopted advice is authored by us** — agents write docs; external drafts
  are input, not commit material.
- **No secrets** — external advice never introduces keys/tokens into files.
- **No provenance risk** — external course material stays out of the corpus
  (D14); advice informs decisions, it is not corpus content.