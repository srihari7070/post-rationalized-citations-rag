"""
Merge per-condition JSONL logs into a single 50-question results table.

Reads the latest log file for each condition+tag combination and produces:
  - experiments/results_{tag}.csv   — full table, one row per query
  - experiments/results_{tag}.md    — markdown table for thesis

Usage:
  python3 evaluation/build_results_table.py --tag 38k_v2
  python3 evaluation/build_results_table.py --tag 38k_v2 --conditions C1 C2 C3 C4
"""

import argparse
import json
import csv
from pathlib import Path

LOG_DIR     = Path("experiments/logs")
RESULTS_DIR = Path("experiments")

CONDITIONS = ["C1", "C2", "C3", "C4", "C5", "C6"]


def latest_log(condition: str, tag: str) -> Path | None:
    prefix = f"{condition}_{tag}" if tag else condition
    files = sorted(LOG_DIR.glob(f"{prefix}_*.jsonl"))
    return files[-1] if files else None


def load_log(path: Path) -> dict[str, dict]:
    """Returns {query_id: record}"""
    records = {}
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
                records[r["query_id"]] = r
            except Exception:
                pass
    return records


def build_table(tag: str, conditions: list[str]) -> list[dict]:
    # Load all available condition logs
    logs = {}
    for cid in conditions:
        path = latest_log(cid, tag)
        if path:
            logs[cid] = load_log(path)
            print(f"  {cid}: loaded {len(logs[cid])} queries from {path.name}")
        else:
            print(f"  {cid}: no log found for tag '{tag}' — skipping")

    if not logs:
        print("No logs found. Run experiments first.")
        return []

    # Get all query IDs from the first available log
    first_log = next(iter(logs.values()))
    query_ids = sorted(first_log.keys())

    rows = []
    for qid in query_ids:
        # Get query metadata from first available condition
        meta = next((logs[c][qid] for c in conditions if c in logs and qid in logs[c]), None)
        if not meta:
            continue

        row = {
            "query_id": qid,
            "tier":     meta.get("tier", ""),
            "query":    meta.get("query", ""),
        }

        for cid in conditions:
            if cid not in logs or qid not in logs[cid]:
                row[f"{cid}_prr_before"] = ""
                row[f"{cid}_prr_after"]  = ""
                row[f"{cid}_disc_acc"]   = ""
                continue

            r = logs[cid][qid]
            pipeline = r.get("pipeline", "baseline")

            row[f"{cid}_prr_before"] = f"{r['prr_before']:.0%}"
            row[f"{cid}_prr_after"]  = f"{r['prr_after']:.0%}"
            if pipeline == "baseline":
                row[f"{cid}_disc_acc"] = "—"
            else:
                row[f"{cid}_disc_acc"] = f"{r.get('discriminator_accuracy', 0):.0%}"

        rows.append(row)

    return rows


def write_csv(rows: list[dict], path: Path):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV saved → {path}")


def write_markdown(rows: list[dict], conditions: list[str], path: Path):
    if not rows:
        return

    # Build header
    header = ["Query", "Tier"]
    for cid in conditions:
        header += [f"{cid} before", f"{cid} after", f"{cid} disc"]

    lines = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")

    for row in rows:
        cells = [row["query_id"], row["tier"]]
        for cid in conditions:
            cells += [
                row.get(f"{cid}_prr_before", ""),
                row.get(f"{cid}_prr_after", ""),
                row.get(f"{cid}_disc_acc", ""),
            ]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")

    with open(path, "w") as f:
        f.write(f"# Results Table — tag: {path.stem}\n\n")
        f.write("\n".join(lines))
        f.write("\n\n")

        # Summary row
        f.write("## Averages\n\n")
        avg_header = ["Condition", "Avg PRR before", "Avg PRR after", "Avg delta", "Avg disc acc"]
        f.write("| " + " | ".join(avg_header) + " |\n")
        f.write("|---|---|---|---|---|\n")
        for cid in conditions:
            befores = [float(r[f"{cid}_prr_before"].strip("%")) / 100
                       for r in rows if r.get(f"{cid}_prr_before") not in ("", None)]
            afters  = [float(r[f"{cid}_prr_after"].strip("%")) / 100
                       for r in rows if r.get(f"{cid}_prr_after") not in ("", None)]
            discs   = [float(r[f"{cid}_disc_acc"].strip("%")) / 100
                       for r in rows if r.get(f"{cid}_disc_acc") not in ("", "—", None)]
            if not befores:
                continue
            avg_b = sum(befores) / len(befores)
            avg_a = sum(afters) / len(afters)
            avg_d = avg_a - avg_b
            avg_disc = (sum(discs) / len(discs)) if discs else None
            disc_str = f"{avg_disc:.1%}" if avg_disc is not None else "—"
            f.write(f"| {cid} | {avg_b:.1%} | {avg_a:.1%} | {avg_d:+.1%} | {disc_str} |\n")

    print(f"Markdown saved → {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True, help="Log tag, e.g. '38k_v2'")
    parser.add_argument("--conditions", nargs="+", default=CONDITIONS,
                        help="Which conditions to include (default: all)")
    args = parser.parse_args()

    print(f"\nBuilding results table for tag='{args.tag}'")
    print(f"Conditions: {args.conditions}\n")

    rows = build_table(args.tag, args.conditions)
    if not rows:
        return

    csv_path = RESULTS_DIR / f"results_{args.tag}.csv"
    md_path  = RESULTS_DIR / f"results_{args.tag}.md"

    write_csv(rows, csv_path)
    write_markdown(rows, args.conditions, md_path)

    print(f"\nTotal queries: {len(rows)}")


if __name__ == "__main__":
    main()
