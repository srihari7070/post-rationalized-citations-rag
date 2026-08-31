"""
Compute PRR, discriminator accuracy, and secondary metrics
from a list of experiment result dicts.
"""

from collections import defaultdict


def compute_prr(results: list[dict]) -> float:
    """Mean PRR across all queries."""
    if not results:
        return 0.0
    return round(sum(r["prr_before"] for r in results) / len(results), 4)


def compute_prr_after(results: list[dict]) -> float:
    if not results:
        return 0.0
    return round(sum(r["prr_after"] for r in results) / len(results), 4)


def compute_discriminator_accuracy(results: list[dict]) -> float:
    all_verdicts = [v for r in results for v in r.get("discriminator_verdicts", [])]
    if not all_verdicts:
        return 0.0
    correct = sum(1 for v in all_verdicts if v["discriminator_correct"])
    return round(correct / len(all_verdicts), 4)


def confusion_matrix(results: list[dict]) -> dict:
    """2x2: discriminator verdict vs removal-test ground truth."""
    counts = defaultdict(int)
    for r in results:
        for v in r.get("discriminator_verdicts", []):
            key = (v["discriminator"], v["removal_test"])
            counts[key] += 1
    return {
        "TP": counts[("post_rationalised", "post_rationalised")],
        "TN": counts[("genuine", "genuine")],
        "FP": counts[("post_rationalised", "genuine")],
        "FN": counts[("genuine", "post_rationalised")],
    }


def summarise(condition_id: str, model: str, pipeline: str, results: list[dict]) -> dict:
    cm = confusion_matrix(results)
    return {
        "condition":              condition_id,
        "model":                  model,
        "pipeline":               pipeline,
        "n_queries":              len(results),
        "prr_before":             compute_prr(results),
        "prr_after":              compute_prr_after(results),
        "prr_delta":              round(compute_prr_after(results) - compute_prr(results), 4),
        "discriminator_accuracy": compute_discriminator_accuracy(results),
        "confusion_matrix":       cm,
    }
