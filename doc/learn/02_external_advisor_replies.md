# Replies to external AI advisors (claude.ai & perplexity.ai)

Context: on 2026-09-11 the golden dataset suite was reviewed by two external AI
advisors. Per house rule **"external reviews are checkpoints, not verdicts"**,
every claim they made was verified against the actual repo before adoption.
This file holds the replies we sent back, the verification evidence behind
them, and what was adopted vs declined (registered as D17–D19).

---

## Reply to claude.ai

> Your four-part framing of the guide (`doc/learn/01_golden_dataset_authoring.md`)
> is accurate with two refinements.
>
> **Confirmed (as you stated):**
> 1. The method (read corpus → hand-write judgment layer → `A()`-style
>    extractor with marker+contiguity asserts → mechanical `path` derivation →
>    independent verifier) is general-purpose for grounded RAG/QA eval datasets
>    from any text corpus.
> 2. The *contract* — 8-key schema, 7 categories, `S[1-5]-Q\d+|MS-Q\d+` ids,
>    the 120–160 / 60–75 / 100–120 bands — is repo-specific, sourced to
>    `doc/design/01_lld_tests.md`.
> 3. In this repo, authoring goldens is the `data`/`tester` role's job (D16,
>    `doc/DECISIONS.md:26`), not the learner's; the learner's deliverable is
>    the NB-01 verifier.
>
> **One refinement:** "the judgment layer isn't automatable" is over-stated.
> The *scripts* don't automate judgment — nothing in the doc claims they do —
> but the judgment *can* be exercised by an LLM acting as a careful reader
> (that's exactly how these goldens were authored; the FAQ says so at
> `01_golden_dataset_authoring.md:366-368`). What's non-negotiable is not
> "no LLM" but "no ungrounded rows": every excerpt and fragment is asserted
> verbatim against the corpus by the assembler/verifier.
>
> **Adopted:** your framing is now baked into the guide as a "Scope boundary"
> note in §1 (D17, this file).
>
> **Noted, not acted on:** nothing in your reply was declined; the boundary
> you drew matched the repo's actual design.

## Reply to perplexity.ai

> Your method advice is sound and mostly matches `doc/learn/01_golden_dataset_authoring.md`
> §1–§7. Three corrections, repo-verified:
>
> **1. The "only if" caveat is moot here — the examples are already grounded.**
> You said the guide's examples are "illustrations, not ground truth" and are
> valid "only if" the bundles contain them. We re-verified all three against
> the actual corpus, and they do — verbatim:
> - `MS-Q002` conflict → `s2_frameworks_bundle.md:87` `"Same embedding as
>   Step 2 (qwen3-embed, 1024-dim)"` vs `s1_early_steps_bundle.md:146`
>   `BAAI/bge-base-en-v1.5`
> - `S2-Q037` misroute → `s1_early_steps_bundle.md:1134` `"LangSmith offers
>   5,000 traces/month free"`
> - `S4:446` typo → `s4_qa_deep_dives.md:446` `findng, not a bug.`
> Your caveat is correct advice for *other* corpora; for this repo it was
> already satisfied. The guide's examples were extracted by the same
> anti-hallucination asserts as the goldens themselves (that's the point of
> the `A()` design, guide §5).
>
> **2. "Treat the doc as a method manual, not a data source" — adopted.**
> That's now an explicit "Scope boundary" note in the guide's §1 so no future
> reader treats the guide as the corpus.
>
> **3. "Draft 3–5 sample golden rows" — declined, on scope, not capability.**
> The committed golden set is **complete and closed**: retriever 139 / routing
> 67 / correctness 107, all in their target bands, all `FAILURES: NONE`,
> verified cross-file. Adding rows to `eval/goldens/` now would be an
> unregistered gap against a closed contract (registered as D19), and per D16
> golden authoring is the `data`/`tester` role's lane anyway.
>
> **The one part we did adopt from you: the toy-corpus sandbox idea.**
> Practice goldens belong in a toy corpus outside `eval/goldens/` (e.g. a
> `toy_bundle.md` + 5–10 rows + a mini verifier) — that's now the registered
> place for hands-on exercise (D19). If you want to help with that sandbox, we
> welcome it; we won't reopen the committed files.

---

## What was adopted vs declined (evidence)

| Advisor claim | Verdict | Evidence |
|---|---|---|
| Doc = method manual, not data source | **Adopted** → guide §1 Scope-boundary note | `01_golden_dataset_authoring.md` §1 |
| Examples need verbatim grounding | **Confirmed as already-true** | lines cited above, `grep -n` verified |
| Judgment layer "not automatable" | **Refined**: scripts don't automate it; LLM *can* do it carefully | FAQ `:366-368` |
| D16 lane (authoring = `data`/`tester`; learner = NB-01) | **Confirmed** | `doc/DECISIONS.md:26` |
| toy-corpus sandbox for practice | **Adopted** → registered D19 | `doc/DECISIONS.md` D19 |
| "Draft 3–5 rows into committed goldens" | **Declined** — closed set + lane | D19, D16 |

## Registered decisions (D17–D19)

- **D17** — External AI advisors' claims are external reviews = checkpoints;
  verified against the repo before adoption; adopted claims fold into docs.
- **D18** — `tools/goldens/*.py` is build tooling for eval data (idempotent,
  portable, zero hardcoded paths) — agent-maintainable, committed in-repo.
- **D19** — Committed golden set is closed at 139/67/107; new rows only via a
  registered gap; practice goldens live in a toy sandbox outside
  `eval/goldens/`.