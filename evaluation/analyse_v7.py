"""
Full analysis of the v7 deterministic run (12 conditions, temperature 0).

Everything needed for the results chapter comes out of this one script, because
v7 logs carry query_type, ground truth, and discriminator identity inline.

    python evaluation/analyse_v7.py
    python evaluation/analyse_v7.py --tag 38k_v7 --out experiments/results/v7_deterministic
"""
import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from scipy.stats import ttest_rel, wilcoxon

LOG_DIR = Path("experiments/logs")

GENERATORS = ["gemini", "mistral", "llama3"]
TYPE_NAMES = {"A": "Answerable", "B": "Broad/Ambiguous",
              "C": "Hard/Paraphrased", "D": "Unanswerable"}

# Section 4.6: Mistral's and Llama 3's three adversarial conditions are the
# same condition run three times — discriminator identity doesn't touch the
# revised answer for a locally hosted generator, so C4/C6/C11 (and C8/C9/C12)
# are byte-identical. Gemini's three conditions are not identical (its output
# varies run to run), so all three are genuinely distinct data and stay
# pooled. Counting the local generators' replicates as three separate
# observations triples their sample size for free — the denominator bug
# flagged in planning/AUDIT_2026-08-16.md (Table 4.5: reported 39/66 and 24/66,
# should be 13/22 and 8/22).
REPLICATE_GROUPS = {
    "mistral": ["C4", "C6", "C11"],
    "llama3": ["C8", "C9", "C12"],
    "gemini": ["C2", "C5", "C10"],
}
CANONICAL_CONDITION = {gen: conds[0] for gen, conds in REPLICATE_GROUPS.items()}
N_DISTINCT_EXPERIMENTS = 3
BONFERRONI_ALPHA = 0.05 / N_DISTINCT_EXPERIMENTS


# ---------------------------------------------------------------- loading

def load_condition(cond, tag):
    """Newest log for this condition+tag, keyed by query_id."""
    matches = sorted(LOG_DIR.glob(f"{cond}_{tag}_*.jsonl"))
    if not matches:
        return None
    return {json.loads(l)["query_id"]: json.loads(l) for l in matches[-1].open()}


def load_all(tag, min_n=75):
    """Complete conditions only.

    A condition stopped part-way would otherwise be averaged over whichever
    queries happened to finish, which is a biased sample — the query set is
    ordered by type (A, then B, C, D), so a partial run is not a random subset.
    """
    data, partial = {}, {}
    for i in range(1, 13):
        cond = f"C{i}"
        recs = load_condition(cond, tag)
        if not recs:
            continue
        if len(recs) >= min_n:
            data[cond] = recs
        else:
            partial[cond] = len(recs)
    return data, partial


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def meta(recs):
    r = next(iter(recs.values()))
    return r.get("model"), r.get("discriminator"), r.get("pipeline")


# ---------------------------------------------------------------- metrics

def prr_summary(data):
    rows = []
    for cond, recs in sorted(data.items(), key=lambda kv: int(kv[0][1:])):
        gen, disc, pipe = meta(recs)
        before = mean(r["prr_before"] for r in recs.values())
        after = mean(r["prr_after"] for r in recs.values())
        rows.append({
            "condition": cond, "generator": gen,
            "discriminator": "—" if pipe == "baseline" else disc,
            "pipeline": pipe, "n": len(recs),
            "prr_before": before, "prr_after": after,
            "delta_pp": (after - before) * 100,
        })
    return rows


def prr_by_type(data):
    out = {}
    for cond, recs in data.items():
        buckets = defaultdict(list)
        for r in recs.values():
            if r.get("query_type"):
                buckets[r["query_type"]].append(r)
        out[cond] = {
            t: {"n": len(rs),
                "before": mean(x["prr_before"] for x in rs),
                "after": mean(x["prr_after"] for x in rs),
                "delta_pp": (mean(x["prr_after"] for x in rs)
                             - mean(x["prr_before"] for x in rs)) * 100}
            for t, rs in sorted(buckets.items())
        }
    return out


