#!/usr/bin/env python3
r"""
NB-01 — Anchor Check (standalone .py mirror of jupyter_notebook/NB-01_anchor_check.ipynb)

Companion to `doc/design/01_lld_tests.md` and `doc/design/01_authoring_recipe.md`.

This script validates the golden datasets against the Mod-01 contract (T-01),
exactly like the notebook — but runs from a plain shell, no Jupyter, no dotenv.

Usage:
    python3 NB-01_anchor_check.py [gold.json ...]
    # no args -> checks all three golden files with their target bands:
    #   retriever_goldens.json            120-160
    #   query_processing_goldens.json      60-75
    #   correctness_goldens.json          100-120

Checks per file (T-01-1..7, 9 — same logic/messages as the notebook):
  T-01-1  counts in target band
  T-01-2  exact 8-field schema, category enum, must_contain shape
  T-01-3  groundedness: ideal_context contiguous + must_contain union-grounded
  T-01-4  ID regex `S[1-5]-Q\d+|MS-Q\d+` + uniqueness (ids and queries)
  T-01-5  source/path truth derived from the corpus manifest
  T-01-6  edge category minimums (misroute/conflict/abstain/degrade >= 5 each),
          plus the basic-share cap (<= 30% of file rows)
  T-01-7  no secrets
  T-01-9  answerable-from-corpus-only (heuristic + spot-check sample; warnings only)

EXTRA vs the notebook: when more than one golden file is checked, ids and
queries are asserted unique ACROSS files (cross-file collision gate).

All checks are offline and deterministic. Exit code 0 when every check passes,
1 otherwise (so CI can fail).
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

# --- Repo root resolution ---------------------------------------------------
# Makes the relative "data/..." and "eval/..." paths work no matter where the
# script is launched from (same trick as notebook cell 1). Checks the current
# directory first, then falls back to the script's own location — so it also
# runs from outside the repo.
def _find_root(start: Path) -> Path:
    p = start
    while not (p / "pyproject.toml").exists() and p != p.parent:
        p = p.parent
    return p


ROOT = _find_root(Path.cwd())
if not (ROOT / "pyproject.toml").exists():
    ROOT = _find_root(Path(__file__).resolve().parent)

assert (ROOT / "pyproject.toml").exists(), (
    f"pyproject.toml not found in any parent directory — stopped at {ROOT}"
)

DATA = ROOT / "data" / "docs"

# --- Corpus manifest (S1..S5) ------------------------------------------------
SRC = {
    "S1": "s1_early_steps_bundle.md",
    "S2": "s2_frameworks_bundle.md",
    "S3": "s3_lifecycle_bundle.md",
    "S4": "s4_qa_deep_dives.md",
    "S5": "s5_docs_bundle.md",
}

# --- Schema contract ----------------------------------------------------------
KEYS = {"id", "category", "query", "ideal_answer", "ideal_context",
        "must_contain", "source", "path"}
CATS = {"cite", "conflict", "misroute", "abstain", "degrade", "multi-source", "basic"}
IDRE = re.compile(r"^(S[1-5]-Q\d+|MS-Q\d+)$")
SEC = re.compile(
    r"(sk-[A-Za-z0-9]{20,}"
    r"|api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}"
    r"|AIza[A-Za-z0-9_\-]{20,}"
    r"|gsk_[A-Za-z0-9]{20,})",
    re.I,
)

# --- Target bands per golden file (T-01-1) -------------------------------------
BANDS = {
    "retriever_goldens.json": (120, 160),
    "query_processing_goldens.json": (60, 75),
    "correctness_goldens.json": (100, 120),
}

# --- Load corpus -----------------------------------------------------------------
bund = {}
for src, filename in SRC.items():
    path = DATA / filename
    if not path.exists():
        sys.exit(f"missing bundle: {path}")
    bund[src] = path.read_text(encoding="utf-8")


def expect_path(srcs):
    """Derive the expected `path` value from the manifest (T-01-5)."""
    return " + ".join("data/docs/" + SRC[s] for s in srcs)


def verify_golden(gold_path, rows, lo, hi):
    """Run T-01-1..7,9 over one golden file; return (bad_checks, per-check prints)."""

    # --- T-01-1: counts in band -------------------------------------------------
    n = len(rows)
    if not (lo <= n <= hi):
        return [("T-01-1", f"count={n}, expected {lo}-{hi}")], []
    print(f"T-01-1 PASS: counts in range (n={n}, band {lo}-{hi})")

    bad = []

    # --- T-01-2: schema exactness, category enum, must_contain shape -------------
    for r in rows:
        rid = r.get("id", "?")
        if set(r.keys()) != KEYS:
            bad.append((rid, "keys", sorted(set(r.keys()) ^ KEYS)))
        if r["category"] not in CATS:
            bad.append((rid, "category", r["category"]))
        mc = r.get("must_contain")
        if not isinstance(mc, list) or len(mc) == 0:
            bad.append((rid, "must_contain_type", "not a non-empty list"))
        elif not all(isinstance(x, str) and x for x in mc):
            bad.append((rid, "must_contain_type", "contains non-string or empty"))
    if bad:
        return [("T-01-2", bad)], []
    print("T-01-2 PASS: schema, category enum, must_contain shape")

    # --- T-01-4: ID regex + uniqueness (ids and queries) --------------------------
    ids = [r["id"] for r in rows]
    qs = [r["query"] for r in rows]
    id_bad = []
    for r in rows:
        if not IDRE.match(r["id"]):
            id_bad.append((r["id"], "id_regex"))
    if len(ids) != len(set(ids)):
        id_bad.append(("ids", "dup"))
    if len(qs) != len(set(qs)):
        id_bad.append(("queries", "dup"))
    if id_bad:
        return [("T-01-4", id_bad)], []
    print("T-01-4 PASS: ID regex + uniqueness")

    # --- T-01-3 & T-01-5: groundedness + source/path truth ------------------------
    g_bad = []
    for r in rows:
        rid = r["id"]
        srcs = r["source"].split("+")
        if any(s not in SRC for s in srcs):
            g_bad.append((rid, "source", srcs))
            continue
        miss = [f for f in r["must_contain"] if not any(f in bund[s] for s in srcs)]
        if miss:
            g_bad.append((rid, "must_contain_grounding", miss))
        if not any(r["ideal_context"] in bund[s] for s in srcs):
            g_bad.append((rid, "context_not_contiguous"))
        if r["path"] != expect_path(srcs):
            g_bad.append((rid, "path", {"got": r["path"], "expected": expect_path(srcs)}))
    if g_bad:
        return [("T-01-3/T-01-5", g_bad)], []
    print("T-01-3 & T-01-5 PASS: groundedness + source/path truth")

    # --- T-01-7: no secrets ---------------------------------------------------------
    sec_bad = []
    for r in rows:
        text = r["ideal_answer"] + r["ideal_context"] + " ".join(r["must_contain"])
        if SEC.search(text):
            sec_bad.append((r["id"], "secret"))
    if sec_bad:
        return [("T-01-7", sec_bad)], []
    print("T-01-7 PASS: no secrets")

    # --- T-01-6: category minimums + basic-share cap ---------------------------------
    cc = Counter(r["category"] for r in rows)
    edge_mins = {"misroute": 5, "conflict": 5, "abstain": 5, "degrade": 5}
    cat_bad = [(c, cc.get(c, 0), m) for c, m in edge_mins.items() if cc.get(c, 0) < m]
    if cc["basic"] > 0.30 * n:
        cat_bad.append(("basic_cap", cc["basic"], int(0.30 * n)))
    if cat_bad:
        return [("T-01-6", cat_bad)], []
    print(
        "T-01-6 PASS: edge category minimums "
        + ", ".join(f"{k}={cc.get(k, 0)}" for k in edge_mins)
        + f" | basic share {cc['basic'] / n:.1%} (cap 30%)"
    )

    # --- T-01-9: answerable-from-corpus-only (heuristic + spot-check sample) ----------
    # Full automation is impossible; heuristic failures are warnings, manual review
    # is the real gate.
    heuristic_failures = []
    for r in rows:
        rid, srcs, query = r["id"], r["source"].split("+"), r["query"]
        tokens = [t for t in query.lower().split() if len(t) > 4]
        if not tokens:
            continue
        if not any(any(t in bund[s].lower() for t in tokens) for s in srcs):
            heuristic_failures.append((rid, query))

    lines = ["T-01-9 heuristic: no warnings" if not heuristic_failures
             else "T-01-9 HEURISTIC WARNINGS (review manually):"]
    lines += [f"  {rid}: {q[:80]}..." for rid, q in heuristic_failures[:20]]
    lines.append("\nT-01-9 spot-check sample (for manual review):")
    by_source = {}
    for r in rows:
        for s in r["source"].split("+"):
            by_source.setdefault(s, []).append(r)
    # deterministic sample (5 per source), no RNG surprises
    for s in sorted(by_source):
        sample = by_source[s][:5]
        lines.append(f"\n{s} sample:")
        lines += [f"  {r['id']}: {r['query'][:80]}" for r in sample]

    return None, lines


def main():
    args = sys.argv[1:]
    if args:
        files = []
        for a in args:
            p = a if Path(a).is_absolute() else ROOT / a
            files.append(p)
        # pull default bands by filename where known
        bands = []
        for p in files:
            bands.append((p, *BANDS.get(p.name, (0, 10**9))))
    else:
        bands = [(ROOT / "eval" / "goldens" / name, *b) for name, b in BANDS.items()]

    all_rows = {}
    any_fail = False

    for gold_path, lo, hi in bands:
        print(f"\n=== {gold_path.relative_to(ROOT)} ({lo}-{hi}) ===")
        if not gold_path.exists():
            print(f"  MISSING FILE: {gold_path}")
            any_fail = True
            continue
        rows = json.loads(gold_path.read_text(encoding="utf-8"))
        all_rows[str(gold_path)] = rows
        bad, t9_lines = verify_golden(gold_path, rows, lo, hi)
        for l in (t9_lines or []):
            print("  " + l)
        if bad:
            any_fail = True
            for tag, detail in bad:
                print(f"  {tag} FAIL: {str(detail)[:200]}")
            print(f"  TOTAL {len(rows)} | FAILURES: {bad}")
        else:
            print(f"  TOTAL {len(rows)} | FAILURES: NONE")

    # --- EXTRA: cross-file id/query uniqueness -----------------------------------
    if len(all_rows) > 1:
        seen_ids, seen_queries = {}, {}
        collision = None
        for path, rows in all_rows.items():
            for r in rows:
                if r["id"] in seen_ids:
                    collision = (r["id"], "id", path, seen_ids[r["id"]])
                if r["query"] in seen_queries:
                    collision = (r["query"], "query", path, seen_queries[r["query"]])
                seen_ids[r["id"]] = path
                seen_queries[r["query"]] = path
        if collision:
            print(f"\nCROSS-FILE collision: {collision}")
            any_fail = True
        else:
            print("\nCROSS-FILE check: ids OK, queries OK")

    print("\n" + "=" * 60)
    print("NB-01 ANCHOR CHECK SUMMARY")
    print("=" * 60)
    print("✅ ALL TESTS PASSED" if not any_fail else "❌ FAILURES PRESENT")
    sys.exit(0 if not any_fail else 1)


if __name__ == "__main__":
    main()