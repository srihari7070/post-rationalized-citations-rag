import re
from pipeline.baseline import build_prompt
from audit.similarity import response_similarity
from config import SIMILARITY_THRESHOLD


def extract_cited_indices(answer: str) -> list[int]:
    return sorted(set(int(m) for m in re.findall(r'\[(\d+)\]', answer)))


def sequential_audit_answer(
    query:       str,
    chunks:      list[dict],
    answer:      str,
    generate_fn: callable,
    embed_fn:    callable,
    threshold:   float = SIMILARITY_THRESHOLD,
    n_runs:      int = 1,
) -> dict:
    """
    Cumulative chunk removal: remove cited chunks one by one in order
    ({c1}, {c1,c2}, {c1,c2,c3}, ...) and stop as soon as the answer changes.

    Verdict logic:
    - Chunks removed BEFORE the first change → post_rationalised (redundant)
    - The chunk whose removal CAUSED the change → genuine (load-bearing)
    - Chunks not yet tested (stopped early) → genuine (benefit of the doubt)
    - If answer never changes after removing all cited chunks → all post_rationalised

    n_runs > 1 regenerates each removal round n_runs times and averages the
    similarity before thresholding. Generators sample stochastically, so a single
    regeneration can land either side of the threshold by chance and flip a verdict.
    """
    cited = extract_cited_indices(answer)
    if not cited:
        return {"cited": [], "results": [], "rounds": [], "prr": 0.0,
                "first_change_round": None}

    rounds = []
    removed_so_far = []
    first_change_round = None  # 0-indexed position in cited list

    for i, idx in enumerate(cited):
        removed_so_far.append(idx)
        reduced = [c for c in chunks if c["index"] not in removed_so_far]

        if not reduced:
            rounds.append({
                "round": i + 1,
                "removed_set": list(removed_so_far),
                "similarity": 0.0,
                "changed": True,
            })
            if first_change_round is None:
                first_change_round = i
            break

        renumbered = [{**c, "index": j + 1} for j, c in enumerate(reduced)]
        prompt = build_prompt(query, renumbered)

        new_answers = [generate_fn(prompt) for _ in range(n_runs)]
        sims = [response_similarity(answer, a, embed_fn) for a in new_answers]
        similarity = sum(sims) / len(sims)
        changed = similarity < threshold

        round_record = {
            "round": i + 1,
            "removed_set": list(removed_so_far),
            "new_answer": new_answers[0],
            "similarity": round(similarity, 4),
            "changed": changed,
        }
        if n_runs > 1:
            round_record["similarity_runs"] = [round(s, 4) for s in sims]
            round_record["similarity_spread"] = round(max(sims) - min(sims), 4)
        rounds.append(round_record)

        if changed:
            first_change_round = i
            break

    # Build per-chunk verdicts (compatible with audit_answer result structure)
    results = []
    for i, idx in enumerate(cited):
        if first_change_round is None:
            verdict = "post_rationalised"
        elif i < first_change_round:
            verdict = "post_rationalised"
        elif i == first_change_round:
            verdict = "genuine"
        else:
            verdict = "genuine"  # not reached; stopped early
        results.append({"cited_index": idx, "verdict": verdict})

    post_count = sum(1 for r in results if r["verdict"] == "post_rationalised")
    prr = round(post_count / len(cited), 4) if cited else 0.0

    return {
        "cited":              cited,
        "results":            results,
        "rounds":             rounds,
        "first_change_round": first_change_round,
        "prr":                prr,
    }


def removal_test(
    query:         str,
    chunks:        list[dict],
    answer:        str,
    cited_index:   int,
    generate_fn:   callable,
    embed_fn:      callable,
    threshold:     float = SIMILARITY_THRESHOLD,
) -> dict:
    reduced = [c for c in chunks if c["index"] != cited_index]

    if not reduced:
        return {
            "cited_index":   cited_index,
            "similarity":    1.0,
            "verdict":       "post_rationalised",
            "new_answer":    answer,
        }

    # Re-index after removal so prompt numbering stays clean
    renumbered = [{**c, "index": i + 1} for i, c in enumerate(reduced)]
    new_answer = generate_fn(build_prompt(query, renumbered))
    similarity = response_similarity(answer, new_answer, embed_fn)
    verdict = "post_rationalised" if similarity >= threshold else "genuine"

    return {
        "cited_index": cited_index,
        "new_answer":  new_answer,
        "similarity":  round(similarity, 4),
        "verdict":     verdict,
    }


def audit_answer(
    query:       str,
    chunks:      list[dict],
    answer:      str,
    generate_fn: callable,
    embed_fn:    callable,
    threshold:   float = SIMILARITY_THRESHOLD,
) -> dict:
    cited = extract_cited_indices(answer)
    if not cited:
        return {"cited": [], "results": [], "prr": 0.0}

    results = [
        removal_test(query, chunks, answer, idx, generate_fn, embed_fn, threshold)
        for idx in cited
    ]
    post_rationalised = [r for r in results if r["verdict"] == "post_rationalised"]
    prr = len(post_rationalised) / len(cited)

    return {
        "cited":   cited,
        "results": results,
        "prr":     round(prr, 4),
    }
