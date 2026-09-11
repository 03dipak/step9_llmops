# 01 — Golden authoring recipe (how source docs become verified golden rows)

> Companion to `doc/design/01_lld_tests.md` (contracts) and `doc/task/01_data_testset.md`
> (task spec). This file records the **exact procedure and Python logic** used to produce
> the verified rows in `eval/goldens/retriever_goldens.json` (67 rows, 2026-09-11).
>
> **Lane note (D16 + house rule):** agents commit markdown only. The code blocks below are
> **reference logic** — the learner ports them into `jupyter_notebook/NB-01_anchor_check.ipynb`
> (their script). They are not committed as repo code by agents.

## 0. Workflow in one line

```
read the bundle → mark anchor lines → extract verbatim (marker + contiguity asserts)
→ author the 8 fields → append → run the T-01 suite → fix → commit
```

Every batch followed: `S1` (32 rows) → `S2`-batch + `MS-Q002` (24 rows) → file 67 rows,
`FAILURES: NONE` on T-01-1..9.

## 1. Prep — corpus manifest

The manifest is the single source of truth for `path` truthfulness (T-01-5). Build it
from the **actual filenames on disk**, never from memory:

```python
DATA = "/home/dipak/agentic/step9_llmops/data/docs/"
SRC = {
    "S1": "s1_early_steps_bundle.md",
    "S2": "s2_frameworks_bundle.md",
    "S3": "s3_lifecycle_bundle.md",
    "S4": "s4_qa_deep_dives.md",
    "S5": "s5_docs_bundle.md",
}
bund = {k: open(DATA + v, encoding="utf-8").read() for k, v in SRC.items()}
```

The expected `path` value for any row is then derived, not typed:

```python
def expect_path(srcs):
    return " + ".join("data/docs/" + SRC[s] for s in srcs)
```

> Lesson from the session: an earlier verifier compared rows against bare basenames and
> produced 43 fake failures. Verify the verifier — derive the expectation from the manifest.

## 2. Finding anchors — keyword scan, then read

Before writing a row: locate candidates by scanning for distinctive tokens, then read the
surrounding lines to confirm context:

```python
lines = bund["S1"].splitlines(keepends=True)
hits = [(i, lines[i - 1].rstrip("\n")) for i in range(1, len(lines) + 1) if "bge-base" in lines[i - 1]]
# [(40, '│     Model: bge-base-en-v1.5 (fastembed, local)  │'),
#  (146, '**Model:** `BAAI/bge-base-en-v1.5` via fastembed (local ONNX, no API needed).'), ...]
```

## 3. Anchor extraction — the helper that makes `ideal_context` byte-exact

This is the core mechanical trick. It **fails loudly** on two things: a marker that isn't
in the excerpt (off-by-one line numbers) and a non-contiguous excerpt (skipped a line,
e.g. a blank line between anchors):

```python
def A(lines, full, nums, marker):
    """nums = 1-based line numbers; marker must appear in the excerpt."""
    txt = "".join(lines[i - 1] for i in nums).rstrip("\n")
    assert marker in txt, f"MARKER FAIL on lines {nums}: {marker!r} -> {txt[:70]!r}"
    assert txt in full, f"NOT CONTIGUOUS lines {nums}"
    return txt
```

Usage — a real row from the S1 batch (`S1-Q014`, the ask() flow):

```python
lines1 = bund["S1"].splitlines(keepends=True)
ctx = A(lines1, bund["S1"], [310, 311, 312, 313, 314], "ask(question, top_k=3)")
# 'ask(question, top_k=3)\n    → embed question\n    → retrieve top-k chunks\n'
# '    → generate answer with context\n    → return answer + citations'
assert ctx in bund["S1"]          # byte-exact contiguity, proven
```

The first attempt used `[311..315]` (off by one, the `ask(` line is 310) and the marker
assert caught it before anything was written.

## 4. Row construction — exact 8 keys, nothing else

