"""
Per-query results table — 75 rows x 12 conditions.

analyse_v7.py aggregates by condition, which answers "does the loop work?" but hides
*which queries* drive the effect. This pivots the same data by query so you can see
which questions are hard for every model, which respond to correction, and which
resist it regardless of generator.

Outputs:
  v7_per_query.csv   full table, one row per query
  v7_per_query.md    readable summary for the thesis results chapter

    python evaluation/build_query_table.py
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

LOG_DIR = Path("experiments/logs")

ADVERSARIAL = ["C2", "C4", "C5", "C6", "C8", "C9", "C10", "C11", "C12"]
BASELINE = ["C1", "C3", "C7"]
ORDER = BASELINE + ADVERSARIAL

TYPE_NAMES = {"A": "Answerable", "B": "Broad/Ambiguous",
              "C": "Hard/Paraphrased", "D": "Unanswerable"}


def load(tag, min_n=75):
    data = {}
    for i in range(1, 13):
        cond = f"C{i}"
        files = sorted(LOG_DIR.glob(f"{cond}_{tag}_*.jsonl"))
        if not files:
            continue
        recs = [json.loads(l) for l in files[-1].open()]
        if len(recs) >= min_n:
            data[cond] = {r["query_id"]: r for r in recs}
    return data


def build_rows(data):
    qids = sorted(set().union(*[set(v) for v in data.values()]))
    rows = []
    for qid in qids:
        src = next(d[qid] for d in data.values() if qid in d)
        row = {
            "query_id": qid,
            "type": src.get("query_type"),
            "tier": src.get("tier"),
            "ground_truth": src.get("ground_truth_company"),
            "query": src.get("query", "")[:120],
        }
        for cond in ORDER:
            if cond not in data or qid not in data[cond]:
                row[f"{cond}_before"] = row[f"{cond}_after"] = None
                continue
            r = data[cond][qid]
            row[f"{cond}_before"] = r["prr_before"]
            row[f"{cond}_after"] = r["prr_after"]
        rows.append(row)
    return rows


def summarise(rows):
    """Per-query behaviour aggregated across generators.

    Uses one representative condition per generator, since replicates within a
    generator are identical (the discriminator is inert) — averaging all nine
    adversarial conditions would triple-count each generator.
    """
    reps = {"gemini": "C2", "mistral": "C4", "llama3": "C8"}
    out = []
    for row in rows:
        befores = [row[f"{c}_before"] for c in reps.values()
                   if row.get(f"{c}_before") is not None]
        deltas = [row[f"{c}_after"] - row[f"{c}_before"] for c in reps.values()
                  if row.get(f"{c}_before") is not None]
        if not befores:
            continue
        out.append({
            **{k: row[k] for k in ("query_id", "type", "tier", "ground_truth", "query")},
            "mean_prr_before": sum(befores) / len(befores),
            "mean_delta": sum(deltas) / len(deltas),
            "n_conditions_flagged": sum(1 for b in befores if b > 0),
            "n_conditions_improved": sum(1 for d in deltas if d < 0),
            **{f"{g}_before": row[f"{c}_before"] for g, c in reps.items()},
            **{f"{g}_delta": row[f"{c}_after"] - row[f"{c}_before"]
               for g, c in reps.items() if row.get(f"{c}_before") is not None},
        })
    return out


def write_csv(rows, path):
    if not rows:
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def write_markdown(summary, path):
    lines = [
        "# Per-Query Results — v7 (temperature 0, 75 queries)",
        "",
        "PRR per query, using one representative condition per generator "
        "(C2 Gemini, C4 Mistral, C8 Llama 3).",
        "Replicates within a generator are identical because the discriminator is inert, "
        "so averaging all nine adversarial conditions would triple-count each generator.",
        "",
        "`before` = PRR before correction · `Δ` = change after correction (pp)",
        "",
        "| Query | Type | Tier | Gemini before | Gemini Δ | Mistral before | Mistral Δ | "
        "Llama3 before | Llama3 Δ |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary:
        def fmt(g, k):
            v = r.get(f"{g}_{k}")
            if v is None:
                return "—"
            return f"{v:.0%}" if k == "before" else f"{v*100:+.0f}"
        lines.append(
            f"| {r['query_id']} | {r['type']} | {r['tier'].replace('-fact','')} | "
            f"{fmt('gemini','before')} | {fmt('gemini','delta')} | "
            f"{fmt('mistral','before')} | {fmt('mistral','delta')} | "
            f"{fmt('llama3','before')} | {fmt('llama3','delta')} |"
        )

    # Queries hard for everyone
    universal = [r for r in summary if r["n_conditions_flagged"] == 3]
    resistant = [r for r in universal if r["n_conditions_improved"] == 0]
    fixable = [r for r in universal if r["n_conditions_improved"] == 3]

    lines += [
        "",
        "---",
        "",
        "## Queries flagged by all three generators",
        "",
        f"**{len(universal)} of {len(summary)} queries** show post-rationalisation in every "
        "generator. These are properties of the query and its retrieved chunks, not of any "
        "one model.",
        "",
    ]
    if resistant:
        lines += [
            f"### Resistant — flagged by all, fixed by none ({len(resistant)})",
            "",
            "The correction loop fails on these regardless of generator.",
            "",
            "| Query | Type | Ground truth | Mean PRR |",
            "|---|---|---|---:|",
        ]
        for r in sorted(resistant, key=lambda x: -x["mean_prr_before"])[:15]:
            gt = (r["ground_truth"] or "—")[:40]
            lines.append(f"| {r['query_id']} | {r['type']} | {gt} | "
                         f"{r['mean_prr_before']:.0%} |")
        lines.append("")
    if fixable:
        lines += [
            f"### Correctable — flagged by all, fixed by all ({len(fixable)})",
            "",
            "| Query | Type | Ground truth | Mean PRR | Mean Δ |",
            "|---|---|---|---:|---:|",
        ]
        for r in sorted(fixable, key=lambda x: x["mean_delta"])[:15]:
            gt = (r["ground_truth"] or "—")[:40]
            lines.append(f"| {r['query_id']} | {r['type']} | {gt} | "
                         f"{r['mean_prr_before']:.0%} | {r['mean_delta']*100:+.0f}pp |")
        lines.append("")

    # By type
    by_type = defaultdict(list)
    for r in summary:
        by_type[r["type"]].append(r)
    lines += [
        "---",
        "",
        "## By query type",
        "",
        "| Type | n | Mean PRR before | Mean Δ | Flagged by all 3 | Never flagged |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for t in sorted(by_type):
        rs = by_type[t]
        lines.append(
            f"| {t} {TYPE_NAMES.get(t,'')} | {len(rs)} | "
            f"{sum(x['mean_prr_before'] for x in rs)/len(rs):.1%} | "
            f"{sum(x['mean_delta'] for x in rs)/len(rs)*100:+.1f}pp | "
            f"{sum(1 for x in rs if x['n_conditions_flagged']==3)} | "
            f"{sum(1 for x in rs if x['n_conditions_flagged']==0)} |"
        )

    path.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="38k_v7")
    ap.add_argument("--out", default="experiments/results/v7_deterministic")
    args = ap.parse_args()

    data = load(args.tag)
    if not data:
        print(f"No complete conditions for tag '{args.tag}'")
        return

    rows = build_rows(data)
    summary = summarise(rows)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    write_csv(rows, out / "v7_per_query.csv")
    write_csv(summary, out / "v7_per_query_summary.csv")
    write_markdown(summary, out / "v7_per_query.md")

    universal = [r for r in summary if r["n_conditions_flagged"] == 3]
    resistant = [r for r in universal if r["n_conditions_improved"] == 0]
    never = [r for r in summary if r["n_conditions_flagged"] == 0]

    print(f"{len(rows)} queries x {len(data)} conditions")
    print(f"  flagged by all 3 generators : {len(universal)}")
    print(f"    of those, fixed by none   : {len(resistant)}")
    print(f"  never flagged by any        : {len(never)}")
    print(f"\nWrote {out}/v7_per_query.csv, v7_per_query_summary.csv, v7_per_query.md")


if __name__ == "__main__":
    main()