def cited_companies(rec):
    """Company names for the chunks the answer actually cites."""
    answer = rec.get("revised_answer") or rec.get("answer") or ""
    cited = {int(m) for m in re.findall(r"\[(\d+)\]", answer)}
    names = []
    for c in rec.get("chunks", []):
        if c.get("index") in cited:
            name = c.get("name") or c.get("text", "").split(".")[0]
            names.append(name.strip())
    return names


def ccr(data):
    """Citation Correctness Rate — did it cite the ground-truth company?

    Only meaningful for types with a real answer (A/B/C). Type D has no correct
    company, so the right behaviour is to cite nothing; scored separately as an
    abstention rate.
    """
    out = {}
    for cond, recs in data.items():
        scored = hits = 0
        d_total = d_abstained = 0
        for r in recs.values():
            gt = r.get("ground_truth_company")
            qtype = r.get("query_type")
            names = cited_companies(r)
            if qtype == "D":
                d_total += 1
                if not names:
                    d_abstained += 1
                continue
            if not gt:
                continue
            scored += 1
            gt_l = gt.lower()
            if any(gt_l in n.lower() or n.lower() in gt_l for n in names if n):
                hits += 1
        out[cond] = {
            "ccr": hits / scored if scored else None,
            "scored": scored, "hits": hits,
            "type_d_abstention": d_abstained / d_total if d_total else None,
            "type_d_n": d_total,
        }
    return out


def citation_counts(data):
    """Citations per answer, before and after.

    Needed to interpret PRR fairly: PRR is a *rate*, so a model that cites once
    per answer can score better than one that cites three times without being
    more faithful. Llama 3 cites markedly less than Gemini, so PRR differences
    between them must be read alongside these counts.
    """
    out = {}
    for cond, recs in data.items():
        before, after = [], []
        for r in recs.values():
            a0 = r.get("answer") or r.get("original_answer") or ""
            before.append(len(set(re.findall(r"\[(\d+)\]", a0))))
            a1 = r.get("revised_answer") or a0
            after.append(len(set(re.findall(r"\[(\d+)\]", a1))))
        gen, _, _ = meta(recs)
        out[cond] = {"generator": gen, "cites_before": mean(before),
                     "cites_after": mean(after),
                     "zero_citation_answers": sum(1 for c in before if c == 0)}
    return out


def gcr(data):
    """Generator Correction Receptivity — of the answers the audit flagged,
    what fraction did the generator actually improve when re-prompted?

    Mistral's and Llama 3's three adversarial conditions are byte-identical
    replicates (see REPLICATE_GROUPS above), so only the canonical condition
    is counted for them — otherwise the denominator triples for free. Gemini's
    three conditions are genuinely distinct data and stay pooled.
    """
    per_gen = defaultdict(lambda: {"reprompted": 0, "improved": 0, "unchanged": 0})
    for cond, recs in data.items():
        gen, _, pipe = meta(recs)
        if pipe != "adversarial":
            continue
        if gen in ("mistral", "llama3") and cond != CANONICAL_CONDITION[gen]:
            continue
        for r in recs.values():
            if r["prr_before"] <= 0:
                continue  # nothing flagged, no re-prompt
            b = per_gen[gen]
            b["reprompted"] += 1
            if r["prr_after"] < r["prr_before"]:
                b["improved"] += 1
            else:
                b["unchanged"] += 1
    return {g: {**v, "gcr": v["improved"] / v["reprompted"] if v["reprompted"] else None}
            for g, v in per_gen.items()}


def trust_matrix(data):
    """generator x discriminator -> PRR delta and discriminator accuracy."""
    m = {}
    for cond, recs in data.items():
        gen, disc, pipe = meta(recs)
        if pipe != "adversarial":
            continue
        before = mean(r["prr_before"] for r in recs.values())
        after = mean(r["prr_after"] for r in recs.values())
        m[(gen, disc)] = {
            "condition": cond,
            "delta_pp": (after - before) * 100,
            "disc_accuracy": mean(r.get("discriminator_accuracy", 0)
                                  for r in recs.values()),
        }
    return m


def cohens_h(p1, p2):
    return 2 * math.asin(math.sqrt(max(p1, 0))) - 2 * math.asin(math.sqrt(max(p2, 0)))


