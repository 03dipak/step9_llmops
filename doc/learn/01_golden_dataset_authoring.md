# Golden Dataset Authoring — a mentor-led walkthrough

> **Audience:** learner. **Goal:** after reading this you can author a
> machine-verified golden dataset for a RAG/LLMOps eval — the same way the
> `eval/goldens/*.json` files in this repo were built (139 + 67 + 107 rows,
> all passing the T-01 suite).
>
> You do **not** need an eval framework, an LLM API, or a template. You need:
> the corpus, a text editor, `python3`, and one skill — *ping-ponging between
> "what does the corpus say?" and "does my JSON say the same thing?"*

---

## 1. What a golden dataset is, and why we build it this way

A **golden dataset** (goldens) is a fixed set of (question → expected answer)
pairs used to grade a system. You run your RAG pipeline on the questions and
compare its answers against the goldens. The eval **reports a score**, and the
regression gate **fails a release** when the score drops.

The danger: if a golden row contains a fact that is **not in your corpus**,
you are not testing your RAG — you are testing the evaluator's ability to
hallucinate. That is why this repo's contract (T-01) demands:

- every `ideal_context` and `must_contain` fragment exists **verbatim** in the
  corpus (groundedness), and
- the `id`, `source`, `path` fields are **provably truthful** (derivable from
  the corpus manifest).

So the whole authoring method is: **make it impossible for a golden to be
wrong without a script screaming at you.** We do that in three layers:

| Layer | Tool | Job |
|---|---|---|
| 1. Author | you (the author) reading the corpus | decide what to ask, write the answer |
| 2. Assemble | a dumb Python batch script | build the JSON with auto-extracted excerpts + asserts |
| 3. Verify | a separate verifier script | re-check the finished file against the corpus, fresh |

Layer 2 and 3 **cannot invent content** — they only extract, assert, and
compare. All the intelligence is in layer 1; all the anti-lying is in 2 and 3.

> **Scope boundary (registered after external review, 2026-09-11):** this guide
> is a **method manual, not a data source**. Its examples (e.g. `MS-Q002`,
> `S2-Q037`, `S4:446`) *are* verbatim excerpts of the real bundles — but the
> only ground truth is `data/docs/*.md`. Never cite this guide as the corpus:
> the T-01 verifier checks fragments against the bundles, not against this
> document. New rows for *this repo's* committed golden set are **closed**
> (D19); practice goldens belong in a toy sandbox outside `eval/goldens/`
> (D19). External AI advice on this method is treated as external review
> (D17): replies sent to claude.ai & perplexity.ai, with verification
> evidence, are in `doc/learn/02_external_advisor_replies.md`.

---

## 2. The schema — the 8 keys, explained

Every row is an object with exactly these 8 keys:

```json
{
  "id": "S1-Q046",
  "category": "cite",
  "query": "Why does step 1 avoid an external vector database for retrieval?",
  "ideal_answer": "Step 1's vector store is pure numpy — no Qdrant, no Chroma...",
  "ideal_context": "**Implementation:** Pure numpy — no Qdrant, no Chroma, no external DB.",
  "must_contain": ["Pure numpy", "no Qdrant, no Chroma"],
  "source": "S1",
  "path": "data/docs/s1_early_steps_bundle.md"
}
```

| Key | What it is | Who decides it |
|---|---|---|
| `id` | `S<1..5>-Q<seq>` or `MS-Q<seq>`, unique per file and across files | you (but the script can check uniqueness) |
| `category` | one of 7 enum values (next section) | you — this is judgment |
| `query` | the question to ask the pipeline | you |
| `ideal_answer` | the reference answer the judge compares against | you |
| `ideal_context` | **verbatim** corpus excerpt the answer is based on | **script extracts it by line number** |
| `must_contain` | short list of **verbatim** strings the answer must include | you (script checks each is in corpus) |
| `source` | corpus id(s), `+`-joined for multi-source rows, e.g. `S1+S4` | you |
| `path` | full bundle path(s) joined with `" + "` | **script computes it** from `source` |

Rules of thumb:

- **Never hand-type `ideal_context`.** Give the script line numbers. Hand-typed
  excerpts are where transcription errors live.
- **Never hand-type `path`.** It is a pure function of `source`. Let the script
  derive it; the verifier checks it independently.
- `must_contain` fragments should be **short and distinctive** — a phrase the
  answer must have, verbatim. E.g. for the refusal answer:
  `"I don't have enough information to answer this question."`
