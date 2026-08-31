"""
Score the manual annotations against the audit's verdicts.

Handles one annotator or many. With several people it reports three things that
matter separately:

  1. Whether the annotators agree with each other (Fleiss' kappa). If they do
     not, there is no human ground truth to validate anything against, and the
     rest of the output is meaningless.
  2. Whether the pooled human judgment agrees with the automated audit (majority
     vote, Cohen's kappa, bootstrap CI). This is the construct validity claim.
  3. Where the two come apart, and whether redundancy explains it.

The disagreement analysis tests one specific hypothesis: that the audit is wrong
when another retrieved chunk carries near-equivalent information, so the answer
stayed similar even though the citation was genuine.

Agreement is also broken out for Type D (unanswerable) items, because the removal
test is not well defined for a refusal: every source is arguably needed to justify
"none of these match", and equally none is, since removing any one leaves the
refusal standing. Pooling those with ordinary assertions hides the distinction.

    python evaluation/score_annotations.py
"""
import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

VAL = Path("experiments/results/validation")

# human judgment -> the audit verdict it corresponds to
MAP = {"needed": "genuine", "not_needed": "post_rationalised"}
LABELS = ["genuine", "post_rationalised"]
CHECK_ID = "__attention_check"


def kappa(a, b):
    """Cohen's kappa for two aligned label sequences."""
    n = len(a)
    if n == 0:
        return None
    labels = sorted(set(a) | set(b))
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return None if pe == 1 else (po - pe) / (1 - pe)


def kappa_ci(a, b, iters=2000, seed=42):
    """Bootstrap CI. n is small, so report an interval rather than a point estimate."""
    rng = random.Random(seed)
    n = len(a)
    vals = []
    for _ in range(iters):
        idx = [rng.randrange(n) for _ in range(n)]
        k = kappa([a[j] for j in idx], [b[j] for j in idx])
        if k is not None:
            vals.append(k)
    if not vals:
        return None, None
    vals.sort()
    return vals[int(.025 * len(vals))], vals[int(.975 * len(vals))]


def fleiss(votes_by_item):
    """Fleiss' kappa, allowing a different number of raters per item.

    votes_by_item: {item_id: Counter(label -> count)}. Items rated fewer than
    twice carry no agreement information and are dropped.
    """
    rows = [c for c in votes_by_item.values() if sum(c.values()) >= 2]
    if len(rows) < 2:
        return None, 0
    cats = sorted({l for c in rows for l in c})
    p_i = []
    total = 0
    col = Counter()
    for c in rows:
        n_i = sum(c.values())
        total += n_i
        for l in cats:
            col[l] += c[l]
        p_i.append((sum(c[l] ** 2 for l in cats) - n_i) / (n_i * (n_i - 1)))
    p_bar = sum(p_i) / len(p_i)
    p_e = sum((col[l] / total) ** 2 for l in cats)
    if p_e >= 1:
        return None, len(rows)
    return (p_bar - p_e) / (1 - p_e), len(rows)


def interpret(k):
    if k is None:
        return "undefined"
    if k < 0:    return "worse than chance"
    if k < 0.20: return "slight"
    if k < 0.40: return "fair"
    if k < 0.60: return "moderate"
    if k < 0.80: return "substantial"
    return "almost perfect"


def load_annotations(paths):
    """Read every CSV. Accepts the new schema with an annotator column and the
    old single-annotator schema, where the filename supplies the name."""
    rows = []
    for p in paths:
        stem = p.stem.replace("annotations_", "").replace("annotations", "") or p.stem
        with p.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if not r.get("item_id"):
                    continue
                rows.append({
                    "annotator": (r.get("annotator") or stem or "anon").strip(),
                    "item_id": r["item_id"].strip(),
                    "judgment": (r.get("judgment") or "").strip(),
                    "note": (r.get("note") or "").strip(),
                    # Which instrument produced this. Older exports predate the
                    # column and are all from the detailed survey.
                    "mode": (r.get("mode") or "full").strip() or "full",
                    "pick": (r.get("pick") or "").strip(),
                    "file": p.name,
                })
    return rows


