# 01 — Corpus Plan (Mod 1, Data & Testset)

Task: `doc/task/01_data_testset.md`. Deliverable 1 of 4 (plan), followed by the three
golden files. step4's goldens stay frozen; step9 grows its own set (task 01:73-74).

## Sources (S1–S5) — inventory

Corpus root: `data/docs/` (committed in `03ecd77`). Each bundle = self-authored
step-series docs only (decision D14; no external material).

| id | Bundle file | Step sources | Lines | Chunk strategy | Golden budget |
|---|---|---|---|---|---|
| S1 | `data/docs/s1_early_steps_bundle.md` | step1 + step2 READMEs | 1638 | headings in `#`/`##`; one section per chunk; fixed-size fallback 512/50 | 32 |
| S2 | `data/docs/s2_frameworks_bundle.md` | step3 + step5 + step6 READMEs | 849 | headings in `#`/`##`; one section per chunk | 25 |
| S3 | `data/docs/s3_lifecycle_bundle.md` | step7 + step8 READMEs | 459 | headings in `#`/`##`; step8 dense sections split at `##` only | 26 |
| S4 | `data/docs/s4_qa_deep_dives.md` | step4 `doc/QA_DEEP_DIVES.md` (verbatim) | 520 | one Q&A per `##` heading — natural semantic units | 26 |
| S5 | `data/docs/s5_docs_bundle.md` | step4 README + AGENTS, step9 README + AGENTS | 546 | headings in `#`; AGENTS tables kept whole | 26 |

Budget total: 32+25+26+26+26 = **135 rows** (inside the 120–160 window, task 01:69).

## Golden schema (exact keys — checker must not see extras)

```json
{
  "id": "<source>-Q<seq>",
  "category": "cite | conflict | misroute | abstain | degrade | multi-source | basic",
  "query": "…",
  "ideal_answer": "… grounded, verifiable from corpus",
  "ideal_context": "… verbatim or near-verbatim anchor text (chunk excerpt)",
  "must_contain": ["…"],
  "source": "S1 … S5",
  "path": "data/docs/<bundle>.md"
}
```

**Multi-source convention (registered here):** `source` uses the `+` union syntax
(`"S1+S3"`), `path` joins the bundle paths with `" + "`, and `ideal_context` holds
each source's anchor separated by `\n\n---\n\n`. `id` prefix is `MS-` (`"MS-Q001"`).
The anchor checker validates `must_contain` against **every** bundle in `path`.

## Authoring rules (enforced per `doc/design/01_lld_tests.md` T-01 matrix + house rules)

1. **Groundedness 100% (T-01-3)** — every `ideal_answer` traces to the corpus. The
   NB-01 anchor check asserts **two** things per row: (a) each `must_contain` fragment
   is verbatim-present in **≥1** bundle of `path` (union check — for `S1+S3` rows a
   fragment may live in either); (b) `ideal_context` is a **contiguous** verbatim
   excerpt of ≥1 bundle (multi-line excerpts must match the file byte-for-byte,
   incl. leading box-drawing characters — assembled splices FAIL this check, verified
   in the 2026-09-10 seed review).
2. **Schema exact, no extra fields (T-01-2)** — exactly the 8 keys above.
3. **Counts are decisions (T-01-1)** — 120–160 retrieval / 60–75 routing / 100–120
   correctness; per-source 25–32 × 5.
4. **Edge-category minimums (T-01-6)** — ≥5 each of `misroute`, `conflict`, `abstain`,
   `degrade` in the final retrieval file (the Mod-3 gate stratifies on `category`).
   `misroute` rows record the *correct* source (the trap is a naive router landing
   them elsewhere); `abstain` rows point at corpus-declared non-content; `degrade`
   covers step-7 failure handling; `conflict` surfaces two corpus passages that
   disagree.
5. **Ids unique + prefixed (T-01-4)** — `S[1-5]-Q\d+` or `MS-Q\d+` (multi-source union),
   no duplicates. **Decision D15 (2026-09-10):** the LLD regex was amended to accept
   `MS-Q\d+` — the `MS-` prefix keeps the union honest for routing filters.
6. **source/path truthful (T-01-5)** — `path` is the actual bundle path; cross-checked
   against the corpus manifest.
7. **No secrets (T-01-7)** — no keys/tokens in any query/answer/anchor, incl. abstain
   rows. Post-author regex scan.
8. **step4 frozen (T-01-8)** — step9 evals use step9 goldens only; step4's files are
   never touched (their numbers stay the smoke baseline).

## Progress

- **Seeded (2026-09-10): 15 rows** in `eval/goldens/retriever_goldens.json` —
  pattern-proof set across all sources and all 7 categories. **Authoring lane: the
  `data`/`tester` roles (D16 — eval data, not application code); the learner authors the
  NB-01 anchor-check script.** Extension: source batches (S1 → S2 → S3 → S4 → S5) toward
  the 135-row budget.
- **S1 batch done (2026-09-10): 28 rows appended → S1 at its full 32-row budget
  (`S1-Q001..Q032`); file now 43 rows**, every row machine-verified: anchors extracted
  with per-row line-marker + byte-contiguity asserts; full T-01-2/3/4/5/7 suite PASS
  (schema exact, must_contain union-grounded, ideal_context contiguous byte-exact,
  ids `S[1-5]-Q\d+|MS-Q\d+` unique, source/path truthful, no secret patterns).
  **Watch items for S2–S5:** `basic` share is 47% (tester cap ~30% at file level —
  S2–S5 must skew cite/multi-source/edge) and edge counts are 2 each vs ≥5 (T-01-6).
- **S2 batch done (2026-09-10): 23 rows (`S2-Q003..Q025`) + `MS-Q002` (embedder
  conflict family the tester flagged: step 2 bge-base-en-v1.5 vs step 3 qwen3-embed
  1024-dim, both claiming 'the Step 2 pipeline') → file now 67 rows.** S1(32/32) and
  S2(25/25) at full budget. Full T-01 suite PASS again. File state: basic 23 (34%),
  cite 28, misroute **5 (target met)**, abstain 4, conflict 3, degrade 3 — remaining
  S3/S4/S5 batches must lift conflict ≥5, abstain ≥5, degrade ≥5 and pull basic below
  ~30%.
- T-01-1 counts (43 vs 120–160) remain a completion target; seed/batch stages are
  knowingly non-final.
- Next: `eval/goldens/query_processing_goldens.json` (60–75, misroute negatives,
  task 01:70) and `eval/goldens/correctness_goldens.json` (100–120, task 01:71).