#!/bin/bash
# Run all 6 conditions for v4 scientific queries.
# Resumes any partially-completed condition automatically.
# Log written to experiments/logs/run_v4_all_conditions.log

set -e
cd "$(dirname "$0")/.."   # repo root (this script lives in scripts/)
source .venv/bin/activate

LOG="experiments/logs/run_v4_all_conditions.log"
mkdir -p experiments/logs

echo "=== v4 run started $(date) ===" | tee -a "$LOG"

for COND in C1 C2 C3 C4 C5 C6; do
    echo "" | tee -a "$LOG"
    echo ">>> Starting $COND at $(date)" | tee -a "$LOG"
    python3 scripts/run_experiment.py \
        --condition "$COND" \
        --tag 38k_v4 \
        --sequential \
        --baselines-tag 38k_v4 \
        --queries-file data/queries/eval_queries_v3.json \
        2>&1 | tee -a "$LOG"
    echo "<<< Finished $COND at $(date)" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "=== ALL CONDITIONS COMPLETE $(date) ===" | tee -a "$LOG"
