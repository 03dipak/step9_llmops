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

---

## Round 5 — Mod-3 regression-gates LLD review (perplexity.ai + claude.ai + gemini + five in-repo role lenses, 2026-09-14)

> Scenario: `doc/design/03_lld_tests.md` (the Mod-3 regression-gates LLD) was
> reviewed by three external AI advisors (perplexity.ai, claude.ai, gemini) as
> an external checkpoint per D17/D20, then by the five in-repo role agents
> (reviewer, tester, ops, security, planner). Everything below was verified
> against the actual repo before adoption; external claims are checkpoints, not
> verdicts.

**What was reviewed:** the Mod-3 LLD — `metric_registry` schema + registered
rows, `run_suite` (offline deterministic), `snapshot` (baseline serialization),
`compare` (PASS/FAIL/REVIEW verdict engine), the file-layout projection, the
data-flow block, the test-case matrix, and the role-review table.

**Adopted (A–G advisor deltas + H1–H15 role refinements), summarized:**

- **Registry id-pattern broadened** to match the actual row ids
  (`eval.(gate|guardrail|info).<name>[(.suffix)]`, `.S[1-5]` source segment;
  `golden_rules` has no pillar segment — the pattern states that, not a fixed
  3-segment shape).
- **+2 latency rows registered with task-04 owner**:
  `eval.guardrail.latency.p95` (guardrail → REVIEW, exit 2) and
  `eval.info.latency.ttft_p95` (info, provenance only) — values arrive with
  Mod 4's SLO report (H15).
- **G4 counting convention** — per-source counts follow split-on-`+` (D15):
  retriever 143 (S1 34/S2 27/S3 28/S4 28/S5 26, 4 double-counts), correctness
  112 (S1 25/S2 22/S3 20/S4 24/S5 21, 5 double-counts); verified against
  `eval/goldens/`.
- **Misroute range corrected** 1–3 → 1–2 (verified S1 1, S2 2, S3 2, S4 2,
  S5 1); the LLD's own "1–3" was the error, fixed.
- **Exit taxonomy 0..4 (D36)** — verdicts unchanged (0/1/2); 3 = eval/input
  error, 4 = config/baseline error; argparse/system errors translated at the
  CLI boundary; CI maps exit 2 → green + ⚠️ annotation (non-blocking), 3/4 →
  red with distinct diagnostics, 1 → red regression.
- **Missing-guardrail skip rule (H2)** — a guardrail absent from the candidate
  is recorded in `detail`, never a verdict (avoids nightly-only guardrails
  keeping the gate permanently yellow).
- **E1 closure scan + extended deny-set** — transitive import closure of the
  four eval modules incl. `__init__` chains; deny-set adds `openai`, `httpx`,
  `requests`, `urllib`, `http.client`, `socket`.
- **E2/E3 seams** — any `os.environ`/`.env` read in the run_suite tree is a
  violation (incl. `EMBED_MODEL`, `LANGSMITH_*`); read-only + no-socket
  backstop.
- **CI outcome map + path-filter globset** (`eval/**`, `data/docs/**`,
  `src/llmops/eval/**`, `tools/goldens/**`, `uv.lock`).
- **active.json atomic + Mod-6 ownership** — canonical pointer rewritten
  atomically in the same commit as the baseline it points to; switch owned by
  Mod 6's promote flow (H15).
- **T-03-7/8 reworded** (boundary math now self-consistent; REVIEW fixture
  keeps all gate rows present-and-passing).
- **16 new matrix rows** added (17 → 33 total, re-derived at amendment; T-03-2a/2b/5a/5b/6a/8c/8d/8e/8f/9b/11b/11c/11d/13b/13c/13d).
- **Snapshot write-time completeness** (T-03-5a) + `schema_version`/`hashes`
  fields on the Snapshot dataclass.
- **INTERVIEW_Q&A buffer clause** — a new Q covers "the gate itself breaks"
  (D36 outcome classes), inserted in the master deck.