```python
row = {
    "id": "S1-Q014",                 # <source>-Q<seq>; MS-Q\d+ for union rows
    "category": "basic",             # cite|conflict|misroute|abstain|degrade|multi-source|basic
    "query": "What happens in the ask() flow of step 1's pipeline?",
    "ideal_answer": "ask(question, top_k=3) embeds the question, retrieves the top-k chunks, "
                    "generates an answer with that context, and returns the answer plus citations.",
    "ideal_context": ctx,            # the A(...) output — byte-exact excerpt
    "must_contain": ["ask(question, top_k=3)", "retrieve top-k chunks",
                     "return answer + citations"],
    "source": "S1",
    "path": expect_path(["S1"]),
}
```

Multi-source rows (`MS-*`, D15): `source` is the union `"S1+S2"`, `path` joins with
`" + "`; `ideal_context` is **one contiguous excerpt from one side** (the convention
established by `MS-Q001`), with `must_contain` fragments union-grounded across all sides.

Batch loop + deterministic sort (source prefix order, then `Q<seq>`):

```python
import json, re
rows = json.load(open(GOLD))
def seq(i): return int(re.search(r"Q(\d+)", i).group(1))
for row in NEW: rows.append(row)
rows.sort(key=lambda r: ((0 if r["id"].startswith("MS")
                          else {"S1":1,"S2":2,"S3":3,"S4":4,"S5":5}[r["id"][:2]]), seq(r["id"])))
json.dump(rows, open(GOLD, "w"), indent=2, ensure_ascii=False)
```

## 5. The T-01 verification suite (the logic NB-01 must mirror)

This is exactly what ran over the 67-row file (output: `TOTAL 67 | FAILURES: NONE`):

```python
import json, re
GOLD = "eval/goldens/retriever_goldens.json"
DATA = "data/docs/"
KEYS = {"id","category","query","ideal_answer","ideal_context","must_contain","source","path"}
CATS = {"cite","conflict","misroute","abstain","degrade","multi-source","basic"}
SRC = {"S1":"s1_early_steps_bundle.md","S2":"s2_frameworks_bundle.md","S3":"s3_lifecycle_bundle.md",
       "S4":"s4_qa_deep_dives.md","S5":"s5_docs_bundle.md"}
bund = {k: open(DATA+v, encoding="utf-8").read() for k, v in SRC.items()}
rows = json.load(open(GOLD))
bad = []

# T-01-2 schema exact + enum + must_contain shape
for r in rows:
    if set(r.keys()) != KEYS: bad.append((r.get("id","?"), "keys", sorted(set(r.keys()) ^ KEYS)))
    if r["category"] not in CATS: bad.append((r["id"], "category"))
    if not isinstance(r["must_contain"], list) or not all(isinstance(x,str) and x for x in r["must_contain"]):
        bad.append((r["id"], "must_contain_type"))

# T-01-4 id regex + uniqueness (ids and queries)
IDRE = re.compile(r"^(S[1-5]-Q\d+|MS-Q\d+)$")
ids = [r["id"] for r in rows]; qs = [r["query"] for r in rows]
for r in rows:
    if not IDRE.match(r["id"]): bad.append((r["id"], "id_regex"))
if len(ids) != len(set(ids)): bad.append(("ids", "dup"))
if len(qs) != len(set(qs)):   bad.append(("queries", "dup"))

# T-01-3 groundedness (union semantics) + T-01-5 source/path truth
for r in rows:
    srcs = r["source"].split("+")
    if any(s not in SRC for s in srcs): bad.append((r["id"], "source")); continue
    miss = [f for f in r["must_contain"] if not any(f in bund[s] for s in srcs)]
    if miss: bad.append((r["id"], "must_contain_grounding", miss))
    if not any(r["ideal_context"] in bund[s] for s in srcs):
        bad.append((r["id"], "context_not_contiguous"))
    if r["path"] != " + ".join("data/docs/"+SRC[s] for s in srcs):
        bad.append((r["id"], "path", r["path"]))

# T-01-7 no secrets
SEC = re.compile(r"(sk-[A-Za-z0-9]{20,}|api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}"
                  r"|AIza[A-Za-z0-9_\-]{20,}|gsk_[A-Za-z0-9]{20,})", re.I)
for r in rows:
    if SEC.search(r["ideal_answer"] + r["ideal_context"] + " ".join(r["must_contain"])):
        bad.append((r["id"], "secret"))

print("TOTAL", len(rows), "| FAILURES:", bad if bad else "NONE")
```