- The **`id` numbering is continuous per-source across all three files**: the
  retriever file owns `S1-Q001..Q032`, routing `S1-Q033..Q045`, correctness
  `S1-Q046..Q066`. Decide the ranges up front and never reuse a number.

---

## 3. The 7 categories — and how to choose one

| Category | What the row tests | How to spot it in a corpus |
|---|---|---|
| `cite` | normal: answer exists, one source | a plain fact stated once |
| `basic` | trivial retrieval (exact-term hit) | the question's own words appear in the doc (e.g. "chunk size" → "512 tokens") — keep the share ≤ 30% of the file |
| `multi-source` | answer requires the same fact from 2+ bundles | the fact is corroborated in S1 and S2 with different wording |
| `conflict` | two sources **disagree**; the answer must surface it | S1 says the pipeline embeds with model A, S2 says model B — both "the step-2 pipeline" |
| `misroute` | the router picks the **wrong but tempting** source | a fact about LangSmith free tier (5,000 traces/month) lives in **S1:1134**, not the S2 bundle everyone reaches for |
| `abstain` | the right answer is **"I don't know" / not in corpus** | a question that *almost* has an answer — the tempting content exists but doesn't answer |
| `degrade` | graceful failure under partial outage | "Groq returns a 500 — does the pipeline fail gracefully?" (corpus answers "yes, falls back") |

Three real examples from this corpus:

