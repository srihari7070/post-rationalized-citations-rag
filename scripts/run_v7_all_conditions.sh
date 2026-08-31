#!/usr/bin/env bash
# v7 — deterministic re-run at temperature 0, full 3x3 condition grid.
#
# Supersedes v4. Every prior PRR figure was measured under uncontrolled sampling
# (Gemini temp 1.0, Ollama 0.8), which let random wording decide roughly half of
# all verdicts near the 0.85 threshold. See MEETING_NOTES.md, "Audit Determinism".
#
# Usage:  ./run_v7_all_conditions.sh
# Safe to re-run: every step resumes from its last completed query.

set -euo pipefail
cd "$(dirname "$0")/.."   # repo root (this script lives in scripts/)

TAG="38k_v7"
QUERIES="data/queries/eval_queries_v3.json"

echo "=============================================="
echo "v7 — deterministic run (temperature 0)"
echo "tag: $TAG   queries: $QUERIES"
echo "started: $(date)"
echo "=============================================="

# Baselines: one shared set per generator, so every condition using that
# generator starts from identical answers and the only variable is the pipeline.
for MODEL in gemini mistral llama3; do
  echo ""
  echo ">>> baselines: $MODEL"
  python3 scripts/generate_baselines.py --model "$MODEL" --tag "$TAG" --queries-file "$QUERIES"
done

# All 12 conditions. --sequential uses cumulative chunk removal.
for C in C1 C2 C3 C4 C5 C6 C7 C8 C9 C10 C11 C12; do
  echo ""
  echo ">>> condition: $C"
  python3 scripts/run_experiment.py \
    --condition "$C" \
    --tag "$TAG" \
    --sequential \
    --baselines-tag "$TAG" \
    --queries-file "$QUERIES"
done

echo ""
echo "=============================================="
echo "v7 complete: $(date)"
echo "logs: experiments/logs/C*_${TAG}_*.jsonl"
echo "=============================================="
