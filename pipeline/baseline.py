from pipeline.retriever import retrieve


def build_prompt(query: str, chunks: list[dict]) -> str:
    context = "\n\n".join([f"[{c['index']}] {c['text']}" for c in chunks])
    return f"""You are a research assistant answering questions about the DACH startup ecosystem.
Answer the question using ONLY the sources provided below.
For every claim you make, cite the source number in square brackets, e.g. [1] or [2].
Only cite a source if it directly supports that specific claim — do not cite sources that are not relevant to the claim.

Sources:
{context}

Question: {query}

Answer:"""


def run_baseline(query: str, generate_fn: callable) -> dict:
    chunks = retrieve(query)
    prompt = build_prompt(query, chunks)
    answer = generate_fn(prompt)
    return {
        "query":  query,
        "chunks": chunks,
        "prompt": prompt,
        "answer": answer,
    }