def find_files(arg):
    p = Path(arg)
    if p.is_dir():
        return sorted(p.glob("*.csv"))
    if p.exists():
        return [p]
    # default layout: a directory of per-annotator exports, else the legacy file
    d = VAL / "annotations"
    if d.is_dir() and any(d.glob("*.csv")):
        return sorted(d.glob("*.csv"))
    legacy = VAL / "annotations.csv"
    return [legacy] if legacy.exists() else []


def rule(title=None, ch="-"):
    print("\n" + ch * 72)
    if title:
        print(title)
        print(ch * 72)


MODE_BLURB = {
    "full": ("DETAILED SURVEY — 'did the AI really use this description?'",
             "Validates the audit's verdict directly, redundancy included."),
    "simple": ("QUICK SURVEY — 'which company answers this question?'",
               "Convergent check, not a replication. People pick the company they\n"
               "  think answers the question; agreement means the AI cited the source\n"
               "  a reader would have used. Cite it for citation correctness\n"
               "  (Table 4.11), and for the duplicate-company evidence below — not\n"
               "  as validation of PRR, which only the detailed survey establishes."),
}


def resolve_picks(rows, key):
    """Turn multiple-choice picks into the two labels the rest of the code uses.

    Picking the company the AI cited means the citation pointed at the source a
    reader would have used, which lines up with the audit calling it genuine.
    Picking a different company, or none, means it did not.
    """
    for r in rows:
        if r["mode"] != "simple" or r["judgment"]:
            continue
        pick, k = r["pick"], key.get(r["item_id"])
        if not pick or not k:
            continue
        if pick == "unclear":
            r["judgment"] = "unclear"
        else:
            r["judgment"] = ("needed" if pick == str(k["target_index"])
                             else "not_needed")


def report_picks(rows, key, names):
    """What people actually chose. This is where the duplicate-company problem
    shows up: several readers independently picking a company the AI did not
    cite, on an item where two records describe the same business."""
    by_item = defaultdict(list)
    for r in rows:
        if r["item_id"] in key and r["pick"] and r["pick"] != "unclear":
            by_item[r["item_id"]].append(r["pick"])
    if not by_item:
        return
    rule("WHAT PEOPLE PICKED  (items where the majority did not pick the cited source)")
    shown = 0
    for iid, picks in sorted(by_item.items()):
        tgt = str(key[iid]["target_index"])
        top, n = Counter(picks).most_common(1)[0]
        if top == tgt or n <= len(picks) / 2:
            continue
        shown += 1
        nm = names.get(iid, {})
        print(f"  {iid:<16} cited {nm.get(tgt, tgt)}")
        print(f"{'':<18} {n}/{len(picks)} picked "
              f"{'none of them' if top == 'none' else nm.get(top, top)}")
    if not shown:
        print("  none — the majority picked the cited source on every item")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotations", default=str(VAL / "annotations"),
                    help="a directory of per-annotator CSVs, or a single CSV")
    ap.add_argument("--key", default=str(VAL / "answer_key.json"))
    ap.add_argument("--min-raters", type=int, default=1,
                    help="drop items with fewer than this many usable judgments")
    ap.add_argument("--mode", choices=["full", "simple", "both"], default="both",
                    help="which instrument to score; 'both' runs each separately")
    args = ap.parse_args()

    files = find_files(args.annotations)
    kpath = Path(args.key)
    if not files:
        print(f"No annotation CSVs found at {args.annotations}")
        print(f"Collect the exported files into {VAL}/annotations/ and re-run.")
        return
    if not kpath.exists():
        print(f"No answer key at {kpath}. Re-run build_annotation_set.py.")
        return

    key = {r["item_id"]: r for r in json.loads(kpath.read_text())}
    all_rows = load_annotations(files)
    resolve_picks(all_rows, key)
    npath = VAL / "pick_options.json"
    names = json.loads(npath.read_text()) if npath.exists() else {}

    # The two instruments ask different questions and must never be pooled.
    present = sorted({r["mode"] for r in all_rows})
    wanted = present if args.mode == "both" else [args.mode]
    todo = [m for m in wanted if m in present]
    if not todo:
        print(f"No judgments for mode '{args.mode}'. Present: {', '.join(present)}")
        return
    for n, mode in enumerate(todo):
        if n:
            print("\n\n")
        score_one([r for r in all_rows if r["mode"] == mode], key, args, mode,
                  len(files), names)