def significance(data):
    """Paired significance test on per-query PRR, before vs after.

    Replaces the two-proportion z-test formerly used here, which was wrong on
    two counts: PRR is a mean of per-query rates in [0, 1], not a count of
    Bernoulli trials, so the z-test's p(1-p)/n variance does not apply; and
    before/after are the same queries, not independent samples, so the test
    needs to be paired. Wilcoxon signed-rank is the paired test reported as
    official here; a paired t-test is carried alongside as a cross-check
    (both are reported in the thesis).
    """
    rows = []
    for cond, recs in sorted(data.items(), key=lambda kv: int(kv[0][1:])):
        _, _, pipe = meta(recs)
        if pipe != "adversarial":
            continue
        before = [recs[qid]["prr_before"] for qid in sorted(recs)]
        after = [recs[qid]["prr_after"] for qid in sorted(recs)]
        n = len(before)
        b, a = mean(before), mean(after)
        changed = sum(1 for x, y in zip(before, after) if x != y)
        if all(x == y for x, y in zip(before, after)):
            t_p, w_p = 1.0, 1.0
        else:
            _, t_p = ttest_rel(after, before)
            _, w_p = wilcoxon(after, before)
        rows.append({
            "condition": cond, "before": b, "after": a, "n": n,
            "queries_changed": changed,
            "t_p": t_p, "p": w_p, "cohens_h": cohens_h(a, b),
        })
    return rows


# ---------------------------------------------------------------- reporting

