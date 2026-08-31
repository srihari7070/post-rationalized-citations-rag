"""
Re-run the chunk removal audit on stored answers with n_runs averaging.

The audit regenerates answers via the generator, which samples stochastically.
A single regeneration can land either side of the 0.85 threshold by chance,
flipping a verdict. This re-audits stored answers with averaged similarity.

Usage:
    python reaudit_averaged.py --condition C3 --n-runs 3
    python reaudit_averaged.py --condition all --n-runs 3
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for audit/ etc.
from audit.chunk_removal import sequential_audit_answer
from models.gemini_client import generate as gemini_generate, embed as gemini_embed
from models.ollama_client import generate as ollama_generate

LOGS = Path("experiments/logs")
OUT = Path("experiments/results/v4_audit_averaged")

V4_LOGS = {
    "C1": "C1_38k_v4_20260726_181012.jsonl",
    "C2": "C2_38k_v4_20260726_182541.jsonl",
    "C3": "C3_38k_v4_20260726_185655.jsonl",
    "C4": "C4_38k_v4_20260726_190900.jsonl",
    "C5": "C5_38k_v4_20260726_193742.jsonl",
    "C6": "C6_38k_v4_20260726_201108.jsonl",
}

GENERATOR = {
    "C1": "gemini", "C2": "gemini", "C5": "gemini",
    "C3": "mistral", "C4": "mistral", "C6": "mistral",
}


def answer_of(record):
    return record.get("answer") or record["original_answer"]


def reaudit(condition, n_runs):
    generate_fn = gemini_generate if GENERATOR[condition] == "gemini" else ollama_generate

    src = LOGS / V4_LOGS[condition]
    records = [json.loads(line) for line in src.open()]

    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"{condition}_averaged_n{n_runs}.jsonl"

    done = set()
    if dst.exists():
        done = {json.loads(line)["query_id"] for line in dst.open()}
        print(f"  resuming — {len(done)} already done")

    started = time.time()
    with dst.open("a") as out:
        for i, rec in enumerate(records, 1):
            qid = rec["query_id"]
            if qid in done:
                continue

            audit = sequential_audit_answer(
                query=rec["query"],
                chunks=rec["chunks"],
                answer=answer_of(rec),
                generate_fn=generate_fn,
                embed_fn=gemini_embed,
                n_runs=n_runs,
            )

            out.write(json.dumps({
                "query_id": qid,
                "tier": rec["tier"],
                "prr_original": rec["prr_before"],
                "prr_averaged": audit["prr"],
                "audit": audit,
            }) + "\n")
            out.flush()

            elapsed = time.time() - started
            print(f"  [{i}/{len(records)}] {qid}  "
                  f"PRR {rec['prr_before']:.0%} → {audit['prr']:.0%}  "
                  f"({elapsed/60:.1f}m)")

    return dst


def summarise(condition, path):
    rows = [json.loads(line) for line in path.open()]
    orig = sum(r["prr_original"] for r in rows) / len(rows)
    avgd = sum(r["prr_averaged"] for r in rows) / len(rows)
    flipped = sum(1 for r in rows if r["prr_original"] != r["prr_averaged"])

    spreads = [
        rnd["similarity_spread"]
        for r in rows for rnd in r["audit"]["rounds"]
        if "similarity_spread" in rnd
    ]

    print(f"\n{condition}:  PRR {orig:.1%} (single) → {avgd:.1%} (averaged)")
    print(f"  {flipped}/{len(rows)} queries changed verdict")
    if spreads:
        print(f"  similarity spread across runs: "
              f"mean {sum(spreads)/len(spreads):.3f}, max {max(spreads):.3f}")
    return {"condition": condition, "prr_original": orig,
            "prr_averaged": avgd, "queries_flipped": flipped, "n": len(rows)}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--condition", default="all")
    p.add_argument("--n-runs", type=int, default=3)
    args = p.parse_args()

    conditions = list(V4_LOGS) if args.condition == "all" else [args.condition]

    summaries = []
    for c in conditions:
        print(f"\n=== {c} ({GENERATOR[c]}) — {args.n_runs}x averaged audit ===")
        summaries.append(summarise(c, reaudit(c, args.n_runs)))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"summary_n{args.n_runs}.json").write_text(json.dumps(summaries, indent=2))

    print(f"\n{'Cond':<6} {'Single':>9} {'Averaged':>9} {'Flipped':>9}")
    for s in summaries:
        print(f"{s['condition']:<6} {s['prr_original']:>8.1%} "
              f"{s['prr_averaged']:>9.1%} {s['queries_flipped']:>6}/{s['n']}")