def score_one(rows, key, args, mode, n_files, names=None):
    head, blurb = MODE_BLURB.get(mode, (mode.upper(), ""))
    print("=" * 72)
    print(head)
    print("=" * 72)
    if blurb:
        print("  " + blurb)
    print(f"\n{n_files} file(s) read, {len(rows)} judgments in this mode")

    # ---- attention check, before anything is trusted -------------------------
    # Passing looks different per instrument: the detailed survey asks for
    # "Can't tell", the quick one for the option that says "Please pick this one".
    checks = {}
    for r in rows:
        if r["item_id"] == CHECK_ID:
            checks[r["annotator"]] = r["pick"] if mode == "simple" else r["judgment"]
    want = "1" if mode == "simple" else "unclear"
    failed = {a for a, j in checks.items() if j != want}
    if checks:
        ok = len(checks) - len(failed)
        print(f"attention check: {ok}/{len(checks)} passed"
              + (f" — FAILED: {', '.join(sorted(failed))}" if failed else ""))
        print("  (failures are kept in the analysis below; exclude them by hand"
              "\n   if you decide to, and say so in the write-up)" if failed else "")

    # ---- organise ------------------------------------------------------------
    by_item = defaultdict(dict)      # item_id -> {annotator: judgment}
    notes = defaultdict(list)        # item_id -> [(annotator, note)]
    unmatched = set()
    for r in rows:
        iid = r["item_id"]
        if iid == CHECK_ID or iid.startswith("__"):
            continue
        if iid not in key:
            unmatched.add(iid)
            continue
        if r["judgment"] in ("needed", "not_needed", "unclear"):
            by_item[iid][r["annotator"]] = r["judgment"]
            if r["note"]:
                notes[iid].append((r["annotator"], r["note"]))
    annotators = sorted({a for v in by_item.values() for a in v})
    print(f"annotators: {len(annotators)} ({', '.join(annotators)})")
    print(f"items with at least one judgment: {len(by_item)}/{len(key)}")
    if unmatched:
        print(f"unmatched item ids ignored: {len(unmatched)}")

    if not by_item:
        print("\nNothing scoreable.")
        return

    # ---- 1. do the humans agree with each other? -----------------------------
    if len(annotators) > 1:
        rule("HUMAN AGREEMENT  (is there a ground truth at all?)")
        votes = {i: Counter(v.values()) for i, v in by_item.items()}
        fk, n_multi = fleiss(votes)
        print(f"  items rated by 2+ people   {n_multi}")
        if fk is not None:
            print(f"  Fleiss' kappa              {fk:.3f}   ({interpret(fk)})")
        else:
            print("  Fleiss' kappa              undefined")

        # Unanimity is the plainer statement and easier to defend in text.
        multi = [c for c in votes.values() if sum(c.values()) >= 2]
        if multi:
            unan = sum(1 for c in multi if len(c) == 1)
            print(f"  unanimous                  {unan}/{len(multi)} "
                  f"({unan/len(multi):.0%})")

        print("\n  pairwise agreement:")
        for x in range(len(annotators)):
            for y in range(x + 1, len(annotators)):
                a1, a2 = annotators[x], annotators[y]
                shared = [(by_item[i][a1], by_item[i][a2]) for i in by_item
                          if a1 in by_item[i] and a2 in by_item[i]]
                if not shared:
                    continue
                agr = sum(1 for p, q in shared if p == q) / len(shared)
                k = kappa([p for p, _ in shared], [q for _, q in shared])
                ks = f"{k:.2f}" if k is not None else "  na"
                print(f"    {a1:<12} vs {a2:<12} {agr:>5.0%}  "
                      f"({len(shared)} shared, kappa {ks})")

    # ---- 2. pooled human judgment vs the audit -------------------------------
    paired, unclear, tied, thin = [], [], [], []
    for iid, v in by_item.items():
        binary = [j for j in v.values() if j in MAP]
        if len(v) < args.min_raters:
            thin.append(iid)
            continue
        if not binary:
            unclear.append({**key[iid], "votes": dict(v)})
            continue
        c = Counter(binary)
        top = c.most_common()
        if len(top) > 1 and top[0][1] == top[1][1]:
            tied.append({**key[iid], "votes": dict(v)})
            continue
        paired.append({
            **key[iid],
            "human": MAP[top[0][0]],
            "votes": dict(v),
            "consensus": top[0][1] / len(binary),
            "n_unclear": sum(1 for j in v.values() if j == "unclear"),
            "note": "; ".join(f"{a}: {n}" for a, n in notes.get(iid, [])),
        })

    rule("HUMAN vs AUDIT", "=")
    print(f"  scored {len(paired)} | all-unclear {len(unclear)} | "
          f"tied {len(tied)} | too few raters {len(thin)}")
    if not paired:
        print("\nNothing scoreable.")
        return

    human = [p["human"] for p in paired]
    audit = [p["audit_verdict"] for p in paired]
    agree = sum(1 for h, a in zip(human, audit) if h == a)
    pct = agree / len(paired)
    k = kappa(human, audit)
    lo, hi = kappa_ci(human, audit)

    print(f"\n  agreement   {agree}/{len(paired)}  ({pct:.1%})")
    if k is not None:
        print(f"  kappa       {k:.3f}  [{lo:.3f}, {hi:.3f}]   ({interpret(k)})")

    rule("CONFUSION  (rows: audit, cols: human)")
    cm = defaultdict(int)
    for h, a in zip(human, audit):
        cm[(a, h)] += 1
    print(f"{'':<20}" + "".join(f"{l:>20}" for l in LABELS))
    for a in LABELS:
        print(f"{a:<20}" + "".join(f"{cm[(a,h)]:>20}" for h in LABELS))

    rule("AGREEMENT BY SIMILARITY BAND")
    bands = defaultdict(list)
    for p in paired:
        bands[p["band"]].append(p["human"] == p["audit_verdict"])
    for b in ["far_below", "below", "above", "far_above"]:
        v = bands.get(b)
        if v:
            print(f"  {b:<12} {sum(v)}/{len(v)}  ({sum(v)/len(v):.0%})")

    # Refusals are a different construct. Report them apart.
    rule("AGREEMENT BY QUERY TYPE  (D = unanswerable, i.e. refusals)")
    types = defaultdict(list)
    for p in paired:
        types[p.get("query_type") or "?"].append(p["human"] == p["audit_verdict"])
    for t in sorted(types):
        v = types[t]
        print(f"  type {t:<8} {sum(v)}/{len(v)}  ({sum(v)/len(v):.0%})")
    d_v = types.get("D")
    nd_v = [x for t, v in types.items() if t != "D" for x in v]
    if d_v and nd_v:
        d_r, nd_r = sum(d_v) / len(d_v), sum(nd_v) / len(nd_v)
        print(f"\n  refusals {d_r:.0%} vs assertions {nd_r:.0%}")
        if abs(d_r - nd_r) >= 0.15:
            print("  These differ materially. The removal test behaves differently on")
            print("  refusals, where necessity is ambiguous by construction. Report the")
            print("  two separately rather than pooling them into one PRR.")

    if mode == "simple":
        report_picks(rows, key, names or {})

    # ---- 3. disagreements ----------------------------------------------------
    dis = [p for p in paired if p["human"] != p["audit_verdict"]]
    rule(f"DISAGREEMENTS ({len(dis)})")
    if not dis:
        print("  none")
    else:
        print(f"{'item':<16}{'sim':>7}{'audit':>19}{'human':>19}"
              f"{'consensus':>11}{'overlap':>9}")
        for d in sorted(dis, key=lambda x: x["similarity"]):
            print(f"{d['item_id']:<16}{d['similarity']:>7.3f}"
                  f"{d['audit_verdict']:>19}{d['human']:>19}"
                  f"{d['consensus']:>10.0%}{d['other_chunk_overlap']:>9.2f}")
            if d.get("note"):
                print(f"    {d['note'][:150]}")

        d_ov = [d["other_chunk_overlap"] for d in dis]
        a_ov = [p["other_chunk_overlap"] for p in paired
                if p["human"] == p["audit_verdict"]]
        if d_ov and a_ov:
            md, ma = sum(d_ov) / len(d_ov), sum(a_ov) / len(a_ov)
            print(f"\n  mean other-chunk overlap:  disagree {md:.3f}  vs  agree {ma:.3f}")
            if md > ma * 1.3:
                print("  Disagreements sit at higher overlap. Consistent with the audit")
                print("  mislabelling citations as fake when a redundant chunk was present.")
                print("  Reportable as a concrete failure mode.")
            else:
                print("  No clear overlap difference. Redundancy does not explain these.")

    if unclear or tied:
        rule(f"NO USABLE MAJORITY ({len(unclear) + len(tied)})")
        for u in unclear + tied:
            why = "all unclear" if u in unclear else "split evenly"
            print(f"  {u['item_id']:<16} sim {u['similarity']:.3f}  "
                  f"audit says {u['audit_verdict']:<18} ({why})")
            for a, n in notes.get(u["item_id"], []):
                print(f"    {a}: {n[:110]}")

    # ---- 4. reading ----------------------------------------------------------
    rule("READING", "=")
    if pct >= 0.80:
        print(f"  Agreement {pct:.0%}. The automated measure tracks human judgment.")
        print("  Report in methodology as construct validation. This also weakens the")
        print("  threshold objection, since the measure demonstrably tracks the concept")
        print("  rather than an arbitrary cutoff.")
    elif pct >= 0.60:
        print(f"  Agreement {pct:.0%}. Partial validity.")
        print("  Report honestly, characterise the disagreements above, and soften any")
        print("  claim that PRR measures post-rationalisation exactly.")
    else:
        print(f"  Agreement {pct:.0%}. The measure does not track human judgment.")
        print("  Stop and reconsider before writing. Every PRR-based claim rests on this.")
    if mode == "simple":
        print("\n  Scope: people here judged which company answers the question, not")
        print("  whether the AI used a source. High agreement means the audit flags")
        print("  as post-rationalised the citations that point away from the company")
        print("  a reader would choose. That supports citation correctness and the")
        print("  redundancy story; it does not by itself validate PRR.")
    if len(paired) < 25:
        print(f"\n  Caveat: n={len(paired)} is small. The kappa interval is wide.")
    if len(annotators) == 1:
        print("\n  Caveat: one annotator. There is no way to show these judgments are")
        print("  reproducible. A reviewer will ask. Recruit at least two more.")

    out = VAL / f"validation_results_{mode}.json"
    payload = {
        "mode": mode,
        "n_annotators": len(annotators),
        "annotators": annotators,
        "attention_check_failed": sorted(failed),
        "n_scored": len(paired),
        "n_all_unclear": len(unclear),
        "n_tied": len(tied),
        "agreement": pct,
        "kappa": k,
        "kappa_ci": [lo, hi],
        "by_band": {b: sum(v) / len(v) for b, v in bands.items()},
        "by_query_type": {t: sum(v) / len(v) for t, v in types.items()},
        "disagreements": dis,
    }
    if len(annotators) > 1:
        fk, n_multi = fleiss({i: Counter(v.values()) for i, v in by_item.items()})
        payload["fleiss_kappa"] = fk
        payload["n_multi_rated"] = n_multi
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