def report(data, out_dir):
    print("=" * 74)
    print(f"v7 DETERMINISTIC RUN — {len(data)}/12 conditions, temperature 0")
    print("=" * 74)

    missing = [f"C{i}" for i in range(1, 13) if f"C{i}" not in data]
    if missing:
        print(f"\n!! not yet present: {', '.join(missing)}\n")

    print("\nPRR BEFORE -> AFTER")
    print("-" * 74)
    print(f"{'Cond':<6}{'Gen':<9}{'Disc':<9}{'n':>4}{'Before':>9}{'After':>9}{'Delta':>10}")
    summary = prr_summary(data)
    for r in summary:
        d = "—" if r["pipeline"] == "baseline" else f"{r['delta_pp']:+.1f}pp"
        print(f"{r['condition']:<6}{r['generator']:<9}{r['discriminator']:<9}"
              f"{r['n']:>4}{r['prr_before']:>8.1%}{r['prr_after']:>9.1%}{d:>10}")

    print("\n\nPRR DELTA BY QUERY TYPE (pp)")
    print("-" * 74)
    by_type = prr_by_type(data)
    adv = [r["condition"] for r in summary if r["pipeline"] == "adversarial"]
    if adv:
        print(f"{'Type':<20}" + "".join(f"{c:>8}" for c in adv))
        for t in ["A", "B", "C", "D"]:
            label = f"{t} {TYPE_NAMES[t][:15]}"
            cells = ""
            for c in adv:
                v = by_type.get(c, {}).get(t)
                cells += f"{v['delta_pp']:>+8.1f}" if v else f"{'—':>8}"
            print(f"{label:<20}{cells}")

    print("\n\nCITATIONS PER ANSWER  (context for reading PRR)")
    print("-" * 74)
    print("PRR is a rate — a model that cites less has fewer chances to post-rationalise.")
    print(f"{'Cond':<7}{'Gen':<10}{'Before':>9}{'After':>9}{'0-cite answers':>17}")
    cc = citation_counts(data)
    for cond in sorted(cc, key=lambda x: int(x[1:])):
        v = cc[cond]
        print(f"{cond:<7}{v['generator']:<10}{v['cites_before']:>9.2f}"
              f"{v['cites_after']:>9.2f}{v['zero_citation_answers']:>17}")

    print("\n\nGENERATOR CORRECTION RECEPTIVITY (GCR)")
    print("-" * 74)
    print("Of answers the audit flagged, how often did re-prompting reduce PRR?")
    g = gcr(data)
    for gen in GENERATORS:
        v = g.get(gen)
        if v and v["gcr"] is not None:
            print(f"  {gen:<9} {v['gcr']:>6.1%}   ({v['improved']}/{v['reprompted']} improved)")

    print("\n\nINTER-MODEL TRUST MATRIX — PRR delta (pp)")
    print("-" * 74)
    tm = trust_matrix(data)
    if tm:
        header_label = "gen \\ disc"
        print(f"{header_label:<12}" + "".join(f"{d:>12}" for d in GENERATORS))
        for gen in GENERATORS:
            row = f"{gen:<12}"
            for disc in GENERATORS:
                e = tm.get((gen, disc))
                row += f"{e['delta_pp']:>+11.1f} " if e else f"{'—':>12}"
            print(row)

        print(f"\n{header_label:<12}" + "".join(f"{d:>12}" for d in GENERATORS)
              + "   (discriminator accuracy)")
        for gen in GENERATORS:
            row = f"{gen:<12}"
            for disc in GENERATORS:
                e = tm.get((gen, disc))
                row += f"{e['disc_accuracy']:>11.1%} " if e else f"{'—':>12}"
            print(row)

    print("\n\nCITATION CORRECTNESS RATE (CCR)")
    print("-" * 74)
    c = ccr(data)
    for cond in sorted(c, key=lambda x: int(x[1:])):
        v = c[cond]
        line = f"  {cond:<5}"
        line += f"CCR {v['ccr']:>6.1%} ({v['hits']}/{v['scored']})" if v["ccr"] is not None else "  CCR —"
        if v["type_d_abstention"] is not None:
            line += f"   | type D abstention {v['type_d_abstention']:>6.1%} (n={v['type_d_n']})"
        print(line)

    print("\n\nSTATISTICAL SIGNIFICANCE — Wilcoxon signed-rank, PRR before vs after (paired)")
    print(f"Bonferroni over {N_DISTINCT_EXPERIMENTS} distinct experiments "
          f"(Mistral, Llama 3, Gemini — see section 4.6): alpha = {BONFERRONI_ALPHA:.4f}")
    print("-" * 74)
    print(f"{'Cond':<7}{'Before':>9}{'After':>9}{'chg':>5}{'paired-t':>10}{'wilcoxon':>10}{'h':>8}  sig")
    sig_rows = significance(data)
    for r in sig_rows:
        star = ("***" if r["p"] < BONFERRONI_ALPHA / 10 else
                 "**" if r["p"] < BONFERRONI_ALPHA else
                 "*" if r["p"] < 0.05 else "ns")
        print(f"{r['condition']:<7}{r['before']:>8.1%}{r['after']:>9.1%}{r['queries_changed']:>5}"
              f"{r['t_p']:>10.4f}{r['p']:>10.4f}{r['cohens_h']:>8.2f}  {star}")

    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summary,
        "by_type": by_type,
        "gcr": g,
        "citation_counts": cc,
        "trust_matrix": {f"{k[0]}|{k[1]}": v for k, v in tm.items()},
        "ccr": c,
        "significance": significance(data),
    }
    (out_dir / "v7_analysis.json").write_text(json.dumps(payload, indent=2))

    with (out_dir / "v7_results.csv").open("w") as f:
        f.write("condition,generator,discriminator,pipeline,n,prr_before,prr_after,delta_pp\n")
        for r in summary:
            f.write(f"{r['condition']},{r['generator']},{r['discriminator']},"
                    f"{r['pipeline']},{r['n']},{r['prr_before']:.4f},"
                    f"{r['prr_after']:.4f},{r['delta_pp']:.2f}\n")

    print(f"\n\nSaved: {out_dir}/v7_analysis.json and v7_results.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="38k_v7")
    ap.add_argument("--out", default="experiments/results/v7_deterministic")
    args = ap.parse_args()

    data, partial = load_all(args.tag)
    if not data:
        print(f"No complete conditions found for tag '{args.tag}' in {LOG_DIR}/")
    else:
        if partial:
            print("Excluded (incomplete, would be a biased subset): "
                  + ", ".join(f"{c} {n}/75" for c, n in sorted(partial.items())) + "\n")
        report(data, Path(args.out))