- **`conflict`** (`MS-Q002`): *"Which embedding model does the shared pipeline
  actually use — bge-base-en-v1.5 or qwen3-embed?"* — **S1** (step 2's own
  README) records `BAAI/bge-base-en-v1.5`; **S2** (step 3's rebuild) records
  `qwen3-embed, 1024-dim` and disclaims bge. Both bundles call their own claim
  "the Step-2 pipeline" — so a faithful answer must surface the discrepancy,
  not pick a side. The row's `source` is `S1+S2`.
- **`misroute`** (`S2-Q037`): asks about the **LangSmith free tier** — the
  tempting S2 bundle mentions LangSmith, but the free-tier fact (5,000 traces /
  month) lives in **S1:1134**, not in S2. The row's `source` is the *correct*
  route (S1), the `query` names the tempting wrong one.
- **`degrade`** (`MS-Q004`): *"Groq returns a 500 error mid-request. Does the
  pipeline fail gracefully?"* → answer carries the fallback behavior and the
  cost of that fallback.

> **Authoring trick for `abstain`:** find a paragraph that *looks* like it
> answers your question but doesn't. Anchor the row in the bundle where the
> tempting content lives, and make the ideal answer the refusal string (e.g.
> "the corpus does not record X").

---

## 4. The workflow, end to end

### Step 0 — Inventory the corpus

Maintain a manifest (this repo: `doc/notes/01_corpus_plan.md`):

```
S1 → data/docs/s1_early_steps_bundle.md   (1638 lines)
S2 → data/docs/s2_frameworks_bundle.md    ( 849 lines)
S3 → data/docs/s3_lifecycle_bundle.md     ( 459 lines)
S4 → data/docs/s4_qa_deep_dives.md        ( 520 lines)
S5 → data/docs/s5_docs_bundle.md          ( 546 lines)
```

Every line number you will ever cite is measured against these files. When in
doubt, `grep -n` the bundle: *the line number on screen and the line number in
your script must be the same number.*

### Step 1 — Read the corpus and collect anchors

This is the only step with judgment. Read each bundle, and for every passage
that looks like a testable fact, note:

```text
S1:173  "Pure numpy"            → vector store choice (cite)
S1:127  "512 tokens"            → chunk size (basic)
S1:262-264  refusal string      → abstention behavior (cite)
S3:231  "V3 is 6% better but 50% more expensive" → A/B decision (cite)
S4:446  "findng, not a bug."    → typo is REAL — quote verbatim or fix? (see §7)
```

> ❗ **Gotcha:** when a fragment wraps across two lines (e.g. a table row
> `| Streamlit Cloud | Low | Free | Prototypes |` on `S3:316`), the verbatim
> fragment is the **exact bytes incl. the `|` separators**. If you ask
> `must_contain: ["Low complexity"]`, the verifier fails, because the corpus
> says `Low`, not `Low complexity`. This exact bug is logged in §7.

### Step 2 — Author rows into a batch script, not into the JSON

Write one Python file that contains your rows as `R(...)` calls. The script:

(a) loads the bundles from disk,
(b) extracts `ideal_context` by line number (asserting markers + contiguity),
(c) derives `path` from `source`,
(d) writes the final JSON.

Why a script and not hand-edited JSON? Because a 100+ row JSON typed by hand
will have escaping/typo/duplicate-id errors, and — far worse — hand-typed
`ideal_context` values can silently disagree with the corpus. The script makes
that class of error **crash loudly** instead.

### Step 3 — Run, fix, repeat until `FAILURES: NONE`

```bash
python3 tools/goldens/batch_correctness.py   # assembles the JSON
python3 tools/goldens/t01_verify.py <gold.json> <lo> <hi> [other_goldens...]
```

These live **inside the repo** at `tools/goldens/` (portable: they locate the
repo root by walking up to `pyproject.toml`, so they work from any cwd). Run
them with `python3`, no dependencies.

The verifier is **separate** from the assembler — that separation is what makes
the result trustworthy. A buggy assembler cannot certify its own output.

---

## 5. The assembler script — line by line

This is the whole trick, commented:

```python
bund = {k: open(DATA + v, encoding="utf-8").read() for k, v in SRC.items()}
lines = {k: v.splitlines(keepends=True) for k, v in bund.items()}

def A(src, nums, marker):
    """Extract the exact bytes of lines src:nums and prove they're in the corpus."""
    txt = "".join(lines[src][i - 1] for i in nums).rstrip("\n")
    assert marker in txt, f"MARKER FAIL {src} {nums}: {marker!r}"   # line numbers right?
    assert txt in bund[src], f"NOT CONTIGUOUS {src} {nums}"          # lines adjacent?
    return txt

def expect_path(srcs):
    return " + ".join("data/docs/" + SRC[s] for s in srcs)           # derive path

def R(i, cat, q, ans, src, nums, marker, must, ctxsrc=None):
    cs = ctxsrc or src
    return {
        "id": i, "category": cat, "query": q, "ideal_answer": ans,
        "ideal_context": A(cs, nums, marker),      # ← extracted, never typed
        "must_contain": must, "source": src,
        "path": expect_path(src.split("+")),       # ← derived, never typed
    }
```

Dissecting `A()`:

- `lines[src][i - 1]` — line 1 of the file is index 0; the `-1` is *the* classic
  off-by-one. If your marker is on `S3:231` but you pass `[230]`, the marker
  assert fires and names the source, the numbers, and the first 80 bytes of what
  was actually extracted. You fix the number, re-run. That is the whole flow.
- `assert txt in bund[src]` — after joining, the snippet must appear verbatim
  somewhere in the bundle. If you tried to splice non-adjacent lines (e.g.
  `["124", "126"]` skipping 125), the join isn't contiguous and this fires.
- Multi-line anchors are legal: `[127, 128]` for the chunk-config table row
  that wraps; the `rstrip("\n")` just removes the trailing newline so the stored
  `ideal_context` is the copy-paste-friendly text.

`R()` is deliberately shallow — one row = one call, so a human can diff the
"rows to add" section the way you'd diff a changelog. The 107-row correctness
file is literally 107 `R(...)` calls in a Python list.

---

## 6. The verifier — what it re-checks, and why separately

`tools/goldens/t01_verify.py` (and its notebook mirror
`jupyter_notebook/NB-01_anchor_check.py`) re-opens the **finished JSON** and
re-checks every claim against disk:

| T-01- | Check |
|---|---|
| 1 | total rows in the per-file band (120–160 / 60–75 / 100–120) |
| 2 | exactly the 8 keys; `category` in the enum; `must_contain` non-empty list of strings |
| 3+5 | each `must_contain` fragment verbatim in ≥1 bundle of `path`; `ideal_context` contiguous; `path` == what the manifest implies |
| 4 | id matches `S[1-5]-Q\d+\|MS-Q\d+`; ids unique; queries unique |
| 6 | misroute/conflict/abstain/degrade each ≥ 5; basic ≤ 30% of file |
| 7 | no `sk-…`, `api_key=…`, `AIza…`, `gsk_…` patterns |
| 9 | answerable-from-corpus heuristic + spot-check sample (manual gate) |
| X | cross-file: no id or query appears in another golden file |

Notice T-01-3 uses **union semantics**: for a `S1+S4` row, each fragment must
exist in at least one of S1 *or* S4 — not both. And the judge (NB-01) mirrors
this logic, so the learner's harness and the author's scripts agree by
construction.

---

## 7. A failure log — every bug that actually happened, and the lesson

These are real, from this repo's build. Learn from them:

| # | Symptom | Root cause | Fix | Lesson |
|---|---|---|---|---|
| 1 | `MARKER FAIL S3 [228]` | line drifted: `228` was `prod_metrics`, `229` is `v3_metrics` | fix nums to `[229]` | the corpus moved; **grep the line before trusting it** |
| 2 | `must_contain_grounding ['Low complexity']` | corpus table cell says `Low`, not `Low complexity` | use `"Free"` (a real verbatim cell) | a fragment must be **byte-exact**, including punctuation: `\| Streamlit Cloud \| Low \| Free \| Prototypes \|` |
| 3 | query collision `S3-Q046` | the same question text was already used in the routing file | rephrase the query | questions are unique **across files**, not just within one |
| 4 | verifier checked the wrong `eval/goldens/` | assembler used **relative** paths and ran from a different cwd → silently compared against another project's goldens | absolute paths everywhere | a script that "passes" while testing the wrong thing is worse than a failing one |
| 5 | `S4-Q030` "HNSW over centroids" | the phrase wraps across a line break in the source | fragment shortened to the bytes actually on the line | line-wrap **is** a byte boundary — see it before you claim it |
| 6 | `S4:446` typo "findng" | the corpus genuinely contains a typo in a judgment call passage | quoted it **verbatim** in goldens that must match it; used the corrected spelling in prose answers | decide the typo policy **up front** and document it |

**Debugging loop for any failure:** read the failure message → open the bundle
with `grep -n` → fix the line number or the fragment → re-run. There is no
mystery step. Every check names the row, the field, and the expected vs got.

---

## 8. Reproduce this repo's goldens, from scratch

```bash
# run from the repo root (or anywhere — the scripts walk up to pyproject.toml)
# 1. three assemblers (they are idempotent: re-running rewrites the same file)
python3 tools/goldens/batch3.py            # retriever_goldens.json   (139)
python3 tools/goldens/batch_routing.py     # query_processing_goldens.json (67)
python3 tools/goldens/batch_correctness.py # correctness_goldens.json (107)

# 2. the independent verifier, each file with its band + the other two for cross-file checks
python3 tools/goldens/t01_verify.py \
  eval/goldens/retriever_goldens.json 120 160 \
  eval/goldens/query_processing_goldens.json eval/goldens/correctness_goldens.json
# …repeat for the other two… expect `FAILURES: NONE` each time

# 3. the notebook mirror, all three at once (also prints the T-01-9 spot-check sample)
python3 jupyter_notebook/NB-01_anchor_check.py
```

### Recovery path — "the session died; re-derive everything"

Every line below is **committed in this repo** — no `/tmp`, no agent session,
no external state. If the golden files, the teaching docs, or your memory of
the method are ever lost, this is the order to rebuild from nothing:

```bash
# 1. Regenerate all three golden files (idempotent: output is byte-identical
#    to the committed versions — an empty `git diff` after re-running proves it)
python3 tools/goldens/batch3.py
python3 tools/goldens/batch_routing.py
python3 tools/goldens/batch_correctness.py

# 2. Prove nothing drifted: diff against the committed JSON
git diff --stat eval/goldens/

# 3. Independent verification, each file with its band + the other two for
#    cross-file id/query uniqueness (expect `FAILURES: NONE`, exit 0)
python3 tools/goldens/t01_verify.py eval/goldens/retriever_goldens.json 120 160 \
  eval/goldens/query_processing_goldens.json eval/goldens/correctness_goldens.json
python3 tools/goldens/t01_verify.py eval/goldens/query_processing_goldens.json 60 75 \
  eval/goldens/retriever_goldens.json eval/goldens/correctness_goldens.json
python3 tools/goldens/t01_verify.py eval/goldens/correctness_goldens.json 100 120 \
  eval/goldens/retriever_goldens.json eval/goldens/query_processing_goldens.json

# 4. Re-learn the method (why, not just what): this guide (§1–§7)
#    Spec contract:          doc/task/01_data_testset.md
#    Shared test matrix:     doc/design/01_lld_tests.md
#    Authoring recipe:       doc/design/01_authoring_recipe.md
```

**What each asset is for, so future-you picks the right one:**

| Asset | Purpose |
|---|---|
| `tools/goldens/batch3.py` | assemble retriever goldens (139) |
| `tools/goldens/batch_routing.py` | assemble routing goldens (67) |
| `tools/goldens/batch_correctness.py` | assemble correctness goldens (107) |
| `tools/goldens/t01_verify.py` | independent verifier (T-01-1..7 + cross-file) |
| `jupyter_notebook/NB-01_anchor_check.py` | notebook mirror — all three at once + T-01-9 sample |
| `doc/learn/01_golden_dataset_authoring.md` | this guide — the method |
| `doc/task/01_data_testset.md` | the binding contract (counts, schema, T-01) |
| `doc/design/01_lld_tests.md` | shared T-01 matrix + per-file counts |
| `doc/design/01_authoring_recipe.md` | the authoring procedure + failure modes |

**The one rule that makes recovery work:** the scripts are *idempotent* and
*portable* — re-running them from any cwd produces byte-identical output. If a
future edit ever makes a script *not* idempotent, that is a bug: stop and fix
it before trusting the recovered state.

### Practice venue — the toy sandbox (D19)

The committed golden set is **closed** (D19): no new rows go into
`eval/goldens/` without a registered gap. To practice the method without
touching official eval data, build a tiny sandbox instead:

1. Write a small corpus by hand, e.g. `toy_docs/toy_bundle.md` — 3–6
   paragraphs, a few facts, at least one deliberately conflicting pair and one
   near-miss passage (so you can practice `conflict` and `abstain` rows).
2. Write 5–10 `R(...)` rows against it, one per category you want to exercise,
   using the §5 assembler pattern (line numbers, marker + contiguity asserts).
3. Run a mini verifier (the T-01 logic from §6) and make the asserts catch
   your deliberate mistakes — e.g. a wrong line number, a fragment that isn't
   verbatim, a duplicated query.
4. Keep the sandbox **outside** `eval/goldens/` and outside the committed
   corpus; it is practice, not product. Delete or keep it as you like — it is
   never part of the repo's eval result.

This is the registered practice venue (D19, adopted from perplexity.ai's
suggestion); it costs nothing and scales your skill before you ever need to
author more official rows.

---

## 9. Your checklist before you call a golden set "done"

- [ ] every `id` matches `S[1-5]-Q\d+|MS-Q\d+` and is unique **across all files**
- [ ] every `query` is unique **across all files**
- [ ] every `ideal_context` is byte-exact-contiguous in the bundle (script-extracted, never hand-typed)
- [ ] every `must_contain` fragment is verbatim in ≥ 1 bundle of `path`
- [ ] `path` is a pure function of `source` (script-derived)
- [ ] each edge category (`misroute`, `conflict`, `abstain`, `degrade`) ≥ 5 rows; `basic` ≤ 30%
- [ ] total row count inside the file's band
- [ ] no secret patterns
- [ ] the verifier ran **separately** from the assembler and printed `FAILURES: NONE`

---

## 10. FAQ

**Q: Do I need an LLM to write goldens?** — No. The authoring is you reading
and writing; the scripts only extract and assert. (This repo's goldens were
authored by an LLM agent *acting as the careful reader* — same method, same
checkpoints: every excerpt asserted against disk before it entered the file.)

**Q: Can I use an eval framework for this?** — Later, yes: `doc/design/01_lld_tests.md`
shows how these goldens feed DeepEval/Ragas. But the *authoring* of goldens is
framework-independent. The framework grades the pipeline; the goldens define
the target.

**Q: What if two sources genuinely disagree?** — Then you write a `conflict`
row whose answer says "the corpus disagrees" and cites both sides. That is the
evaluation *feature*, not a bug: it tells the judge and the reader exactly how
the system behaves on conflicting evidence.

**Q: How do I keep 100+ rows manageable?** — One `R(...)` call per row, grouped
by source and category, with a one-line comment per group. Never generate JSON
by string-concatenation; let the script `json.dump` with `indent=2` so diffs
stay readable.

**Q: Where do the authoring scripts live?** — In the repo: `tools/goldens/`
(`batch3.py`, `batch_routing.py`, `batch_correctness.py`, `t01_verify.py`).
They were kept outside the repo while the golden set was being built; once the
recipe stabilized they were moved in — with hardcoded paths replaced by a
repo-root walk — so a lost agent session never loses the build tooling. They
are *build/verification tooling for eval data*, not application code: they
never touch `src/`, and running them only ever rewrites `eval/goldens/*.json`
to byte-identical content (idempotent). The three assemblers are documented
here in §5.