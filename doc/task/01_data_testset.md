# Task 01 — Data & Testset (goldens) — Mod 1

## LLMOps framing

Pillar 1 (Data & testset) — the golden corpus is the *foundation of every verdict*: the
regression gate's tolerance is meaningless if the testset is too small to detect a
regression, and worse than meaningless if rows are ungrounded (hallucinated data in an eval
portfolio is fatal). Quantity is a decision, not a wish.

**Cross-ref:** `step4/doc/QA_DEEP_DIVES.md §7` pillar 1; step4 `eval/goldens/` + `eval/golden.jsonl`.

## Current state (verified 2026-09-10, step4)

| File | Rows | Problem |
|---|---|---|
| `eval/golden.jsonl` (shared L2 pool) | 20 | 1 failure = 5 points; tolerance ±0.03 ≈ 0.6 answers → gate blind to small regressions |
| `retriever_goldens.json` | 27 | ≈5/source over 5 sources — too thin for `where`-filter routing proof |
| `correctness_goldens.json` | 25 | thin for faithfulness/correctness stats |
| `query_processing_goldens.json` | 20 | no misroute (**#24**)/conflict (**#29**) labels |
| chunking/ingestion/embeddings/vector_store | 7/5/4/7 | smoke-scale (fine as component smoke, not as gate input) |

## step9 target (your build, this module)

| Golden set | Target | Why this count |
|---|---|---|
| **Multi-source retrieval** (`retriever`) | **120–160** (25–32 per source × 5 sources, incl. edge cases) | per-source stratification + gate stability |
| **Routing / query processing** | **60–75** (incl. adversarial) | must include misroute negatives (**#24**) and multi-source intent |
| **Correctness + faithfulness** | **100–120** | per-gate-metric ~100+ so ±0.03 tolerance is honest |
| Pipeline / chunking / ingestion / store | keep step4 counts, add **only** missing edge cases | component smoke ≠ gate input — don't overspend here |

Corpus for query authoring (grounding anchors): your **18 class transcripts** (LLMOps
topics — the material you study is the RAG's data) + step4's `doc/QA_DEEP_DIVES.md` + README
docs. Goldens must be *answerable from that text alone*.

## Schema (extend step4's retriever schema with a category)

```json
{
  "id": "S1-Q042",              // source-prefixed, sequential
  "category": "cite | conflict | misroute | abstain | degrade | multi-source | basic",
  "query": "…",
  "ideal_answer": "… grounded, verifiable from corpus",
  "ideal_context": "… verbatim or near-verbatim anchor text (chunk excerpt)",
  "must_contain": ["…"],        // citation-critical verbatim strings
  "source": "S1 | S2 | S3 | S4 | S5",  // S1..S5 = corpus source ids (not step4's type tags)
  "path": "data/…"
}
```

- **`category` is new** — it is what makes the set *adversarially labeled*, and it is what
  the gate can stratify on later (e.g. "misroute regressions must not regress").
- **`must_contain`** — verbatim strings the answer must include (citation allowlist proof).
- **No secrets** — never a query whose ideal answer contains an API key / token.
- **Groundedness rule:** every row's `ideal_answer` must trace to a chunk in the corpus. If
  you cannot paste the anchor, the row does not exist. (This is the anti-hallucination rule
  for the testset itself.)
- **Source ids (S1–S5):** S1 = module-1 transcripts · S2 = module-2 transcripts ·
  S3 = module-3 transcripts · S4 = step4 `doc/QA_DEEP_DIVES.md` · S5 = README/docs bundle
  (step4 README + step9 README/AGENTS). A deliberate shift from step4's type tags
  (`pdf | web | db | text`): step9's corpus is documents, and `where`-filter routing
  (Mod 4) keys off source ids — the same ids prefix every golden `id`.

## Deliverables

1. `doc/notes/01_corpus_plan.md` — list sources, per-source chunk strategy, per-source golden counts.
2. `eval/goldens/retriever_goldens.json` (step9) — 120–160 rows, all categories present.
3. `eval/goldens/query_processing_goldens.json` (step9) — 60–75 rows incl. misroute negatives.
4. `eval/goldens/correctness_goldens.json` (step9) — 100–120 rows.

> step4's goldens are **not modified** — it is a green repo; step9 grows its own set. The
> cross-ref stays: step9 evals use step9 goldens; step4's numbers remain the smoke baseline.

## Depends on

- Task 00b (package + pytest scaffold exist; the NB-01 anchor-check script runs under `uv run`).
- Corpus present: the 18 class transcripts + step4 docs (`doc/QA_DEEP_DIVES.md`, README) —
  read-only inputs for query authoring.

## Contracts (reference, don't redefine)

- Golden-row schema is exactly: `id`, `category`, `query`, `ideal_answer`, `ideal_context`,
  `must_contain`, `source`, `path` (schema block above) — no extra fields.
- `category` enum: `cite | conflict | misroute | abstain | degrade | multi-source | basic`.
- Groundedness rule is 100%: a row whose `ideal_answer` has no corpus anchor does not exist.
- No secrets: never a query/answer containing an API key or token.
- step4 goldens stay frozen; step9 grows its own set only.

## Exit criteria

- [ ] Counts in the target ranges (both files documented with a wc-style verification line in `doc/notes/01_…`)
- [ ] Every row grounded: 100% of `ideal_answer` entries have a matching corpus anchor (spot-check + a scripted anchor check you write in NB-01)
- [ ] Categories present: at least 5 misroute, 5 conflict, 5 abstain, 5 degrade rows
- [ ] `source` + `path` correct on every row (no row claims a source its text doesn't come from)
- [ ] Ask `tester` to review groundedness, then `review` for the verification pass

## Verify

`uv run python -m …` — a scripted anchor check (your code, NB-01) that for every row
asserts `ideal_context` (or a `must_contain` fragment) exists in the corpus chunks. The
notebook asserts are the evidence, like NB-000.

## Interview-Q&A (Mod 1)

**Q1. "How many goldens do you need, and why?"**
**A:** Not a magic number — two requirements decide it. (1) *Gate stability:* at ~100 rows per
gate metric, one bad answer moves the mean ~1 point, inside the ±0.03 tolerance budget — at
20 rows it's 5 points and tolerance is fiction. (2) *Stratification:* a multi-source system
needs 25–32 per source plus labeled edge cases (misroute/conflict/abstain/degrade) or the
`where`-filter routing isn't proven. My multi-source set: ~150 retrieval + ~70 routing rows.
**Check:** they hear "tolerance-to-sample-size" reasoning, not a number picked from air.

**Q2. "How do you know your goldens aren't garbage?"**
**A:** Groundedness rule — every `ideal_answer` must trace to a verbatim corpus anchor
(`ideal_context` / `must_contain`); a scripted anchor check fails the row if no chunk
contains it. If I can't paste the anchor, the row doesn't exist. An eval portfolio built on
ungrounded goldens is hallucinated eval — worse than none.
**Check:** the anti-hallucination stance applied to data, not just answers.

**Q3. "Why did you not modify step4's goldens?"**
**A:** step4 is a green, reviewed repo — its goldens are a baked smoke baseline. Changing its
schema re-opens verdicts that are closed. step9 grows its own enriched set (new `category`
field, adversarial labels) and cross-refs step4 as the baseline. Separate concerns: the
archive stays frozen; the teaching repo grows.
**Check:** scope discipline — they hear "closed vs open" reasoning, not hesitation.

## Next module

Mod 2 ("Prompts & the judge") — after `tester`/`review` pass on the goldens.