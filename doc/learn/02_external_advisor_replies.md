# Replies to external AI advisors (claude.ai & perplexity.ai)

> **Status (2026-09-11): CLOSED.** Both engagements converged — claude.ai
> conceded cleanly (round 2), perplexity.ai adopted the corrections with one
> lane correction logged (round 2). **No further discussion with either
> advisor.** If either returns with a round 3, the protocol is unchanged:
> external reviews = checkpoints; verify claims against the repo before
> adopting; fold adoptions into existing docs; decline scope creep. The D19
> closed-set policy and D16 lane boundaries are binding regardless of what any
> external advisor proposes.

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

---

## Round 3 — claude.ai Mod 2 gap analysis (2026-09-11)

> **claude.ai:** Provided an 11-point gap analysis for the Mod 2 LLD
> (`doc/design/02_lld_tests.md` + `doc/task/02_prompts_judge.md`), with an
> offer to draft the judge prompt and `JudgeResponse` pydantic model.

**Protocol applied:** D17/D20 external-review checkpoint. Every claim
verified against actual files (`doc/design/02_lld_tests.md`, step4
`eval/judge.py`, step4 `doc/notes/00b_probe_notes.md`).

**Adopted (9 of 11 — all folded into the LLD, registered as D25):**

- **Winner domain undefined** (#3): step4 probe notes show `"winner": "B"`;
  no source anywhere defines allowed values. Adopted: `winner: Literal["A","B"]`
  as the step9 binding domain — evidence-grounded, narrow. (ADL
  `JudgeResponse` definition added to LLD, claim 3.)
- **No prompt_id / source_type named** (#4): registry structure specified but
  prompt not named for the two required versions. Adopted: prompt_id =
  `judge_system`, two versions (v1.0.0 → approve → v1.1.0 → rollback); the
  review's offer to draft *content* was declined — content authoring is
  learner's lane per D2. (Naming added to LLD registry schema.)
- **No selection key** (#5): data-flow step 2 says "select approved prompt"
  without specifying how. Adopted: Mod 2 registry holds exactly one
  `(prompt_id, source_type)` — selection = the approved version of that pair;
  multi-key selection is OUT (Mod 6 lifecycle). (One-line scope statement
  added to LLD.)
- **NB-002 input source unspecified** (#6): golden-row source for the wiring
  demo never stated. Adopted: NB-002 uses one golden row from
  `eval/goldens/` (row id asserted in notebook assert). (One-line added to
  LLD data-flow annotation.)
- **`record_eval()` untested** (#7): matrix covers approve/rollback/unknown
  but not record_eval. Adopted: T-02-7a added — writes `eval_scores` dict
  + increments `run_count` by 1.
- **`_MIN_SPACING_S` undeclared** (#8): test T-02-3 references the constant
  but interface stub only shows `_lock` / `_last_send`. Adopted: `_MIN_SPACING_S:
  float = 60.0 / 18` added to `_JudgeThrottle` body.
- **JSON-mode fallback untested** (#9): T-02-5/6 test salvage, not the
  "endpoint ignores `json_object`" primary fallback. Adopted: T-02-5a added
  — mock endpoint ignores `response_format` → fence-strip + `json.loads`
  succeeds without salvage.
- **T-02-14 oracle soft** (#10): "(or D9-verified default)" defers the
  oracle to another doc. Adopted: T-02-14 now inlines D9's decision
  (`Qwen/Qwen2.5-7B-Instruct-AWQ`), with the cross-ref as evidence
  source, not oracle.
- **Role reviews unowned** (#1 + #11): all `⏳` before this review.
  Adopted: role-review table now closed with reviewer verdict (see
  `doc/design/02_lld_tests.md` post-D25 edits); ops: single-writer
  assumption acceptable for Mod 2; cross-process serialization OUT until
  Mod 6.

**Declined (2):**

- **Prompt content not specified** (#4, content part): the review offered
  to draft the judge prompt and `JudgeResponse` model. The
  `JudgeResponse` schema (winner domain, 0-10 scores) was adopted, but
  drafting the actual prompt text is **learner's lane (D2)**. Agents write
  markdown + interfaces; the learner writes all code including prompt
  text. The LLD defines *what* the registry holds (prompt_id = `judge_system`,
  two versions, approved/retired lifecycle); the learner authors the prompt
  *template* content inside that structure.
- **0-10 bound ungrounded** (#2): **already resolved as F-2** in commit
  `ec743e3` — labeled a step9 design choice, noted that the judge prompt
  must instruct the range, and probe notes (scores 7/9) are consistent.
  Already tracked, no new work.

**Declined (content, not gap):** "registry concurrency unowned" (#11):
documented as a *single-writer assumption* at save_registry design level.
For Mod 2 (single-process notebook workflow + offline tests on in-memory
dicts), this is acceptable. The ops role now signs off on this acceptance.
Parallel-CI writes to registry.json are structurally out of scope until
Mod 6 lifecycle (documented), not a gap to mitigate.

**Overall:** 9 of 11 claims were factual and verified; 1 already tracked;
1 was a D2-lane question (content, not gap). All adoptions folded into the
LLD; the engagement remains closed (D17 protocol — checkpoints, not
back-and-forth).

---

## Round 4 — lifecycle / registry-approval scope (perplexity.ai + follow-up, 2026-09-11)

> **External AIs (perplexity.ai, then a composed Gemini/Microsoft-style
> follow-up):** two answers on the Mod 2 registry lifecycle. The first framed
> Mod 2 as *mechanism-only*: approve/rollback are status flips, `record_eval`
> is a data hook, full golden-eval is Tasks 12–13. The follow-up agreed and
> added the *production* view: "tests must run first — evaluate draft vs
> goldens → `record_eval` → threshold → approve," plus a pairwise-judge eval
> spec (accuracy, position-bias, score calibration).

**Protocol applied:** D17/D20 checkpoint. Claims verified against
`doc/design/02_lld_tests.md` (LLD), `doc/task/0{1,2,3,6}*.md`,
`doc/SPRINT_PLAN.md`, and `doc/GAP_REGISTER.md`. Five role-relevant facts
pulled from the two answers and checked:

1. **"Mod 2 register tests are offline/deterministic mechanism tests"** —
   CONFIRMED. LLD tester row: "all offline except T-02-13/13a/14
   (integration-marked)." ✅
2. **"`approve`/`rollback` never parse/compare/sort versions"** — CONFIRMED.
   `02_lld_tests.md:166`: they flip the status flag only. ✅
3. **"`eval_scores` + `record_eval` are data hooks, not a Mod-2 decision
   gate"** — CONFIRMED. T-02-7a uses dummy `accuracy=0.82, latency_ms=400`. ✅
4. **"Position-bias swap (A/B + B/A) needed; score calibration needed;
   approval needs a threshold policy"** — genuinely NEW, absent from every
   repo doc (grep: position/swap/calibrat/threshold → zero hits except
   unrelated D10/D5/D3 mentions). This is the D20 standing channel working
   a second time (first: D5/D11).
5. **Proposed key naming `judge_pairwise_v1/v2`** — DECLINED. Conflicts with
   the registered D25 naming (`judge_system_generic_1.0.0`, underscores,
   semver, no V-prefix).

**Adopted → registered:**

- **D28** — Position-bias mitigation (A/B + B/A both orders) for the pairwise
  judge. Mentor-ruled an *evaluation-time* manipulation, not a golden-schema
  change (Mod 1 golden schema stays frozen). Folds into **Mod 3**
  methodology.
- **D29** — Score calibration (flawless→8-10, hallucinated→≤4) as a Mod-3
  **guardrail** metric (soft REVIEW, not a hard gate). Schema-neutral.
- **D30** — Approval-decision policy layer (`MIN_ACCURACY_THRESHOLD` +
  latency-in-budget) lives in **Mod 6** promote flow, NOT in Mod-2's
  threshold-free `approve()`. This is precisely the step between
  `record_eval` (evidence) and `approve` (decision) the LLD deliberately
  separates (`02_lld_tests.md:166`).
- **D31** — Mod 2 ships ONE approved judge prompt (`judge_system_generic_1.0.0`);
  v1.1.0 stays a draft freelab only for the mechanism demo on a scratch copy.
  Folds the follow-up's "production = evaluate-first" concern into its real
  home (Mod 3/6), keeping Mod 2 scoped to mechanism proof.
- **D32** — "One prompt checks retriever & all": the single approved judge
  prompt is the only judge across every source/category; per-category golden
  subsets feed separate `metric_registry` rows. Confirms the follow-up's
  "same dataset, same pairs, same harness, different prompt" is a Mod-3
  comparison, not a Mod-2 multi-prompt scope.

**Mapping correction (honest, mentor):** earlier drafts of this round aimed
the gaps at "Task 12/13" (step4's numbering). Verified: step9's eval
lifecycle lives in **Mod 3** (regression gates) and **Mod 6** (lifecycle);
the three gaps were re-anchored to those modules before registering.

**Overall:** 1 claim confirmed, 3 genuinely-new gaps adopted as D28–D30 and
folded (D31/D32 scope), 1 naming proposal declined. All grounded in the
actual task map; no golden-schema reopened, no dependency reorder.