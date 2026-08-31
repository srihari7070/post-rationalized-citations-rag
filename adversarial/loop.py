from pipeline.baseline import build_prompt
from audit.chunk_removal import audit_answer, extract_cited_indices, removal_test
from config import SIMILARITY_THRESHOLD

# audit_answer is the default; callers may pass sequential_audit_answer instead


def build_feedback_prompt(query: str, chunks: list[dict], answer: str, pr_indices: list[int]) -> str:
    context = "\n\n".join([f"[{c['index']}] {c['text']}" for c in chunks])
    flagged = ", ".join(f"[{i}]" for i in pr_indices)
    return f"""You previously answered the question below and cited sources {flagged}.
Testing showed that removing those sources did not change your answer — they were not genuinely needed.

Revise your answer. For each flagged citation either:
1. Remove the citation if the source is truly not needed, or
2. Rewrite that specific claim so it genuinely relies on the source.

Only keep citations that are load-bearing — where removing the source would actually change your answer.

Sources:
{context}

Question: {query}

Original answer:
{answer}

Revised answer:"""


def run_adversarial_cycle(
    query:            str,
    chunks:           list[dict],
    answer:           str,
    generate_fn:      callable,
    discriminator_fn: callable,
    embed_fn:         callable,
    threshold:        float = SIMILARITY_THRESHOLD,
    audit_fn:         callable = audit_answer,
) -> dict:
    # Step 1 — audit the original answer (single or sequential removal)
    audit = audit_fn(query, chunks, answer, generate_fn, embed_fn, threshold)
    prr_before = audit["prr"]
    pr_indices = [r["cited_index"] for r in audit["results"] if r["verdict"] == "post_rationalised"]

    # Step 2 — discriminator independently judges each citation
    discriminator_verdicts = []
    for r in audit["results"]:
        chunk_text = next((c["text"] for c in chunks if c["index"] == r["cited_index"]), "")
        disc_prompt = f"""Question: {query}

Answer: {answer}

Cited source [{r['cited_index']}]: {chunk_text}

Is this source genuinely load-bearing for the answer, or could the answer have been given without it?
Respond with exactly one word: GENUINE or POST_RATIONALISED"""
        verdict_raw = discriminator_fn(disc_prompt).strip().upper()
        disc_verdict = "post_rationalised" if "POST" in verdict_raw else "genuine"
        discriminator_verdicts.append({
            "cited_index":       r["cited_index"],
            "discriminator":     disc_verdict,
            "removal_test":      r["verdict"],
            "discriminator_correct": disc_verdict == r["verdict"],
        })

    # Step 3 — re-prompt generator for post-rationalised citations
    revised_answer = answer
    prr_after = prr_before
    revised_audit = audit

    if pr_indices:
        feedback_prompt = build_feedback_prompt(query, chunks, answer, pr_indices)
        revised_answer = generate_fn(feedback_prompt)
        revised_audit = audit_fn(query, chunks, revised_answer, generate_fn, embed_fn, threshold)
        prr_after = revised_audit["prr"]

    disc_correct = [v for v in discriminator_verdicts if v["discriminator_correct"]]
    disc_accuracy = len(disc_correct) / len(discriminator_verdicts) if discriminator_verdicts else 0.0

    return {
        "query":                  query,
        "original_answer":        answer,
        "revised_answer":         revised_answer,
        "chunks":                 chunks,
        "audit_before":           audit,
        "audit_after":            revised_audit,
        "prr_before":             prr_before,
        "prr_after":              prr_after,
        "discriminator_verdicts": discriminator_verdicts,
        "discriminator_accuracy": round(disc_accuracy, 4),
    }