**Corrected checkpoints (advisor claims that didn't survive verification):**

- **claude.ai "45–50 hidden rows / too few rows"** — misread of per-source
  counts. Verified: the misroute sums are 1–2 per source (S1 1, S2 2, S3 2,
  S4 2, S5 1); the LLD's "1–3" was the actual bug, now fixed. Per-file totals
  are retriever 139, routing 67, correctness 107 (313 rows, closed set D19).
- **gemini float-arithmetic uncertainty** about `1.0 - 0.03` — reproduced on
  this platform: `1.0 - 0.03 == 0.97` exactly; the inclusive band means
  boundary tests are 0.97 PASS / 0.96 FAIL (computed bound).
- **gemini zero-sample (n=0 → 0.0 soft fallback)** — overruled by mentor: a
  typed error (exit 3/4) wins; a silently-zero metric would corrupt the gate
  (registered change, D19-analogous).

**Declined (with the standing reason):**

- baseline governance machinery — Mod-6 territory, D30
- structured comparison objects — post-step9, D34
- hypothesis property tests — no new dependency; deterministic unit rows suffice
- T-03-12 split — task-03 exit-criterion 4 scope
- network-disabled CI container — the offline seam is enforced in code, not by
  container topology (T-03-11/11b/11c/11d)
- n=0 → 0.0 soft fallback — typed error wins (above)
- blanket ignore-new-metrics — refined to gate-missing → exit 4, info-only →
  log
- `isclose` — inclusive computed-band boundary is already deterministic
- Snapshot-reuse with candidate marker — separate concerns kept separate
- 10-field Provenance — scope creep vs step4 parity

**Verdicts:**

- **reviewer** 28 ✅ / 3 ⚠️ / 0 ❌
- **tester** boundary-verified + 3 genuinely-new gap notes adopted
  (write-time completeness, empty-`must_contain` guard H8, binary-in-practice
  note H9)
- **ops** all-adopt incl. CI outcome map — 1 genuinely-new operational gap
  (required-check exit-2 semantics) folded into D36
- **security** all-adopt — closure-scope upgrade to E1
- **planner** no-reorder + 2 ownership lines (task 04 / task 06)

**Registered:** D36, D37 — this file's Round 5 is the D37 evidence.

---

## Round 6 — perplexity.ai (second review of the amended LLD, 2026-09-14)

> Scenario: the already-amended Mod-3 LLD (`doc/design/03_lld_tests.md`) got a
> second external checkpoint from perplexity.ai (D17/D20), 20 findings, all 20
> adopted as contract-precision amendments. Every claim was verified against
> the actual repo before adoption; external claims are checkpoints, not
> verdicts.

**What was reviewed:** the round-5-amended LLD — required-check workflow
contract (workflow contract paragraph), file layout projection, `metric_registry`
schema, `run_suite` rules, `snapshot` serialization + canonical pointer, `compare`
docstring + CLI, and the 33-row test-case matrix.

**Adopted (20/20), summarized:**

- **Required-check deadlock fixed (workflow contract + T-03-13b/13d):** a
  path-filtered `pull_request` trigger gets skipped when the globset is
  unchanged, leaving the required check Pending and blocking merge (verified:
  docs.github.com, troubleshooting-required-status-checks). The `llm-eval-gate`
  job now ALWAYS runs on `pull_request` + `workflow_dispatch`; the globset
  survives only as an INTERNAL detection set that no-ops with an annotation
  when nothing changed.
- **`active.json` pointer contract (file tree + snapshot + CLI):** pointer
  added to the LLD file tree; schema `{schema_version, baseline_id, path}`;
  path-safety rules (basename-only, `.json`, inside `eval/baselines/`, no
  traversal, target exists, `baseline_id` matches snapshot id); resolution
  before compare; CLI `--baseline <explicit>` vs `--active`; any violation →
  ConfigurationError → exit 4.
- **Snapshot manifest/hash contract:** `hashes: dict[str,str]` → explicit
  `goldens_sha256` + `corpus_sha256` (sorted relative paths + file bytes);
  `save_snapshot(path: Path | None = None)` — invalid default removed;
  write-time completeness = all 16 gate rows (guardrail/info optional);
  `meta` comment drops the judge mention (Mod 3 has no judge; live judge is
  nightly-only, D5).
- **`compare` contract sharpened:** returns ONLY `Verdict`; error classes are
  RAISED, `main()` maps them to 3/4 at the CLI boundary; unknown candidate
  metric id → **FAIL(1)** (not exit 3); duplicate candidate ids →
  EvaluationInputError → exit 3 — no dedupe-by-last-value, duplicates are an
  input error (supersedes a round-5 draft intent; `grep` confirmed no dedupe
  wording was ever committed to `doc/`).
- **Registry precision:** `value_domain: Literal[fraction, nonnegative]` field;
  tolerance validation `>= 0` (0.0-tolerance rows: `golden_rules`,
  `snapshot_rowcount`); relative tolerance requires baseline >= 0
  (zero-baseline × relative → exit 4).
- **data/docs scoping + provenance:** `data/docs/*` used ONLY by the
  `golden_rules` L1 invariant check via `tools/goldens/t01_verify.py`; corpus
  rides into provenance via `corpus_sha256`; all other gate rows are pure
  functions of the golden files.
- **Normalization contract:** NFC (`unicodedata.normalize`), line endings →
  `\n`, trim, PRESERVE case, case-sensitive substring via the shared t01_verify
  helper (313/313 non-empty `must_contain` intact).
- **JSON float serialization contract:** standard numbers (Python/uv only — no
  cross-language contract), never rounded, dict keys sorted, single trailing
  newline; determinism pinning kept.
- **Matrix precision (count stays 33):** T-03-1 compiled-id-regex assertion;
  T-03-5/5a hash renames; T-03-5b malformed-pointer battery (7 cases, all
  exit 4); T-03-11d deny-set EXACTNESS reframe (set equality, distinct from the
  T-03-11 traversal scan); T-03-13/13b/13d reworded (always-run/no-filter,
  source-provable-only); count note re-derived at 33.

**D17/D20 honesty note:** all 17 repo-fact greps confirmed before adoption
(tolerance `>= 0` rows, `meta` comment, `save_snapshot` signature, `hashes`
field); the round-5 "dedupe by last value" wording was a draft intent only —
no such string exists in `doc/`, and the LLD now states duplicates are an input
error. Scope stayed closed: no new modules, no reorder, no golden-schema change.

**Verdicts:** five-role conditional approval — LLD amendments adopted in
place; matrix re-verified at 33; re-verify contracts at NB-003 build per D21;
D36 amended (exit-3 bucket now lists duplicate candidate ids, not unknown
metric id) + D38 registered.

**Registered:** D36 (amended), D38 — this Round 6 is the D38 evidence.

---

## Round 7 — claude.ai + gemini (second reviews of the round-6-amended LLD, 2026-09-14)

> Scenario: the round-6-amended Mod-3 LLD (`doc/design/03_lld_tests.md`) got its second review
> pass from claude.ai (12 findings, 1 correctness bug + 11 contract/precision items) and gemini
> (approval, no changes) as external checkpoints per D17/D20. Everything below was verified
> against the actual repo before adoption; external claims are checkpoints, not verdicts.

**claude.ai — adopted (12/12):**

- **The S1 tolerance bug (real defect):** at ±0.03, retriever S1 (n=34) computes 33/34 =
  0.970588 > bound 1.00−0.03 = 0.97 → PASS, so S1 silently needed TWO flipped goldens to go red
  while every other source (n≤28) trips on one. Fixed: per-source agreement/answer_cited gate
  rows now use the **single-flip floor `1/(n+1)`** at the committed closed-set n (registry table +
  tolerance policy; T-03-6b real-fraction boundary + T-03-7 retoleranced in the matrix).
- **313-reconciliation line** — per-source gate rows cover 254 unique rows (retriever 139 +
  misroute 8 + correctness 107); residual 59 = query_processing non-misroute rows (cite 38,
  conflict 5, abstain 5, degrade 5, multi-source 5, basic 1); 139+8+107+59 = 313 (verified).
- **T-03-3c multi-source double regression** — one edited multi-source golden row regresses every
  listed source (D15 split-on-+).
- **sample_size coverage rule** (compare step 9): candidate gate-row n != baseline n → FAIL(1)
  coverage regression (shrink OR growth; 1/(n+1) floors hold only at the committed n).
- **t01_verify import seam** — golden_rules imports t01_verify as a module so T-03-11's
  transitive-closure scan covers it; subprocess invocation prohibited (would escape the scan).
- **T-03-8g unregistered-candidate-id test** — unregistered id in candidate → FAIL(1), never
  swallowed (round-6 reaffirmed).
- **T-03-8h both-missing precedence** — same gate missing from baseline AND candidate: step 2
  (candidate-missing) fires first → FAIL(1).
- **Concurrency `${{ github.ref }}`** (per-branch, PRs never cancel each other) +
  `workflow_dispatch` always runs the full suite (globset no-op applies to `pull_request` only).
- **T-03-2c empty-`must_contain` runtime guard** — EvaluationInputError → exit 3, schema
  unchanged; H8 now runtime-enforced rather than authoring-diligence.
- **T-03-6b real-fraction boundary test** (33/34 vs bound 1−1/35, complements T-03-6a).
- **T-03-5 asserts `git_commit` round-trip** (value or None preserved).
- **Matrix 33 → 39** re-derived (T-03-2c/3c/6b/8g/8h/8i added; count note + tester role cell).

**gemini — checkpoint confirm:** "contract finalized and ready for development". Implementation
nuances already covered in-house: AST transitive-closure incl. `__init__` facades = E1/T-03-11;
atomic `os.replace` = snapshot atomic note; raw float math / never-rounded + sorted-keys = the
determinism pinning. Correction adopted: gemini's "T-03-11a–d" mislabels — there is NO T-03-11a;
the seams are T-03-11/11b/11c/11d (labels re-checked; no LLD change needed).

**Verdict:** all 12 claude items verified and adopted; gemini approved without changes; D39
registered; matrix finalized at 39 rows for the NB-003 build; re-verify at D21.

**Registered:** D39 — this Round 7 is the D39 evidence.

---

## Round 8 — claude.ai (blocking review) + approvals (2026-09-14)

> Scenario: the round-7-amended Mod-3 LLD (`doc/design/03_lld_tests.md`) received one blocking
> review from claude.ai (12 findings, 6 blocking + 6 important, all adopted) plus two approval
> checkpoints — a second claude pass ("yes, ready to build") and another advisor approval (citing
> a stale 33-case count, corrected). Everything was verified against the repo before adoption per
> D17/D20; external claims are checkpoints, not verdicts.

**claude.ai blocking review — adopted (12/12):**

*6 blocking:*
- **`expected_sample_size` contract on `Metric`** — registered committed n is the source of truth;
  tolerance = 1/(expected_sample_size+1), never derived from the candidate's own sample_size
  (field `int | None`; guards against the S1 silent-hole recursion, claude #1).
- **Structural-first compare precedence** (11 steps) — sample-size check, unknown-id, and
  missing-gate checks run BEFORE any value comparison; both-missing → candidate-missing wins
  (unchanged from Round 7); FAIL>REVIEW>PASS stated explicitly (step 11).
- **Consolidated exit map** — unknown candidate metric id → FAIL(1) not exit 3 (regression,
  not infra); main() and T-03-9b updated.
- **Report envelope aligned** — `{schema_version, generated_utc, metrics}` matches snapshot's
  field name; `meta` stays snapshot-only; `version` removed from the candidate envelope.
- **data/docs + t01_verify interface precision** — `run_suite` reads `data/docs` in exactly two
  ways (corpus_sha256 manifest + t01_verify L1 checks); no free-corpus search exists anywhere in
  Mod 3.
- **Normalization ownership** — matching contract assigned to the shared t01_verify helper;
  committed t01_verify.py:53 currently performs RAW substring (line 53 confirmed) — implementing
  normalization inside that helper is an explicit NB-003 requirement surfaced 2026-09-14.

*6 important:*
- **T-03-13c reword** — valid baseline+pointer → PASS; broken → exit 4 (ConfigurationError),
  never "gate still exit 0" as a blanket promise.
- **Concurrency block** — `group: llm-eval-gate-${{ github.event.pull_request.number || github.ref }};`
  `cancel-in-progress: true`; each PR gets its own group; stale-run cancellation for same PR/ref.
- **T-03-11d subset semantics** — required deny-set ⊆ actual scanned deny-set; extending the
  deny-set is a registered-change action, not a test break.
- **Canonical-bytes determinism** — byte identity defined over the DETERMINISTIC subset
  (schema_version + sorted metrics); generated_utc excluded; T-03-2 and T-03-5 fixture-
  asserted accordingly.
- **One-flip-floor wording + platform-observation boundary** — T-03-6b reworded; T-03-6a
  extended to note decimal equality is a platform observation, not the portable contract.
- **golden_rules no-1.0-assumption** — compare never assumes a baseline value of 1.0;
  tolerance 0.0 = any strict degradation from the stored baseline fails.

**Approval checkpoints:**
- Second claude pass — "yes, ready to build"; two non-blocking notes: (1) 6b bound literal
  "n/(n+1)" (folded into the one-flip-floor wording); (2) `git_commit` cross-environment
  round-trip test (nice-to-have; not adopted — git presence is cheap-optional, None path already
  covered). Checkpoint correction: this pass cited "T-03-11a–d" — there is NO T-03-11a; the seams
  are T-03-11/11b/11c/11d (same mislabel as prior rounds, corrected here).
- Advisor approval citing "33 cases" — corrected: the matrix is 39 since Round 7 (re-derived,
  verified by grep-count); stale count is a checkpoint-only issue, not a regression.

**Verdict:** all 12 blocking corrections verified + adopted with zero matrix-count change
(matrix confirmed at 39, count note + tester cell byte-matched). D40 registered; LLD converged —
freeze for NB-003 build; re-verify at D21.

**Registered:** D40 — this Round 8 is the D40 evidence.

---

## Round 9 — perplexity.ai re-review of the round-8 LLD (2026-09-14)

> Scenario: the round-8-amended LLD got a fresh perplexity.ai pass. Verdict: "approved for
> implementation" with two minor edits and a set of small consistency fixes. All claims verified —
> external reviews are checkpoints, not verdicts (D17/D20). Registered as D41.

**Adopted (2 minor edits):**
- **argparse exit-code collision fixed** — argparse's NATIVE usage-error exit code is 2, which
  collides with REVIEW(2). The LLD now mandates a custom `ArgumentParser.error()` override so
  usage errors raise `EvaluationInputError` → exit 3, and states that argparse's native 2 must
  never escape (main() docstring + T-03-9b expected column).
- **Envelope wording** — verified already consistent from Round 8: the candidate envelope is
  `{schema_version, generated_utc, metrics: list[MetricValue]}` with `meta` Snapshot-only
  (Snapshot dataclass, line ~208). No edit needed; the advisor's `meta` inclusion proposal was
  DECLINED because `meta` is free-form/optional (golden counts, notes) and would break the
  canonical-bytes determinism contract (T-03-2). Advisory sole-owner confirmed.

**Adopted (small consistency fixes):**
- **run_suite docstring** now states the canonical-bytes rule (schema_version + sorted metrics;
  generated_utc excluded) in addition to the rules-section note.
- **`compare never rounds`** moved out of `validate_registry()` into the `compare()` docstring as
  an explicit INVARIANT (raw float math; no boundary-flipping rounding).
- **Data-flow diagram** now shows `--active` → `eval/baselines/active.json` resolution next to
  `--baseline <path>`.
- **T-03-2 exit-criterion label** reworded to "offline gate execution end-to-end" — explicitly
  NOT the D36 exit-1 regression code; T-03-14's "exit 1 end-to-end" label likewise relabeled to
  "task-03 exit criterion 1 (label, not the D36 exit-1 code)."

**No count change:** matrix confirmed at 39 (grep-count verified after edits); count note updated
to "count unchanged in Round-8" is retroactive — Round 9 also changed zero rows.

**Verdict:** LLD remains converged at 39 rows; Round 9 folded as contract-precision amendments,
no blocking remaining. Re-verify at D21.

**Registered:** D41 — this Round 9 is the D41 evidence.