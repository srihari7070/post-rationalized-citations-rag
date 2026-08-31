"""
Threshold sensitivity — does the 0.85 cutoff drive the conclusions?

0.85 is a methodological choice, not an empirically calibrated value. The obvious
challenge is that the results are an artifact of where the line was drawn. This
re-applies the verdict rule at other thresholds using the similarity scores already
stored in the logs — no regeneration, no API calls, runs in seconds.

Verdict rule being re-applied (sequential audit):
  similarity >= threshold  -> chunk not needed  -> post_rationalised
  similarity <  threshold  -> chunk was needed  -> genuine, stop

    python evaluation/threshold_sensitivity.py
    python evaluation/threshold_sensitivity.py --thresholds 0.75,0.80,0.85,0.90,0.95
"""
import argparse
import json
from pathlib import Path

LOG_DIR = Path("experiments/logs")


def prr_at(audit, threshold):
    """Recompute PRR from stored rounds at a different threshold.

    Mirrors sequential_audit_answer: walk the rounds in order, stop at the first
    round whose similarity falls below the threshold. Chunks removed before that
    point were not needed; the rest get the benefit of the doubt.
    """
    cited = audit.get("cited") or []
    if not cited:
        return 0.0

    rounds = audit.get("rounds") or []
    first_change = None
    for i, rnd in enumerate(rounds):
        if rnd.get("similarity", 1.0) < threshold:
            first_change = i
            break

    # No round dropped below the threshold -> nothing was load-bearing.
    # Only valid if every cited chunk was actually tested; otherwise the untested
    # tail keeps the benefit of the doubt.
    if first_change is None:
        n_post = len(cited) if len(rounds) >= len(cited) else len(rounds)
    else:
        n_post = first_change

    return n_post / len(cited)


def load(tag, min_n=75):
    data, partial = {}, {}
    for i in range(1, 13):
        cond = f"C{i}"
        files = sorted(LOG_DIR.glob(f"{cond}_{tag}_*.jsonl"))
        if not files:
            continue
        recs = [json.loads(l) for l in files[-1].open()]
        (data if len(recs) >= min_n else partial)[cond] = recs
    return data, partial


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="38k_v7")
    ap.add_argument("--thresholds", default="0.75,0.80,0.85,0.90,0.95")
    ap.add_argument("--out", default="experiments/results/v7_deterministic")
    args = ap.parse_args()

    thresholds = [float(t) for t in args.thresholds.split(",")]
    data, partial = load(args.tag)

    if not data:
        print(f"No complete conditions for tag '{args.tag}'")
        return
    if partial:
        print("Excluded (incomplete): "
              + ", ".join(f"{c} {len(r)}/75" for c, r in sorted(partial.items())) + "\n")

    print("=" * 78)
    print("THRESHOLD SENSITIVITY — PRR recomputed from stored similarity scores")
    print("=" * 78)
    print("\nPRR BEFORE at each threshold")
    print("-" * 78)
    print(f"{'Cond':<6}{'Gen':<9}" + "".join(f"{t:>9.2f}" for t in thresholds))

    results = {}
    for cond in sorted(data, key=lambda c: int(c[1:])):
        recs = data[cond]
        gen = recs[0].get("model", "?")
        row = {}
        for t in thresholds:
            vals = [prr_at(r.get("audit_before") or {}, t) for r in recs]
            row[t] = sum(vals) / len(vals)
        results[cond] = {"generator": gen, "prr_before": row}
        print(f"{cond:<6}{gen:<9}" + "".join(f"{row[t]:>8.1%}" for t in thresholds))

    # Deltas for adversarial conditions
    print("\n\nPRR DELTA (after - before) at each threshold")
    print("-" * 78)
    print("Does the correction loop still work if the threshold moves?")
    print(f"{'Cond':<6}{'Gen':<9}" + "".join(f"{t:>9.2f}" for t in thresholds))

    for cond in sorted(data, key=lambda c: int(c[1:])):
        recs = data[cond]
        if recs[0].get("pipeline") != "adversarial":
            continue
        gen = recs[0].get("model", "?")
        row = {}
        for t in thresholds:
            b = [prr_at(r.get("audit_before") or {}, t) for r in recs]
            a = [prr_at(r.get("audit_after") or r.get("audit_before") or {}, t)
                 for r in recs]
            row[t] = (sum(a) / len(a) - sum(b) / len(b)) * 100
        results[cond]["delta_pp"] = row
        print(f"{cond:<6}{gen:<9}" + "".join(f"{row[t]:>+8.1f}" for t in thresholds))

    # Verdict
    print("\n" + "=" * 78)
    print("READING")
    print("=" * 78)
    adv = [c for c in results if "delta_pp" in results[c]]
    if adv:
        stable = []
        for c in adv:
            vals = list(results[c]["delta_pp"].values())
            sign_consistent = all(v <= 0 for v in vals) or all(v >= 0 for v in vals)
            spread = max(vals) - min(vals)
            stable.append((c, sign_consistent, spread, vals))

        for c, consistent, spread, vals in stable:
            base = results[c]["delta_pp"].get(0.85, 0)
            verdict = "direction holds" if consistent else "SIGN FLIPS"
            print(f"  {c}: at 0.85 = {base:+.1f}pp | range {min(vals):+.1f} to "
                  f"{max(vals):+.1f}pp | {verdict}")

        n_flip = sum(1 for _, c, _, _ in stable if not c)
        print()
        if n_flip == 0:
            print("  No condition changes the sign of its effect across the tested range.")
            print("  The conclusions are not an artifact of the 0.85 cutoff.")
        else:
            print(f"  {n_flip} condition(s) change sign — those results ARE "
                  f"threshold-dependent")
            print("  and must be reported with that caveat.")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "threshold_sensitivity.json").write_text(json.dumps(
        {"thresholds": thresholds, "results": results}, indent=2))
    print(f"\nSaved: {out}/threshold_sensitivity.json")


if __name__ == "__main__":
    main()
