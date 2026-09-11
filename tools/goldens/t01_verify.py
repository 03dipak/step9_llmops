#!/usr/bin/env python3
"""T-01 verifier (mirrors doc/design/01_authoring_recipe.md section 5) + file-level
counts (T-01-1) + category minimums (T-01-6). Usage:
    python3 t01_verify.py <gold.json> <lo> <hi> [other_goldens...]
Checks T-01-2/3/4/5/7 per row; prints counts, edge minimums, basic share, and
cross-file id/query uniqueness when extra golden files are passed.
"""
import json, re, sys

KEYS = {"id", "category", "query", "ideal_answer", "ideal_context",
        "must_contain", "source", "path"}
CATS = {"cite", "conflict", "misroute", "abstain", "degrade", "multi-source", "basic"}
IDRE = re.compile(r"^(S[1-5]-Q\d+|MS-Q\d+)$")
SEC = re.compile(r"(sk-[A-Za-z0-9]{20,}|api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}"
                 r"|AIza[A-Za-z0-9_\-]{20,}|gsk_[A-Za-z0-9]{20,})", re.I)
SRC = {"S1": "s1_early_steps_bundle.md", "S2": "s2_frameworks_bundle.md",
       "S3": "s3_lifecycle_bundle.md", "S4": "s4_qa_deep_dives.md", "S5": "s5_docs_bundle.md"}
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]  # this file lives at <repo>/tools/goldens/

DATA = str(ROOT / "data" / "docs") + "/"
bund = {k: open(DATA + v, encoding="utf-8").read() for k, v in SRC.items()}

def verify(path, lo, hi):
    rows = json.load(open(path))
    bad = []

    # T-01-2 schema exact + enum + must_contain shape
    for r in rows:
        if set(r.keys()) != KEYS:
            bad.append((r.get("id", "?"), "keys", sorted(set(r.keys()) ^ KEYS)))
        if r["category"] not in CATS:
            bad.append((r["id"], "category"))
        if not isinstance(r["must_contain"], list) or not all(
                isinstance(x, str) and x for x in r["must_contain"]):
            bad.append((r["id"], "must_contain_type"))

    # T-01-4 id regex + uniqueness (ids and queries)
    ids = [r["id"] for r in rows]; qs = [r["query"] for r in rows]
    for r in rows:
        if not IDRE.match(r["id"]):
            bad.append((r["id"], "id_regex"))
    if len(ids) != len(set(ids)):
        bad.append(("ids", "dup"))
    if len(qs) != len(set(qs)):
        bad.append(("queries", "dup"))

    # T-01-3 groundedness (union semantics) + T-01-5 source/path truth
    for r in rows:
        srcs = r["source"].split("+")
        if any(s not in SRC for s in srcs):
            bad.append((r["id"], "source")); continue
        miss = [f for f in r["must_contain"] if not any(f in bund[s] for s in srcs)]
        if miss:
            bad.append((r["id"], "must_contain_grounding", miss))
        if not any(r["ideal_context"] in bund[s] for s in srcs):
            bad.append((r["id"], "context_not_contiguous"))
        if r["path"] != " + ".join("data/docs/" + SRC[s] for s in srcs):
            bad.append((r["id"], "path", r["path"]))

    # T-01-7 no secrets
    for r in rows:
        blob = r["ideal_answer"] + r["ideal_context"] + " ".join(r["must_contain"])
        if SEC.search(blob):
            bad.append((r["id"], "secret"))

    # T-01-1 counts + basic cap; T-01-6 edge minimums
    from collections import Counter
    cc = Counter(r["category"] for r in rows)
    n = len(rows)
    ok = (lo <= n <= hi and all(cc[c] >= 5 for c in ("misroute", "conflict", "abstain", "degrade"))
          and cc["basic"] <= 0.30 * n)

    print(f"--- {path}")
    print(f"TOTAL {n} (range {lo}-{hi}) | FAILURES: {bad if bad else 'NONE'}")
    print("categories:", dict(cc))
    for c in ("misroute", "conflict", "abstain", "degrade"):
        print(f"  edge {c}: {cc[c]} (target >=5: {'OK' if cc[c] >= 5 else 'FAIL'})")
    print(f"  basic share: {cc['basic'] / n:.1%} (cap 30%: {'OK' if cc['basic'] <= 0.30 * n else 'FAIL'})")
    print("  file-level targets:", "PASS" if ok and not bad else "FAIL")
    return rows, (ok and not bad)

if __name__ == "__main__":
    def _res(p):
        return p if Path(p).is_absolute() else ROOT / p

    rows, okflag = verify(str(_res(sys.argv[1])), int(sys.argv[2]), int(sys.argv[3]))
    # cross-file id/query collision with any additional golden files
    for other in sys.argv[4:]:
        other = str(_res(other))
        orows = json.load(open(other))
        oids = {r["id"] for r in orows}; oqs = {r["query"] for r in orows}
        iid = oids & {r["id"] for r in rows}
        iq = oqs & {r["query"] for r in rows}
        if iid:
            print("  CROSS-FILE id collision:", iid); okflag = False
        if iq:
            print("  CROSS-FILE query collision:", iq); okflag = False
        else:
            print(f"  cross-file vs {other}: ids OK, queries OK")
    sys.exit(0 if okflag else 1)