Exit-criteria mapping: T-01-1 counts + T-01-6 category minimums (≥5 each of
misroute/conflict/abstain/degrade) are **completion targets at file level** — report them
every run:

```python
from collections import Counter
cc = Counter(r["category"] for r in rows)
print("categories:", dict(cc))
print("edge: misroute", cc["misroute"], "conflict", cc["conflict"],
      "abstain", cc["abstain"], "degrade", cc["degrade"], "(target ≥5 each)")
```

## 6. Failure modes hit this session (and the fixes)

| Symptom | Cause | Fix |
|---|---|---|
| `MARKER FAIL` | anchor lines off by one (assumed from an earlier read) | re-read the real lines, fix `nums` — the assert *is* the safety net |
| `NOT CONTIGUOUS` | skipped a blank line between anchors (e.g. `[190,191,192,194,195]`, 193 blank) | include the blank line in `nums` |
| `must_contain_grounding` on `**measured answer**` | markdown bold spans the fragment | use the verbatim substring `"measured answer (code volume,"` or drop it |
| `must_contain_grounding` on `"not the source of truth"` | the phrase wraps across a line break (`"not the source of\n"` + `truth.**`) | use the unwrapped fragment `"not the source of"` |
| `must_contain_grounding` on `avg_score < 0.5` | real text is `agent_scores["avg_score"] < 0.5` | quote the exact code: `"\"avg_score\"] < 0.5"` |
| marker split by backtick | `` `BAAI/bge-base-en-v1.5` `` — the backtick is between `BAAI/...v1.5` and ` via` | marker ``"**Model:** `BAAI/bge-base-en-v1.5`"`` |

Rule: **never edit the JSON by hand after a failure** — re-run the batch script with the
fixed tuple; it is idempotent (reloads committed rows) and rewrites the file atomically.

## 7. Category heuristics (the judgment half — not scriptable)

- **cite** — a number/fact that must be quoted verbatim; `must_contain` = the citation-critical
  strings. *(bulk of the file)*
- **misroute** — row's query mentions a topic a naive router would send elsewhere (e.g. a
  "retry" question whose correct source is S2, tempting S3; a "judge model" question whose
  correct source is S1, tempting S4/S5). `source`/`path` record the **correct** source; the
  `ideal_answer` names the wrong target explicitly.
- **conflict** — two corpus passages disagree (e.g. step-2 README embeds `bge` while step 3
  claims "same as Step 2" with `qwen3-embed` → `MS-Q002`; `S1-Q031` recall-score mismatch).
  Answer must surface both sides, never pick one.
- **abstain** — corpus-declared non-content: a question the bundle poses but never answers
  (`S2-Q015`), or a documented refusal behavior (`S1-Q029`). Answer says "not recorded;
  do not invent".
- **degrade** — runtime handling of degraded conditions: rate-limit/retry behavior
  (`S1-Q018`), grade-and-retry loops (`S2-Q024`).
- **multi-source** — union rows `MS-*`, the seam for `where`-filter routing (Mod 4).
- **basic** — direct facts ("what X uses", "which model"). The tester cap is **≤ ~30%** of a
  file — write cite/edge rows preferentially for S3..S5.

## 8. NB-01 handoff checklist (learner's script must assert)

1. Load `retriever_goldens.json` + the 5 bundles via the manifest (section 1).
2. Exact-8-keys, category enum, `must_contain` shape (T-01-2).
3. Id regex `S[1-5]-Q\d+|MS-Q\d+`, unique ids, unique queries (T-01-4).
4. `must_contain` union-grounding + `ideal_context` contiguity, per row, with a
   per-row PASS/FAIL report (T-01-3).
5. `path` derived from the manifest (T-01-5).
6. Secret regex scan (T-01-7).
7. Counts + per-category report (T-01-1, T-01-6).
8. Print `FAILURES: NONE` or the failure list; exit non-zero on failures.

## Verify

```bash
uv run python - <<'EOF'
# paste section 5's suite, run against eval/goldens/retriever_goldens.json
# expected: TOTAL 67 | FAILURES: NONE  (2026-09-11)
EOF
```