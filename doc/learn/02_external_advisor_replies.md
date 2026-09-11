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
> `01_golden_dataset_authoring.md:377-382`). What's non-negotiable is not
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
| Judgment layer "not automatable" | **Refined**: scripts don't automate it; LLM *can* do it carefully | FAQ `:377-382` |
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

---

## Round 2 — claude.ai's reply to our reply (2026-09-11)

> **claude.ai (verbatim):**
> "That's a fair correction, and it's worth being precise about what changes.
> What I got wrong: I wrote 'the judgment layer isn't automatable' in a way
> that implied it requires a human specifically. That's not what the doc says.
> ... the accurate version is 'not mechanizable by the dumb layer-2/3 scripts,
> but performable by a careful reader, human or LLM, as long as every claim it
> writes gets checked against disk before it counts.' ... The three-layer
> separation (author → assemble/assert → independently verify) is what makes
> an LLM-authored golden trustworthy despite LLMs being unreliable narrators
> of their own certainty — the scripts are the check on the LLM, not a
> replacement for something only humans can do. The other three points —
> method-general, schema/contract-specific to this repo, and the D16 role
> boundary — stand as stated."

**Verdict (repo-verified):** fully conceded and consistent with the guide.
Two factual claims checked:
- The FAQ quote it attributes (`guide:377-382`) is accurate: "No. The
  authoring is you reading and writing; the scripts only extract and assert."
- "313 rows" = 139 + 67 + 107 ✓ (verified against the three golden files).

**Our outcome:** adoption is already complete — the guide's §1 scope note and
the three-layer framing in §1 already say exactly what claude.ai converged
on. No further doc change needed; this round only re-verified and closed the
loop. If a future round proposes changing the guide's FAQ from "Do I need an
LLM? No." to a softer claim, the D17 record is the evidence that the current
phrasing was already the agreed one.

---

## Round 2 — perplexity.ai's reply to our reply (2026-09-11)

> **perplexity.ai (summarized):**
> "Understood — I'll treat the three corrections as binding. Going forward:
> (1) examples are documented as grep-verified verbatim; (2) this doc = method
> manual, not data source; (3) committed set is closed, D16 applies, toy
> sandbox is the registered practice venue. I can draft a Practice venue
> subsection for §9, or help refine wording."

**Corrections to note:** perplexity's point (3) states "D16 lane applies
(agents commit markdown only; code / new goldens are learner/owner work)" —
this conflates D16 with D2. D16 (`DECISIONS.md:26`) says the **opposite**:
golden rows *are* authored by `data`/`tester` roles (eval data, not app code;
D2's no-go zones `src/`, `tests/`, `jupyter_notebook/`, CI do not cover
`eval/goldens/*.json`). The actual reason new rows are declined is **D19
(closed set)**, not D16 — D16 would actually *license* agent-authored goldens.
If perplexity carries the D16 conflation into future guidance, its lane
assessment for golden authoring would be wrong.

**Factual check on its cited anchors:** all four lines re-verified this round
(S2:87, S1:146, S1:1134, S4:446) — all byte-exact in the corpus.

**Accepted from this reply:** the toy-sandbox "Practice venue" subsection idea
(D19-registered, already accepted in round 1). Authored by us (agents write
docs) and added as a subsection in §8 of the guide; perplexity's draft offer
was not needed — the content was D19-derived, not perplexity-specific. No new
scope: the subsection documents an already-registered decision, not an
external idea.

**Declined from this reply:** offer (b) "refine any specific paragraph to
reflect points (1) and (2)" — already done; our §1 Scope boundary note (D19)
and FAQ `:377-382` were written before this reply and are the binding
phrasing. The D17 record is the evidence.

**Overall:** perplexity's round-2 is substantially aligned; the only
correction needed was the D16-vs-D2 imprecision noted above.