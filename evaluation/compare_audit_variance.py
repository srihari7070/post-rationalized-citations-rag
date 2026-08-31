"""
Compare single-run vs 3x-averaged audit results.

The v4 headline puzzle: C3 and C6 start from byte-identical Mistral baseline
answers, yet report PRR-before of 22.1% and 16.0%. If that gap is audit noise,
averaging should collapse it. If it survives, something real is going on.

Usage:
    python evaluation/compare_audit_variance.py
"""
import json
from pathlib import Path

LOGS = Path("experiments/logs")
AVG = Path("experiments/results/v4_audit_averaged")

V4_LOGS = {
    "C1": "C1_38k_v4_20260726_181012.jsonl",
    "C2": "C2_38k_v4_20260726_182541.jsonl",
    "C3": "C3_38k_v4_20260726_185655.jsonl",
    "C4": "C4_38k_v4_20260726_190900.jsonl",
    "C5": "C5_38k_v4_20260726_193742.jsonl",
    "C6": "C6_38k_v4_20260726_201108.jsonl",
}


def load_averaged(condition, n_runs=3):
    path = AVG / f"{condition}_averaged_n{n_runs}.jsonl"
    if not path.exists():
        return None
    return {json.loads(l)["query_id"]: json.loads(l) for l in path.open()}


def load_original(condition):
    return {
        json.loads(l)["query_id"]: json.loads(l)
        for l in (LOGS / V4_LOGS[condition]).open()
    }


def spread_stats(averaged):
    spreads = [
        rnd["similarity_spread"]
        for rec in averaged.values()
        for rnd in rec["audit"]["rounds"]
        if "similarity_spread" in rnd
    ]
    if not spreads:
        return None
    spreads.sort()
    return {
        "n_rounds": len(spreads),
        "mean": sum(spreads) / len(spreads),
        "median": spreads[len(spreads) // 2],
        "max": spreads[-1],
        "over_0.10": sum(1 for s in spreads if s > 0.10) / len(spreads),
    }


def near_threshold(averaged, threshold=0.85, band=0.05):
    """Rounds whose averaged similarity sits close enough to the threshold that
    a single draw could plausibly have landed on the other side."""
    total = borderline = 0
    for rec in averaged.values():
        for rnd in rec["audit"]["rounds"]:
            if "similarity_runs" not in rnd:
                continue
            total += 1
            if abs(rnd["similarity"] - threshold) < band:
                borderline += 1
            elif min(rnd["similarity_runs"]) < threshold <= max(rnd["similarity_runs"]):
                borderline += 1  # runs straddled the threshold outright
    return borderline, total


def main():
    print("=" * 68)
    print("AUDIT VARIANCE — single run vs 3x averaged")
    print("=" * 68)

    rows = []
    for cond in V4_LOGS:
        averaged = load_averaged(cond)
        if averaged is None:
            continue
        original = load_original(cond)
        qids = sorted(averaged)

        orig_prr = sum(original[q]["prr_before"] for q in qids) / len(qids)
        avg_prr = sum(averaged[q]["prr_averaged"] for q in qids) / len(qids)
        flipped = sum(
            1 for q in qids
            if original[q]["prr_before"] != averaged[q]["prr_averaged"]
        )
        rows.append((cond, orig_prr, avg_prr, flipped, len(qids), averaged))

    if not rows:
        print("\nNo averaged results yet. Run scripts/reaudit_averaged.py first.")
        return

    print(f"\n{'Cond':<6} {'Single':>9} {'Averaged':>10} {'Shift':>8} {'Flipped':>10}")
    print("-" * 68)
    for cond, orig, avg, flipped, n, _ in rows:
        print(f"{cond:<6} {orig:>8.1%} {avg:>10.1%} "
              f"{(avg - orig) * 100:>+7.1f}pp {flipped:>6}/{n}")

    print("\n" + "-" * 68)
    print("SIMILARITY SPREAD ACROSS THE 3 RUNS")
    print("-" * 68)
    for cond, *_, averaged in rows:
        s = spread_stats(averaged)
        if s:
            print(f"{cond}: mean {s['mean']:.3f} | median {s['median']:.3f} | "
                  f"max {s['max']:.3f} | {s['over_0.10']:.0%} of rounds spread >0.10")

    print("\n" + "-" * 68)
    print("ROUNDS WHERE A SINGLE DRAW COULD HAVE FLIPPED THE VERDICT")
    print("-" * 68)
    for cond, *_, averaged in rows:
        borderline, total = near_threshold(averaged)
        if total:
            print(f"{cond}: {borderline}/{total} rounds ({borderline/total:.0%}) "
                  f"sit within 0.05 of the threshold or straddle it")

    # The headline question
    by_cond = {r[0]: r for r in rows}
    if "C3" in by_cond and "C6" in by_cond:
        _, c3o, c3a, *_ = by_cond["C3"]
        _, c6o, c6a, *_ = by_cond["C6"]
        gap_before = abs(c3o - c6o) * 100
        gap_after = abs(c3a - c6a) * 100

        print("\n" + "=" * 68)
        print("DID C3 AND C6 CONVERGE?")
        print("=" * 68)
        print(f"  Single run: C3 {c3o:.1%} vs C6 {c6o:.1%}  → gap {gap_before:.1f}pp")
        print(f"  3x average: C3 {c3a:.1%} vs C6 {c6a:.1%}  → gap {gap_after:.1f}pp")
        print()
        if gap_after < gap_before * 0.5:
            print(f"  CONVERGED — gap shrank {gap_before:.1f}pp → {gap_after:.1f}pp.")
            print("  The original difference was largely audit noise. Both conditions")
            print("  start from identical answers, so this is the expected result.")
        elif gap_after < gap_before:
            print(f"  PARTIAL — gap shrank {gap_before:.1f}pp → {gap_after:.1f}pp but")
            print("  did not close. Some noise removed; a residual difference remains")
            print("  that averaging alone does not explain. Consider more runs.")
        else:
            print(f"  DID NOT CONVERGE — gap {gap_before:.1f}pp → {gap_after:.1f}pp.")
            print("  Averaging did not close it. Since both conditions audit identical")
            print("  answers with the same generator, investigate for a systematic")
            print("  difference in the audit path rather than sampling noise.")


if __name__ == "__main__":
    main()
