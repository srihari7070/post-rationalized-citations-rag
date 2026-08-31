"""
Generate baseline answers for all queries using a specified model.
Run this ONCE per model before running experiments, so that both the
baseline condition (C1/C3) and the adversarial condition (C2/C4) start
from identical answers — making the PRR comparison clean.

Usage:
  python3 generate_baselines.py --model gemini --tag 38k
  python3 generate_baselines.py --model mistral --tag 38k

Output:
  experiments/baselines/{model}_{tag}_{timestamp}.jsonl
  Each line: {query_id, tier, query, model, answer, chunks}

Resume:
  Re-run the same command — it picks up from the last saved file automatically.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for pipeline/ etc.
from pipeline.baseline import run_baseline

BASELINES_DIR = Path("experiments/baselines")
BASELINES_DIR.mkdir(parents=True, exist_ok=True)

QUERIES_FILE_DEFAULT = Path("data/queries/eval_queries_v2.json")


def get_generate_fn(model_name: str):
    if model_name == "gemini":
        from models.gemini_client import generate as gemini_gen
        return gemini_gen
    from models.ollama_client import make_generate
    return make_generate(model_name)


def get_resume_path(prefix: str) -> Path | None:
    existing = sorted(BASELINES_DIR.glob(f"{prefix}_*.jsonl"))
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, choices=["gemini", "mistral", "llama3"],
                        help="Which model to generate baselines for")
    parser.add_argument("--tag", default="",
                        help="Tag for the output file, e.g. '38k'")
    parser.add_argument("--no-resume", action="store_true",
                        help="Start fresh, ignore existing baseline file")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only generate for first N queries (for testing)")
    parser.add_argument("--queries-file", default=str(QUERIES_FILE_DEFAULT),
                        help="Path to queries JSON file (default: eval_queries_v2.json)")
    args = parser.parse_args()

    with open(args.queries_file) as f:
        queries = json.load(f)
    if args.limit:
        queries = queries[:args.limit]

    generate_fn = get_generate_fn(args.model)
    prefix = f"{args.model}_{args.tag}" if args.tag else args.model

    resume_path = None if args.no_resume else get_resume_path(prefix)
    done_ids = set()
    if resume_path:
        done_ids = load_done_ids(resume_path)
        if done_ids:
            print(f"Resuming {prefix} — {len(done_ids)} queries already done, skipping.",
                  flush=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = resume_path if done_ids else BASELINES_DIR / f"{prefix}_{timestamp}.jsonl"
    out_file = open(out_path, "a")

    print(f"\nGenerating baselines: {args.model.upper()} | tag={args.tag or '(none)'}", flush=True)
    pending = [q for q in queries if q["id"] not in done_ids]

    bar = tqdm(pending, desc=args.model, unit="query", file=sys.stdout,
               bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")

    for q in bar:
        bar.set_postfix_str(q["id"])
        result = run_baseline(q["query"], generate_fn)
        record = {
            "query_id": q["id"],
            "tier":     q["tier"],
            "query":    q["query"],
            "model":    args.model,
            "answer":   result["answer"],
            "chunks":   result["chunks"],
        }
        out_file.write(json.dumps(record, default=str) + "\n")
        out_file.flush()

    out_file.close()
    print(f"\nBaselines saved → {out_path}", flush=True)
    print(f"Pass to experiments with: --baselines-tag {args.tag}", flush=True)


if __name__ == "__main__":
    main()
