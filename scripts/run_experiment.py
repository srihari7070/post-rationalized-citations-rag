"""
Run all experimental conditions and save results.

Conditions:
  C1 — Gemini    + Baseline
  C2 — Gemini    + Adversarial  (discriminator = Mistral, cross-model)
  C3 — Mistral   + Baseline
  C4 — Mistral   + Adversarial  (discriminator = Gemini, cross-model)
  C5 — Gemini    + Adversarial  (discriminator = Gemini, same-model)
  C6 — Mistral   + Adversarial  (discriminator = Mistral, same-model)

Usage:
  python run_experiment.py --condition C1
  python run_experiment.py --condition all
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for pipeline/ etc.
from models.gemini_client import generate as gemini_gen, embed as gemini_embed
from pipeline.baseline import run_baseline
from adversarial.loop import run_adversarial_cycle
from audit.chunk_removal import audit_answer, sequential_audit_answer
from evaluation.metrics import summarise
from config import GEN_TEMPERATURE

LOG_DIR = Path("experiments/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

BASELINES_DIR = Path("experiments/baselines")

QUERIES_FILE_DEFAULT = Path("data/queries/eval_queries_v2.json")

# Full 3x3 design: three generators, each paired with each discriminator,
# plus one baseline per generator. C1-C6 keep their original meaning so older
# results stay comparable; C7-C12 complete the grid.
#
#            disc:  gemini    mistral   llama3
#  gen gemini        C5        C2        C10
#  gen mistral       C4        C6        C11
#  gen llama3        C9        C12       C8
CONDITIONS = {
    "C1":  {"model": "gemini",  "pipeline": "baseline",    "discriminator": "mistral"},
    "C2":  {"model": "gemini",  "pipeline": "adversarial", "discriminator": "mistral"},
    "C3":  {"model": "mistral", "pipeline": "baseline",    "discriminator": "gemini"},
    "C4":  {"model": "mistral", "pipeline": "adversarial", "discriminator": "gemini"},
    "C5":  {"model": "gemini",  "pipeline": "adversarial", "discriminator": "gemini"},
    "C6":  {"model": "mistral", "pipeline": "adversarial", "discriminator": "mistral"},
    "C7":  {"model": "llama3",  "pipeline": "baseline",    "discriminator": "llama3"},
    "C8":  {"model": "llama3",  "pipeline": "adversarial", "discriminator": "llama3"},
    "C9":  {"model": "llama3",  "pipeline": "adversarial", "discriminator": "gemini"},
    "C10": {"model": "gemini",  "pipeline": "adversarial", "discriminator": "llama3"},
    "C11": {"model": "mistral", "pipeline": "adversarial", "discriminator": "llama3"},
    "C12": {"model": "llama3",  "pipeline": "adversarial", "discriminator": "mistral"},
}

GENERATORS = ["gemini", "mistral", "llama3"]


def get_generate_fn(model_name: str):
    if model_name == "gemini":
        return gemini_gen
    from models.ollama_client import make_generate
    return make_generate(model_name)


def load_baselines(model_name: str, baselines_tag: str) -> dict[str, dict]:
    """Load pre-generated baseline answers keyed by query_id."""
    prefix = f"{model_name}_{baselines_tag}" if baselines_tag else model_name
    existing = sorted(BASELINES_DIR.glob(f"{prefix}_*.jsonl"))
    if not existing:
        raise FileNotFoundError(
            f"No baseline file found for prefix '{prefix}' in {BASELINES_DIR}/\n"
            f"Run: python3 generate_baselines.py --model {model_name} --tag {baselines_tag}"
        )
    path = existing[-1]
    print(f"Loading baselines from {path}", flush=True)
    baselines = {}
    with open(path) as f:
        for line in f:
            rec = json.loads(line)
            baselines[rec["query_id"]] = {"answer": rec["answer"], "chunks": rec["chunks"]}
    return baselines


def get_resume_path(prefix: str) -> Path | None:
    existing = sorted(LOG_DIR.glob(f"{prefix}_*.jsonl"))
    return existing[-1] if existing else None


def load_done_ids(path: Path) -> set[str]:
    done = set()
    with open(path) as f:
        for line in f:
            try:
                done.add(json.loads(line)["query_id"])
            except Exception:
                pass
    return done


def run_condition(condition_id: str, queries: list[dict], tag: str = "",
                  no_resume: bool = False, sequential: bool = False,
                  baselines: dict | None = None) -> list[dict]:
    cfg = CONDITIONS[condition_id]
    model_name = cfg["model"]
    pipeline   = cfg["pipeline"]

    generate_fn = get_generate_fn(model_name)
    discriminator_fn = get_generate_fn(cfg["discriminator"])
    audit_fn = sequential_audit_answer if sequential else audit_answer

    prefix = f"{condition_id}_{tag}" if tag else condition_id

    # Resume: find existing log and skip completed queries
    resume_path = None if no_resume else get_resume_path(prefix)
    done_ids = set()
    if resume_path:
        done_ids = load_done_ids(resume_path)
        if done_ids:
            print(f"\nResuming {prefix} — {len(done_ids)} queries already done, skipping.", flush=True)

    # Open log file for incremental writing (append if resuming)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = resume_path if done_ids else LOG_DIR / f"{prefix}_{timestamp}.jsonl"
    log_file = open(log_path, "a")

    print(f"\n{'='*60}", flush=True)
    print(f"Condition {condition_id}: {model_name.upper()} + {pipeline.upper()}", flush=True)
    print(f"{'='*60}", flush=True)

    pending = [q for q in queries if q["id"] not in done_ids]
    results = []
    bar = tqdm(pending, desc=f"{condition_id}", unit="query", file=sys.stdout,
               bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")

    for q in bar:
        bar.set_postfix_str(f"{q['id']} — {q['query'][:40]}...")

        # Use pre-generated baseline if provided, otherwise generate fresh
        if baselines and q["id"] in baselines:
            baseline = baselines[q["id"]]
        else:
            baseline = run_baseline(q["query"], generate_fn)

        if pipeline == "baseline":
            audit = audit_fn(
                q["query"], baseline["chunks"], baseline["answer"],
                generate_fn, gemini_embed
            )
            result = {
                "query_id":       q["id"],
                "tier":           q["tier"],
                "query":          q["query"],
                "model":          model_name,
                "pipeline":       pipeline,
                "answer":         baseline["answer"],
                "chunks":         baseline["chunks"],
                "prr_before":     audit["prr"],
                "prr_after":      audit["prr"],
                "discriminator_verdicts": [],
                "discriminator_accuracy": 0.0,
                "audit_before":   audit,
            }
        else:
            result = run_adversarial_cycle(
                query=q["query"],
                chunks=baseline["chunks"],
                answer=baseline["answer"],
                generate_fn=generate_fn,
                discriminator_fn=discriminator_fn,
                embed_fn=gemini_embed,
                audit_fn=audit_fn,
            )
            result["query_id"] = q["id"]
            result["tier"]     = q["tier"]
            result["model"]    = model_name
            result["pipeline"] = pipeline

        # Carry query metadata into the log so downstream analysis (CCR,
        # type-stratified PRR) reads one file instead of re-joining the query set.
        result["query_type"]           = q.get("type")
        result["ground_truth_company"] = q.get("ground_truth_company")
        result["ground_truth_id"]      = q.get("ground_truth_id")
        result["discriminator"]        = cfg["discriminator"]
        result["temperature"]          = GEN_TEMPERATURE

        results.append(result)
        log_file.write(json.dumps(result, default=str) + "\n")
        log_file.flush()
        bar.write(f"  {q['id']} PRR: {result['prr_before']:.0%} → {result['prr_after']:.0%}")

    log_file.close()
    print(f"\nResults saved incrementally → {log_path}", flush=True)
    return results


def save_results(condition_id: str, results: list[dict]):
    # Results already saved incrementally during run_condition — this is now a no-op
    pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", default="C1",
                        help="C1, C2, C3, C4, or 'all'")
    parser.add_argument("--limit", type=int, default=None,
                        help="Run only first N queries (for testing)")
    parser.add_argument("--tag", default="",
                        help="Tag appended to log filenames e.g. '38k' → C1_38k_timestamp.jsonl")
    parser.add_argument("--no-resume", action="store_true",
                        help="Start fresh, ignore existing logs for this condition+tag")
    parser.add_argument("--sequential", action="store_true",
                        help="Use sequential (cumulative) chunk removal instead of single")
    parser.add_argument("--baselines-tag", default="",
                        help="Load pre-generated baselines with this tag (e.g. '38k'). "
                             "Run generate_baselines.py first to create them.")
    parser.add_argument("--queries-file", default=str(QUERIES_FILE_DEFAULT),
                        help="Path to queries JSON file (default: eval_queries_v2.json)")
    args = parser.parse_args()

    with open(args.queries_file) as f:
        queries = json.load(f)

    if args.limit:
        queries = queries[:args.limit]

    to_run = list(CONDITIONS.keys()) if args.condition == "all" else [args.condition]

    summaries = []
    for cid in to_run:
        # Load shared baselines if requested (ensures C1/C2 and C3/C4 start from same answers)
        baselines = None
        if args.baselines_tag:
            model_name = CONDITIONS[cid]["model"]
            baselines = load_baselines(model_name, args.baselines_tag)

        results = run_condition(cid, queries, tag=args.tag, no_resume=args.no_resume,
                                sequential=args.sequential, baselines=baselines)
        save_results(cid, results)
        cfg = CONDITIONS[cid]
        summary = summarise(cid, cfg["model"], cfg["pipeline"], results)
        summaries.append(summary)
        print(f"\nSummary — {cid}:")
        print(f"  PRR before:             {summary['prr_before']:.1%}")
        print(f"  PRR after:              {summary['prr_after']:.1%}")
        print(f"  PRR delta:              {summary['prr_delta']:+.1%}")
        print(f"  Discriminator accuracy: {summary['discriminator_accuracy']:.1%}")

    if len(summaries) > 1:
        print("\n" + "="*60)
        print("ALL CONDITIONS SUMMARY")
        print("="*60)
        for s in summaries:
            print(f"  {s['condition']} ({s['model']:8} + {s['pipeline']:12}) "
                  f"PRR {s['prr_before']:.1%} → {s['prr_after']:.1%}  "
                  f"disc_acc {s['discriminator_accuracy']:.1%}")


if __name__ == "__main__":
    main()
