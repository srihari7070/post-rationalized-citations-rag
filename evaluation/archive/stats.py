"""
Statistical tests on PRR differences between conditions.
z-test for two proportions + effect size (Cohen's h).

ARCHIVED 2026-08-27, never called from anywhere in the codebase. Superseded by
the paired Wilcoxon signed-rank test in evaluation/analyse_v7.py — the
two-proportion z-test here treats before/after PRR as independent proportions,
which is wrong for this design (same 75 queries measured twice, paired data).
Kept for the record, not the live analysis path.
"""

import math
from scipy import stats


def z_test_proportions(p1: float, n1: int, p2: float, n2: int) -> dict:
    """Two-proportion z-test. p1/p2 are PRRs, n1/n2 are total cited chunks."""
    p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return {"z": 0.0, "p_value": 1.0, "cohen_h": 0.0}
    z = (p1 - p2) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    cohen_h = 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))
    return {
        "z":        round(z, 4),
        "p_value":  round(p_value, 4),
        "cohen_h":  round(cohen_h, 4),
    }


def compare_conditions(summary_a: dict, summary_b: dict, n_citations: int) -> dict:
    """Compare PRR between two conditions."""
    return {
        "condition_a": summary_a["condition"],
        "condition_b": summary_b["condition"],
        "prr_a":       summary_a["prr_before"],
        "prr_b":       summary_b["prr_before"],
        **z_test_proportions(
            summary_a["prr_before"], n_citations,
            summary_b["prr_before"], n_citations,
        ),
    }
